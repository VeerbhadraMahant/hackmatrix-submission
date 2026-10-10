import type {
  Account,
  AnswerContract,
  ChatEngine,
  SchemesFeed,
  Budget,
  BudgetStatus,
  CategorizationRule,
  CategorizationRuleCreate,
  CategorizationRuleList,
  CreateAccountRequest,
  CreateBudgetRequest,
  CreateGoalRequest,
  CreateHouseholdRequest,
  CreateInviteRequest,
  DashboardSnapshot,
  DocumentInfo,
  Goal,
  GoalProgress,
  FinancialSecurity,
  FinancialSecurityBrief,
  Household,
  HouseholdInvite,
  HouseholdSummary,

  NetWorthHistory,
  Connector,
  ConnectProfile,
  NotificationItem,
  PlanParams,
  PlanResult,
  PlanScenario,
  PlanScenarioSummary,
  PlanShock,
  RecomputeDiff,
  CopilotInsight,
  ReplanResult,
  ReviewQueueResponse,
  ReviewTransactionRequest,
  SafeToSpend,
  SimulationRequest,
  SimulationResult,
  TaxCalculationRequest,
  TaxOptimizationAnalysis,
  Transaction,
  TransactionFilters,
  TransactionPage,
  TransactionUpdate,
  UpdateBudgetRequest,
  UpdateGoalRequest,
  SecurityEvent,
  SecurityFinding,
  SecurityGraph,
  SecurityReport,
  MyData,
} from "./types";
import { publishCopilotInsights } from "./copilotBus";
import { DATA_CHANGED_EVENT } from "./hooks";
import { getOfflineOnly } from "./user";

// Production (Vercel multi-service project) serves the backend on the same
// origin under /api, so default to relative URLs there; local dev talks to
// the separate uvicorn server. NEXT_PUBLIC_API_URL overrides either.
// Dev uses 127.0.0.1, not "localhost": uvicorn binds IPv4 only, and clients
// that try IPv6 (::1) first wait ~2s per request before falling back.
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8000");

/** Attach the Firebase ID token whenever a user is signed in. Demo-only usage
 * (no signed-in session) omits the header, which the backend already allows
 * for the demo personas. authStateReady() waits for Firebase to restore the
 * persisted session so first-load requests aren't sent anonymously. */
async function authHeader(): Promise<Record<string, string>> {
  try {
    const { auth: firebaseAuth } = await import("./firebase/config");
    await firebaseAuth.authStateReady();
    if (firebaseAuth.currentUser) {
      const fbToken = await firebaseAuth.currentUser.getIdToken();
      if (fbToken) return { Authorization: `Bearer ${fbToken}` };
    }
  } catch {
    // Firebase auth not available or not signed in
  }
  return {};
}

/** After a successful write, tell every mounted useAsync() to refetch. */
function notifyIfWrite(method?: string) {
  if (method && method !== "GET" && typeof window !== "undefined") {
    window.dispatchEvent(new Event(DATA_CHANGED_EVENT));
  }
}

function publishInsights(d: RecomputeDiff): RecomputeDiff {
  if (d.insights?.length) publishCopilotInsights(d.insights);
  return d;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const auth = await authHeader();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...auth, ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let detail = body;
    try {
      const d = JSON.parse(body)?.detail;
      if (typeof d === "string") detail = d; // surface FastAPI's message (e.g. "Demo data is read-only...") as-is
    } catch {
      // not JSON -- keep the raw body
    }
    throw new Error(`API ${path} failed: ${res.status} ${detail}`);
  }
  notifyIfWrite(init?.method);
  // DELETE endpoints (e.g. budgets/goals) return 204 with no body -- res.json()
  // would throw on the empty string, so short-circuit for callers typed <void>.
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function planQuery(p: PlanParams): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) if (v !== undefined) q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => apiFetch<{ status: string }>("/api/health"),
  dashboard: (userId: string) => apiFetch<DashboardSnapshot>(`/api/dashboard/${userId}`),
  // user_id must be threaded through explicitly -- ChatRequest defaults to
  // "demo-priya" server-side, so omitting it here would silently ignore
  // whatever persona the rest of the app (dashboard/simulate/timeline, all
  // of which use useUserId()) is currently showing.
  chat: (message: string, userId: string, model: ChatEngine = "auto", history: { role: "user" | "assistant"; content: string }[] = []) =>
    apiFetch<AnswerContract>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, user_id: userId, force_offline: getOfflineOnly(), model, history }),
    }),
  schemes: () => apiFetch<SchemesFeed>("/api/schemes"),
  simulate: (userId: string, req: SimulationRequest) =>
    apiFetch<SimulationResult>(`/api/simulate/${userId}`, { method: "POST", body: JSON.stringify(req) }),
  addEvent: (userId: string, payload: Record<string, unknown>) =>
    apiFetch<RecomputeDiff>(`/api/events/${userId}`, { method: "POST", body: JSON.stringify(payload) }).then(publishInsights),
  copilotInsights: (userId: string, since?: string) =>
    apiFetch<CopilotInsight[]>(`/api/copilot/insights/${userId}?limit=20${since ? `&since=${encodeURIComponent(since)}` : ""}`),

  // Transactions
  transactions: (userId: string, filters: TransactionFilters = {}) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
    }
    const qs = params.toString();
    return apiFetch<TransactionPage>(`/api/transactions/${userId}${qs ? `?${qs}` : ""}`);
  },
  updateTransaction: (userId: string, transactionId: string, update: TransactionUpdate) =>
    apiFetch<Transaction>(`/api/transactions/${userId}/${transactionId}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    }),
  reviewQueue: (userId: string, limit = 20) =>
    apiFetch<ReviewQueueResponse>(`/api/transactions/${userId}/review-queue?limit=${limit}`),
  reviewTransaction: (userId: string, transactionId: string, req: ReviewTransactionRequest) =>
    apiFetch<Transaction>(`/api/transactions/${userId}/${transactionId}/review`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  // Categorization Rules
  rules: (userId: string) => apiFetch<CategorizationRuleList>(`/api/rules/${userId}`),
  createRule: (userId: string, req: CategorizationRuleCreate) =>
    apiFetch<CategorizationRule>(`/api/rules/${userId}`, { method: "POST", body: JSON.stringify(req) }),
  deleteRule: (userId: string, ruleId: string) =>
    apiFetch<{ ok: boolean; deleted_id: string }>(`/api/rules/${userId}/${ruleId}`, { method: "DELETE" }),

  // Budgets
  budgets: (userId: string) => apiFetch<Budget[]>(`/api/budgets/${userId}`),
  createBudget: (userId: string, req: CreateBudgetRequest) =>
    apiFetch<Budget>(`/api/budgets/${userId}`, { method: "POST", body: JSON.stringify(req) }),
  updateBudget: (userId: string, budgetId: string, req: UpdateBudgetRequest) =>
    apiFetch<Budget>(`/api/budgets/${userId}/${budgetId}`, { method: "PATCH", body: JSON.stringify(req) }),
  deleteBudget: (userId: string, budgetId: string) =>
    apiFetch<void>(`/api/budgets/${userId}/${budgetId}`, { method: "DELETE" }),
  budgetStatus: (userId: string) => apiFetch<BudgetStatus[]>(`/api/budgets/${userId}/status`),
  safeToSpend: (userId: string) => apiFetch<SafeToSpend>(`/api/budgets/${userId}/safe-to-spend`),

  // Goals
  goals: (userId: string) => apiFetch<GoalProgress[]>(`/api/goals/${userId}`),
  createGoal: (userId: string, req: CreateGoalRequest) =>
    apiFetch<GoalProgress | Goal>(`/api/goals/${userId}`, { method: "POST", body: JSON.stringify(req) }),
  updateGoal: (userId: string, goalId: string, req: UpdateGoalRequest) =>
    apiFetch<Goal>(`/api/goals/${userId}/${goalId}`, { method: "PATCH", body: JSON.stringify(req) }),
  deleteGoal: (userId: string, goalId: string) =>
    apiFetch<void>(`/api/goals/${userId}/${goalId}`, { method: "DELETE" }),

  // Connectors: linking a source is what fills the app with data
  connectors: (userId: string) => apiFetch<Connector[]>(`/api/connectors/${userId}`),
  connectConnector: (userId: string, connector: string, profile: ConnectProfile, url = "") =>
    apiFetch<{ connected: boolean; accounts: number; transactions: number }>(
      `/api/connectors/${userId}/${connector}/connect`,
      { method: "POST", body: JSON.stringify({ profile, url }) }
    ),
  /** Re-reads the linked Google Sheet. Only announces a data change when the sheet actually changed. */
  syncSheet: async (userId: string): Promise<boolean> => {
    const res = await fetch(`${API_URL}/api/connectors/${userId}/google_sheets/sync`, { method: "POST", headers: await authHeader() });
    if (!res.ok) throw new Error(`Sheet sync failed: ${res.status}`);
    const { changed } = (await res.json()) as { changed: boolean };
    if (changed) notifyIfWrite("POST");
    return changed;
  },
  /** Downloads a connected source's dataset as a CSV file. */
  exportConnector: async (userId: string, connector: string) => {
    const res = await fetch(`${API_URL}/api/connectors/${userId}/${connector}/export`, { headers: await authHeader() });
    if (!res.ok) throw new Error(`Export failed: ${res.status} ${await res.text()}`);
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: `${connector}.csv` });
    a.click();
    URL.revokeObjectURL(url);
  },
  disconnectConnector: (userId: string, connector: string) =>
    apiFetch<void>(`/api/connectors/${userId}/${connector}`, { method: "DELETE" }),

  // Security suite: Evidence Room, Twin Simulator, My Data
  /** Streams agent progress events (NDJSON); the last event is the saved report. */
  investigate: async (userId: string, onEvent: (e: SecurityEvent) => void) => {
    const res = await fetch(`${API_URL}/api/security/${userId}/investigate`, { method: "POST", headers: await authHeader() });
    if (!res.ok || !res.body) throw new Error(`Investigation failed: ${res.status}`);
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      lines.filter(Boolean).forEach((l) => onEvent(JSON.parse(l)));
    }
  },
  financialSecurity: (userId: string) => apiFetch<FinancialSecurity>(`/api/security/${userId}/financial`),
  financialSecurityBrief: (userId: string) => apiFetch<FinancialSecurityBrief>(`/api/security/${userId}/financial/brief`),
  securityReport: (userId: string) => apiFetch<SecurityReport | null>(`/api/security/${userId}/report`),
  plantThreats: (userId: string) => apiFetch<{ planted: number }>(`/api/security/${userId}/demo-threats`, { method: "POST" }),
  clearThreats: (userId: string) => apiFetch<{ removed: number }>(`/api/security/${userId}/demo-threats`, { method: "DELETE" }),
  securityGraph: (userId: string, months: number) => apiFetch<SecurityGraph>(`/api/security/${userId}/graph?months=${months}`),
  simulateFraud: (userId: string, merchant: string, amount: number) =>
    apiFetch<{ caught: boolean; findings: SecurityFinding[] }>(`/api/security/${userId}/simulate-fraud`, { method: "POST", body: JSON.stringify({ merchant, amount }) }),
  myData: (userId: string) => apiFetch<MyData>(`/api/security/${userId}/data`),
  exportAllData: async (userId: string) => {
    const res = await fetch(`${API_URL}/api/security/${userId}/data/export`, { headers: await authHeader() });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    const url = URL.createObjectURL(await res.blob());
    Object.assign(document.createElement("a"), { href: url, download: "finpilot-all-data.json" }).click();
    URL.revokeObjectURL(url);
  },

  // Net worth + accounts
  netWorthHistory: (userId: string, days = 180) =>
    apiFetch<NetWorthHistory>(`/api/networth/${userId}/history?days=${days}`),
  accounts: (userId: string) => apiFetch<Account[]>(`/api/accounts/${userId}`),
  createAccount: (userId: string, req: CreateAccountRequest) =>
    apiFetch<Account>(`/api/accounts/${userId}`, { method: "POST", body: JSON.stringify(req) }),
  /** Bank-statement CSV upload (multipart -- so no JSON Content-Type header). */
  upload: async (userId: string, file: File): Promise<RecomputeDiff> => {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`${API_URL}/api/upload/${userId}`, {
      method: "POST",
      headers: await authHeader(),
      body,
    });
    if (!res.ok) throw new Error(`API upload failed: ${res.status} ${await res.text()}`);
    notifyIfWrite("POST");
    return publishInsights((await res.json()) as RecomputeDiff);
  },

  // Documents the Copilot reads when answering (.txt .md .csv .json, <=2MB)
  documents: (userId: string) => apiFetch<DocumentInfo[]>(`/api/documents/${userId}`),
  uploadDocument: async (userId: string, file: File): Promise<{ id: string; name: string; chars: number; chunks: number }> => {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`${API_URL}/api/documents/${userId}`, { method: "POST", headers: await authHeader(), body });
    if (!res.ok) throw new Error(`Upload failed: ${res.status} ${await res.text()}`);
    return res.json();
  },
  deleteDocument: (userId: string, id: string) =>
    apiFetch<unknown>(`/api/documents/${userId}/${id}`, { method: "DELETE" }),

  // Financial plan (constrained action planner + monthly probabilistic forecast)
  plan: (userId: string, p: PlanParams = {}) =>
    apiFetch<PlanResult>(`/api/plan/${userId}${planQuery(p)}`),
  replan: (userId: string, p: PlanParams, shock: PlanShock) =>
    apiFetch<ReplanResult>(`/api/plan/${userId}/replan`, { method: "POST", body: JSON.stringify({ ...p, shock }) }),
  // Public (synthetic data) -- no user id.
  planScenarios: () => apiFetch<PlanScenarioSummary[]>("/api/planning/scenarios"),
  planScenario: (name: string) => apiFetch<PlanScenario>(`/api/planning/scenarios/${name}`),

  // Notifications
  notifications: (userId: string) => apiFetch<NotificationItem[]>(`/api/notifications/${userId}`),

  // Household & Collaboration (Pillar 5D)
  household: (userId: string) => apiFetch<HouseholdSummary>(`/api/household/${userId}`),
  createHousehold: (userId: string, req: CreateHouseholdRequest) =>
    apiFetch<HouseholdSummary>(`/api/household/${userId}`, { method: "POST", body: JSON.stringify(req) }),
  createInvite: (userId: string, req: CreateInviteRequest) =>
    apiFetch<HouseholdInvite>(`/api/household/${userId}/invites`, { method: "POST", body: JSON.stringify(req) }),
  acceptInvite: (userId: string, token: string) =>
    apiFetch<HouseholdSummary>(`/api/household/${userId}/invites/accept`, {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  revokeInvite: (userId: string, inviteId: string) =>
    apiFetch<{ revoked: boolean; id: string }>(`/api/household/${userId}/invites/${inviteId}`, { method: "DELETE" }),
  removeMember: (userId: string, memberUserId: string) =>
    apiFetch<{ removed: boolean; user_id: string }>(`/api/household/${userId}/members/${memberUserId}`, {
      method: "DELETE",
    }),

  // Tax Optimizer
  taxAnalysis: (userId: string) => apiFetch<TaxOptimizationAnalysis>(`/api/tax/${userId}/analysis`),
  calculateTax: (userId: string, req: TaxCalculationRequest) =>
    apiFetch<TaxOptimizationAnalysis>(`/api/tax/${userId}/calculate`, {
      method: "POST",
      body: JSON.stringify(req),
    }),
};

