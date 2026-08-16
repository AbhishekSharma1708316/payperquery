import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    agent_id: uuid.UUID | None = None,
    provider_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, le=1000),
) -> list[Transaction]:
    query = select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
    if agent_id is not None:
        query = query.where(Transaction.agent_id == agent_id)
    if provider_id is not None:
        query = query.where(Transaction.provider_id == provider_id)
    if status_filter is not None:
        query = query.where(Transaction.status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(transaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Transaction:
    txn = await db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
