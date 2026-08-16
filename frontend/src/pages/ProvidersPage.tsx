import { useEffect, useState } from "react";
import { api, ApiError } from "../services/api";
import { Card } from "../components/Card";
import type { Provider } from "../types";

function ReputationBar({ score }: { score: number }) {
  const color = score >= 80 ? "bg-vault-success" : score >= 50 ? "bg-vault-warn" : "bg-vault-danger";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-vault-border">
        <div className={`h-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-400">{score}/100</span>
    </div>
  );
}

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [category, setCategory] = useState("search");
  const [price, setPrice] = useState("0.03");
  const [payTo, setPayTo] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setProviders(await api.listProviders());
  }

  useEffect(() => {
    load();
  }, []);

  function randomAddress() {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    return Array.from({ length: 58 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  }

  async function createProvider() {
    setError(null);
    try {
      await api.createProvider({
        name,
        endpoint,
        category,
        price_usd: price,
        pay_to_address: payTo || randomAddress(),
      });
      setShowForm(false);
      setName("");
      setEndpoint("");
      setPayTo("");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create provider");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Providers</h1>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded-lg bg-vault-accent px-4 py-2 text-sm font-semibold text-vault-bg hover:brightness-110"
        >
          {showForm ? "Cancel" : "+ Add Provider"}
        </button>
      </div>

      {showForm && (
        <Card>
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
              <label className="block text-xs text-slate-500">Category</label>
              <input
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-slate-500">Endpoint URL</label>
              <input
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="http://localhost:8000/mock-provider/search"
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500">Price (USD)</label>
              <input
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500">
                Pay-to address (leave blank to auto-generate a demo address)
              </label>
              <input
                value={payTo}
                onChange={(e) => setPayTo(e.target.value)}
                className="mt-1 w-full rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-sm font-mono"
              />
            </div>
          </div>
          {error && <p className="mt-3 text-sm text-vault-danger">{error}</p>}
          <button
            onClick={createProvider}
            className="mt-4 rounded-lg bg-vault-accent px-4 py-2 text-sm font-semibold text-vault-bg hover:brightness-110"
          >
            Add provider
          </button>
        </Card>
      )}

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-vault-border text-xs uppercase text-slate-500">
                <th className="py-2 pr-4">Provider</th>
                <th className="py-2 pr-4">Category</th>
                <th className="py-2 pr-4">Price</th>
                <th className="py-2 pr-4">Reputation</th>
                <th className="py-2 pr-4">Success rate</th>
                <th className="py-2 pr-4">Latency</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => {
                const total = p.successful_transactions + p.failed_transactions;
                const successRate = total > 0 ? Math.round((p.successful_transactions / total) * 100) : 100;
                return (
                  <tr key={p.id} className="border-b border-vault-border/50">
                    <td className="py-2 pr-4">
                      <div className="font-medium">{p.name}</div>
                      <div className="font-mono text-xs text-slate-500">{p.pay_to_address.slice(0, 16)}…</div>
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{p.category}</td>
                    <td className="py-2 pr-4 font-mono">${Number(p.price_usd).toFixed(2)}</td>
                    <td className="py-2 pr-4">
                      <ReputationBar score={p.reputation_score} />
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{successRate}%</td>
                    <td className="py-2 pr-4 text-slate-400">{p.average_latency_ms}ms</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {providers.length === 0 && (
            <p className="py-4 text-sm text-slate-500">No providers yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
