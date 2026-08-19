import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { Agent, Escrow, Listing, Transaction } from "../types";
import { Card, StatCard } from "../components/Card";
import StatusBadge from "../components/StatusBadge";
import EmptyState from "../components/EmptyState";
import { formatDate, formatMicro, shortAddr } from "../lib/format";

export default function DashboardPage() {
  const [health, setHealth] = useState<{ status: string; network: string; escrow_wallet: string } | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [escrows, setEscrows] = useState<Escrow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.health(),
      api.listAgents(),
      api.listListings(),
      api.listTransactions(),
      api.listEscrows(),
    ])
      .then(([h, a, l, t, e]) => {
        setHealth(h);
        setAgents(a);
        setListings(l);
        setTransactions(t);
        setEscrows(e);
      })
      .catch((err) => setError(err.message ?? "Could not reach the APIMarket API"))
      .finally(() => setLoading(false));
  }, []);

  const heldValue = escrows.filter((e) => e.status === "HELD").reduce((sum, e) => sum + e.amount_microalgos, 0);
  const releasedValue = escrows.filter((e) => e.status === "RELEASED").reduce((sum, e) => sum + e.amount_microalgos, 0);
  const refundedCount = escrows.filter((e) => e.status === "REFUNDED").length;
  const disputedCount = escrows.filter((e) => e.status === "DISPUTED").length;

  if (loading) {
    return <div className="text-sm text-paper-dim">Loading ledger…</div>;
  }

  if (error) {
    return (
      <Card className="border-vault-red/40">
        <p className="font-display text-sm font-medium text-vault-red">Can't reach the API</p>
        <p className="mt-1 text-xs text-paper-dim">{error} — is the backend running on the proxied port?</p>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-paper">Escrow overview</h1>
        <p className="mt-1 text-sm text-paper-dim">
          Funds currently in platform custody, and where they've gone once each purchase resolved.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Held in escrow" value={formatMicro(heldValue)} tone="brass" hint="awaiting outcome" />
        <StatCard label="Released to providers" value={formatMicro(releasedValue)} tone="green" hint="lifetime" />
        <StatCard label="Refunded to agents" value={String(refundedCount)} hint="purchases" />
        <StatCard
          label="Disputed"
          value={String(disputedCount)}
          tone={disputedCount > 0 ? "red" : "default"}
          hint="needs manual review"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Active listings" value={listings.filter((l) => l.is_active).length} />
        <StatCard label="Registered agents" value={agents.length} />
        <StatCard label="Total purchases" value={transactions.length} />
      </div>

      {health && (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-widest text-paper-dim">
                Platform escrow wallet · {health.network}
              </div>
              <div className="mono-chip mt-1 text-sm text-paper">{health.escrow_wallet}</div>
            </div>
            <StatusBadge status={health.status === "ok" ? "SERVICE_COMPLETED" : "FAILED"} />
          </div>
          <p className="mt-3 text-xs text-paper-dim">
            Every quote in this marketplace names this address as <span className="text-paper">payTo</span> — never
            the provider's own address. Funds only move on from here once a purchase is confirmed delivered.
          </p>
        </Card>
      )}

      <div>
        <h2 className="font-display text-lg font-semibold text-paper">Recent activity</h2>
        {transactions.length === 0 ? (
          <div className="mt-3">
            <EmptyState
              title="No purchases yet"
              hint="Publish a listing and register an agent to run the first purchase through escrow."
            />
          </div>
        ) : (
          <Card className="mt-3 divide-y divide-ink-line p-0">
            {transactions.slice(0, 8).map((t) => (
              <div key={t.id} className="flex items-center justify-between gap-4 px-5 py-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={t.status} />
                    <span className="mono-chip text-xs text-paper-dim">{shortAddr(t.deposit_tx_id)}</span>
                  </div>
                  {t.failure_reason && (
                    <p className="mt-1 truncate text-xs text-paper-dim">{t.failure_reason}</p>
                  )}
                </div>
                <div className="shrink-0 text-right">
                  <div className="font-mono text-sm text-paper">{formatMicro(t.amount_microalgos)}</div>
                  <div className="text-[11px] text-paper-dim">{formatDate(t.created_at)}</div>
                </div>
              </div>
            ))}
          </Card>
        )}
      </div>
    </div>
  );
}
