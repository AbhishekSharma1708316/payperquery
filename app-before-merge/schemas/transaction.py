import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    listing_id: uuid.UUID | None
    amount_microalgos: int
    status: str
    deposit_tx_id: str | None
    payer_address: str | None
    risk_score: int | None
    response_status_code: int | None
    failure_reason: str | None
    created_at: datetime
    completed_at: datetime | None


class EscrowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    status: str
    amount_microalgos: int
    platform_fee_microalgos: int
    deposit_tx_id: str
    payout_tx_id: str | None
    refund_tx_id: str | None
    notes: str | None
    created_at: datetime
    resolved_at: datetime | None


class EscrowResolveRequest(BaseModel):
    notes: str | None = None
