from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.listing import ListingOut, ListingSearchResult
from app.services.marketplace_service import search_listings

router = APIRouter(prefix="/market", tags=["marketplace"])


@router.get("/search", response_model=list[ListingSearchResult])
async def search(
    q: str | None = None,
    category: str | None = None,
    min_reputation: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """What an agent calls to find an API: free-text query, optional
    category filter, and an optional reputation floor. Results are sorted
    by live-computed reputation, best first."""
    scored = await search_listings(db, query=q, category=category, min_reputation=min_reputation)
    results = []
    for listing, score in scored:
        base = ListingOut.model_validate(listing, from_attributes=True)
        results.append(ListingSearchResult(**base.model_dump(), reputation_score=score))
    return results
