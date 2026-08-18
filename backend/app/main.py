import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_agents,
    routes_dashboard,
    routes_escrow,
    routes_listings,
    routes_marketplace,
    routes_purchase,
)
from app.core.config import get_settings
from app.core.database import init_models
from app.payments import escrow_wallet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apimarket.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT == "development":
        await init_models()

    if settings.ESCROW_WALLET_MNEMONIC:
        derived = escrow_wallet.escrow_wallet_address()
        if derived != settings.ESCROW_WALLET_ADDRESS:
            logger.warning(
                "ESCROW_WALLET_ADDRESS (%s) does not match the address derived from "
                "ESCROW_WALLET_MNEMONIC (%s) -- quotes and payouts will disagree on "
                "where funds live. Fix this before accepting real payments.",
                settings.ESCROW_WALLET_ADDRESS, derived,
            )
        else:
            logger.info("Escrow wallet configured correctly: %s", derived)
    else:
        logger.warning(
            "ESCROW_WALLET_MNEMONIC is not set -- quotes will be issued but escrow "
            "release/refund payouts will fail until it is configured."
        )
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A marketplace where AI agents search for APIs, and pay for them via the "
        "x402 protocol into a platform-held escrow wallet -- not directly to the "
        "provider. Funds are only released to the provider once the paid API call "
        "has actually been proxied and confirmed successful; otherwise they're "
        "refunded back to the agent. No pay-and-pray."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_agents.router)
app.include_router(routes_listings.router)
app.include_router(routes_marketplace.router)
app.include_router(routes_purchase.router)
app.include_router(routes_escrow.router)
app.include_router(routes_dashboard.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "network": settings.ALGORAND_NETWORK, "escrow_wallet": settings.ESCROW_WALLET_ADDRESS}
