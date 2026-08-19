"""Marketplace discovery: what an AI agent uses to find an API worth buying."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.policies.reputation import compute_reputation


async def search_listings(
    db: AsyncSession,
    *,
    query: str | None = None,
    category: str | None = None,
    min_reputation: int = 0,
    include_inactive: bool = False,
) -> list[tuple[Listing, int]]:
    """Returns (listing, reputation_score) pairs, best reputation first.

    Reputation is computed live from each listing's transaction counters
    rather than cached, so it always reflects the latest escrow outcomes.
    """
    stmt = select(Listing)
    if not include_inactive:
        stmt = stmt.where(Listing.is_active.is_(True))
    if category:
        stmt = stmt.where(Listing.category == category)
    if query:
        like = f"%{query}%"
        stmt = stmt.where(or_(Listing.name.ilike(like), Listing.description.ilike(like), Listing.category.ilike(like)))

    result = await db.execute(stmt)
    listings = list(result.scalars().all())

    scored = []
    for listing in listings:
        reputation = compute_reputation(
            successful_transactions=listing.successful_transactions,
            failed_transactions=listing.failed_transactions,
            average_latency_ms=listing.average_latency_ms,
            refund_count=listing.refund_count,
            dispute_count=listing.dispute_count,
        )
        if reputation.score >= min_reputation:
            scored.append((listing, reputation.score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
