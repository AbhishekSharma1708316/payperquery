# AgentVault — Trustworthy Payments for AI Agents

## 1. Problem

AI agents increasingly need to pay for things autonomously — APIs, data,
compute, tools — but handing an autonomous agent an unlimited-spend wallet
is a real financial risk. Existing "agent + wallet" demos skip the part
that makes this safe to actually deploy: programmable, enforced spending
controls that sit *between* the agent and the money.

## 2. Solution

AgentVault is a policy-gated payment gateway for AI agents using the x402
protocol. Every payment an agent attempts is checked against a
per-transaction limit, a daily budget, an allowed-provider list, and a
provider reputation threshold — **before** any on-chain payment is
attempted. Blocked payments never reach the blockchain. All payments and
policy decisions are logged for audit.

## 3. Why x402

x402 turns HTTP 402 Payment Required into an actual, machine-executable
payment protocol: a resource server can require payment inline in the
HTTP exchange, and a client (here, AgentVault acting for an agent) can
satisfy that requirement with a signed, verifiable payment before
retrying the request. This is what lets an agent's payments be verified
independently rather than trusted on the client's word.

**Network used:** Algorand Testnet (AVM), via the official `x402-avm`
Python SDK's FastAPI integration, using USDC as the payment asset and
Coinbase's public facilitator (`https://x402.org/facilitator`) for
protocol-conformant settlement/verification.

## 4. Architecture

```
                    ┌─────────────────────────┐
                    │       React Frontend    │
                    │  Dashboard / Policies /  │
                    │  Transactions / Providers│
                    └────────────┬────────────┘
                                 │ REST (JSON)
                                 ▼
                    ┌─────────────────────────┐
                    │       FastAPI Backend    │
                    │                          │
                    │ Policy Engine (pure fn)  │
                    │ Payment Service          │
                    │ Reputation Scoring       │
                    │ Escrow Service (app-level)│
                    └────────────┬────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
          PostgreSQL      x402-avm SDK      Mock Provider
        (agents, policies  (facilitator:    (x402-avm-protected
         providers, txns,   x402.org)        demo endpoints)
         escrow)                 │
                                  ▼
                          Algorand Testnet
                             (USDC ASA)
```

## 5. How AgentVault protects autonomous agents

- **Policy engine runs BEFORE payment.** `check_payment_policy()` in
  `backend/app/policies/policy_engine.py` is a pure, deterministic
  function — no I/O, fully unit-tested — checked in a fixed order: agent
  active/paused → provider active/allowed/reputation → per-transaction
  limit → daily limit. The first failing check blocks the payment; the
  x402 payment flow is never initiated for a blocked request.
- **Independent verification.** The backend never marks a transaction
  successful because a client said so. `POST /api/payments/{id}/verify`
  re-reads the server-recorded status, which is only ever set by
  `payment_service.py` based on actual policy/x402 outcomes.
- **Idempotency is enforced at the database level** via a unique index on
  `transactions.idempotency_key` — not just an in-memory check — so a
  retried request can never double-charge even under concurrent retries.
- **Emergency pause.** `PATCH /api/agents/{id}/pause` sets `is_paused`,
  which the policy engine checks first; every subsequent payment attempt
  is blocked with `AGENT_PAUSED` until unpaused.
- **Provider reputation is transparent, not a black box.** See
  `backend/app/policies/reputation.py` for the explainable weighted
  formula (success rate, latency, refund rate, dispute rate) — deliberately
  not framed as an "AI fraud model."
- **Escrow is explicitly application-level.** `backend/app/models/escrow.py`
  documents and enforces the distinction: x402 payment settlement (via
  the facilitator) is final once confirmed; AgentVault's escrow tracks
  whether the *task result* was accepted, as a separate workflow signal,
  not an automatic on-chain clawback.

## 6. Setup instructions

### Prerequisites
- Python 3.11+
- PostgreSQL (or use `docker-compose up db` for a local instance)
- Node.js 18+ (for the frontend)
- An Algorand Testnet address to receive demo payments (see step 4)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## 7. Environment variables

Edit `backend/.env`:

| Variable | Description |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/agentvault` |
| `X402_FACILITATOR_URL` | Defaults to Coinbase's public testnet facilitator |
| `ALGORAND_NETWORK_CAIP2` | Algorand Testnet CAIP-2 ID (default already set) |
| `USDC_TESTNET_ASA_ID` | Testnet USDC ASA ID (default already set) |
| `MOCK_PROVIDER_PAY_TO` | Your Algorand Testnet address to receive demo payments |
| `SECRET_KEY` | Any long random string |
| `CORS_ORIGINS` | Frontend origin(s), JSON list |

## 8. Database setup

```bash
cd backend
alembic upgrade head
```

(In `ENVIRONMENT=development`, the app also auto-creates tables on
startup as a convenience — Alembic is the source of truth for anything
beyond local iteration.)

## 9. Running backend

```bash
cd backend
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive OpenAPI docs. The mock
provider (`/mock-provider/search`, `/mock-provider/weather`,
`/mock-provider/ocr`) is mounted on the same app, protected by the real
`x402-avm` payment middleware.

Or via Docker:
```bash
docker-compose up --build
```

## 10. Running frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

## 11. Running tests

```bash
cd backend
pytest -q
```

29 tests covering: policy engine (all block reasons, boundary conditions),
reputation formula, idempotency (service-level and HTTP-level), the full
approve/block demo scenario, agent pause/unpause, escrow state machine,
and dashboard aggregation.

## 12. Demo flow

See `DEMO_SCRIPT.md` for the full 3-minute walkthrough.

## 13. Security model

- No private keys or mnemonics are ever logged (see `payment_service.py`
  and `x402_client.py` — only transaction IDs and public addresses appear
  in logs).
- `X-Payer-Mnemonic` header (demo/test convenience only) is never
  persisted — it's used in-memory for a single signing operation and
  discarded.
- All monetary values use `Decimal`/SQL `Numeric`, never floats.
- CORS is explicitly configured (`CORS_ORIGINS`), not wildcarded in
  production.
- Every financial state transition goes through a single service
  function (`process_payment_request`) so there is one, auditable code
  path for how a transaction's status can change.

## 14. Known limitations

- The client-side x402 signing path (`payments/x402_client.py`) submits
  directly to Algorand via `algosdk` rather than through a higher-level
  `x402-avm` client convenience wrapper, because that client-side API
  surface was less consistently documented than the server-side
  (FastAPI resource-server) API at the time of writing. It is
  protocol-correct but hasn't been screened against every future
  `x402-avm` client SDK convenience method.
- Escrow is an explicit application-level abstraction, not on-chain
  escrow — see section 5.
- No authentication/authorization layer beyond basic input validation;
  this is an MVP and would need real auth before handling production
  funds.
- Rate limiting is not yet implemented.
- The frontend covers the core demo flow; it is not a fully production
  hardened dashboard (no auth, no pagination edge cases beyond basic
  limits).

## 15. Future roadmap

- Real auth (API keys or OAuth) scoping which agents a caller can act on
  behalf of.
- Webhook/callback verification for provider task-result confirmation to
  drive automatic escrow release.
- Multi-network support (beyond Algorand Testnet) once `x402-avm`'s
  mainnet path is production-ready.
- Rate limiting and anomaly detection on top of the existing reputation
  system.
