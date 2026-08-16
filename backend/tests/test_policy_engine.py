from decimal import Decimal

from app.policies.policy_engine import PolicyBlockReason, check_payment_policy


def _base_kwargs(**overrides) -> dict:
    kwargs = dict(
        agent_is_active=True,
        agent_is_paused=False,
        amount=Decimal("0.03"),
        max_transaction_amount=Decimal("0.10"),
        daily_limit=Decimal("5.00"),
        already_spent_today=Decimal("0.28"),
        provider_is_allowed=True,
        provider_is_active=True,
        provider_reputation=96,
        min_provider_reputation=50,
    )
    kwargs.update(overrides)
    return kwargs


def test_small_transaction_within_limits_is_approved():
    decision = check_payment_policy(**_base_kwargs())
    assert decision.approved is True
    assert decision.reason is None
    assert 0 <= decision.risk_score <= 100


def test_transaction_exceeding_per_transaction_limit_is_blocked():
    decision = check_payment_policy(**_base_kwargs(amount=Decimal("2.00")))
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.TRANSACTION_LIMIT_EXCEEDED
    assert decision.details["requested"] == "2.00"
    assert decision.details["max_allowed"] == "0.10"


def test_daily_limit_exceeded_is_blocked():
    decision = check_payment_policy(
        **_base_kwargs(amount=Decimal("0.08"), already_spent_today=Decimal("4.95"))
    )
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.DAILY_LIMIT_EXCEEDED


def test_provider_not_allowed_is_blocked():
    decision = check_payment_policy(**_base_kwargs(provider_is_allowed=False))
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.PROVIDER_NOT_ALLOWED


def test_low_reputation_provider_is_blocked():
    decision = check_payment_policy(
        **_base_kwargs(provider_reputation=30, min_provider_reputation=50)
    )
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.PROVIDER_REPUTATION_TOO_LOW


def test_paused_agent_is_blocked():
    decision = check_payment_policy(**_base_kwargs(agent_is_paused=True))
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.AGENT_PAUSED


def test_inactive_agent_is_blocked():
    decision = check_payment_policy(**_base_kwargs(agent_is_active=False))
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.AGENT_INACTIVE


def test_inactive_provider_is_blocked():
    decision = check_payment_policy(**_base_kwargs(provider_is_active=False))
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.PROVIDER_INACTIVE


def test_zero_or_negative_amount_is_blocked():
    decision = check_payment_policy(**_base_kwargs(amount=Decimal("0")))
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.INVALID_AMOUNT


def test_exact_boundary_amount_equal_to_limit_is_approved():
    """amount == max_transaction_amount should be approved (limit is inclusive)."""
    decision = check_payment_policy(**_base_kwargs(amount=Decimal("0.10")))
    assert decision.approved is True


def test_exact_boundary_amount_over_limit_by_smallest_unit_is_blocked():
    decision = check_payment_policy(**_base_kwargs(amount=Decimal("0.100001")))
    assert decision.approved is False
    assert decision.reason == PolicyBlockReason.TRANSACTION_LIMIT_EXCEEDED
