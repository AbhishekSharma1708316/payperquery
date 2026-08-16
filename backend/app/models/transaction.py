import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    SERVICE_COMPLETED = "SERVICE_COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Transaction(Base):
    """A record of a single payment attempt by an agent to a provider.

    `idempotency_key` has a unique index: retried requests with the same
    key resolve to the SAME row instead of creating a new transaction
    or re-charging.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_idempotency_key_unique", "idempotency_key", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Numeric] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USDC", nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status"),
        default=TransactionStatus.PENDING,
        nullable=False,
    )
    payment_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    x402_payment_identifier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped["Agent"] = relationship(back_populates="transactions")
    escrow: Mapped["Escrow | None"] = relationship(
        back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} status={self.status} amount={self.amount}>"
