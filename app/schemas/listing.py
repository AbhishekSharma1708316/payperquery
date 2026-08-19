import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ListingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    category: str = Field(default="general", max_length=60)
    path: str = Field(..., min_length=1, max_length=200)
    upstream_url: str = Field(..., min_length=1)
    price_microalgos: int = Field(..., gt=0, description="Price in micro-USDC (6dp)")
    pay_to_address: str = Field(..., min_length=10, max_length=80)
    asa_id: int | None = None
    owner_contact: str | None = None

    @field_validator("path")
    @classmethod
    def normalize_path(cls, v: str) -> str:
        return v.strip("/")

    @field_validator("upstream_url")
    @classmethod
    def validate_upstream(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("upstream_url must start with http:// or https://")
        return v


class ListingUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    upstream_url: str | None = None
    price_microalgos: int | None = Field(default=None, gt=0)
    pay_to_address: str | None = None
    asa_id: int | None = None
    is_active: bool | None = None


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    category: str
    path: str
    upstream_url: str
    price_microalgos: int
    asa_id: int | None
    pay_to_address: str
    successful_transactions: int
    failed_transactions: int
    average_latency_ms: int
    is_active: bool
    created_at: datetime


class ListingSearchResult(ListingOut):
    reputation_score: int
