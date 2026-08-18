import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Listing(Base):
    """A paid API published to the marketplace.

    Combines PayPerQuery's registered "Endpoint" (what to call, and the
    x402 price) with AgentVault's "Provider" (reputation bookkeeping),
    with one crucial change: `pay_to_address` is the PROVIDER'S OWN payout
    address, but it is never handed to the buying agent as the x402
    recipient. The x402 quote for every listing always names the
    platform's escrow wallet as `payTo` (see payments/x402_quote.py) --
    `pay_to_address` here is only used later, by the escrow service, to
    pay the provider out of escrow after a successful call.
    """

    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # --- Marketplace catalog fields ---
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="general", index=True)
    path: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    upstream_url: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Pricing (x402 "exact" scheme, USDC on Algorand) ---
    price_microalgos: Mapped[int] = mapped_column(BigInteger, nullable=False)  # micro-USDC, 6dp
    asa_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # None => native ALGO

    # --- Where the provider actually gets paid, from escrow, on release ---
    pay_to_address: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- Reputation inputs (see policies/reputation.py for the formula) ---
    successful_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_latency_ms: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    refund_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dispute_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Listing path={self.path} price={self.price_microalgos}>"
