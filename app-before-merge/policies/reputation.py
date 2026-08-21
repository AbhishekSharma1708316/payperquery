"""Provider reputation scoring.

Deliberately simple and fully explainable -- this is NOT a fraud-detection
model. The score (0-100) is a weighted blend of four signals:

  - success rate      (60%): successful / (successful + failed)
  - latency            (15%): faster = better, capped at a 2s reference ceiling
  - refund rate        (15%): fewer refunds relative to volume = better
  - dispute rate       (10%): fewer disputes relative to volume = better

Providers with fewer than MIN_VOLUME_FOR_FULL_CONFIDENCE total transactions
get a neutral baseline blended in, so a brand-new provider with 1 success
doesn't score a misleading 100.
"""

from dataclasses import dataclass

MIN_VOLUME_FOR_FULL_CONFIDENCE = 20
NEUTRAL_BASELINE_SCORE = 60.0
LATENCY_REFERENCE_CEILING_MS = 2000

WEIGHT_SUCCESS_RATE = 0.60
WEIGHT_LATENCY = 0.15
WEIGHT_REFUND_RATE = 0.15
WEIGHT_DISPUTE_RATE = 0.10


@dataclass
class ReputationBreakdown:
    score: int
    success_rate: float
    latency_score: float
    refund_penalty: float
    dispute_penalty: float
    total_volume: int
    confidence_weight: float


def compute_reputation(
    *,
    successful_transactions: int,
    failed_transactions: int,
    average_latency_ms: int,
    refund_count: int,
    dispute_count: int,
) -> ReputationBreakdown:
    total_volume = successful_transactions + failed_transactions

    if total_volume == 0:
        success_rate = 1.0
    else:
        success_rate = successful_transactions / total_volume

    latency_score = max(0.0, 1.0 - min(average_latency_ms, LATENCY_REFERENCE_CEILING_MS) / LATENCY_REFERENCE_CEILING_MS)

    refund_penalty = 1.0 - min(refund_count / max(total_volume, 1), 1.0)
    dispute_penalty = 1.0 - min(dispute_count / max(total_volume, 1), 1.0)

    raw_score = (
        WEIGHT_SUCCESS_RATE * success_rate
        + WEIGHT_LATENCY * latency_score
        + WEIGHT_REFUND_RATE * refund_penalty
        + WEIGHT_DISPUTE_RATE * dispute_penalty
    ) * 100

    # Blend toward a neutral baseline for low-volume providers so early
    # transactions can't produce an overconfident extreme score.
    confidence_weight = min(total_volume / MIN_VOLUME_FOR_FULL_CONFIDENCE, 1.0)
    blended_score = confidence_weight * raw_score + (1 - confidence_weight) * NEUTRAL_BASELINE_SCORE

    return ReputationBreakdown(
        score=round(blended_score),
        success_rate=round(success_rate, 4),
        latency_score=round(latency_score, 4),
        refund_penalty=round(refund_penalty, 4),
        dispute_penalty=round(dispute_penalty, 4),
        total_volume=total_volume,
        confidence_weight=round(confidence_weight, 4),
    )
