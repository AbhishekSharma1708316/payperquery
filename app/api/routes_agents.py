import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.agent import Agent, AllowedListing, SpendingPolicy
from app.schemas.agent import AgentCreate, AgentOut, AgentPauseRequest

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)) -> Agent:
    agent = Agent(
        name=payload.name,
        wallet_address=payload.wallet_address,
        api_key=secrets.token_hex(24),
    )
    db.add(agent)
    await db.flush()

    policy = SpendingPolicy(
        agent_id=agent.id,
        max_transaction_amount=payload.policy.max_transaction_amount,
        daily_limit=payload.policy.daily_limit,
        min_provider_reputation=payload.policy.min_provider_reputation,
        restrict_to_allowed_listings=payload.policy.restrict_to_allowed_listings,
    )
    db.add(policy)
    await db.flush()

    for listing_id in payload.policy.allowed_listing_ids:
        db.add(AllowedListing(policy_id=policy.id, listing_id=listing_id))

    await db.commit()

    result = await db.execute(
        select(Agent).where(Agent.id == agent.id).options(selectinload(Agent.policy))
    )
    return result.scalar_one()


@router.get("", response_model=list[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_db)) -> list[Agent]:
    result = await db.execute(select(Agent).options(selectinload(Agent.policy)))
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.policy))
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}/pause", response_model=AgentOut)
async def pause_agent(
    agent_id: uuid.UUID, payload: AgentPauseRequest, db: AsyncSession = Depends(get_db)
) -> Agent:
    """Emergency stop: the policy engine checks is_paused BEFORE any
    payment attempt, so this blocks every subsequent purchase instantly."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.policy))
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_paused = payload.paused
    await db.commit()
    await db.refresh(agent)
    return agent
