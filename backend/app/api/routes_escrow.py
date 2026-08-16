import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.escrow.escrow_service import EscrowError, open_escrow, refund_escrow, release_escrow
from app.models.escrow import Escrow
from app.models.transaction import Transaction
from app.schemas.transaction import EscrowOut, EscrowResolveRequest

router = APIRouter(prefix="/api/escrow", tags=["escrow"])


@router.post("", response_model=EscrowOut, status_code=201)
async def create_escrow(transaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Escrow:
    txn = await db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    try:
        return await open_escrow(db, txn)
    except EscrowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{escrow_id}", response_model=EscrowOut)
async def get_escrow(escrow_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Escrow:
    escrow = await db.get(Escrow, escrow_id)
    if escrow is None:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return escrow


@router.post("/{escrow_id}/release", response_model=EscrowOut)
async def release(
    escrow_id: uuid.UUID, payload: EscrowResolveRequest, db: AsyncSession = Depends(get_db)
) -> Escrow:
    escrow = await db.get(Escrow, escrow_id)
    if escrow is None:
        raise HTTPException(status_code=404, detail="Escrow not found")
    try:
        return await release_escrow(db, escrow, notes=payload.notes)
    except EscrowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{escrow_id}/refund", response_model=EscrowOut)
async def refund(
    escrow_id: uuid.UUID, payload: EscrowResolveRequest, db: AsyncSession = Depends(get_db)
) -> Escrow:
    escrow = await db.get(Escrow, escrow_id)
    if escrow is None:
        raise HTTPException(status_code=404, detail="Escrow not found")
    try:
        return await refund_escrow(db, escrow, notes=payload.notes)
    except EscrowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
