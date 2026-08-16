import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    endpoint: str = Field(..., min_length=1, max_length=500)
    category: str = Field(default="general", max_length=60)
    price_usd: Decimal = Field(..., gt=0)
    pay_to_address: str = Field(..., min_length=8, max_length=80)


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    endpoint: str
    category: str
    price_usd: Decimal
    pay_to_address: str
    successful_transactions: int
    failed_transactions: int
    average_latency_ms: int
    refund_count: int
    dispute_count: int
    active: bool
    reputation_score: int
    created_at: datetime
