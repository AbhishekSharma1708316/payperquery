import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card } from "../components/Card";
import type { Agent } from "../types";

export default function SecurityPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    setAgents(await api.listAgents());
  }

  useEffect(() => {
    load();
  }, []);

  const anyPaused = agents.some((a) => a.is_paused);
  const allPaused = agents.length > 0 && agents.every((a) => a.is_paused);

  async function pauseAll() {
    setBusy(true);
    try {
      await Promise.all(agents.map((a) => api.setPause(a.id, true)));
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function resumeAll() {
    setBusy(true);
    try {
      await Promise.all(agents.map((a) => api.setPause(a.id, false)));
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Security &amp; Policies</h1>

      <Card className={allPaused ? "border-vault-danger/60" : ""}>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold">Emergency controls</h2>
            <p className="mt-1 text-sm text-slate-400">
              Immediately pauses every agent. Paused agents are blocked by the policy engine
              before any x402 payment is attempted.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={pauseAll}
              disabled={busy || agents.length === 0}
              className="rounded-lg bg-vault-danger px-4 py-2 text-sm font-bold text-white hover:brightness-110 disabled:opacity-50"
            >
              PAUSE ALL PAYMENTS
            </button>
            {anyPaused && (
              <button
                onClick={resumeAll}
                disabled={busy}
                className="rounded-lg border border-vault-border px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-vault-border"
              >
                Resume all
              </button>
            )}
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="mb-4 font-semibold">Per-agent policies</h2>
        <div className="space-y-3">
          {agents.map((a) => (
            <div
              key={a.id}
              className="flex items-center justify-between rounded-lg border border-vault-border p-3"
            >
              <div>
                <div className="font-medium">
                  {a.name}{" "}
                  {a.is_paused && (
                    <span className="ml-2 rounded-full bg-red-900/60 px-2 py-0.5 text-xs text-red-300">
                      PAUSED
                    </span>
                  )}
                </div>
                {a.policy && (
                  <div className="mt-1 text-xs text-slate-500">
                    Per-tx: ${Number(a.policy.max_transaction_amount).toFixed(2)} · Daily: $
                    {Number(a.policy.daily_limit).toFixed(2)} · Min reputation:{" "}
                    {a.policy.min_provider_reputation} · Allowed providers:{" "}
                    {a.policy.allowed_provider_ids.length}
                  </div>
                )}
              </div>
            </div>
          ))}
          {agents.length === 0 && <p className="text-sm text-slate-500">No agents configured yet.</p>}
        </div>
      </Card>
    </div>
  );
}
