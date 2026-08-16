import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AllowedProvider, SpendingPolicy
from app.models.provider import Provider
from app.models.transaction import TransactionStatus
from app.payments.payment_service import AgentOrProviderNotFound, process_payment_request

pytestmark = pytest.mark.asyncio


async def _make_agent_and_provider(
    db: AsyncSession,
    *,
    max_transaction_amount: str = "0.10",
    daily_limit: str = "5.00",
    min_provider_reputation: int = 50,
    allow_provider: bool = True,
    provider_active: bool = True,
    provider_reputation_inputs: dict | None = None,
) -> tuple[Agent, Provider]:
    agent = Agent(name="ResearchBot", wallet_address=f"AGENT{uuid.uuid4().hex[:20].upper()}")
    db.add(agent)
    await db.flush()

    policy = SpendingPolicy(
        agent_id=agent.id,
        max_transaction_amount=Decimal(max_transaction_amount),
        daily_limit=Decimal(daily_limit),
        min_provider_reputation=min_provider_reputation,
    )
    db.add(policy)
    await db.flush()

    rep = provider_reputation_inputs or {}
    provider = Provider(
        name="Search API",
        endpoint="http://localhost/mock-provider/search",
        category="search",
        price_usd=Decimal("0.03"),
        pay_to_address=f"PROV{uuid.uuid4().hex[:20].upper()}",
        active=provider_active,
        successful_transactions=rep.get("successful_transactions", 96),
        failed_transactions=rep.get("failed_transactions", 4),
        average_latency_ms=rep.get("average_latency_ms", 150),
        refund_count=rep.get("refund_count", 0),
        dispute_count=rep.get("dispute_count", 0),
    )
    db.add(provider)
    await db.flush()

    if allow_provider:
        db.add(AllowedProvider(policy_id=policy.id, provider_id=provider.id))
        await db.flush()

    await db.refresh(agent, attribute_names=["policy"])
    await db.commit()
    return agent, provider


async def test_approved_payment_within_limits_reaches_payment_required(db_session):
    agent, provider = await _make_agent_and_provider(db_session)

    txn = await process_payment_request(
        db_session,
        agent_id=agent.id,
        provider_id=provider.id,
        amount=Decimal("0.03"),
        currency="USDC",
        idempotency_key=str(uuid.uuid4()),
        payer_mnemonic=None,
    )

    assert txn.status == TransactionStatus.PAYMENT_REQUIRED
    assert txn.failure_reason is None


async def test_excessive_payment_is_blocked_before_any_payment_attempt(db_session):
    agent, provider = await _make_agent_and_provider(
        db_session, max_transaction_amount="0.10"
    )

    txn = await process_payment_request(
        db_session,
        agent_id=agent.id,
        provider_id=provider.id,
        amount=Decimal("2.00"),
        currency="USDC",
        idempotency_key=str(uuid.uuid4()),
        payer_mnemonic=None,
    )

    assert txn.status == TransactionStatus.POLICY_BLOCKED
    assert txn.failure_reason == "TRANSACTION_LIMIT_EXCEEDED"
    assert txn.payment_reference is None


async def test_disallowed_provider_is_blocked(db_session):
    agent, provider = await _make_agent_and_provider(db_session, allow_provider=False)

    txn = await process_payment_request(
        db_session,
        agent_id=agent.id,
        provider_id=provider.id,
        amount=Decimal("0.03"),
        currency="USDC",
        idempotency_key=str(uuid.uuid4()),
        payer_mnemonic=None,
    )

    assert txn.status == TransactionStatus.POLICY_BLOCKED
    assert txn.failure_reason == "PROVIDER_NOT_ALLOWED"


async def test_same_idempotency_key_returns_same_transaction_never_double_charges(db_session):
    agent, provider = await _make_agent_and_provider(db_session)
    key = str(uuid.uuid4())

    first = await process_payment_request(
        db_session,
        agent_id=agent.id,
        provider_id=provider.id,
        amount=Decimal("0.03"),
        currency="USDC",
        idempotency_key=key,
        payer_mnemonic=None,
    )
    second = await process_payment_request(
        db_session,
        agent_id=agent.id,
        provider_id=provider.id,
        amount=Decimal("0.03"),
        currency="USDC",
        idempotency_key=key,
        payer_mnemonic=None,
    )

    assert first.id == second.id

    from sqlalchemy import func, select

    from app.models.transaction import Transaction

    count = (
        await db_session.execute(
            select(func.count(Transaction.id)).where(Transaction.idempotency_key == key)
        )
    ).scalar_one()
    assert count == 1


async def test_agent_not_found_raises_clear_error(db_session):
    _, provider = await _make_agent_and_provider(db_session)

    with pytest.raises(AgentOrProviderNotFound):
        await process_payment_request(
            db_session,
            agent_id=uuid.uuid4(),
            provider_id=provider.id,
            amount=Decimal("0.03"),
            currency="USDC",
            idempotency_key=str(uuid.uuid4()),
            payer_mnemonic=None,
        )


async def test_low_reputation_provider_blocks_even_if_allowed(db_session):
    agent, provider = await _make_agent_and_provider(
        db_session,
        min_provider_reputation=80,
        provider_reputation_inputs={
            "successful_transactions": 10,
            "failed_transactions": 90,
            "average_latency_ms": 1800,
            "refund_count": 20,
            "dispute_count": 15,
        },
    )

    txn = await process_payment_request(
        db_session,
        agent_id=agent.id,
        provider_id=provider.id,
        amount=Decimal("0.03"),
        currency="USDC",
        idempotency_key=str(uuid.uuid4()),
        payer_mnemonic=None,
    )

    assert txn.status == TransactionStatus.POLICY_BLOCKED
    assert txn.failure_reason == "PROVIDER_REPUTATION_TOO_LOW"
