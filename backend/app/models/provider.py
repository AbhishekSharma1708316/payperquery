import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Provider(Base):
    """A paid API/service provider that agents can pay via x402."""

    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    price_usd: Mapped[Numeric] = mapped_column(Numeric(18, 6), nullable=False)
    pay_to_address: Mapped[str] = mapped_column(String(80), nullable=False)

    # Reputation inputs (see policies/reputation.py for the transparent formula)
    successful_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_latency_ms: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    refund_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dispute_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Provider name={self.name} category={self.category}>"
