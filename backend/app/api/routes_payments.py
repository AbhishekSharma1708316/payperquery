import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.transaction import Transaction
from app.payments.payment_service import AgentOrProviderNotFound, process_payment_request
from app.schemas.transaction import PaymentRequest, PaymentResult, TransactionOut

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/request", response_model=PaymentResult)
async def request_payment(
    payload: PaymentRequest,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    payer_mnemonic: str | None = Header(default=None, alias="X-Payer-Mnemonic"),
) -> dict:
    """The core policy-gated payment entrypoint.

    Requires an `Idempotency-Key` header. Retrying the same request with
    the same key is guaranteed to resolve to the same Transaction and
    never double-charges (enforced by a unique DB index on
    idempotency_key, not just this in-memory check).

    `X-Payer-Mnemonic` is optional and intended for demo/test use only --
    it lets this single call drive a real signed Algorand Testnet payment
    end-to-end. In a production agent integration, the agent's own
    wallet/signer would perform this step instead of handing a mnemonic
    to the server.
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key header is required for payment requests"
        )

    try:
        txn: Transaction = await process_payment_request(
            db,
            agent_id=payload.agent_id,
            provider_id=payload.provider_id,
            amount=payload.amount,
            currency=payload.currency,
            idempotency_key=idempotency_key,
            payer_mnemonic=payer_mnemonic,
        )
    except AgentOrProviderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "transaction": TransactionOut.model_validate(txn).model_dump(),
        "policy_decision": {
            "approved": txn.status.value
            not in ("POLICY_BLOCKED",),
            "reason": txn.failure_reason,
            "risk_score": txn.risk_score,
        },
        "service_result": None,
    }


@router.post("/{transaction_id}/verify", response_model=TransactionOut)
async def verify_payment_status(
    transaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Transaction:
    """Independently re-reads the transaction's server-recorded status.

    This exists specifically so a client can never simply assert success --
    it must ask AgentVault, which only ever reflects state set by
    payment_service based on actual policy/x402 outcomes.
    """
    txn = await db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
