import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.provider import Provider
from app.policies.reputation import compute_reputation
from app.schemas.provider import ProviderCreate, ProviderOut

router = APIRouter(prefix="/api/providers", tags=["providers"])


def _provider_out(provider: Provider) -> dict:
    reputation = compute_reputation(
        successful_transactions=provider.successful_transactions,
        failed_transactions=provider.failed_transactions,
        average_latency_ms=provider.average_latency_ms,
        refund_count=provider.refund_count,
        dispute_count=provider.dispute_count,
    )
    return {
        "id": provider.id,
        "name": provider.name,
        "endpoint": provider.endpoint,
        "category": provider.category,
        "price_usd": provider.price_usd,
        "pay_to_address": provider.pay_to_address,
        "successful_transactions": provider.successful_transactions,
        "failed_transactions": provider.failed_transactions,
        "average_latency_ms": provider.average_latency_ms,
        "refund_count": provider.refund_count,
        "dispute_count": provider.dispute_count,
        "active": provider.active,
        "reputation_score": reputation.score,
        "created_at": provider.created_at,
    }


@router.get("", response_model=list[ProviderOut])
async def list_providers(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Provider).order_by(Provider.created_at.desc()))
    return [_provider_out(p) for p in result.scalars().all()]


@router.get("/{provider_id}", response_model=ProviderOut)
async def get_provider(provider_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    provider = await db.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _provider_out(provider)


@router.post("", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
async def create_provider(payload: ProviderCreate, db: AsyncSession = Depends(get_db)) -> dict:
    provider = Provider(**payload.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return _provider_out(provider)
