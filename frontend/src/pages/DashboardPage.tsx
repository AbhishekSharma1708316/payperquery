import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card, StatCard } from "../components/Card";
import StatusBadge from "../components/StatusBadge";
import type { DashboardStats, Transaction } from "../types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [s, txns] = await Promise.all([
        api.dashboardStats(),
        api.listTransactions(),
      ]);
      setStats(s);
      setRecent(txns.slice(0, 8));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <Card className="border-vault-danger/50">
        <p className="text-vault-danger">Could not reach the backend: {error}</p>
        <p className="mt-2 text-sm text-slate-400">
          Make sure the API is running at <code>http://localhost:8000</code>.
        </p>
      </Card>
    );
  }

  if (!stats) {
    return <p className="text-slate-400">Loading dashboard…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Today's spending" value={`$${Number(stats.today_spending).toFixed(2)}`} />
        <StatCard
          label="Successful payments today"
          value={stats.successful_payments_today}
          tone="success"
        />
        <StatCard
          label="Blocked payments today"
          value={stats.blocked_payments_today}
          tone={stats.blocked_payments_today > 0 ? "danger" : "default"}
        />
        <StatCard
          label="Avg transaction value"
          value={`$${Number(stats.average_transaction_value).toFixed(4)}`}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-2">
        <StatCard label="Total agents" value={stats.total_agents} />
        <StatCard label="Total providers" value={stats.total_providers} />
      </div>

      <Card>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Recent transactions
        </h2>
        {recent.length === 0 ? (
          <p className="text-sm text-slate-500">No transactions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-vault-border text-xs uppercase text-slate-500">
                  <th className="py-2 pr-4">Time</th>
                  <th className="py-2 pr-4">Amount</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Reason</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((t) => (
                  <tr key={t.id} className="border-b border-vault-border/50">
                    <td className="py-2 pr-4 text-slate-400">
                      {new Date(t.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-2 pr-4 font-mono">${Number(t.amount).toFixed(4)}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{t.failure_reason ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
