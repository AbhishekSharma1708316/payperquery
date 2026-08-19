import type { Agent, Escrow, Listing, ListingSearchResult, QuotePreview, Transaction } from "../types";

class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed with ${status}`,
    );
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await res.json() : await res.text();
  if (!res.ok && res.status !== 402) {
    throw new ApiError(res.status, body);
  }
  return body as T;
}

export const api = {
  health: () => request<{ status: string; network: string; escrow_wallet: string }>("/health"),

  // Agents
  listAgents: () => request<Agent[]>("/api/agents"),
  createAgent: (payload: {
    name: string;
    wallet_address: string;
    policy: {
      max_transaction_amount: string;
      daily_limit: string;
      min_provider_reputation: number;
      restrict_to_allowed_listings: boolean;
    };
  }) => request<Agent>("/api/agents", { method: "POST", body: JSON.stringify(payload) }),
  setAgentPaused: (agentId: string, paused: boolean) =>
    request<Agent>(`/api/agents/${agentId}/pause`, { method: "PATCH", body: JSON.stringify({ paused }) }),

  // Listings (provider admin)
  listListings: (includeInactive = false) =>
    request<Listing[]>(`/api/listings${includeInactive ? "?include_inactive=true" : ""}`),
  createListing: (payload: {
    name: string;
    description?: string;
    category: string;
    path: string;
    upstream_url: string;
    price_microalgos: number;
    pay_to_address: string;
    asa_id?: number | null;
  }) => request<Listing>("/api/listings", { method: "POST", body: JSON.stringify(payload) }),
  deactivateListing: (listingId: string) =>
    fetch(`/api/listings/${listingId}`, { method: "DELETE" }),

  // Marketplace search
  searchMarketplace: (params: { q?: string; category?: string; min_reputation?: number }) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.category) qs.set("category", params.category);
    if (params.min_reputation) qs.set("min_reputation", String(params.min_reputation));
    return request<ListingSearchResult[]>(`/market/search?${qs.toString()}`);
  },

  // Preview a 402 quote for a listing without an API key requirement bypass --
  // uses a throwaway request so shoppers can see terms before an agent buys.
  previewQuote: (path: string, apiKey: string) =>
    request<QuotePreview>(`/market/${path}/call`, { headers: { "X-Agent-Key": apiKey } }),

  // Transactions
  listTransactions: (params?: { agent_id?: string; status_filter?: string }) => {
    const qs = new URLSearchParams();
    if (params?.agent_id) qs.set("agent_id", params.agent_id);
    if (params?.status_filter) qs.set("status_filter", params.status_filter);
    return request<Transaction[]>(`/api/transactions?${qs.toString()}`);
  },

  // Escrow
  listEscrows: (statusFilter?: string) =>
    request<Escrow[]>(`/api/escrow${statusFilter ? `?status_filter=${statusFilter}` : ""}`),
  releaseEscrow: (escrowId: string, notes?: string) =>
    request<Escrow>(`/api/escrow/${escrowId}/release`, { method: "POST", body: JSON.stringify({ notes }) }),
  refundEscrow: (escrowId: string, notes?: string) =>
    request<Escrow>(`/api/escrow/${escrowId}/refund`, { method: "POST", body: JSON.stringify({ notes }) }),

  // Support chatbot
  sendChatMessage: (message: string, history: { role: "user" | "assistant"; content: string }[]) =>
    request<{ reply: string }>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, history }),
    }),
};

export { ApiError };
