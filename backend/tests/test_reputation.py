from app.policies.reputation import compute_reputation


def test_high_volume_high_success_provider_scores_high():
    result = compute_reputation(
        successful_transactions=95,
        failed_transactions=5,
        average_latency_ms=150,
        refund_count=1,
        dispute_count=0,
    )
    assert result.score >= 85


def test_new_provider_with_single_success_gets_neutral_not_extreme_score():
    result = compute_reputation(
        successful_transactions=1,
        failed_transactions=0,
        average_latency_ms=100,
        refund_count=0,
        dispute_count=0,
    )
    # Should be blended toward the neutral baseline, not 100
    assert 55 <= result.score <= 75


def test_provider_with_no_transactions_gets_neutral_baseline():
    result = compute_reputation(
        successful_transactions=0,
        failed_transactions=0,
        average_latency_ms=200,
        refund_count=0,
        dispute_count=0,
    )
    assert result.score == 60


def test_high_failure_rate_provider_scores_low():
    result = compute_reputation(
        successful_transactions=10,
        failed_transactions=90,
        average_latency_ms=1500,
        refund_count=20,
        dispute_count=10,
    )
    assert result.score < 35


def test_high_dispute_and_refund_rate_penalizes_score():
    baseline = compute_reputation(
        successful_transactions=100,
        failed_transactions=0,
        average_latency_ms=200,
        refund_count=0,
        dispute_count=0,
    )
    with_disputes = compute_reputation(
        successful_transactions=100,
        failed_transactions=0,
        average_latency_ms=200,
        refund_count=30,
        dispute_count=20,
    )
    assert with_disputes.score < baseline.score
