import { useEffect, useState } from "react";
import { api, ApiError } from "../services/api";
import { Card } from "../components/Card";
import type { Agent, PaymentResult, Provider } from "../types";

function BlockedBanner({ result }: { result: PaymentResult }) {
  const t = result.transaction;
  return (
    <div className="mt-3 rounded-lg border border-vault-danger/60 bg-red-950/40 p-4">
      <div className="font-semibold text-vault-danger">PAYMENT BLOCKED</div>
      <div className="mt-1 text-sm text-slate-300">
        Reason: <span className="font-mono">{t.failure_reason}</span>
      </div>
      <div className="mt-1 text-sm text-slate-400">
        Requested: ${Number(t.amount).toFixed(2)}
      </div>
      <div className="mt-2 text-xs text-slate-500">
        No blockchain payment was attempted for this request.
      </div>
    </div>
  );
}

function ApprovedBanner({ result }: { result: PaymentResult }) {
  const t = result.transaction;
  return (
    <div className="mt-3 rounded-lg border border-vault-success/60 bg-emerald-950/40 p-4">
      <div className="font-semibold text-vault-success">Payment approved</div>
      <div className="mt-1 text-sm text-slate-300">
        Status: <span className="font-mono">{t.status}</span> · Amount: $
        {Number(t.amount).toFixed(4)} · Risk score: {t.risk_score ?? "—"}
      </div>
      {t.payment_reference && (
        <div className="mt-1 truncate text-xs text-slate-500">Tx ref: {t.payment_reference}</div>
      )}
    </div>
  );
}

function AgentCard({ agent, providers, onChanged }: { agent: Agent; providers: Provider[]; onChanged: () => void }) {
  const [amount, setAmount] = useState("0.03");
  const [providerId, setProviderId] = useState(providers[0]?.id ?? "");
  const [result, setResult] = useState<PaymentResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!providerId && providers[0]) setProviderId(providers[0].id);
  }, [providers]);

  async function pay() {
    if (!providerId) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.requestPayment(
        { agent_id: agent.id, provider_id: providerId, amount, currency: "USDC" },
        `demo-${agent.id}-${Date.now()}`,
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Payment request failed");
    } finally {
      setBusy(false);
    }
  }

  async function togglePause() {
    await api.setPause(agent.id, !agent.is_paused);
    onChanged();
  }

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold">{agent.name}</h3>
          <p className="mt-0.5 font-mono text-xs text-slate-500">{agent.wallet_address}</p>
        </div>
        <button
          onClick={togglePause}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
            agent.is_paused
              ? "bg-vault-danger/20 text-vault-danger hover:bg-vault-danger/30"
              : "bg-vault-border text-slate-300 hover:bg-slate-700"
          }`}
        >
          {agent.is_paused ? "Paused — click to resume" : "Pause"}
        </button>
      </div>

      {agent.policy && (
        <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <div>
            <div className="text-xs text-slate-500">Per-tx limit</div>
            <div className="font-mono">${Number(agent.policy.max_transaction_amount).toFixed(2)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Daily limit</div>
            <div className="font-mono">${Number(agent.policy.daily_limit).toFixed(2)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Min reputation</div>
            <div className="font-mono">{agent.policy.min_provider_reputation}</div>
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-vault-border pt-4">
        <div>
          <label className="block text-xs text-slate-500">Provider</label>
          <select
            value={providerId}
            onChange={(e) => setProviderId(e.target.value)}
            className="mt-1 rounded-lg border border-vault-border bg-vault-bg px-2 py-1.5 text-sm"
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500">Amount (USD)</label>
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="mt-1 w-24 rounded-lg border border-vault-border bg-vault-bg px-2 py-1.5 text-sm font-mono"
          />
        </div>
        <button
          onClick={pay}
          disabled={busy || !providerId}
          className="rounded-lg bg-vault-accent px-4 py-1.5 text-sm font-semibold text-vault-bg hover:brightness-110 disabled:opacity-50"
        >
          {busy ? "Sending…" : "Attempt payment"}
        </button>
        <button
          onClick={() => setAmount("2.00")}
          className="rounded-lg border border-vault-border px-3 py-1.5 text-xs text-slate-400 hover:bg-vault-border"
        >
          Try $2.00 (should block)
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-vault-danger">{error}</p>}
      {result &&
        (result.transaction.status === "POLICY_BLOCKED" ? (
          <BlockedBanner result={result} />
        ) : (
          <ApprovedBanner result={result} />
        ))}
    </Card>
  );
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("ResearchBot");
  const [wallet, setWallet] = useState("");
  const [maxTx, setMaxTx] = useState("0.10");
  const [dailyLimit, setDailyLimit] = useState("5.00");
  const [minRep, setMinRep] = useState("50");
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [a, p] = await Promise.all([api.listAgents(), api.listProviders()]);
    setAgents(a);
    setProviders(p);
  }

  useEffect(() => {
    load();
  }, []);

  function randomAddress() {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    return Array.from({ length: 58 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  }

  async function createAgent() {
    setError(null);
    try {
      await api.createAgent({
        name,
        wallet_address: wallet || randomAddress(),
        policy: {
          max_transaction_amount: maxTx,
          daily_limit: dailyLimit,
          min_provider_reputation: Number(minRep),
          allowed_provider_ids: selectedProviders,
        },
      });
      setShowForm(false);
      setWallet("");
      setSelectedProviders([]);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create agent");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Agents</h1>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded-lg bg-vault-accent px-4 py-2 text-sm font-semibold text-vault-bg hover:brightness-110"
        >
          {showForm ? "Cancel" : "+ Create Agent"}
        </button>
      </div>

      {showForm && (
        <Card>
          <h2 className="mb-4 font-semibold">New agent</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500">
                Wallet address (leave blank to auto-generate a demo address)
              </label>
              <input
                value={wallet}
                onChange={(e) => setWallet(e.target.value)}
                placeholder="Algorand address"
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500">Per-transaction limit ($)</label>
              <input
                value={maxTx}
                onChange={(e) => setMaxTx(e.target.value)}
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500">Daily limit ($)</label>
              <input
                value={dailyLimit}
                onChange={(e) => setDailyLimit(e.target.value)}
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500">Min provider reputation</label>
              <input
                value={minRep}
                onChange={(e) => setMinRep(e.target.value)}
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500">Allowed providers</label>
              <div className="mt-1 flex flex-wrap gap-2">
                {providers.map((p) => (
                  <label
                    key={p.id}
                    className="flex items-center gap-1.5 rounded-lg border border-vault-border px-2 py-1 text-xs"
                  >
                    <input
                      type="checkbox"
                      checked={selectedProviders.includes(p.id)}
                      onChange={(e) =>
                        setSelectedProviders((prev) =>
                          e.target.checked ? [...prev, p.id] : prev.filter((id) => id !== p.id),
                        )
                      }
                    />
                    {p.name}
                  </label>
                ))}
                {providers.length === 0 && (
                  <span className="text-xs text-slate-500">
                    No providers yet — create one on the Providers page first.
                  </span>
                )}
              </div>
            </div>
          </div>
          {error && <p className="mt-3 text-sm text-vault-danger">{error}</p>}
          <button
            onClick={createAgent}
            className="mt-4 rounded-lg bg-vault-accent px-4 py-2 text-sm font-semibold text-vault-bg hover:brightness-110"
          >
            Create
          </button>
        </Card>
      )}

      <div className="space-y-4">
        {agents.map((a) => (
          <AgentCard key={a.id} agent={a} providers={providers} onChanged={load} />
        ))}
        {agents.length === 0 && (
          <Card>
            <p className="text-sm text-slate-500">
              No agents yet. Create one above to try the payment policy demo.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
