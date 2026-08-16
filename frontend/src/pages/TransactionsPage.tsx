import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card } from "../components/Card";
import StatusBadge from "../components/StatusBadge";
import type { Transaction } from "../types";

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);

  async function load() {
    setTransactions(await api.listTransactions());
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Transactions</h1>
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-vault-border text-xs uppercase text-slate-500">
                <th className="py-2 pr-4">Time</th>
                <th className="py-2 pr-4">Amount</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Payment ref</th>
                <th className="py-2 pr-4">Risk</th>
                <th className="py-2 pr-4">Reason</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id} className="border-b border-vault-border/50">
                  <td className="py-2 pr-4 text-slate-400">{new Date(t.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-4 font-mono">
                    ${Number(t.amount).toFixed(4)} {t.currency}
                  </td>
                  <td className="py-2 pr-4">
                    <StatusBadge status={t.status} />
                  </td>
                  <td className="py-2 pr-4 max-w-[160px] truncate font-mono text-xs text-slate-500">
                    {t.payment_reference ?? "—"}
                  </td>
                  <td className="py-2 pr-4 text-slate-400">{t.risk_score ?? "—"}</td>
                  <td className="py-2 pr-4 text-slate-400">{t.failure_reason ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {transactions.length === 0 && <p className="py-4 text-sm text-slate-500">No transactions yet.</p>}
        </div>
      </Card>
    </div>
  );
}
