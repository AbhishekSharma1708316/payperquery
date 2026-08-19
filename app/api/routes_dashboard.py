import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["dashboard"])


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    agent_id: uuid.UUID | None = None,
    listing_id: uuid.UUID | None = None,
    status_filter: TransactionStatus | None = None,
    limit: int = Query(default=50, le=500),
) -> list[Transaction]:
    query = select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
    if agent_id:
        query = query.where(Transaction.agent_id == agent_id)
    if listing_id:
        query = query.where(Transaction.listing_id == listing_id)
    if status_filter:
        query = query.where(Transaction.status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(transaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Transaction:
    from fastapi import HTTPException

    txn = await db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
