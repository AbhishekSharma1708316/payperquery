import asyncio
import logging
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger("apimarket.algorand_verifier")
settings = get_settings()


class PaymentVerificationError(Exception):
    pass


@dataclass
class VerifiedPayment:
    tx_id: str
    payer_address: str
    receiver_address: str
    amount: int
    asa_id: int | None
    confirmed_round: int = 0
    note: str | None = None


def _get_facilitator():
    from x402.http import HTTPFacilitatorClient, FacilitatorConfig

    return HTTPFacilitatorClient(
        FacilitatorConfig(
            url=settings.FACILITATOR_URL
        )
    )


def build_payment_requirements(
    *,
    resource: str,
    expected_recipient: str,
    expected_amount: int,
    expected_asa_id: int | None,
) -> dict:
    """
    Build the x402 v2 PaymentRequirements object expected by the
    GoPlausible facilitator.
    """

    return {
        "scheme": settings.X402_SCHEME,
        "network": settings.ALGORAND_NETWORK,
        "maxAmountRequired": str(expected_amount),
        "resource": resource,
        "description": "APIMarket escrow payment",
        "mimeType": "application/json",
        "payTo": expected_recipient,
        "maxTimeoutSeconds": settings.X402_QUOTE_TTL_SECONDS,
        "asset": str(expected_asa_id or 0),
        "outputSchema": None,
        "extra": {
            "name": "USDC" if expected_asa_id else "ALGO",
            "decimals": 6,
        },
    }


async def verify_payment_with_facilitator(
    *,
    payment_payload: dict,
    payment_requirements: dict,
) -> dict:
    """
    Verify the signed x402 payment through GoPlausible's hosted
    facilitator.
    """

    facilitator = _get_facilitator()

    try:
        result = await facilitator.verify(
            payment_payload,
            payment_requirements,
        )
    except Exception as exc:
        logger.exception("GoPlausible facilitator verification failed")
        raise PaymentVerificationError(
            f"Facilitator verification request failed: {exc}"
        ) from exc

    if not result:
        raise PaymentVerificationError(
            "Facilitator returned an empty verification response"
        )

    if not getattr(result, "is_valid", False):
        error = getattr(result, "invalid_reason", None) or "Payment rejected"
        raise PaymentVerificationError(
            f"GoPlausible rejected payment: {error}"
        )

    return result


async def settle_payment_with_facilitator(
    *,
    payment_payload: dict,
    payment_requirements: dict,
):
    """
    Ask GoPlausible to settle the verified x402 payment.

    For Algorand this is the operation that actually submits the
    signed payment group to the network through the facilitator.
    """

    facilitator = _get_facilitator()

    try:
        result = await facilitator.settle(
            payment_payload,
            payment_requirements,
        )
    except Exception as exc:
        logger.exception("GoPlausible facilitator settlement failed")
        raise PaymentVerificationError(
            f"Facilitator settlement request failed: {exc}"
        ) from exc

    if not result:
        raise PaymentVerificationError(
            "Facilitator returned an empty settlement response"
        )

    if not getattr(result, "success", False):
        error = getattr(result, "error", None) or "Settlement rejected"
        raise PaymentVerificationError(
            f"GoPlausible settlement failed: {error}"
        )

    return result


async def verify_and_settle_payment(
    *,
    payment_payload: dict,
    payment_requirements: dict,
) -> VerifiedPayment:
    """
    Complete x402 flow:

        PaymentPayload
              ↓
        GoPlausible /verify
              ↓
        GoPlausible /settle
              ↓
        Algorand Testnet

    Returns the confirmed payment information.
    """

    await verify_payment_with_facilitator(
        payment_payload=payment_payload,
        payment_requirements=payment_requirements,
    )

    settlement = await settle_payment_with_facilitator(
        payment_payload=payment_payload,
        payment_requirements=payment_requirements,
    )

    tx_id = (
        getattr(settlement, "transaction", None)
        or getattr(settlement, "tx_id", None)
        or getattr(settlement, "transaction_hash", None)
    )

    if not tx_id:
        raise PaymentVerificationError(
            "GoPlausible settlement succeeded but no transaction ID was returned"
        )

    payer = (
        payment_payload.get("payload", {})
        .get("from")
        or payment_payload.get("payload", {})
        .get("sender")
        or "unknown"
    )

    return VerifiedPayment(
        tx_id=tx_id,
        payer_address=payer,
        receiver_address=payment_requirements["payTo"],
        amount=int(payment_requirements["maxAmountRequired"]),
        asa_id=int(payment_requirements["asset"]),
    )
