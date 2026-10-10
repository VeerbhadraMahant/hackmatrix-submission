"use client";

import { useCallback, useMemo, useRef, useState, useEffect } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Car,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Cloud,
  CreditCard,
  Download,
  Film,
  HeartPulse,
  Home,
  Percent,
  Receipt,
  Search,
  ShoppingBag,
  ShoppingCart,
  TrendingUp,
  Utensils,
  Zap,
  HelpCircle,
  X,
  Sparkles,
  Tag,
  FileText,
  SlidersHorizontal,
  Plus,
  Trash2,
  CheckCircle2,
  Clock,
  CornerDownRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { useAsync, useDebouncedValue, useUserId } from "@/lib/hooks";
import type {
  CategorizationRule,
  CategorizationRuleCreate,
  ReviewAction,
  ReviewStatus,
  RuleMatchType,
  Transaction,
  TxnCategory,
} from "@/lib/types";
import { TxnSummary } from "@/components/transactions/TxnSummary";
import { MerchantLogo } from "@/components/dashboard/MerchantLogo";
import { CATEGORY_META } from "@/lib/spend";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { triggerConfetti } from "@/components/ui/Confetti";
import { formatCurrency, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export const CATEGORY_CONFIG: Record<
  TxnCategory,
  { label: string; icon: LucideIcon; tone: "neutral" | "accent" | "outline" | "success" | "warning" | "danger" | "info" }
> = {
  income: { label: "Income", icon: ArrowDownLeft, tone: "success" },
  rent_housing: { label: "Rent & Housing", icon: Home, tone: "info" },
  emi_loan: { label: "EMI & Loan", icon: CreditCard, tone: "danger" },
  groceries: { label: "Groceries", icon: ShoppingCart, tone: "success" },
  dining: { label: "Dining & Food", icon: Utensils, tone: "warning" },
  transport: { label: "Transport & Fuel", icon: Car, tone: "neutral" },
  utilities: { label: "Utilities", icon: Zap, tone: "accent" },
  subscriptions: { label: "Subscriptions", icon: Cloud, tone: "info" },
  shopping: { label: "Shopping", icon: ShoppingBag, tone: "accent" },
  healthcare: { label: "Healthcare", icon: HeartPulse, tone: "danger" },
  entertainment: { label: "Entertainment", icon: Film, tone: "info" },
  investment_sip: { label: "Investment & SIP", icon: TrendingUp, tone: "success" },
  credit_card_payment: { label: "Credit Card", icon: CreditCard, tone: "neutral" },
  transfer: { label: "Transfer", icon: ArrowLeftRight, tone: "neutral" },
  fees_interest: { label: "Fees & Interest", icon: Percent, tone: "warning" },
  other: { label: "Other", icon: HelpCircle, tone: "neutral" },
};

const CATEGORIES = Object.keys(CATEGORY_CONFIG) as TxnCategory[];

function categoryLabel(cat: string): string {
  const item = CATEGORY_CONFIG[cat as TxnCategory];
  return item ? item.label : cat.replace(/_/g, " ");
}

type QuickFilterId = "all" | "pending_review" | "subscriptions" | "high_value" | "inflow" | "dining" | "groceries";

interface QuickFilter {
  id: QuickFilterId;
  label: string;
  category?: TxnCategory;
  reviewStatus?: ReviewStatus;
  isHighValue?: boolean;
  isInflow?: boolean;
}

const QUICK_FILTERS: QuickFilter[] = [
  { id: "all", label: "All Transactions" },
  { id: "pending_review", label: "Pending Review", reviewStatus: "pending" },
  { id: "subscriptions", label: "Subscriptions", category: "subscriptions" },
  { id: "high_value", label: "High Value (> ₹5k)", isHighValue: true },
  { id: "inflow", label: "Inflow", isInflow: true },
  { id: "dining", label: "Dining", category: "dining" },
  { id: "groceries", label: "Groceries", category: "groceries" },
];

type SortField = "date" | "merchant" | "category" | "amount";
type SortDirection = "asc" | "desc";

const PAGE_SIZES = [10, 25, 50];

export default function TransactionsPage() {
  const userId = useUserId();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 250);
  const [showRulesModal, setShowRulesModal] = useState(false);
  const [category, setCategory] = useState<TxnCategory | "">("");
  const [reviewStatusFilter, setReviewStatusFilter] = useState<string>("");
  const [tagFilter, setTagFilter] = useState<string>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [openPanel, setOpenPanel] = useState<"" | "views" | "filters" | "date" | "keywords">("");
  const [activeQuickFilter, setActiveQuickFilter] = useState<QuickFilterId>("all");

  const [sortField, setSortField] = useState<SortField>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // Review Queue state
  const [showReviewDeck, setShowReviewDeck] = useState(true);

  const fetchTransactions = useCallback(
    () =>
      api.transactions(userId, {
        search: debouncedSearch || undefined,
        category: category || undefined,
        review_status: reviewStatusFilter || undefined,
        tag: tagFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        page_size: pageSize,
      }),
    [userId, debouncedSearch, category, reviewStatusFilter, tagFilter, dateFrom, dateTo, page, pageSize]
  );

  const { data, error, loading, reload } = useAsync(
    fetchTransactions,
    [userId, debouncedSearch, category, reviewStatusFilter, tagFilter, dateFrom, dateTo, page, pageSize],
    { identity: userId }
  );

  // Review queue fetcher
  const fetchQueue = useCallback(() => api.reviewQueue(userId, 20), [userId]);
  const { data: queueData, reload: reloadQueue } = useAsync(fetchQueue, [userId], { identity: userId });

  const { data: accounts } = useAsync(useCallback(() => api.accounts(userId), [userId]), [userId], { identity: userId });
  const accountName = useMemo(() => new Map((accounts ?? []).map((a) => [a.id, a.name])), [accounts]);

  // Rules fetcher
  const fetchRules = useCallback(() => api.rules(userId), [userId]);
  const { data: rulesData, reload: reloadRules } = useAsync(fetchRules, [userId], { identity: userId });

  function resetToFirstPage() {
    setPage(1);
  }

  function handleQuickFilterClick(qf: QuickFilter) {
    if (activeQuickFilter === qf.id && qf.id !== "all") {
      setActiveQuickFilter("all");
      setCategory("");
      setReviewStatusFilter("");
      resetToFirstPage();
      return;
    }

    setActiveQuickFilter(qf.id);
    resetToFirstPage();

    if (qf.category) {
      setCategory(qf.category);
      setReviewStatusFilter("");
    } else if (qf.reviewStatus) {
      setReviewStatusFilter(qf.reviewStatus);
      setCategory("");
    } else {
      setCategory("");
      setReviewStatusFilter("");
    }
  }

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection(field === "amount" || field === "date" ? "desc" : "asc");
    }
  }

  // Client-side filtering and sorting for active page items
  const pageItems = data?.items;
  const displayItems = useMemo(() => {
    if (!pageItems) return [];
    let items = [...pageItems];

    if (activeQuickFilter === "high_value") {
      items = items.filter((t) => Math.abs(t.amount) > 5000);
    } else if (activeQuickFilter === "inflow") {
      items = items.filter((t) => t.amount > 0);
    }

    items.sort((a, b) => {
      let comparison = 0;
      if (sortField === "date") {
        comparison = new Date(a.date).getTime() - new Date(b.date).getTime();
      } else if (sortField === "merchant") {
        comparison = a.merchant.localeCompare(b.merchant);
      } else if (sortField === "category") {
        comparison = a.category.localeCompare(b.category);
      } else if (sortField === "amount") {
        comparison = a.amount - b.amount;
      }
      return sortDirection === "asc" ? comparison : -comparison;
    });

    return items;
  }, [pageItems, activeQuickFilter, sortField, sortDirection]);

  function handleExportCSV() {
    const base = displayItems.length > 0 ? displayItems : data?.items ?? [];
    const itemsToExport = selected.size > 0 ? base.filter((t) => selected.has(t.id)) : base;
    if (itemsToExport.length === 0) return;

    const headers = ["ID", "Date", "Merchant", "Category", "Amount (INR)", "Review Status", "Tags", "Notes", "Account ID"];
    const rows = itemsToExport.map((t) => [
      t.id,
      t.date,
      `"${t.merchant.replace(/"/g, '""')}"`,
      t.category,
      t.amount,
      t.review_status || "pending",
      `"${(t.tags || []).join(", ").replace(/"/g, '""')}"`,
      `"${(t.notes || "").replace(/"/g, '""')}"`,
      t.account_id,
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "finpilot_transactions_audited.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function handleTransactionActionCompleted() {
    reload();
    reloadQueue();
    reloadRules();
  }

  return (
    <div className="flex flex-col gap-4 pb-16 min-w-0 max-w-full">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Transactions</h1>
          <p className="text-xs text-graphite">See where your money came from and where it went.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => setShowRulesModal(true)} className="text-xs font-semibold gap-1.5">
          <SlidersHorizontal className="h-3.5 w-3.5 text-pewter" />
          <span>Auto-sort rules ({rulesData?.total ?? 0})</span>
        </Button>
      </div>

      <TxnSummary />

      {/* Review Queue Deck (Matching Showcase Track Pattern) */}
      {queueData && queueData.pending_count > 0 && showReviewDeck && (
        <ReviewQueueSection
          userId={userId}
          queue={queueData.items}
          pendingCount={queueData.pending_count}
          onCompleted={handleTransactionActionCompleted}
          onDismiss={() => setShowReviewDeck(false)}
        />
      )}

      {/* Error View */}
      {error && (
        <Card className="flex flex-col gap-3 border-rose-200 bg-rose-50/30 p-6">
          <p className="text-sm font-semibold text-rose-800">Could not load transactions: {error}</p>
          <Button variant="secondary" size="sm" onClick={reload} className="self-start">
            Retry Loading
          </Button>
        </Card>
      )}

      {/* Main Ledger Table Card */}
      <Card className="p-0 sm:p-0 overflow-hidden max-w-full">
        <div className="relative flex flex-wrap items-center gap-2 border-b border-black/[0.06] px-5 py-4">
          <h2 className="mr-auto font-display text-base font-semibold text-ink">All transactions</h2>
          {([
            ["views", "Quick views"],
            ["filters", "Filters"],
            ["date", "Date"],
            ["keywords", "Search"],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setOpenPanel(openPanel === id ? "" : id)}
              className={cn("inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium", openPanel === id ? "border-ink bg-fog text-ink" : "border-mist bg-white text-graphite hover:text-ink")}
            >
              {label}
              <ChevronDown className="h-3 w-3" />
            </button>
          ))}
          <Button variant="secondary" size="sm" onClick={handleExportCSV} disabled={!data || data.items.length === 0} className="text-xs font-semibold gap-1.5">
            <Download className="h-3.5 w-3.5 text-pewter" />
            {selected.size > 0 ? `Export ${selected.size} selected` : "Export all"}
          </Button>
          {openPanel && (
            <div className="mt-2 flex w-full flex-wrap items-center gap-2 rounded-2xl bg-fog/60 p-3">
              {openPanel === "views" &&
                QUICK_FILTERS.map((qf) => (
                  <button
                    key={qf.id}
                    type="button"
                    onClick={() => handleQuickFilterClick(qf)}
                    className={cn("rounded-full px-3 py-1 text-xs font-medium", activeQuickFilter === qf.id ? "bg-lime text-ink" : "bg-white text-graphite hover:text-ink")}
                  >
                    {qf.label}
                  </button>
                ))}
              {openPanel === "filters" && (
                <>
                  <select
                    value={category}
                    onChange={(e) => {
                      setCategory(e.target.value as TxnCategory | "");
                      setActiveQuickFilter("all");
                      resetToFirstPage();
                    }}
                    className="rounded-xl border border-mist bg-white px-3 py-1.5 text-xs text-ink"
                  >
                    <option value="">All categories</option>
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {categoryLabel(c)}
                      </option>
                    ))}
                  </select>
                  <select
                    value={reviewStatusFilter}
                    onChange={(e) => {
                      setReviewStatusFilter(e.target.value);
                      setActiveQuickFilter("all");
                      resetToFirstPage();
                    }}
                    className="rounded-xl border border-mist bg-white px-3 py-1.5 text-xs text-ink"
                  >
                    <option value="">Any status</option>
                    <option value="pending">To review</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="skipped">Skipped</option>
                  </select>
                </>
              )}
              {openPanel === "date" && (
                <>
                  <label className="flex items-center gap-1.5 text-xs text-graphite">
                    From
                    <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); resetToFirstPage(); }} className="rounded-xl border border-mist bg-white px-2 py-1 text-xs text-ink" />
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-graphite">
                    To
                    <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); resetToFirstPage(); }} className="rounded-xl border border-mist bg-white px-2 py-1 text-xs text-ink" />
                  </label>
                </>
              )}
              {openPanel === "keywords" && (
                <div className="relative min-w-[240px] flex-1">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pewter" />
                  <input
                    type="search"
                    autoFocus
                    placeholder="Search shop, note or tag"
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); resetToFirstPage(); }}
                    className="w-full rounded-xl border border-mist bg-white py-1.5 pl-9 pr-3 text-sm text-ink"
                  />
                </div>
              )}
              {(search || category || reviewStatusFilter || tagFilter || dateFrom || dateTo || activeQuickFilter !== "all") && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearch(""); setCategory(""); setReviewStatusFilter(""); setTagFilter(""); setDateFrom(""); setDateTo("");
                    setActiveQuickFilter("all"); resetToFirstPage();
                  }}
                  className="px-2 text-xs text-pewter hover:text-ink"
                >
                  <X className="mr-1 h-3.5 w-3.5" /> Clear
                </Button>
              )}
            </div>
          )}
        </div>
        <div className="overflow-x-auto w-full max-w-full">
          <table className="w-full min-w-[760px] text-left text-sm border-collapse">
            <thead>
              <tr className="border-b border-black/[0.06] text-xs font-medium text-pewter select-none">
                <th className="w-10 pl-5 py-3.5">
                  <input
                    type="checkbox"
                    aria-label="Select all on this page"
                    checked={displayItems.length > 0 && displayItems.every((t) => selected.has(t.id))}
                    onChange={(e) => setSelected(e.target.checked ? new Set(displayItems.map((t) => t.id)) : new Set())}
                  />
                </th>
                <SortableHeader field="date" label="Date" currentField={sortField} direction={sortDirection} onSort={handleSort} className="px-3 py-3.5 w-28" />
                <SortableHeader field="merchant" label="Paid to / from" currentField={sortField} direction={sortDirection} onSort={handleSort} className="px-3 py-3.5 min-w-[200px]" />
                <th className="px-3 py-3.5 w-28">Status</th>
                <SortableHeader field="amount" label="Amount" currentField={sortField} direction={sortDirection} onSort={handleSort} className="px-3 py-3.5 text-right w-32" align="right" />
                <th className="px-3 py-3.5 w-40">Account</th>
                <SortableHeader field="category" label="Category" currentField={sortField} direction={sortDirection} onSort={handleSort} className="px-3 py-3.5 w-48" />
                <th className="px-3 py-3.5 w-24 text-center">Note</th>
              </tr>
            </thead>

            {loading && !data ? (
              <tbody className="divide-y divide-black/[0.04]">
                {Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="pl-6 py-4">
                      <Skeleton className="h-4 w-20" />
                    </td>
                    <td className="px-6 py-4">
                      <Skeleton className="h-4 w-36" />
                    </td>
                    <td className="px-6 py-4">
                      <Skeleton className="h-6 w-28 rounded-chip" />
                    </td>
                    <td className="px-6 py-4">
                      <Skeleton className="h-5 w-20 rounded-full" />
                    </td>
                    <td className="pr-6 py-4 text-right">
                      <Skeleton className="h-4 w-20 ml-auto" />
                    </td>
                  </tr>
                ))}
              </tbody>
            ) : displayItems.length === 0 ? (
              <tbody>
                <tr>
                  <td colSpan={8} className="p-8">
                    <EmptyState
                      icon={<Receipt className="h-10 w-10 text-pewter" />}
                      title="No transactions match these filters"
                      body="Try adjusting your search terms, clearing status filters, or resetting date boundaries."
                      action={
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setSearch("");
                            setCategory("");
                            setReviewStatusFilter("");
                            setTagFilter("");
                            setDateFrom("");
                            setDateTo("");
                            setActiveQuickFilter("all");
                            resetToFirstPage();
                          }}
                        >
                          Reset Filters
                        </Button>
                      }
                    />
                  </td>
                </tr>
              </tbody>
            ) : (
              <tbody className="divide-y divide-black/[0.04] bg-white">
                {displayItems.map((txn) => (
                  <TransactionRowItem
                    key={txn.id}
                    txn={txn}
                    userId={userId}
                    accountName={accountName.get(txn.account_id) ?? "Account"}
                    selected={selected.has(txn.id)}
                    onToggle={() => setSelected((prev) => { const n = new Set(prev); if (n.has(txn.id)) n.delete(txn.id); else n.add(txn.id); return n; })}
                    onUpdated={handleTransactionActionCompleted}
                  />
                ))}
              </tbody>
            )}
          </table>
        </div>

        {/* Pagination & Ledger Stats Footer */}
        {data && data.total > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-black/[0.06] bg-fog/40 px-6 py-4">
            <div className="flex items-center gap-2 text-xs text-pewter">
              <span>Showing</span>
              <span className="font-semibold text-ink tnum">
                {Math.min(data.total, (page - 1) * pageSize + 1)}–
                {Math.min(data.total, (page - 1) * pageSize + displayItems.length)}
              </span>
              <span>of</span>
              <span className="font-semibold text-ink tnum">{data.total}</span>
              <span>results</span>
              {activeQuickFilter !== "all" && (
                <span className="text-[11px] text-ember font-medium ml-1">
                  (filtered by {QUICK_FILTERS.find((q) => q.id === activeQuickFilter)?.label})
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 text-xs text-graphite">
                Rows per page
                <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); resetToFirstPage(); }} className="rounded-xl border border-mist bg-white px-2 py-1 text-xs text-ink">
                  {PAGE_SIZES.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-8 px-2.5 text-xs"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Previous
              </Button>
              <span className="text-xs text-graphite font-medium px-2 tnum">
                Page {page} of {Math.max(1, Math.ceil(data.total / pageSize))}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page * pageSize >= data.total || loading}
                onClick={() => setPage((p) => p + 1)}
                className="h-8 px-2.5 text-xs"
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Categorization Rules Modal */}
      {showRulesModal && (
        <RulesManagerModal
          userId={userId}
          rules={rulesData?.items ?? []}
          onClose={() => setShowRulesModal(false)}
          onRulesChanged={handleTransactionActionCompleted}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Review Queue Section (Interactive Card Stack matching Showcase TRACK scene)
// ---------------------------------------------------------------------------

function ReviewQueueSection({
  userId,
  queue,
  pendingCount,
  onCompleted,
  onDismiss,
}: {
  userId: string;
  queue: Transaction[];
  pendingCount: number;
  onCompleted: () => void;
  onDismiss: () => void;
}) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState<TxnCategory | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [notes, setNotes] = useState<string>("");
  const [createRule, setCreateRule] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [tagInput, setTagInput] = useState("");
  const [showTagAdder, setShowTagAdder] = useState(false);

  const currentTxn = queue[currentIndex] || queue[0];

  useEffect(() => {
    if (currentTxn) {
      setSelectedCategory(currentTxn.category);
      setTags(currentTxn.tags || []);
      setNotes(currentTxn.notes || "");
    }
  }, [currentTxn]);

  // Keyboard shortcut listener: Enter to Confirm, S to Skip
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't trigger shortcuts if focus is inside an input or textarea
      if (["INPUT", "TEXTAREA", "SELECT"].includes((e.target as HTMLElement)?.tagName)) {
        return;
      }
      if (e.key === "Enter" && !submitting && currentTxn) {
        e.preventDefault();
        handleReviewAction("confirm");
      } else if ((e.key === "s" || e.key === "S") && !submitting && currentTxn) {
        e.preventDefault();
        handleReviewAction("skip");
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentTxn, selectedCategory, tags, notes, createRule, submitting]);

  if (!currentTxn) {
    return null;
  }

  const isInflow = currentTxn.amount > 0;
  const config = CATEGORY_CONFIG[selectedCategory || currentTxn.category] || CATEGORY_CONFIG.other;
  const CategoryIcon = config.icon;

  async function handleReviewAction(action: ReviewAction) {
    if (!currentTxn) return;
    setSubmitting(true);
    try {
      await api.reviewTransaction(userId, currentTxn.id, {
        action,
        category: selectedCategory || currentTxn.category,
        tags,
        notes: notes.trim() || undefined,
        create_rule: createRule,
        rule_pattern: currentTxn.merchant.split("#")[0].trim(),
      });
      if (currentIndex < queue.length - 1) {
        setCurrentIndex((prev) => prev + 1);
      } else {
        triggerConfetti({ count: 75 });
      }
      onCompleted();
    } finally {
      setSubmitting(false);
    }
  }

  function handleAddTag(tagText: string) {
    const clean = tagText.trim();
    if (clean && !tags.includes(clean)) {
      setTags([...tags, clean]);
    }
    setTagInput("");
    setShowTagAdder(false);
  }

  function handleRemoveTag(tagToRemove: string) {
    setTags(tags.filter((t) => t !== tagToRemove));
  }

  return (
    <Card className="border border-orange-200/80 bg-gradient-to-b from-[#FEF9EB] to-[#FBF8EF] p-5 sm:p-6 shadow-sm overflow-hidden relative">
      <div className="flex items-center justify-between pb-4 border-b border-orange-200/50">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-full bg-ember/10 flex items-center justify-center text-ember">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-ember">
                Smart Review Deck
              </span>
              <span className="text-[11px] font-semibold bg-white text-ink border border-orange-200 px-2 py-0.5 rounded-full tnum">
                {pendingCount} left to review
              </span>
            </div>
            <p className="text-xs text-graphite mt-0.5">
              Confirm or classify pending transactions with auto-rule learning.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onDismiss}
          className="text-pewter hover:text-ink p-1 rounded-md transition-colors"
          title="Minimize review deck"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-5 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Main Swipe / Presentation Card */}
        <div className="lg:col-span-7">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentTxn.id}
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.98 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="bg-white rounded-2xl p-5 sm:p-6 border border-black/[0.08] shadow-md flex flex-col gap-4 relative"
            >
              {/* Top Row: Merchant + Category Icon */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="h-11 w-11 rounded-2xl bg-fog flex items-center justify-center text-ink border border-black/[0.06] shadow-xs shrink-0">
                    <CategoryIcon className="h-5 w-5 text-ember" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-base sm:text-lg text-ink leading-tight">
                      {currentTxn.merchant}
                    </h3>
                    <span className="text-xs text-pewter font-medium mt-0.5 block">
                      {formatDate(currentTxn.date)} • Ref: {currentTxn.account_id}
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <span
                    className={cn(
                      "font-display text-xl sm:text-2xl font-bold tracking-tight tnum",
                      isInflow ? "text-emerald-700" : "text-ink"
                    )}
                  >
                    {isInflow ? "+" : "-"}
                    {formatCurrency(Math.abs(currentTxn.amount))}
                  </span>
                </div>
              </div>

              {/* Category Selector Selector */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-black/[0.05]">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-pewter uppercase tracking-wide">
                    Category:
                  </span>
                  <select
                    value={selectedCategory || currentTxn.category}
                    onChange={(e) => setSelectedCategory(e.target.value as TxnCategory)}
                    className="rounded-chip border border-mist bg-fog/60 px-3 py-1.5 text-xs font-semibold text-ink focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember cursor-pointer"
                  >
                    {CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {categoryLabel(cat)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Quick Auto-Rule Checkbox */}
                <label className="flex items-center gap-2 text-xs text-graphite cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={createRule}
                    onChange={(e) => setCreateRule(e.target.checked)}
                    className="rounded border-mist text-ember focus:ring-ember h-3.5 w-3.5 cursor-pointer accent-ember"
                  />
                  <span>Always categorize this merchant as <strong>{categoryLabel(selectedCategory || currentTxn.category)}</strong></span>
                </label>
              </div>

              {/* Tags & Notes Bar */}
              <div className="flex flex-wrap items-center gap-2 pt-2">
                <span className="text-xs font-semibold text-pewter flex items-center gap-1">
                  <Tag className="h-3 w-3" />
                  Tags:
                </span>
                {tags.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center gap-1 bg-fog border border-mist text-graphite px-2 py-0.5 rounded-full text-[11px] font-medium"
                  >
                    <span>{t}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(t)}
                      className="hover:text-ember"
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </span>
                ))}

                {showTagAdder ? (
                  <div className="inline-flex items-center gap-1">
                    <input
                      type="text"
                      placeholder="Tag..."
                      value={tagInput}
                      autoFocus
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleAddTag(tagInput);
                        if (e.key === "Escape") setShowTagAdder(false);
                      }}
                      className="rounded-chip border border-ember bg-white px-2 py-0.5 text-xs text-ink w-20 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => handleAddTag(tagInput)}
                      className="text-xs font-semibold text-ember hover:underline"
                    >
                      Add
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowTagAdder(true)}
                    className="inline-flex items-center gap-1 text-[11px] font-medium text-ember hover:underline cursor-pointer"
                  >
                    <Plus className="h-3 w-3" />
                    <span>Tag</span>
                  </button>
                )}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Action Controls & Shortcuts Guide */}
        <div className="lg:col-span-5 flex flex-col gap-3">
          <div className="flex flex-col sm:flex-row lg:flex-col gap-2.5">
            <Button
              variant="primary"
              size="md"
              disabled={submitting}
              onClick={() => handleReviewAction(selectedCategory !== currentTxn.category ? "recategorize" : "confirm")}
              className="w-full justify-center text-sm font-semibold shadow-sm h-11 bg-[#172554] hover:bg-[#1e3a8a] text-white"
            >
              <CheckCircle2 className="h-4 w-4 mr-2" />
              <span>
                {selectedCategory !== currentTxn.category ? "Recategorize & Confirm" : "Confirm Classification"}
              </span>
              <span className="ml-auto text-[11px] bg-white/20 px-1.5 py-0.5 rounded font-mono">
                ↵ Enter
              </span>
            </Button>

            <Button
              variant="secondary"
              size="md"
              disabled={submitting}
              onClick={() => handleReviewAction("skip")}
              className="w-full justify-center text-sm font-medium h-10 border-mist"
            >
              <Clock className="h-4 w-4 mr-2 text-pewter" />
              <span>Skip for Now</span>
              <span className="ml-auto text-[11px] bg-fog px-1.5 py-0.5 rounded text-pewter font-mono">
                S
              </span>
            </Button>
          </div>

          <div className="bg-white/60 rounded-xl p-3 border border-orange-200/40 text-[11px] text-graphite leading-relaxed">
            <p>
              💡 <strong>Smart Learning Active:</strong> FinPilot checks custom pattern rules first before falling back to natural language models.
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Table Row with Detail Drawer & Interactive Popover
// ---------------------------------------------------------------------------

function TransactionRowItem({
  txn,
  userId,
  accountName,
  selected,
  onToggle,
  onUpdated,
}: {
  txn: Transaction;
  userId: string;
  accountName: string;
  selected: boolean;
  onToggle: () => void;
  onUpdated: () => void;
}) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Detail Drawer state
  const [tags, setTags] = useState<string[]>(txn.tags || []);
  const [notes, setNotes] = useState<string>(txn.notes || "");
  const [newTag, setNewTag] = useState("");

  const isInflow = txn.amount > 0;
  const config = CATEGORY_CONFIG[txn.category] || CATEGORY_CONFIG.other;
  const CategoryIcon = config.icon;

  useEffect(() => {
    if (!popoverOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setPopoverOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [popoverOpen]);

  async function handleSelectCategory(next: TxnCategory) {
    if (next === txn.category) {
      setPopoverOpen(false);
      return;
    }
    setSaving(true);
    setPopoverOpen(false);
    try {
      await api.updateTransaction(userId, txn.id, {
        category: next,
        review_status: "reviewed",
      });
      onUpdated();
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveDetails() {
    setSaving(true);
    try {
      await api.updateTransaction(userId, txn.id, {
        tags,
        notes: notes.trim() || undefined,
        review_status: "reviewed",
      });
      setDetailOpen(false);
      onUpdated();
    } finally {
      setSaving(false);
    }
  }

  function handleAddTag() {
    const clean = newTag.trim();
    if (clean && !tags.includes(clean)) {
      setTags([...tags, clean]);
      setNewTag("");
    }
  }

  function handleRemoveTag(t: string) {
    setTags(tags.filter((x) => x !== t));
  }

  const reviewStatus = txn.review_status || "pending";

  return (
    <>
      <tr className={cn("hover:bg-fog/50 transition-colors duration-150 group", selected && "bg-tint-lime/50")}>
        <td className="pl-5 py-3.5">
          <input type="checkbox" aria-label={`Select ${txn.merchant}`} checked={selected} onChange={onToggle} />
        </td>
        <td className="whitespace-nowrap px-3 py-3.5 text-xs text-graphite tnum font-medium">{formatDate(txn.date)}</td>
        <td className="px-3 py-3.5">
          <div className="flex items-center gap-2.5">
            <MerchantLogo merchant={txn.merchant} color={CATEGORY_META[txn.category]?.color ?? "#9aa08a"} className="size-8 shrink-0" />
            <span className="font-semibold text-ink text-sm truncate">{txn.merchant}</span>
            {txn.notes && <FileText className="h-3 w-3 text-pewter" aria-label={txn.notes} />}
          </div>
        </td>
        <td className="px-3 py-3.5">
          {reviewStatus === "reviewed" ? (
            <span className="inline-flex rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800">Reviewed</span>
          ) : reviewStatus === "skipped" ? (
            <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-semibold text-slate-700">Skipped</span>
          ) : (
            <span className="inline-flex rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-800">To review</span>
          )}
        </td>
        <td className="whitespace-nowrap px-3 py-3.5 text-right">
          <span className={cn("tnum font-semibold text-sm", isInflow ? "text-emerald-700" : "text-ink")}>
            {isInflow ? "+" : "-"}
            {formatCurrency(Math.abs(txn.amount))}
          </span>
        </td>
        <td className="px-3 py-3.5 text-xs text-graphite">
          <span className="inline-flex max-w-[150px] truncate rounded-full border border-mist bg-white px-2.5 py-0.5">{accountName}</span>
        </td>
        {/* Interactive Category Badge & Popover Picker */}
        <td className="px-3 py-3.5 relative">
          <div className="relative inline-block" ref={popoverRef}>
            <button
              type="button"
              onClick={() => setPopoverOpen(!popoverOpen)}
              disabled={saving}
              className="group/badge inline-flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-ember/40 rounded-chip transition-transform active:scale-[0.98]"
              title="Click to reclassify category"
            >
              <Chip tone={config.tone} className="cursor-pointer hover:shadow-xs py-1 px-2.5 text-xs">
                <CategoryIcon className="h-3.5 w-3.5 mr-0.5 shrink-0" />
                <span>{saving ? "Saving..." : config.label}</span>
                <ChevronDown className="h-3 w-3 opacity-50 group-hover/badge:opacity-100 transition-opacity ml-0.5" />
              </Chip>
            </button>

            {/* Clean Floating Popover Category Picker */}
            {popoverOpen && (
              <div className="absolute left-0 top-full z-30 mt-2 w-72 rounded-surface border border-mist bg-white/98 p-3 shadow-xl backdrop-blur-md">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-black/[0.06]">
                  <span className="text-xs font-semibold text-ink">Reclassify Category</span>
                  <span className="text-[10px] text-pewter uppercase tracking-wide">Ledger Rule</span>
                </div>

                <div className="grid grid-cols-2 gap-1.5 max-h-64 overflow-y-auto pr-1">
                  {CATEGORIES.map((catKey) => {
                    const item = CATEGORY_CONFIG[catKey];
                    const ItemIcon = item.icon;
                    const isSelected = txn.category === catKey;

                    return (
                      <button
                        key={catKey}
                        type="button"
                        onClick={() => handleSelectCategory(catKey)}
                        className={cn(
                          "flex items-center gap-2 rounded-chip px-2.5 py-1.5 text-left text-xs transition-colors cursor-pointer select-none",
                          isSelected
                            ? "bg-sage text-ink font-semibold shadow-xs"
                            : "text-graphite hover:bg-fog hover:text-ink"
                        )}
                      >
                        <ItemIcon className={cn("h-3.5 w-3.5 shrink-0", isSelected ? "text-ember" : "text-pewter")} />
                        <span className="truncate">{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </td>

        <td className="px-3 py-3.5 text-center">
          <button
            type="button"
            onClick={() => setDetailOpen(!detailOpen)}
            className="inline-flex size-7 items-center justify-center rounded-full bg-fog text-graphite hover:bg-lime/50"
            title={txn.tags?.length ? txn.tags.join(", ") : "Add a tag or note"}
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </td>
      </tr>

      {/* Expandable Edit Tags & Notes Drawer */}
      {detailOpen && (
        <tr className="bg-fog/40 border-b border-black/[0.04]">
          <td colSpan={8} className="px-6 py-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-black/[0.06] shadow-xs">
              <div className="flex-1 flex flex-col gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-pewter">Tags:</span>
                  {tags.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1 bg-fog border border-mist px-2 py-0.5 rounded-full text-xs font-medium text-graphite"
                    >
                      {t}
                      <button type="button" onClick={() => handleRemoveTag(t)}>
                        <X className="h-3 w-3 hover:text-ember" />
                      </button>
                    </span>
                  ))}
                  <div className="inline-flex items-center gap-1">
                    <input
                      type="text"
                      placeholder="Add tag..."
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleAddTag();
                      }}
                      className="rounded-chip border border-mist px-2.5 py-1 text-xs text-ink focus:border-ember focus:outline-none w-28"
                    />
                    <Button variant="ghost" size="sm" onClick={handleAddTag} className="h-7 text-xs px-2">
                      Add
                    </Button>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-pewter">Note:</span>
                  <input
                    type="text"
                    placeholder="Audit note or receipt memo..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="flex-1 rounded-chip border border-mist px-2.5 py-1 text-xs text-ink focus:border-ember focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-center">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDetailOpen(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={saving}
                  onClick={handleSaveDetails}
                  className="text-xs"
                >
                  {saving ? "Saving..." : "Save Details"}
                </Button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Custom Categorization Rules Modal
// ---------------------------------------------------------------------------

function RulesManagerModal({
  userId,
  rules,
  onClose,
  onRulesChanged,
}: {
  userId: string;
  rules: CategorizationRule[];
  onClose: () => void;
  onRulesChanged: () => void;
}) {
  const [pattern, setPattern] = useState("");
  const [matchType, setMatchType] = useState<RuleMatchType>("contains");
  const [category, setCategory] = useState<TxnCategory>("dining");
  const [tagsText, setTagsText] = useState("");
  const [applyToExisting, setApplyToExisting] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleCreateRule(e: React.FormEvent) {
    e.preventDefault();
    if (!pattern.trim()) return;
    setSaving(true);
    try {
      const parsedTags = tagsText
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      await api.createRule(userId, {
        pattern: pattern.trim(),
        match_type: matchType,
        category,
        tags: parsedTags,
        apply_to_existing: applyToExisting,
      });

      setPattern("");
      setTagsText("");
      onRulesChanged();
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteRule(ruleId: string) {
    setDeletingId(ruleId);
    try {
      await api.deleteRule(userId, ruleId);
      onRulesChanged();
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-sage/70 p-4 backdrop-blur-xs">
      <div className="w-full max-w-2xl rounded-2xl border border-mist bg-white shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-black/[0.06] px-6 py-4 bg-fog/50">
          <div>
            <h2 className="font-display text-lg font-bold text-ink">
              Custom Categorization Rules
            </h2>
            <p className="text-xs text-graphite mt-0.5">
              Automate ledger classification based on merchant name matching.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-pewter hover:bg-mist/50 hover:text-ink transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          {/* Add New Rule Form */}
          <form onSubmit={handleCreateRule} className="bg-fog/60 rounded-xl p-4 border border-black/[0.05] flex flex-col gap-3">
            <span className="text-xs font-bold text-ink uppercase tracking-wide">
              Create New Auto-Rule
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-1">
                <label className="text-[11px] font-semibold text-pewter block mb-1">
                  Match Type
                </label>
                <select
                  value={matchType}
                  onChange={(e) => setMatchType(e.target.value as RuleMatchType)}
                  className="w-full rounded-chip border border-mist bg-white px-2.5 py-1.5 text-xs text-ink focus:border-ember focus:outline-none"
                >
                  <option value="contains">Contains substring</option>
                  <option value="exact">Exact Match</option>
                  <option value="starts_with">Starts With</option>
                  <option value="regex">Regex</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="text-[11px] font-semibold text-pewter block mb-1">
                  Merchant Pattern
                </label>
                <input
                  type="text"
                  placeholder="e.g. Swiggy, Netflix, Amazon"
                  value={pattern}
                  onChange={(e) => setPattern(e.target.value)}
                  required
                  className="w-full rounded-chip border border-mist bg-white px-3 py-1.5 text-xs text-ink placeholder:text-pewter focus:border-ember focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-pewter block mb-1">
                  Assign Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as TxnCategory)}
                  className="w-full rounded-chip border border-mist bg-white px-2.5 py-1.5 text-xs text-ink focus:border-ember focus:outline-none"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {categoryLabel(c)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-pewter block mb-1">
                  Tags (comma separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Food, Tax-Deductible"
                  value={tagsText}
                  onChange={(e) => setTagsText(e.target.value)}
                  className="w-full rounded-chip border border-mist bg-white px-3 py-1.5 text-xs text-ink placeholder:text-pewter focus:border-ember focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <label className="flex items-center gap-2 text-xs text-graphite cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={applyToExisting}
                  onChange={(e) => setApplyToExisting(e.target.checked)}
                  className="rounded border-mist text-ember focus:ring-ember h-3.5 w-3.5 cursor-pointer accent-ember"
                />
                <span>Apply immediately to existing matching transactions</span>
              </label>

              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={saving || !pattern.trim()}
                className="text-xs bg-[#172554] hover:bg-[#1e3a8a] text-white"
              >
                {saving ? "Creating..." : "Save Rule"}
              </Button>
            </div>
          </form>

          {/* Active Rules List */}
          <div className="flex flex-col gap-2">
            <span className="text-xs font-bold text-ink uppercase tracking-wide">
              Active User Rules ({rules.length})
            </span>

            {rules.length === 0 ? (
              <div className="text-center py-6 text-xs text-pewter bg-fog/30 rounded-xl border border-dashed border-mist">
                No custom categorization rules saved yet.
              </div>
            ) : (
              <div className="divide-y divide-black/[0.05] border border-black/[0.06] rounded-xl overflow-hidden bg-white">
                {rules.map((rule) => {
                  const item = CATEGORY_CONFIG[rule.category] || CATEGORY_CONFIG.other;
                  const RuleIcon = item.icon;

                  return (
                    <div
                      key={rule.id}
                      className="p-3 sm:px-4 flex items-center justify-between gap-3 hover:bg-fog/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-7 w-7 rounded-lg bg-fog flex items-center justify-center text-ink shrink-0">
                          <RuleIcon className="h-3.5 w-3.5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs text-ink">
                              &ldquo;{rule.pattern}&rdquo;
                            </span>
                            <span className="text-[10px] text-pewter bg-fog px-1.5 py-0.2 rounded border border-mist">
                              {rule.match_type}
                            </span>
                            <CornerDownRight className="h-3 w-3 text-pewter" />
                            <Chip tone={item.tone} className="py-0.2 px-2 text-[10px]">
                              {item.label}
                            </Chip>
                          </div>
                          {rule.tags && rule.tags.length > 0 && (
                            <div className="flex items-center gap-1 mt-1">
                              {rule.tags.map((t) => (
                                <span
                                  key={t}
                                  className="text-[10px] font-medium bg-fog text-graphite px-1.5 py-0.2 rounded"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      <button
                        type="button"
                        disabled={deletingId === rule.id}
                        onClick={() => handleDeleteRule(rule.id)}
                        className="text-pewter hover:text-rose-600 p-1.5 rounded transition-colors"
                        title="Delete rule"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-black/[0.06] px-6 py-3 bg-fog/40 flex justify-end">
          <Button variant="secondary" size="sm" onClick={onClose} className="text-xs">
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sortable Header Helper
// ---------------------------------------------------------------------------

interface SortableHeaderProps {
  field: SortField;
  label: string;
  currentField: SortField;
  direction: SortDirection;
  onSort: (field: SortField) => void;
  className?: string;
  align?: "left" | "right";
}

function SortableHeader({
  field,
  label,
  currentField,
  direction,
  onSort,
  className,
  align = "left",
}: SortableHeaderProps) {
  const isActive = currentField === field;

  return (
    <th className={className}>
      <button
        type="button"
        onClick={() => onSort(field)}
        className={cn(
          "inline-flex items-center gap-1.5 font-semibold text-xs tracking-wider transition-colors hover:text-ink cursor-pointer focus:outline-none",
          isActive ? "text-ink font-bold" : "text-pewter",
          align === "right" && "justify-end w-full"
        )}
      >
        <span>{label}</span>
        {isActive ? (
          direction === "asc" ? (
            <ArrowUp className="h-3 w-3 text-ember" />
          ) : (
            <ArrowDown className="h-3 w-3 text-ember" />
          )
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-40 hover:opacity-100" />
        )}
      </button>
    </th>
  );
}
