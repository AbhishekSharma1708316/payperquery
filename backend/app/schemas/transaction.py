import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentRequest(BaseModel):
    agent_id: uuid.UUID
    provider_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USDC", max_length=10)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    provider_id: uuid.UUID | None
    amount: Decimal
    currency: str
    status: str
    payment_reference: str | None
    x402_payment_identifier: str | None
    idempotency_key: str
    risk_score: int | None
    failure_reason: str | None
    created_at: datetime
    completed_at: datetime | None


class PaymentResult(BaseModel):
    transaction: TransactionOut
    policy_decision: dict
    service_result: dict | None = None


class EscrowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    status: str
    notes: str | None
    created_at: datetime
    resolved_at: datetime | None


class EscrowResolveRequest(BaseModel):
    notes: str | None = None


class DashboardStats(BaseModel):
    wallet_balance_placeholder: str = Field(
        description="AgentVault does not custody funds; this reflects the sum "
        "of verified payments made, not a real wallet balance."
    )
    today_spending: Decimal
    successful_payments_today: int
    blocked_payments_today: int
    average_transaction_value: Decimal
    total_agents: int
    total_providers: int
