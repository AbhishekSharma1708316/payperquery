import type { TransactionStatus } from "../types";

const STYLES: Record<string, string> = {
  PENDING: "bg-slate-700 text-slate-200",
  POLICY_BLOCKED: "bg-red-900/60 text-red-300 border border-red-700",
  PAYMENT_REQUIRED: "bg-amber-900/60 text-amber-300 border border-amber-700",
  PAYMENT_SUBMITTED: "bg-amber-900/60 text-amber-300 border border-amber-700",
  PAYMENT_VERIFIED: "bg-emerald-900/60 text-emerald-300 border border-emerald-700",
  SERVICE_COMPLETED: "bg-emerald-900/60 text-emerald-300 border border-emerald-700",
  FAILED: "bg-red-900/60 text-red-300 border border-red-700",
  REFUNDED: "bg-sky-900/60 text-sky-300 border border-sky-700",
};

export default function StatusBadge({ status }: { status: TransactionStatus | string }) {
  const style = STYLES[status] ?? "bg-slate-700 text-slate-200";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
