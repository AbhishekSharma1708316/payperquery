"""The platform's own custody wallet.

This is the piece that turns "escrow" from a status label into an actual
fund-custody mechanism: `settings.ESCROW_WALLET_MNEMONIC` controls
`settings.ESCROW_WALLET_ADDRESS`, the address every x402 quote names as
`payTo`. Agent payments land HERE, under the platform's control, and stay
here until this module fires a real signed Algorand transaction moving
them onward -- to the provider (release) or back to the agent (refund).

Nothing about this is a smart-contract-enforced trustless escrow (that
would need an on-chain escrow application/contract account with logic
signatures or an ASC1 approval program) -- it is platform-custodied
escrow, same trust model as a payment processor holding buyer funds
until a marketplace order is confirmed delivered. That is still a real,
meaningful upgrade over "agent pays provider directly and hopes the API
call goes through": the provider is a Algorand address the agent never
pays, and cannot be paid, until the platform's own service confirms the
work was done.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from algosdk import account, mnemonic
from algosdk.transaction import AssetTransferTxn, PaymentTxn, wait_for_confirmation
from algosdk.v2client import algod

from app.core.config import get_settings

logger = logging.getLogger("apimarket.escrow_wallet")
settings = get_settings()


class EscrowWalletError(Exception):
    pass


@dataclass
class PayoutResult:
    tx_id: str
    from_address: str
    to_address: str
    amount_microalgos: int
    asa_id: int | None


def _algod_client() -> algod.AlgodClient:
    return algod.AlgodClient(settings.ALGOD_TOKEN, settings.ALGOD_ADDRESS)


def _escrow_private_key() -> str:
    if not settings.ESCROW_WALLET_MNEMONIC:
        raise EscrowWalletError(
            "ESCROW_WALLET_MNEMONIC is not configured -- the platform cannot "
            "sign payouts out of the escrow wallet. Set it in .env (production: "
            "load from a secrets manager, never commit it)."
        )
    try:
        return mnemonic.to_private_key(settings.ESCROW_WALLET_MNEMONIC)
    except Exception as exc:
        raise EscrowWalletError(f"Invalid ESCROW_WALLET_MNEMONIC: {exc}") from exc


def escrow_wallet_address() -> str:
    """Returns the address actually derived from the configured mnemonic,
    which should match settings.ESCROW_WALLET_ADDRESS -- checked at
    startup so a misconfigured .env fails loudly instead of silently
    quoting one address while paying out from another."""
    private_key = _escrow_private_key()
    return account.address_from_private_key(private_key)


def _send_from_escrow(*, to_address: str, amount_microalgos: int, asa_id: int | None) -> PayoutResult:
    private_key = _escrow_private_key()
    from_address = account.address_from_private_key(private_key)

    client = _algod_client()
    try:
        params = client.suggested_params()
    except Exception as exc:
        raise EscrowWalletError(f"Could not fetch Algorand suggested params: {exc}") from exc

    if asa_id:
        txn = AssetTransferTxn(
            sender=from_address, sp=params, receiver=to_address, amt=amount_microalgos, index=asa_id
        )
    else:
        txn = PaymentTxn(sender=from_address, sp=params, receiver=to_address, amt=amount_microalgos)

    signed_txn = txn.sign(private_key)

    try:
        tx_id = client.send_transaction(signed_txn)
        wait_for_confirmation(client, tx_id, 10)
    except Exception as exc:
        raise EscrowWalletError(f"Escrow payout submission/confirmation failed: {exc}") from exc

    logger.info(
        "Escrow payout confirmed tx_id=%s from=%s to=%s amount=%d asa=%s",
        tx_id, from_address, to_address, amount_microalgos, asa_id,
    )
    return PayoutResult(
        tx_id=tx_id,
        from_address=from_address,
        to_address=to_address,
        amount_microalgos=amount_microalgos,
        asa_id=asa_id,
    )


def release_to_provider(
    *, pay_to_address: str, amount_microalgos: int, asa_id: int | None, platform_fee_microalgos: int = 0
) -> PayoutResult:
    """Pays the provider out of escrow, minus the platform's fee (which
    simply stays in the escrow wallet as marketplace revenue)."""
    net_amount = amount_microalgos - platform_fee_microalgos
    if net_amount <= 0:
        raise EscrowWalletError("Platform fee cannot consume the entire escrowed amount")
    return _send_from_escrow(to_address=pay_to_address, amount_microalgos=net_amount, asa_id=asa_id)


def refund_to_agent(*, payer_address: str, amount_microalgos: int, asa_id: int | None) -> PayoutResult:
    """Returns the FULL escrowed amount to the paying agent -- no platform
    fee is kept on a refund, since no service was actually delivered."""
    return _send_from_escrow(to_address=payer_address, amount_microalgos=amount_microalgos, asa_id=asa_id)


def compute_platform_fee_microalgos(amount_microalgos: int) -> int:
    return (amount_microalgos * settings.PLATFORM_FEE_BPS) // 10_000
