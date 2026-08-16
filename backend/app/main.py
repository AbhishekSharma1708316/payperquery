import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_agents,
    routes_dashboard,
    routes_escrow,
    routes_payments,
    routes_providers,
    routes_transactions,
)
from app.core.config import get_settings
from app.core.database import init_models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentvault.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT == "development":
        await init_models()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AgentVault: programmable spending controls for AI agents paying "
        "autonomously via the x402 protocol on Algorand."
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
app.include_router(routes_providers.router)
app.include_router(routes_payments.router)
app.include_router(routes_transactions.router)
app.include_router(routes_escrow.router)
app.include_router(routes_dashboard.router)

try:
    from app.payments.mock_provider import build_mock_provider_app

    app.mount("/", build_mock_provider_app())
    logger.info("Mock provider mounted with real x402-avm payment middleware")
except ImportError as exc:
    logger.warning(
        "x402-avm not installed; mock provider endpoints disabled. "
        "Install with `pip install \"x402-avm[fastapi,avm]\"` to enable them. (%s)",
        exc,
    )


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "network": settings.ALGORAND_NETWORK_CAIP2}
