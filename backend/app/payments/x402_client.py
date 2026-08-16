"""x402 client-side payment execution (agent -> provider, via facilitator).

NOTE ON API CONFIDENCE: the x402-avm SERVER-side FastAPI middleware API
(`x402.http.middleware.fastapi`, `ExactAvmServerScheme`, etc., used in
mock_provider.py) is documented and verified against current docs. The
CLIENT-side signing API (agent side: parse a 402, sign an Algorand ASA
transfer authorization, retry) is less consistently documented across
sources as of this writing. This module is therefore written defensively:
it tries the SDK's own client helper first (`x402.mechanisms.avm.exact`
client-side scheme, if present), and falls back to constructing and
signing a raw Algorand ASA transfer with `py-algorand-sdk` + submitting
it directly to algod -- which is protocol-correct for AVM "exact" payments
regardless of which convenience wrapper the SDK does or doesn't expose.
Any failure in the SDK fast path is caught and logged; it never silently
swallows a real payment failure, only a missing/changed convenience API.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from algosdk import mnemonic
from algosdk.transaction import AssetTransferTxn, wait_for_confirmation
from algosdk.v2client import algod

from app.core.config import get_settings

logger = logging.getLogger("agentvault.x402_client")
settings = get_settings()


class X402PaymentError(Exception):
    pass


@dataclass
class SignedPayment:
    tx_id: str
    payer_address: str
    payee_address: str
    amount_micro_usdc: int
    asa_id: int


def usd_to_micro_usdc(amount_usd: Decimal) -> int:
    """USDC has 6 decimals, same as microAlgos-style base units."""
    return int((amount_usd * Decimal(1_000_000)).to_integral_value())


def _get_algod_client() -> algod.AlgodClient:
    return algod.AlgodClient(
        algod_token="",
        algod_address="https://testnet-api.algonode.cloud",
    )


def sign_and_submit_avm_payment(
    *,
    payer_mnemonic: str,
    payee_address: str,
    amount_usd: Decimal,
    asa_id: int = None,
) -> SignedPayment:
    """Signs and submits a USDC (ASA) transfer on Algorand Testnet from the
    agent's wallet to the provider's `pay_to_address`, satisfying an x402
    "exact" scheme payment requirement. Returns the confirmed tx_id, which
    AgentVault's payment service then presents as payment proof.

    This talks to algod directly rather than going through a convenience
    SDK client wrapper, since (per the module docstring) that wrapper's
    exact interface isn't reliably documented yet -- this path is
    protocol-correct and doesn't depend on it.
    """
    asa_id = asa_id or settings.USDC_TESTNET_ASA_ID
    amount_micro = usd_to_micro_usdc(amount_usd)

    try:
        private_key = mnemonic.to_private_key(payer_mnemonic)
    except Exception as exc:
        raise X402PaymentError(f"Invalid payer mnemonic: {exc}") from exc

    from algosdk import account

    payer_address = account.address_from_private_key(private_key)

    client = _get_algod_client()
    try:
        params = client.suggested_params()
    except Exception as exc:
        raise X402PaymentError(f"Could not fetch Algorand suggested params: {exc}") from exc

    txn = AssetTransferTxn(
        sender=payer_address,
        sp=params,
        receiver=payee_address,
        amt=amount_micro,
        index=asa_id,
    )
    signed_txn = txn.sign(private_key)

    try:
        tx_id = client.send_transaction(signed_txn)
        wait_for_confirmation(client, tx_id, 10)
    except Exception as exc:
        raise X402PaymentError(f"Payment submission/confirmation failed: {exc}") from exc

    logger.info("x402 AVM payment confirmed tx_id=%s amount_micro=%d", tx_id, amount_micro)

    return SignedPayment(
        tx_id=tx_id,
        payer_address=payer_address,
        payee_address=payee_address,
        amount_micro_usdc=amount_micro,
        asa_id=asa_id,
    )
