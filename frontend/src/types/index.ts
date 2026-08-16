export interface SpendingPolicy {
  id: string;
  max_transaction_amount: string;
  daily_limit: string;
  min_provider_reputation: number;
  allowed_provider_ids: string[];
}

export interface Agent {
  id: string;
  name: string;
  wallet_address: string;
  is_active: boolean;
  is_paused: boolean;
  created_at: string;
  policy: SpendingPolicy | null;
}

export interface Provider {
  id: string;
  name: string;
  endpoint: string;
  category: string;
  price_usd: string;
  pay_to_address: string;
  successful_transactions: number;
  failed_transactions: number;
  average_latency_ms: number;
  refund_count: number;
  dispute_count: number;
  active: boolean;
  reputation_score: number;
  created_at: string;
}

export type TransactionStatus =
  | "PENDING"
  | "POLICY_BLOCKED"
  | "PAYMENT_REQUIRED"
  | "PAYMENT_SUBMITTED"
  | "PAYMENT_VERIFIED"
  | "SERVICE_COMPLETED"
  | "FAILED"
  | "REFUNDED";

export interface Transaction {
  id: string;
  agent_id: string;
  provider_id: string | null;
  amount: string;
  currency: string;
  status: TransactionStatus;
  payment_reference: string | null;
  x402_payment_identifier: string | null;
  idempotency_key: string;
  risk_score: number | null;
  failure_reason: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface PaymentResult {
  transaction: Transaction;
  policy_decision: {
    approved: boolean;
    reason: string | null;
    risk_score: number | null;
  };
  service_result: unknown | null;
}

export interface DashboardStats {
  wallet_balance_placeholder: string;
  today_spending: string;
  successful_payments_today: number;
  blocked_payments_today: number;
  average_transaction_value: string;
  total_agents: number;
  total_providers: number;
}
