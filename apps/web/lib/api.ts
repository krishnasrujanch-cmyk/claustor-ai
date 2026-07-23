/**
 * Claustor AI — API Client
 * All fetch calls to FastAPI backend go through here.
 * Handles: auth headers, error handling, token refresh.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Token Management ─────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  // Read from Zustand persist storage
  try {
    const stored = localStorage.getItem("claustor-auth");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed?.state?.token || null;
    }
  } catch {}
  return null;
}

export function setToken(token: string): void {
  // Zustand persist handles this automatically
  // This is kept for compatibility
  try {
    const stored = localStorage.getItem("claustor-auth");
    const parsed = stored ? JSON.parse(stored) : { state: {}, version: 0 };
    parsed.state.token = token;
    localStorage.setItem("claustor-auth", JSON.stringify(parsed));
  } catch {}
}

export function clearToken(): void {
  try {
    const stored = localStorage.getItem("claustor-auth");
    const parsed = stored ? JSON.parse(stored) : { state: {}, version: 0 };
    parsed.state.token = null;
    localStorage.setItem("claustor-auth", JSON.stringify(parsed));
  } catch {}
}

// ── Base Fetch ────────────────────────────────────────

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

export class APIError extends Error {
  constructor(
    public status: number,
    public detail: string | Record<string, unknown>
  ) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.name = "APIError";
  }
}

async function apiFetch<T>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { skipAuth, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    ...(fetchOptions.headers as Record<string, string>),
  };

  // Add auth header
  if (!skipAuth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  // Add content-type for JSON bodies
  if (
    fetchOptions.body &&
    typeof fetchOptions.body === "string" &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_URL}/api/v1${path}`, {
    ...fetchOptions,
    headers,
  });

  // Handle 401 — clear token and redirect to login
  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new APIError(401, "Session expired");
  }

  // Handle errors
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new APIError(response.status, errorData.detail || errorData);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ── Auth ─────────────────────────────────────────────

export const auth = {
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    org_name: string;
  }) =>
    apiFetch<{ access_token: string; user_id: string; org_id: string; plan: string }>(
      "/auth/register",
      { method: "POST", body: JSON.stringify(data), skipAuth: true }
    ),

  login: (email: string, password: string) =>
    apiFetch<{ access_token: string; user_id: string; org_id: string; plan: string }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
        skipAuth: true,
      }
    ),

  me: () =>
    apiFetch<{ user_id: string; org_id: string; email: string; role: string; plan: string }>(
      "/auth/me"
    ),

  devToken: () =>
    apiFetch<{ access_token: string }>("/auth/dev-token", {
      method: "POST",
      skipAuth: true,
    }),
};

// ── Contracts ─────────────────────────────────────────

export interface Contract {
  id: string;
  title: string;
  original_filename: string;
  contract_type: string | null;
  counterparty: string | null;
  governing_law: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  auto_renewal: boolean | null;
  status: string;
  risk_score: number | null;
  risk_level: string | null;
  health_score: number | null;
  clause_count: number;
  summary: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Clause {
  id: string;
  clause_type: string;
  title: string | null;
  summary: string | null;
  risk_score: number;
  risk_level: string;
  risk_reason: string | null;
  section_reference: string | null;
}

export const contracts = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    risk_level?: string;
    search?: string;
  }) => {
    const qs = new URLSearchParams(
      Object.entries(params || {})
        .filter(([, v]) => v != null)
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return apiFetch<{
      contracts: Contract[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    }>(`/contracts/${qs ? "?" + qs : ""}`);
  },

  get: (id: string) =>
    apiFetch<Contract & { clauses: Clause[] }>(`/contracts/${id}`),

  status: (id: string) =>
    apiFetch<{
      status: string;
      progress_pct: number;
      current_step: string;
      steps_completed: string[];
      error: string | null;
    }>(`/contracts/${id}/status`),

  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch<{
      contract_id: string;
      status: string;
      message: string;
      queue_position: number;
      estimated_wait_seconds: number;
    }>("/contracts/", { method: "POST", body: form });
  },

  delete: (id: string) =>
    apiFetch<void>(`/contracts/${id}`, { method: "DELETE" }),
};

// ── Chat ─────────────────────────────────────────────

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{
    citation_number: number;
    clause_type: string;
    rrf_score: number;
    source: string;
    text_preview: string;
  }>;
  created_at?: string;
}

export const chat = {
  send: (query: string, contract_id?: string) =>
    apiFetch<{
      answer: string;
      citations: ChatMessage["citations"];
      is_safe: boolean;
      tokens_used: number;
      provider: string;
    }>("/chat/", {
      method: "POST",
      body: JSON.stringify({ query, contract_id }),
    }),

  history: (contract_id?: string) =>
    apiFetch<{ history: ChatMessage[]; total: number }>(
      `/chat/history${contract_id ? `?contract_id=${contract_id}` : ""}`
    ),

  feedback: (conversation_id: string, feedback: "positive" | "negative") =>
    apiFetch("/chat/feedback", {
      method: "POST",
      body: JSON.stringify({ conversation_id, feedback }),
    }),

  clearHistory: (contract_id?: string) =>
    apiFetch(
      `/chat/history${contract_id ? `?contract_id=${contract_id}` : ""}`,
      { method: "DELETE" }
    ),
};

// ── Billing ──────────────────────────────────────────

export const billing = {
  plans: () => apiFetch<{ plans: unknown[] }>("/billing/plans", { skipAuth: true }),

  usage: () =>
    apiFetch<{
      plan: string;
      billing_provider: string;
      usage: {
        contracts: { used: number; limit: number; pct: number };
        queries: { used: number; limit: number; pct: number };
        storage_mb: { used: number; limit: number };
      };
    }>("/billing/usage"),

  summary: () => apiFetch("/billing/summary"),

  subscribe: (plan: string, interval: "monthly" | "annual" = "monthly") =>
    apiFetch("/billing/subscribe", {
      method: "POST",
      body: JSON.stringify({ plan, interval }),
    }),

  invoices: () => apiFetch<{ invoices: unknown[]; total: number }>("/billing/invoices"),
};

// ── Users ────────────────────────────────────────────

export const users = {
  list: (params?: { page?: number; role?: string; search?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params || {})
        .filter(([, v]) => v != null)
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return apiFetch<{
      users: unknown[];
      total: number;
      seats: { used: number; max: number; plan: string };
    }>(`/users/${qs ? "?" + qs : ""}`);
  },

  invite: (data: {
    email: string;
    full_name: string;
    role: string;
    is_external?: boolean;
  }) =>
    apiFetch("/users/invite", { method: "POST", body: JSON.stringify(data) }),

  deactivate: (userId: string) =>
    apiFetch(`/users/${userId}`, { method: "DELETE" }),
};
