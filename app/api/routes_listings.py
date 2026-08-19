import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.listing import Listing
from app.schemas.listing import ListingCreate, ListingOut, ListingUpdate

router = APIRouter(prefix="/api/listings", tags=["provider-admin"])


@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
async def publish_listing(payload: ListingCreate, db: AsyncSession = Depends(get_db)) -> Listing:
    """A provider registers an API on the marketplace. `pay_to_address`
    is where THEY get paid on escrow release -- it is never handed to
    buying agents as the payment destination."""
    listing = Listing(**payload.model_dump())
    db.add(listing)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"A listing already exists at path '{payload.path}'") from exc
    await db.refresh(listing)
    return listing


@router.get("", response_model=list[ListingOut])
async def list_listings(db: AsyncSession = Depends(get_db), include_inactive: bool = False) -> list[Listing]:
    query = select(Listing).order_by(Listing.created_at.desc())
    if not include_inactive:
        query = query.where(Listing.is_active.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(listing_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Listing:
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.patch("/{listing_id}", response_model=ListingOut)
async def update_listing(
    listing_id: uuid.UUID, payload: ListingUpdate, db: AsyncSession = Depends(get_db)
) -> Listing:
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)
    await db.commit()
    await db.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_listing(listing_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.is_active = False
    await db.commit()
