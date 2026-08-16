import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.agent import Agent, AllowedProvider, SpendingPolicy
from app.schemas.agent import AgentCreate, AgentOut, AgentPauseUpdate, SpendingPolicyIn

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _agent_out_with_provider_ids(agent: Agent) -> dict:
    data = AgentOut.model_validate(agent).model_dump()
    if agent.policy:
        data["policy"]["allowed_provider_ids"] = [
            ap.provider_id for ap in agent.policy.allowed_providers
        ]
    return data


@router.get("", response_model=list[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        select(Agent).options(
            selectinload(Agent.policy).selectinload(SpendingPolicy.allowed_providers)
        )
    )
    agents = result.scalars().all()
    return [_agent_out_with_provider_ids(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(selectinload(Agent.policy).selectinload(SpendingPolicy.allowed_providers))
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_out_with_provider_ids(agent)


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)) -> dict:
    agent = Agent(name=payload.name, wallet_address=payload.wallet_address)
    db.add(agent)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail=f"Wallet address '{payload.wallet_address}' already registered"
        ) from exc

    policy = SpendingPolicy(
        agent_id=agent.id,
        max_transaction_amount=payload.policy.max_transaction_amount,
        daily_limit=payload.policy.daily_limit,
        min_provider_reputation=payload.policy.min_provider_reputation,
    )
    db.add(policy)
    await db.flush()

    for provider_id in payload.policy.allowed_provider_ids:
        db.add(AllowedProvider(policy_id=policy.id, provider_id=provider_id))

    await db.commit()

    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent.id)
        .options(selectinload(Agent.policy).selectinload(SpendingPolicy.allowed_providers))
    )
    return _agent_out_with_provider_ids(result.scalar_one())


@router.put("/{agent_id}/policy", response_model=AgentOut)
async def update_policy(
    agent_id: uuid.UUID, payload: SpendingPolicyIn, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(selectinload(Agent.policy).selectinload(SpendingPolicy.allowed_providers))
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = agent.policy
    policy.max_transaction_amount = payload.max_transaction_amount
    policy.daily_limit = payload.daily_limit
    policy.min_provider_reputation = payload.min_provider_reputation

    for existing in list(policy.allowed_providers):
        await db.delete(existing)
    await db.flush()

    for provider_id in payload.allowed_provider_ids:
        db.add(AllowedProvider(policy_id=policy.id, provider_id=provider_id))

    await db.commit()

    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(selectinload(Agent.policy).selectinload(SpendingPolicy.allowed_providers))
    )
    return _agent_out_with_provider_ids(result.scalar_one())


@router.patch("/{agent_id}/pause", response_model=AgentOut)
async def set_pause_state(
    agent_id: uuid.UUID, payload: AgentPauseUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    """Toggles the agent's paused state. When paused, the policy engine
    rejects every payment attempt (AGENT_PAUSED) before any x402 payment
    is ever initiated -- this backs the dashboard's 'PAUSE ALL PAYMENTS'
    control.
    """
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(selectinload(Agent.policy).selectinload(SpendingPolicy.allowed_providers))
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_paused = payload.is_paused
    await db.commit()
    await db.refresh(agent)
    return _agent_out_with_provider_ids(agent)
