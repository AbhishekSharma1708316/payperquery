# AgentVault — 3-Minute Demo Script

**Setup before recording:** backend running (`uvicorn app.main:app --reload`),
frontend running (`npm run dev`), one Algorand Testnet address funded with
test USDC as the demo provider's `pay_to_address`.

---

### 0:00 – 0:20 — The problem

"AI agents need money to use paid services, but you should never have to
give an autonomous agent unlimited spending authority. AgentVault is
programmable financial control for agent payments, built on x402."

### 0:20 – 0:50 — Create an agent with a policy

- Open the dashboard → **Agents** → **Create Agent**
- Name: `ResearchBot`
- Per-transaction limit: `$0.10`
- Daily limit: `$5.00`
- Allowed providers: Search API, Weather API, OCR API
- Show the created agent card with its policy visible

### 0:50 – 1:30 — Successful payment

- Trigger a request: ResearchBot calls the Search API for `$0.03`
- Narrate live: "Policy engine checks: provider allowed ✓, reputation 96/100 ✓,
  under transaction limit ✓, under daily budget ✓ — payment proceeds."
- Show the x402 402 challenge → signed Algorand USDC payment → verified
- Transaction appears in the **Transactions** table with status
  `PAYMENT_VERIFIED`, tagged with the real Algorand tx id

### 1:30 – 2:10 — Blocked payment (the security moment)

- Trigger a request: ResearchBot attempts to spend `$2.00`
- Show the **PAYMENT BLOCKED** response *before* any chain interaction:
  ```
  PAYMENT BLOCKED
  Reason: Transaction exceeds agent spending policy.
  Requested: $2.00
  Maximum allowed: $0.10
  ```
- Emphasize: "No blockchain payment occurred. The policy engine caught
  this before x402 was ever invoked."

### 2:10 – 2:35 — Provider reputation + emergency pause

- Switch to **Providers** tab: show reputation score, success rate,
  latency — explain the formula is transparent, not a black box
- Switch to **Security / Policies** tab, hit **PAUSE ALL PAYMENTS**
- Attempt another payment → blocked with `AGENT_PAUSED`
- Unpause

### 2:35 – 3:00 — Close

- Show the dashboard: today's spending, blocked count, average
  transaction value, all updating live
- "That's AgentVault — Stripe-style spending controls for autonomous
  agent payments, built on the x402 protocol on Algorand."
