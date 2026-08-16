"""Payment orchestration service.

Responsible for:
  1. Idempotency (same key -> same transaction, never double-charge)
  2. Loading agent/policy/provider state
  3. Calling the pure policy engine
  4. If approved: executing the x402 payment and recording the result
  5. Never trusting client-supplied "payment succeeded" claims -- every
     transaction's status is set by this service based on what actually
     happened (policy engine result, x402 payment confirmation), never by
     data passed in from the request body.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent, AllowedProvider, SpendingPolicy
from app.models.provider import Provider
from app.models.transaction import Transaction, TransactionStatus
from app.payments.x402_client import X402PaymentError, sign_and_submit_avm_payment
from app.policies.policy_engine import check_payment_policy
from app.policies.reputation import compute_reputation

logger = logging.getLogger("agentvault.payment_service")


class PaymentServiceError(Exception):
    pass


class AgentOrProviderNotFound(PaymentServiceError):
    pass


async def _get_spent_today(db: AsyncSession, agent_id) -> Decimal:
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.agent_id == agent_id,
            Transaction.status.in_(
                [TransactionStatus.PAYMENT_VERIFIED, TransactionStatus.SERVICE_COMPLETED]
            ),
            Transaction.created_at >= start_of_day,
        )
    )
    return Decimal(result.scalar_one())


async def process_payment_request(
    db: AsyncSession,
    *,
    agent_id,
    provider_id,
    amount: Decimal,
    currency: str,
    idempotency_key: str,
    payer_mnemonic: str | None,
) -> Transaction:
    """Main entrypoint. Returns the (possibly pre-existing) Transaction row.

    `payer_mnemonic` is optional: if omitted, the transaction is recorded
    through policy evaluation and, if approved, left at PAYMENT_REQUIRED
    so a client can complete signing out-of-band. Demo/test flows pass it
    in directly for a fully automated round trip against Algorand Testnet.
    """
    existing = await db.execute(
        select(Transaction).where(Transaction.idempotency_key == idempotency_key)
    )
    existing_txn = existing.scalar_one_or_none()
    if existing_txn is not None:
        logger.info("Idempotent replay for key=%s -> tx=%s", idempotency_key, existing_txn.id)
        return existing_txn

    agent_result = await db.execute(
        select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.policy))
    )
    agent = agent_result.scalar_one_or_none()
    if agent is None:
        raise AgentOrProviderNotFound(f"Agent {agent_id} not found")
    if agent.policy is None:
        raise AgentOrProviderNotFound(f"Agent {agent_id} has no spending policy configured")

    provider = await db.get(Provider, provider_id)
    if provider is None:
        raise AgentOrProviderNotFound(f"Provider {provider_id} not found")

    policy = agent.policy

    allowed_result = await db.execute(
        select(AllowedProvider).where(
            AllowedProvider.policy_id == policy.id, AllowedProvider.provider_id == provider.id
        )
    )
    provider_is_allowed = allowed_result.scalar_one_or_none() is not None

    reputation = compute_reputation(
        successful_transactions=provider.successful_transactions,
        failed_transactions=provider.failed_transactions,
        average_latency_ms=provider.average_latency_ms,
        refund_count=provider.refund_count,
        dispute_count=provider.dispute_count,
    )

    already_spent_today = await _get_spent_today(db, agent.id)

    decision = check_payment_policy(
        agent_is_active=agent.is_active,
        agent_is_paused=agent.is_paused,
        amount=amount,
        max_transaction_amount=policy.max_transaction_amount,
        daily_limit=policy.daily_limit,
        already_spent_today=already_spent_today,
        provider_is_allowed=provider_is_allowed,
        provider_is_active=provider.active,
        provider_reputation=reputation.score,
        min_provider_reputation=policy.min_provider_reputation,
    )

    if not decision.approved:
        txn = Transaction(
            agent_id=agent.id,
            provider_id=provider.id,
            amount=amount,
            currency=currency,
            status=TransactionStatus.POLICY_BLOCKED,
            idempotency_key=idempotency_key,
            risk_score=decision.risk_score,
            failure_reason=decision.reason.value if decision.reason else "blocked",
            completed_at=datetime.now(UTC),
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)
        logger.warning(
            "Payment BLOCKED agent=%s provider=%s amount=%s reason=%s",
            agent.id,
            provider.id,
            amount,
            decision.reason,
        )
        return txn

    txn = Transaction(
        agent_id=agent.id,
        provider_id=provider.id,
        amount=amount,
        currency=currency,
        status=TransactionStatus.PAYMENT_REQUIRED,
        idempotency_key=idempotency_key,
        risk_score=decision.risk_score,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)

    if not payer_mnemonic:
        return txn

    txn.status = TransactionStatus.PAYMENT_SUBMITTED
    await db.commit()

    try:
        signed = sign_and_submit_avm_payment(
            payer_mnemonic=payer_mnemonic,
            payee_address=provider.pay_to_address,
            amount_usd=amount,
        )
    except X402PaymentError as exc:
        txn.status = TransactionStatus.FAILED
        txn.failure_reason = str(exc)
        txn.completed_at = datetime.now(UTC)
        provider.failed_transactions += 1
        await db.commit()
        await db.refresh(txn)
        logger.error("Payment FAILED tx=%s: %s", txn.id, exc)
        return txn

    txn.status = TransactionStatus.PAYMENT_VERIFIED
    txn.payment_reference = signed.tx_id
    txn.x402_payment_identifier = signed.tx_id
    txn.completed_at = datetime.now(UTC)
    provider.successful_transactions += 1
    await db.commit()
    await db.refresh(txn)

    logger.info("Payment VERIFIED tx=%s reference=%s", txn.id, signed.tx_id)
    return txn


async def mark_service_completed(db: AsyncSession, transaction: Transaction) -> Transaction:
    transaction.status = TransactionStatus.SERVICE_COMPLETED
    await db.commit()
    await db.refresh(transaction)
    return transaction
