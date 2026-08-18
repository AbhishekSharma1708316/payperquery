"""Orchestrates one agent-buys-an-API purchase end to end.

Flow for POST /market/{path}/call:

  1. Resolve the agent (by API key) and the listing (by path).
  2. Run the pure policy engine BEFORE anything touches money. A blocked
     purchase never reaches the payment step, exactly like AgentVault.
  3. If the request carries no payment proof, issue a signed 402 quote
     naming the platform escrow wallet as payTo (see payments/x402_quote.py).
  4. If it does carry a proof, verify the quote and the on-chain payment
     against the ESCROW WALLET (not the provider) -- this is the step
     that turns "pay and pray" into "pay into escrow". Replay protection
     is a unique index on Transaction.deposit_tx_id.
  5. Only once funds are confirmed HELD in escrow does the platform proxy
     the actual request to the provider's upstream_url.
  6. On a successful upstream response, escrow is released to the
     provider (real payout tx) and the listing's reputation counters move.
     On failure, escrow is refunded back to the agent's own wallet
     address (real payout tx) and the provider's failure counter moves
     instead -- the provider only gets paid for work it actually did.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.agent import Agent, AllowedListing
from app.models.escrow import Escrow, EscrowStatus
from app.models.listing import Listing
from app.models.transaction import Transaction, TransactionStatus
from app.payments import escrow_wallet, x402_quote
from app.payments.algorand_verifier import PaymentVerificationError, verify_payment
from app.policies.policy_engine import PolicyDecision, check_payment_policy
from app.policies.reputation import compute_reputation

logger = logging.getLogger("apimarket.purchase_service")
settings = get_settings()

HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


class PurchaseError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def microalgos_to_usd(amount_microalgos: int) -> Decimal:
    """Marketplace pricing assumes the configured ASA is a USD-pegged
    stablecoin (USDC on Algorand Testnet by default), so 1 micro-unit of
    the asset == $0.000001 for policy-limit purposes."""
    return Decimal(amount_microalgos) / Decimal(1_000_000)


async def _get_agent_by_api_key(db: AsyncSession, api_key: str) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.api_key == api_key).options(selectinload(Agent.policy))
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise PurchaseError(401, "Unknown or invalid agent API key")
    if agent.policy is None:
        raise PurchaseError(409, "Agent has no spending policy configured")
    return agent


async def _get_listing(db: AsyncSession, path: str) -> Listing:
    result = await db.execute(select(Listing).where(Listing.path == path, Listing.is_active.is_(True)))
    listing = result.scalar_one_or_none()
    if listing is None:
        raise PurchaseError(404, f"No active marketplace listing at '{path}'")
    return listing


async def _spent_today(db: AsyncSession, agent_id) -> Decimal:
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount_microalgos), 0)).where(
            Transaction.agent_id == agent_id,
            Transaction.status.in_(
                [TransactionStatus.ESCROW_HELD, TransactionStatus.UPSTREAM_CALLED, TransactionStatus.SERVICE_COMPLETED]
            ),
            Transaction.created_at >= start_of_day,
        )
    )
    return microalgos_to_usd(int(result.scalar_one()))


async def _evaluate_policy(db: AsyncSession, agent: Agent, listing: Listing) -> PolicyDecision:
    policy = agent.policy
    reputation = compute_reputation(
        successful_transactions=listing.successful_transactions,
        failed_transactions=listing.failed_transactions,
        average_latency_ms=listing.average_latency_ms,
        refund_count=listing.refund_count,
        dispute_count=listing.dispute_count,
    )

    provider_is_allowed = True
    if policy.restrict_to_allowed_listings:
        allowed = await db.execute(
            select(AllowedListing).where(
                AllowedListing.policy_id == policy.id, AllowedListing.listing_id == listing.id
            )
        )
        provider_is_allowed = allowed.scalar_one_or_none() is not None

    already_spent_today = await _spent_today(db, agent.id)

    return check_payment_policy(
        agent_is_active=agent.is_active,
        agent_is_paused=agent.is_paused,
        amount=microalgos_to_usd(listing.price_microalgos),
        max_transaction_amount=policy.max_transaction_amount,
        daily_limit=policy.daily_limit,
        already_spent_today=already_spent_today,
        provider_is_allowed=provider_is_allowed,
        provider_is_active=listing.is_active,
        provider_reputation=reputation.score,
        min_provider_reputation=policy.min_provider_reputation,
    )


def build_402_body(listing: Listing) -> tuple[dict, dict]:
    quote_token, expires_at = x402_quote.create_quote(
        listing_path=listing.path,
        price_microalgos=listing.price_microalgos,
        asa_id=listing.asa_id,
    )
    asset_label = f"asa:{listing.asa_id}" if listing.asa_id else "algo:native"
    body = {
        "x402Version": 1,
        "scheme": settings.X402_SCHEME,
        "network": settings.ALGORAND_NETWORK,
        "resource": f"/market/{listing.path}/call",
        "description": f"Escrowed payment required to call '{listing.name}'",
        "payTo": settings.ESCROW_WALLET_ADDRESS,
        "maxAmountRequired": str(listing.price_microalgos),
        "asset": asset_label,
        "quote": quote_token,
        "expiresAt": str(expires_at),
        "note": "payTo is the marketplace's escrow wallet, not the provider. "
                "Funds are held until the API call is proxied and confirmed successful.",
    }
    headers = {
        "X-402-Price": str(listing.price_microalgos),
        "X-402-Recipient": settings.ESCROW_WALLET_ADDRESS,
        "X-402-Network": settings.ALGORAND_NETWORK,
        "X-402-Asset": asset_label,
        "X-402-Quote": quote_token,
    }
    return body, headers


async def start_or_settle_purchase(
    db: AsyncSession,
    *,
    api_key: str,
    listing_path: str,
    idempotency_key: str,
    payment_proof: dict | None,
) -> tuple[Agent, Listing, Transaction | None, dict | None, dict | None]:
    """Returns (agent, listing, transaction_or_None, quote_402_body_or_None, headers_or_None).

    If a Transaction is returned with status ESCROW_HELD, funds are
    confirmed in platform custody and the caller should proceed to proxy
    the upstream request. If quote_402_body is returned instead, no
    Transaction exists yet -- the caller should respond 402 with it.
    """
    agent = await _get_agent_by_api_key(db, api_key)
    listing = await _get_listing(db, listing_path)

    existing = await db.execute(select(Transaction).where(Transaction.idempotency_key == idempotency_key))
    existing_txn = existing.scalar_one_or_none()
    if existing_txn is not None:
        return agent, listing, existing_txn, None, None

    decision = await _evaluate_policy(db, agent, listing)
    if not decision.approved:
        txn = Transaction(
            agent_id=agent.id,
            listing_id=listing.id,
            amount_microalgos=listing.price_microalgos,
            asa_id=listing.asa_id,
            status=TransactionStatus.POLICY_BLOCKED,
            idempotency_key=idempotency_key,
            risk_score=decision.risk_score,
            failure_reason=decision.reason.value if decision.reason else "blocked",
            completed_at=datetime.now(UTC),
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)
        raise PurchaseError(403, f"Purchase blocked by policy: {txn.failure_reason}")

    if payment_proof is None:
        body, headers = build_402_body(listing)
        return agent, listing, None, body, headers

    tx_id = payment_proof.get("tx_id")
    quote_token = payment_proof.get("quote")
    if not tx_id or not quote_token:
        raise PurchaseError(400, "Payment proof must include 'tx_id' and 'quote'")

    try:
        x402_quote.verify_quote(
            quote_token,
            listing_path=listing.path,
            price_microalgos=listing.price_microalgos,
            asa_id=listing.asa_id,
        )
    except x402_quote.QuoteError as exc:
        raise PurchaseError(402, f"Invalid quote: {exc}") from exc

    replay = await db.execute(select(Transaction).where(Transaction.deposit_tx_id == tx_id))
    if replay.scalar_one_or_none() is not None:
        raise PurchaseError(409, f"Transaction {tx_id} has already been used for a purchase (replay)")

    try:
        verified = await verify_payment(
            tx_id=tx_id,
            expected_recipient=settings.ESCROW_WALLET_ADDRESS,
            expected_amount=listing.price_microalgos,
            expected_asa_id=listing.asa_id,
        )
    except PaymentVerificationError as exc:
        raise PurchaseError(402, f"Escrow payment verification failed: {exc}") from exc

    txn = Transaction(
        agent_id=agent.id,
        listing_id=listing.id,
        amount_microalgos=listing.price_microalgos,
        asa_id=listing.asa_id,
        status=TransactionStatus.ESCROW_HELD,
        quote_token=quote_token,
        deposit_tx_id=verified.tx_id,
        payer_address=verified.payer_address,
        idempotency_key=idempotency_key,
        risk_score=decision.risk_score,
    )
    db.add(txn)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise PurchaseError(409, f"Transaction {tx_id} has already been used for a purchase (replay)") from exc
    await db.refresh(txn)

    fee = escrow_wallet.compute_platform_fee_microalgos(txn.amount_microalgos)
    escrow = Escrow(
        transaction_id=txn.id,
        status=EscrowStatus.HELD,
        amount_microalgos=txn.amount_microalgos,
        asa_id=txn.asa_id,
        platform_fee_microalgos=fee,
        deposit_tx_id=verified.tx_id,
    )
    db.add(escrow)
    await db.commit()

    logger.info("Escrow HELD tx=%s deposit=%s amount=%d", txn.id, verified.tx_id, txn.amount_microalgos)
    return agent, listing, txn, None, None


async def fulfil_and_settle(
    db: AsyncSession,
    *,
    transaction: Transaction,
    listing: Listing,
    method: str,
    headers: dict,
    query_params: dict,
    body: bytes | None,
) -> httpx.Response:
    """Proxies the paid-for request to the provider's upstream_url, then
    releases or refunds escrow based on whether it actually succeeded."""
    transaction.status = TransactionStatus.UPSTREAM_CALLED
    await db.commit()

    forward_headers = {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}

    try:
        async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT_SECONDS) as client:
            upstream_response = await client.request(
                method=method, url=listing.upstream_url, headers=forward_headers,
                params=query_params, content=body if body else None,
            )
    except httpx.TimeoutException:
        await _settle_failure(db, transaction, listing, reason="Upstream request timed out")
        raise PurchaseError(504, "Upstream request timed out; your payment has been refunded")
    except httpx.RequestError as exc:
        await _settle_failure(db, transaction, listing, reason=f"Upstream request failed: {exc}")
        raise PurchaseError(502, "Upstream request failed; your payment has been refunded")

    transaction.response_status_code = upstream_response.status_code

    if 200 <= upstream_response.status_code < 300:
        await _settle_success(db, transaction, listing)
    else:
        await _settle_failure(
            db, transaction, listing,
            reason=f"Upstream returned {upstream_response.status_code}",
        )

    return upstream_response


async def _settle_success(db: AsyncSession, transaction: Transaction, listing: Listing) -> None:
    escrow_result = await db.execute(select(Escrow).where(Escrow.transaction_id == transaction.id))
    escrow = escrow_result.scalar_one()

    try:
        payout = escrow_wallet.release_to_provider(
            pay_to_address=listing.pay_to_address,
            amount_microalgos=escrow.amount_microalgos,
            asa_id=escrow.asa_id,
            platform_fee_microalgos=escrow.platform_fee_microalgos,
        )
        escrow.status = EscrowStatus.RELEASED
        escrow.payout_tx_id = payout.tx_id
        escrow.resolved_at = datetime.now(UTC)
        transaction.status = TransactionStatus.SERVICE_COMPLETED
        transaction.completed_at = datetime.now(UTC)
        listing.successful_transactions += 1
        logger.info("Escrow RELEASED tx=%s payout=%s", transaction.id, payout.tx_id)
    except escrow_wallet.EscrowWalletError as exc:
        # Upstream succeeded but the payout couldn't be signed/submitted --
        # do NOT silently drop the funds; flag for manual admin release.
        escrow.status = EscrowStatus.DISPUTED
        escrow.notes = f"Auto-release failed, needs manual resolution: {exc}"
        transaction.status = TransactionStatus.DISPUTED
        transaction.failure_reason = str(exc)
        logger.error("Escrow auto-release FAILED tx=%s: %s", transaction.id, exc)

    await db.commit()


async def _settle_failure(db: AsyncSession, transaction: Transaction, listing: Listing, *, reason: str) -> None:
    escrow_result = await db.execute(select(Escrow).where(Escrow.transaction_id == transaction.id))
    escrow = escrow_result.scalar_one()

    try:
        refund = escrow_wallet.refund_to_agent(
            payer_address=transaction.payer_address,
            amount_microalgos=escrow.amount_microalgos,
            asa_id=escrow.asa_id,
        )
        escrow.status = EscrowStatus.REFUNDED
        escrow.refund_tx_id = refund.tx_id
        escrow.resolved_at = datetime.now(UTC)
        transaction.status = TransactionStatus.REFUNDED
        transaction.failure_reason = reason
        transaction.completed_at = datetime.now(UTC)
        listing.failed_transactions += 1
        logger.warning("Escrow REFUNDED tx=%s refund=%s reason=%s", transaction.id, refund.tx_id, reason)
    except escrow_wallet.EscrowWalletError as exc:
        escrow.status = EscrowStatus.DISPUTED
        escrow.notes = f"Auto-refund failed, needs manual resolution: {exc}"
        transaction.status = TransactionStatus.DISPUTED
        transaction.failure_reason = f"{reason}; refund also failed: {exc}"
        logger.error("Escrow auto-refund FAILED tx=%s: %s", transaction.id, exc)

    await db.commit()
