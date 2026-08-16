import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SpendingPolicyIn(BaseModel):
    max_transaction_amount: Decimal = Field(..., gt=0)
    daily_limit: Decimal = Field(..., gt=0)
    min_provider_reputation: int = Field(default=50, ge=0, le=100)
    allowed_provider_ids: list[uuid.UUID] = Field(default_factory=list)


class SpendingPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    max_transaction_amount: Decimal
    daily_limit: Decimal
    min_provider_reputation: int
    allowed_provider_ids: list[uuid.UUID] = Field(default_factory=list)


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    wallet_address: str = Field(..., min_length=8, max_length=80)
    policy: SpendingPolicyIn


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    wallet_address: str
    is_active: bool
    is_paused: bool
    created_at: datetime
    policy: SpendingPolicyOut | None = None


class AgentPauseUpdate(BaseModel):
    is_paused: bool
