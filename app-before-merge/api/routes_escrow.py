import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.escrow import Escrow, EscrowStatus
from app.models.listing import Listing
from app.models.transaction import Transaction, TransactionStatus
from app.payments import escrow_wallet
from app.schemas.transaction import EscrowOut, EscrowResolveRequest

router = APIRouter(prefix="/api/escrow", tags=["escrow"])


@router.get("", response_model=list[EscrowOut])
async def list_escrows(status_filter: EscrowStatus | None = None, db: AsyncSession = Depends(get_db)) -> list[Escrow]:
    query = select(Escrow).order_by(Escrow.created_at.desc())
    if status_filter:
        query = query.where(Escrow.status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{escrow_id}", response_model=EscrowOut)
async def get_escrow(escrow_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Escrow:
    escrow = await db.get(Escrow, escrow_id)
    if escrow is None:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return escrow


@router.post("/{escrow_id}/release", response_model=EscrowOut)
async def manual_release(
    escrow_id: uuid.UUID, payload: EscrowResolveRequest, db: AsyncSession = Depends(get_db)
) -> Escrow:
    """Manual admin override -- e.g. resolving a DISPUTED escrow where
    auto-release failed, once the underlying issue is fixed."""
    escrow = await db.get(Escrow, escrow_id)
    if escrow is None:
        raise HTTPException(status_code=404, detail="Escrow not found")
    if escrow.status not in (EscrowStatus.HELD, EscrowStatus.DISPUTED):
        raise HTTPException(status_code=409, detail=f"Escrow {escrow_id} is {escrow.status}, cannot release")

    txn = await db.get(Transaction, escrow.transaction_id)
    listing = await db.get(Listing, txn.listing_id) if txn else None
    if listing is None:
        raise HTTPException(status_code=409, detail="Underlying listing no longer exists")

    try:
        payout = escrow_wallet.release_to_provider(
            pay_to_address=listing.pay_to_address,
            amount_microalgos=escrow.amount_microalgos,
            asa_id=escrow.asa_id,
            platform_fee_microalgos=escrow.platform_fee_microalgos,
        )
    except escrow_wallet.EscrowWalletError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    escrow.status = EscrowStatus.RELEASED
    escrow.payout_tx_id = payout.tx_id
    escrow.notes = payload.notes
    escrow.resolved_at = datetime.now(UTC)
    if txn:
        txn.status = TransactionStatus.SERVICE_COMPLETED
        txn.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(escrow)
    return escrow


@router.post("/{escrow_id}/refund", response_model=EscrowOut)
async def manual_refund(
    escrow_id: uuid.UUID, payload: EscrowResolveRequest, db: AsyncSession = Depends(get_db)
) -> Escrow:
    escrow = await db.get(Escrow, escrow_id)
    if escrow is None:
        raise HTTPException(status_code=404, detail="Escrow not found")
    if escrow.status not in (EscrowStatus.HELD, EscrowStatus.DISPUTED):
        raise HTTPException(status_code=409, detail=f"Escrow {escrow_id} is {escrow.status}, cannot refund")

    txn = await db.get(Transaction, escrow.transaction_id)
    if txn is None or not txn.payer_address:
        raise HTTPException(status_code=409, detail="No payer address recorded for this transaction")

    try:
        refund = escrow_wallet.refund_to_agent(
            payer_address=txn.payer_address,
            amount_microalgos=escrow.amount_microalgos,
            asa_id=escrow.asa_id,
        )
    except escrow_wallet.EscrowWalletError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    escrow.status = EscrowStatus.REFUNDED
    escrow.refund_tx_id = refund.tx_id
    escrow.notes = payload.notes
    escrow.resolved_at = datetime.now(UTC)
    txn.status = TransactionStatus.REFUNDED
    txn.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(escrow)
    return escrow
