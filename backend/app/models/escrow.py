import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EscrowStatus(str, enum.Enum):
    HELD = "HELD"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"


class Escrow(Base):
    """Application-level escrow state layered on top of an already-settled
    x402 payment.

    IMPORTANT: this is NOT on-chain escrow. The underlying x402 payment
    (see Transaction.status == PAYMENT_VERIFIED) has already settled funds
    to the provider's address via the facilitator before this row is even
    created. This model exists purely so AgentVault can track, in its own
    application logic, whether the *result* of a paid task has been
    verified as acceptable ("released") or flagged as unacceptable
    ("refunded") -- refunds here are AgentVault-mediated (e.g. a manual or
    policy-driven off-chain reimbursement), not an automatic on-chain
    clawback. This distinction is surfaced explicitly in the API response
    and the frontend UI so it is never confused with native settlement.
    """

    __tablename__ = "escrows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus, name="escrow_status"), default=EscrowStatus.HELD, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="escrow")

    def __repr__(self) -> str:
        return f"<Escrow tx_id={self.transaction_id} status={self.status}>"
