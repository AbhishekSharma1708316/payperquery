import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Agent(Base):
    """An autonomous AI agent with a wallet and a spending policy."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    wallet_address: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    policy: Mapped["SpendingPolicy"] = relationship(
        back_populates="agent", uselist=False, cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="agent")

    def __repr__(self) -> str:
        return f"<Agent name={self.name} wallet={self.wallet_address}>"


class SpendingPolicy(Base):
    """Enforced spending policy for a single agent.

    Monetary values are stored as USD with 6 decimal places (matching USDC's
    6-decimal precision) using Numeric, never floats, to avoid rounding
    errors in financial comparisons.
    """

    __tablename__ = "spending_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    max_transaction_amount: Mapped[Numeric] = mapped_column(Numeric(18, 6), nullable=False)
    daily_limit: Mapped[Numeric] = mapped_column(Numeric(18, 6), nullable=False)
    min_provider_reputation: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    agent: Mapped["Agent"] = relationship(back_populates="policy")
    allowed_providers: Mapped[list["AllowedProvider"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SpendingPolicy agent_id={self.agent_id} max_tx={self.max_transaction_amount}>"


class AllowedProvider(Base):
    """Join table: which providers a given policy permits the agent to pay."""

    __tablename__ = "allowed_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spending_policies.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )

    policy: Mapped["SpendingPolicy"] = relationship(back_populates="allowed_providers")
    provider: Mapped["Provider"] = relationship()
