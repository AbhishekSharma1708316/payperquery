"""Application-level escrow service.

See app/models/escrow.py for the important distinction this enforces:
AgentVault escrow tracks whether a task RESULT was accepted, layered on
top of an x402 payment that has already settled. It is not on-chain
escrow and never claims to be.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.escrow import Escrow, EscrowStatus
from app.models.transaction import Transaction, TransactionStatus


class EscrowError(Exception):
    pass


async def open_escrow(db: AsyncSession, transaction: Transaction) -> Escrow:
    if transaction.status not in (
        TransactionStatus.PAYMENT_VERIFIED,
        TransactionStatus.SERVICE_COMPLETED,
    ):
        raise EscrowError(
            "Cannot open escrow for a transaction whose payment has not been verified "
            f"(status={transaction.status})"
        )
    escrow = Escrow(transaction_id=transaction.id, status=EscrowStatus.HELD)
    db.add(escrow)
    await db.commit()
    await db.refresh(escrow)
    return escrow


async def release_escrow(db: AsyncSession, escrow: Escrow, notes: str | None = None) -> Escrow:
    if escrow.status != EscrowStatus.HELD:
        raise EscrowError(f"Escrow {escrow.id} is not HELD (status={escrow.status})")
    escrow.status = EscrowStatus.RELEASED
    escrow.notes = notes
    escrow.resolved_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(escrow)
    return escrow


async def refund_escrow(db: AsyncSession, escrow: Escrow, notes: str | None = None) -> Escrow:
    """Marks the escrow refunded at the AgentVault application level.

    IMPORTANT: this does NOT reverse the underlying on-chain x402 payment
    -- x402/AVM settlement is final once confirmed. This records that
    AgentVault considers the task result unacceptable and that an
    off-chain/manual reimbursement process should be triggered; it is a
    bookkeeping and workflow signal, not an automatic fund clawback.
    """
    if escrow.status != EscrowStatus.HELD:
        raise EscrowError(f"Escrow {escrow.id} is not HELD (status={escrow.status})")
    escrow.status = EscrowStatus.REFUNDED
    escrow.notes = notes
    escrow.resolved_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(escrow)
    return escrow
