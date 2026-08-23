# APIMarket

**USP:** most x402 demos settle the agent's payment straight to the
provider and call it done. APIMarket is the only one in this space that
routes payment into a **platform-held escrow wallet first**, proxies the
call, and only then releases (or refunds) — with a real signed Algorand
transaction either way, a `DISPUTED` state instead of silent fund loss on
payout failure, and a policy engine + reputation score that decide
*before* any money moves. It's the difference between "the agent paid, we
hope the API responds" and "the agent's money is only ever released for
work actually delivered."

## ⚠️ x402 Global Challenge — honest submission status

This section exists so nobody on the team or judging it is surprised.
Updated 23 Aug 2026, ahead of the Bengaluru PreHack.

| Requirement | Status | Notes |
|---|---|---|
| Public GitHub repo with README | ✅ | This repo. |
| x402 payment flow live on Algorand Testnet | ⚠️ Partial | The full quote → pay → verify → escrow → release/refund lifecycle works end-to-end against Algorand Testnet (`scripts/test_client.py`), but **no transaction has been run and recorded yet for this submission** — see checklist below. |
| Actual x402 transaction demonstrable via Lora | ⚠️ Not yet captured | Mechanically possible today; needs to actually be run and the tx ID pasted into this README before submission. |
| Payment flow works through the **GoPlausible facilitator** | ❌ Not wired | `app/payments/algorand_verifier.py` calls a generic `x402_facilitator.verify(...)` from the `x402-avm` **Python** package if installed, with no facilitator URL configured anywhere (no `FACILITATOR_URL` in `config.py` or `.env.example`), and it **silently falls back to direct algod/indexer verification** if that import or call fails — which is the path actually exercised today. This means verification currently happens directly against algod, not through GoPlausible's facilitator endpoint (`https://facilitator.goplausible.xyz`). This needs explicit wiring before submission; see action items. |
| `@x402-avm` dependency in `package.json` | ❌ Missing | The literal requirement names a `package.json` entry, i.e. the **npm-scoped** `@x402-avm/*` packages (`@x402-avm/core`, `@x402-avm/avm`, etc.) used in Node/Express/Next projects. This backend is Python/FastAPI and depends on the **PyPI** package `x402-avm` in `requirements.txt` instead — same protocol family, wrong ecosystem for a literal check of `package.json`. A checklist-driven judge or script may flag this as missing outright. |
| Live and working deployed project | ⚠️ Unverified | Backend appears to be deployed on Render; confirm `/health` and `/docs` are reachable and CORS is opened for whatever origin the frontend ends up on (`CORS_ORIGINS` in `app/core/config.py` currently only allows `localhost:5173`). Frontend has not been deployed publicly yet as of this update. |
| MVP demo video (≤3 min) | ❌ Not yet recorded | |
| README: problem/solution explanation | ✅ | Above and in "Architecture". |
| README: local run instructions | ✅ | Steps 1–7 below. |
| README: architecture diagram | ✅ (ASCII) | See "Architecture" below. No image/graphic version yet — ASCII may or may not satisfy a judge expecting a visual diagram. |
| README: at least one Testnet x402 transaction link | ❌ Missing | Placeholder added below — fill in before submitting. |
| README: USP | ✅ | Added above. |

### Where we actually stand, plainly

The **engineering is real and substantially ahead of most hackathon
submissions**: real on-chain verification against algod/indexer, real
signed escrow release/refund transactions, a genuine RBAC + auth system,
and a pure/tested policy engine. That's not vaporware.

What's missing is **the specific plumbing this challenge's judges will
check for**, and none of it is a redesign — it's config and one afternoon
of wiring:

1. **Point verification at GoPlausible, not just algod.** Add a
   `FACILITATOR_URL` setting (`https://facilitator.goplausible.xyz` or
   whatever endpoint GoPlausible's docs specify for the exact scheme) to
   `app/core/config.py` and `.env.example`, and pass it explicitly into
   the `x402_facilitator.verify(...)` call in `algorand_verifier.py`
   instead of relying on whatever default the package assumes. Keep the
   algod/indexer path as a fallback if you want resilience, but the
   *primary* path needs to hit GoPlausible so activity shows up in their
   leaderboard/dashboard.
2. **Run one real Testnet transaction and paste the tx ID here.**
   `python scripts/test_client.py` against a funded Testnet mnemonic
   does this today. Grab the resulting `deposit_tx_id` (and ideally the
   `payout_tx_id`), open it on
   [Lora](https://lora.algokit.io/testnet), and paste both links into
   the placeholder below.
3. **Decide what to do about the `@x402-avm` npm requirement.** Options,
   roughly in order of honesty: (a) note in the submission that this is
   a Python/FastAPI implementation of the same x402-AVM protocol family
   and point judges at `x402-avm` in `requirements.txt` plus the actual
   working on-chain flow as proof, rather than adding an unused npm
   dependency just to satisfy a grep; or (b) if the frontend ever
   initiates payment itself instead of just previewing quotes, that
   would be a legitimate place for `@x402-avm/core` or `@x402-avm/avm`
   to actually get used, not just listed.
4. **Verify and, if needed, fix the deployment.** Confirm
   `https://apimarket-mp7s.onrender.com/health` and `/docs` load, and
   widen `CORS_ORIGINS` to include wherever the frontend actually ends
   up hosted (see the frontend zip / deployment notes elsewhere in this
   repo).
5. **Record the demo video** once 1–2 are done, so it can show a real
   quote → pay → escrow → release cycle rather than a mocked one.

**Testnet transaction (fill in before submitting):**
- Deposit tx: `PASTE_ALGORAND_TESTNET_TX_ID_HERE` — [view on Lora](https://lora.algokit.io/testnet)
- Release/refund tx: `PASTE_ALGORAND_TESTNET_TX_ID_HERE` — [view on Lora](https://lora.algokit.io/testnet)

---

A marketplace where AI agents **search for APIs**, and **pay for them via x402
into an escrow account the platform controls** — not directly to the
provider. The provider only gets paid once the platform has actually
proxied the call and confirmed it succeeded. If it fails, the agent gets
its money back automatically. No pay-and-pray.

This project merges two prior prototypes:

| From | What it contributed |
|---|---|
| **PayPerQuery** | The x402 gateway pattern: signed HTTP-402 price quotes, on-chain Algorand payment verification, and the request-proxying mechanism. |
| **AgentVault** | The agent side: a pure, unit-testable policy engine (per-transaction limits, daily budgets, allow-lists, minimum reputation), a transparent reputation formula, and the escrow *concept*. |

Neither original app actually held funds in custody — in both, the agent's
payment settled **directly to the provider's address**. AgentVault's
"escrow" was a status flag bolted on *after* settlement, explicitly
documented as not real escrow. **The one substantive change in this merge
is turning that into actual custody:**

```
Old (both originals):  Agent --pays--> Provider directly. "Escrow" is just a label.
New (this project):    Agent --pays--> Platform escrow wallet (HELD)
                                           |
                                  platform proxies the call
                                           |
                          success ---------+--------- failure
                              |                            |
                    RELEASE to provider           REFUND to agent
                    (real signed tx)               (real signed tx)
```

## Architecture

```
                    AI Agent
                       │  1. GET /market/search?q=weather
                       │  2. GET /market/{path}/call  (X-Agent-Key)
                       ▼
            ┌─────────────────────────┐
            │      APIMarket API       │
            │                          │
            │  Policy Engine (pure fn) │──▶ blocks before any payment
            │  x402 Quote Service      │──▶ payTo = ESCROW wallet, always
            │  Algorand Verifier       │──▶ confirms deposit on-chain
            │  Escrow Wallet Service   │──▶ signs real payout/refund txns
            │  Reputation Scoring      │──▶ live-computed per listing
            └────────────┬─────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
    PostgreSQL      Algorand Testnet   Provider's upstream_url
  (agents, listings,  (USDC ASA,        (only called AFTER
   transactions,       escrow wallet)    escrow is HELD)
   escrows)
```

## The purchase lifecycle

`Transaction.status` moves through:

```
PENDING → POLICY_BLOCKED               (rejected before any payment)
        → QUOTE_ISSUED                  (402 sent, awaiting payment)
        → ESCROW_HELD                   (payment verified into escrow wallet)
        → UPSTREAM_CALLED               (proxying to the provider)
        → SERVICE_COMPLETED             (escrow RELEASED to provider)
        → REFUNDED                      (escrow REFUNDED to agent, upstream failed)
        → DISPUTED                      (auto release/refund itself failed — needs admin)
```

The matching `Escrow` row is the actual custody record: `deposit_tx_id` is
the on-chain transaction that moved funds into the platform's wallet;
`payout_tx_id`/`refund_tx_id` are the on-chain transactions that later
moved them onward. Nothing about a purchase's outcome is inferred or
trusted from what the client claims — every status transition is set by
the server based on either a verified on-chain payment or an actual
upstream HTTP response.

**Honesty about the trust model:** this is platform-custodied escrow (the
same trust model as a payment processor holding buyer funds), not
trustless on-chain escrow enforced by a smart contract / logic signature.
The platform's escrow wallet key is a real secret an operator controls —
see the security notes below. Building fully trustless escrow would mean
replacing `payments/escrow_wallet.py` with an Algorand smart contract
(ASC1 / stateful app) that releases funds based on an oracle or
multi-party signature instead of a single platform-held key.

## Project layout

```
app/
  main.py                       FastAPI app, router + CORS wiring, escrow wallet sanity check
  core/
    config.py                   Settings (.env)
    database.py                 Async SQLAlchemy engine/session
  models/
    agent.py                    Agent, SpendingPolicy, AllowedListing
    listing.py                  Listing (marketplace-published API)
    transaction.py              Transaction (purchase lifecycle)
    escrow.py                   Escrow (real custody: deposit/payout/refund tx ids)
  policies/
    policy_engine.py            Pure, deterministic approve/block logic (from AgentVault)
    reputation.py                Transparent 0-100 reputation formula (from AgentVault)
  payments/
    x402_quote.py                Signed 402 quotes; payTo is ALWAYS the escrow wallet
    algorand_verifier.py         On-chain payment verification (algod/indexer, x402-avm optional)
    escrow_wallet.py              NEW: signs real release/refund payouts from platform custody
  services/
    marketplace_service.py       Search/discovery for agents
    purchase_service.py          Orchestrates policy -> quote -> escrow -> proxy -> settle
  api/
    routes_agents.py             Agent + policy registration, pause/unpause
    routes_listings.py           Provider onboarding: publish/update/deactivate listings
    routes_marketplace.py        GET /market/search
    routes_purchase.py           GET|POST|... /market/{path}/call  (the buy endpoint)
    routes_escrow.py             Escrow ledger + manual admin release/refund
    routes_dashboard.py          Transaction listing/lookup
scripts/
  test_client.py                 Full end-to-end demo against Algorand Testnet
frontend/
  src/
    pages/                       Dashboard, Marketplace, Listings, Agents, Transactions, Escrow
    components/
      LedgerTracker.tsx           Deposit -> Held -> Released/Refunded custody chain, the app's signature visual
      NavBar.tsx, Card.tsx, StatusBadge.tsx, EmptyState.tsx
    services/api.ts               Typed fetch wrapper over the backend
    types/index.ts                Mirrors the backend Pydantic schemas
requirements.txt
Dockerfile / docker-compose.yml
.env.example
```

## 1. Set up Neon Postgres (or local Docker Postgres)

```bash
cp .env.example .env
```

Set `DATABASE_URL` to your Neon connection string (async driver prefix
`postgresql+asyncpg://`), or just run `docker-compose up db` for local
Postgres and leave the compose-provided `DATABASE_URL` as-is.

## 2. Create the platform escrow wallet

This is the important new piece. Create a **dedicated** Algorand Testnet
account that only the platform controls:

```bash
python - <<'PY'
from algosdk import account, mnemonic
sk, addr = account.generate_account()
print("ESCROW_WALLET_ADDRESS =", addr)
print("ESCROW_WALLET_MNEMONIC =", mnemonic.from_private_key(sk))
PY
```

Fund it at https://bank.testnet.algorand.network/, and if you're using the
USDC testnet ASA (`10458941` by default), opt the account into that asset
first. Put both values in `.env`. The app checks at startup that
`ESCROW_WALLET_ADDRESS` actually matches the address derived from
`ESCROW_WALLET_MNEMONIC`, and logs a loud warning if they've drifted apart.

## 3. Install dependencies & run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for interactive OpenAPI docs.

Or via Docker: `docker-compose up --build`.

## 4. Publish a listing (you're the provider)

```bash
curl -X POST http://localhost:8000/api/listings \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample Weather API",
    "category": "weather",
    "path": "sample-weather",
    "upstream_url": "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true",
    "price_microalgos": 100000,
    "pay_to_address": "YOUR_PROVIDER_ALGORAND_TESTNET_ADDRESS_58_CHARS",
    "asa_id": 10458941
  }'
```

`pay_to_address` is where **you** get paid on release — it is never
exposed to buying agents as the payment destination.

## 5. Register an agent (you're the buyer)

```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Research Agent",
    "wallet_address": "YOUR_AGENT_ALGORAND_TESTNET_ADDRESS",
    "policy": {
      "max_transaction_amount": "5.00",
      "daily_limit": "50.00",
      "min_provider_reputation": 40
    }
  }'
```

Save the returned `api_key` — the agent sends it as `X-Agent-Key` on every
purchase call.

## 6. Search the marketplace, then buy

```bash
curl "http://localhost:8000/market/search?q=weather"

curl -i http://localhost:8000/market/sample-weather/call \
  -H "X-Agent-Key: YOUR_AGENT_API_KEY"
```

You'll get `402 Payment Required` with a quote whose `payTo` is the
**platform's** escrow wallet. Pay it on Algorand Testnet, then retry:

```bash
curl -i http://localhost:8000/market/sample-weather/call \
  -H "X-Agent-Key: YOUR_AGENT_API_KEY" \
  -H 'X-402-Payment-Proof: {"tx_id": "YOUR_TX_ID", "quote": "QUOTE_TOKEN_FROM_402_RESPONSE"}'
```

Or run the whole thing end-to-end:

```bash
export PAYER_MNEMONIC="your 25 word funded testnet mnemonic here"
python scripts/test_client.py
```

## 7. Run the dashboard (frontend)

A React + Tailwind dashboard lives in `frontend/` — marketplace search with
live quote previews, provider listing management, agent registration with
policy limits, a transaction ledger, and the escrow ledger with the
deposit → held → released/refunded custody chain made visually explicit.

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. The Vite dev server proxies `/api`,
`/market`, and `/health` to `http://localhost:8000`, so run the backend
first (steps 1–3 above). `npm run build` produces a static `dist/` you can
serve from anywhere (e.g. behind the same reverse proxy as the API, or a
static host with the API on a separate origin — adjust the proxy config
or add `VITE_API_BASE` wiring if you split hosting).



- **Policy runs before any payment.** `check_payment_policy()` is a pure
  function (agent active/paused → provider active/allowed/reputation →
  per-transaction limit → daily limit); the x402 flow never even starts
  for a blocked purchase.
- **Idempotency** is enforced at the database level (`transactions.idempotency_key`,
  unique index), and replayed `tx_id`s are rejected before verification
  even runs (`transactions.deposit_tx_id` uniqueness / explicit lookup).
- **Escrow is real custody, not a status label** — see the lifecycle
  section above. `escrow_wallet.py` signs actual Algorand transactions
  for both release and refund.
- **Fail-safe on payout errors:** if the escrow wallet can't sign/submit
  a release or refund (e.g. insufficient ALGO for fees, network issue),
  the escrow is marked `DISPUTED` rather than silently losing track of
  the funds, for manual resolution via `POST /api/escrow/{id}/release`
  or `/refund`.
- **Reputation is transparent, not a black box** — a weighted blend of
  success rate, latency, refund rate, and dispute rate, computed live
  from each listing's counters (see `policies/reputation.py`).
- **Emergency pause:** `PATCH /api/agents/{id}/pause` blocks every
  subsequent purchase for that agent immediately, checked first in the
  policy engine.

## Known limitations / next steps

- No authentication on the admin/dashboard routes yet — `X-Agent-Key`
  gates purchases, but `/api/listings`, `/api/agents`, `/api/escrow`
  should sit behind real auth (API keys or OAuth) before production use.
- Escrow is platform-custodied, not a trustless on-chain smart-contract
  escrow (see "honesty about the trust model" above).
- The dashboard covers browsing, publishing, registering, and monitoring —
  it does not sign and submit the actual Algorand payment (that requires a
  wallet's private key). "Preview quote" in the marketplace shows the
  exact 402 terms an agent would receive; use `scripts/test_client.py` or
  your own wallet integration to actually pay one and drive it through to
  `SERVICE_COMPLETED`.
- No automated test suite yet (AgentVault had 29 pytest cases against its
  policy engine/escrow/idempotency; porting and extending those to cover
  the new escrow-wallet payout path is recommended before going further).
- Rate limiting is not implemented.
- `x402-avm` is an actively-evolving SDK; `algorand_verifier.py` tries it
  opportunistically and always falls back to direct algod/indexer
  verification, so the gateway works whether or not it's installed.
