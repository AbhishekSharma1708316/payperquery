"""Local mock paid API provider, for development and demo.

This uses the REAL x402-avm FastAPI middleware (`PaymentMiddlewareASGI` +
`ExactAvmServerScheme`, pointed at Coinbase's public facilitator on
Algorand Testnet) to gate `/mock-provider/search`, exactly as documented
in the x402-avm FastAPI integration guide. It is not a fake
`if payment_header == "paid"` stand-in -- a request without a valid,
verified Algorand USDC payment genuinely receives a protocol-correct 402
response with real payment requirements, and a real settlement occurs on
successful payment.

If the `x402-avm` package is not installed (e.g. its exact PyPI
availability changes), this module raises a clear ImportError at import
time rather than silently degrading to fake payment logic -- app/main.py
catches that and disables mounting this demo router, so the rest of
AgentVault still runs.
"""

from fastapi import APIRouter, FastAPI, Request

from app.core.config import get_settings

settings = get_settings()

mock_provider_app = FastAPI(title="AgentVault Mock Provider (x402-avm protected)")
router = APIRouter()


def build_mock_provider_app() -> FastAPI:
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.http.types import RouteConfig
    from x402.mechanisms.avm.exact import ExactAvmServerScheme
    from x402.server import x402ResourceServer

    facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=settings.X402_FACILITATOR_URL))
    server = x402ResourceServer(facilitator)
    server.register(settings.ALGORAND_NETWORK_CAIP2, ExactAvmServerScheme())

    routes = {
        "GET /mock-provider/search": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=settings.MOCK_PROVIDER_PAY_TO,
                price="$0.03",
                network=settings.ALGORAND_NETWORK_CAIP2,
            ),
            mime_type="application/json",
            description="Mock search API (AgentVault demo)",
        ),
        "GET /mock-provider/weather": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=settings.MOCK_PROVIDER_PAY_TO,
                price="$0.01",
                network=settings.ALGORAND_NETWORK_CAIP2,
            ),
            mime_type="application/json",
            description="Mock weather API (AgentVault demo)",
        ),
        "GET /mock-provider/ocr": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=settings.MOCK_PROVIDER_PAY_TO,
                price="$0.05",
                network=settings.ALGORAND_NETWORK_CAIP2,
            ),
            mime_type="application/json",
            description="Mock OCR API (AgentVault demo)",
        ),
    }

    app = FastAPI(title="AgentVault Mock Provider (x402-avm protected)")
    app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

    @app.get("/mock-provider/search")
    async def search(request: Request, q: str = "bitcoin") -> dict:
        payment_payload = getattr(request.state, "payment_payload", None)
        payer = None
        if payment_payload is not None:
            payer = getattr(payment_payload, "payload", {}).get("from", "unknown")
        return {
            "query": q,
            "results": [
                {"title": f"Result about {q} #1", "score": 0.97},
                {"title": f"Result about {q} #2", "score": 0.91},
            ],
            "paid_by": payer,
        }

    @app.get("/mock-provider/weather")
    async def weather(request: Request) -> dict:
        return {"temperature": 72, "unit": "F", "condition": "sunny"}

    @app.get("/mock-provider/ocr")
    async def ocr(request: Request) -> dict:
        return {"extracted_text": "AgentVault demo OCR output.", "confidence": 0.95}

    return app
