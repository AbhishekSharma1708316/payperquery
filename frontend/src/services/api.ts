import type {
  Agent,
  DashboardStats,
  PaymentResult,
  Provider,
  SpendingPolicy,
  Transaction,
} from "../types";

const BASE = "";

class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(typeof body === "object" && body && "detail" in body ? String((body as any).detail) : `Request failed with ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    throw new ApiError(res.status, body);
  }
  return body as T;
}

export const api = {
  health: () => request<{ status: string; network: string }>("/health"),

  listAgents: () => request<Agent[]>("/api/agents"),
  getAgent: (id: string) => request<Agent>(`/api/agents/${id}`),
  createAgent: (payload: {
    name: string;
    wallet_address: string;
    policy: Omit<SpendingPolicy, "id">;
  }) =>
    request<Agent>("/api/agents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updatePolicy: (agentId: string, policy: Omit<SpendingPolicy, "id">) =>
    request<Agent>(`/api/agents/${agentId}/policy`, {
      method: "PUT",
      body: JSON.stringify(policy),
    }),
  setPause: (agentId: string, is_paused: boolean) =>
    request<Agent>(`/api/agents/${agentId}/pause`, {
      method: "PATCH",
      body: JSON.stringify({ is_paused }),
    }),

  listProviders: () => request<Provider[]>("/api/providers"),
  createProvider: (payload: {
    name: string;
    endpoint: string;
    category: string;
    price_usd: string;
    pay_to_address: string;
  }) =>
    request<Provider>("/api/providers", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listTransactions: (params?: { agent_id?: string; provider_id?: string; status?: string }) => {
    const qs = params
      ? "?" +
        Object.entries(params)
          .filter(([, v]) => v)
          .map(([k, v]) => `${k}=${encodeURIComponent(v as string)}`)
          .join("&")
      : "";
    return request<Transaction[]>(`/api/transactions${qs}`);
  },

  requestPayment: (
    payload: { agent_id: string; provider_id: string; amount: string; currency: string },
    idempotencyKey: string,
  ) =>
    request<PaymentResult>("/api/payments/request", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(payload),
    }),

  dashboardStats: () => request<DashboardStats>("/api/dashboard/stats"),
};

export { ApiError };
