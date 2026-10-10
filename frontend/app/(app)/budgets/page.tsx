"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Car,
  CheckCircle2,
  Cloud,
  CreditCard,
  Film,
  HeartPulse,
  Home,
  Percent,
  Plus,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  Sparkles,
  Trash2,
  TrendingUp,
  Utensils,
  Zap,
  HelpCircle,
  RotateCcw,
  Sliders,
  ArrowRight,
  TrendingDown,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAsync, useUserId } from "@/lib/hooks";
import type { Budget, BudgetStatus, TxnCategory } from "@/lib/types";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatCurrency, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export const CATEGORY_ICONS: Record<
  TxnCategory,
  { label: string; icon: LucideIcon }
> = {
  income: { label: "Income", icon: TrendingUp },
  rent_housing: { label: "Rent & Housing", icon: Home },
  emi_loan: { label: "EMI & Loan", icon: CreditCard },
  groceries: { label: "Groceries", icon: ShoppingCart },
  dining: { label: "Dining & Food", icon: Utensils },
  transport: { label: "Transport & Fuel", icon: Car },
  utilities: { label: "Utilities", icon: Zap },
  subscriptions: { label: "Subscriptions", icon: Cloud },
  shopping: { label: "Shopping", icon: ShoppingBag },
  healthcare: { label: "Healthcare", icon: HeartPulse },
  entertainment: { label: "Entertainment", icon: Film },
  investment_sip: { label: "Investment & SIP", icon: TrendingUp },
  credit_card_payment: { label: "Credit Card", icon: CreditCard },
  transfer: { label: "Transfer", icon: CreditCard },
  fees_interest: { label: "Fees & Interest", icon: Percent },
  other: { label: "Other", icon: HelpCircle },
};

const BUDGETABLE_CATEGORIES: TxnCategory[] = [
  "rent_housing",
  "emi_loan",
  "groceries",
  "dining",
  "transport",
  "utilities",
  "subscriptions",
  "shopping",
  "healthcare",
  "entertainment",
  "investment_sip",
  "fees_interest",
  "other",
];

function categoryLabel(category: string): string {
  const item = CATEGORY_ICONS[category as TxnCategory];
  return item ? item.label : category.replace(/_/g, " ");
}

function normalizePercent(value: number): number {
  const pct = value <= 1 ? value * 100 : value;
  return Math.min(100, Math.max(0, Math.round(pct)));
}

const PRESET_AMOUNTS = [5000, 10000, 20000, 35000];

export default function BudgetsPage() {
  const userId = useUserId();

  const fetchSafeToSpend = useCallback(() => api.safeToSpend(userId), [userId]);
  const safeToSpend = useAsync(fetchSafeToSpend, [userId]);

  const fetchBudgets = useCallback(() => api.budgets(userId), [userId]);
  const budgets = useAsync(fetchBudgets, [userId]);

  const fetchStatus = useCallback(() => api.budgetStatus(userId), [userId]);
  const status = useAsync(fetchStatus, [userId]);

  const [newCategory, setNewCategory] = useState<TxnCategory>(BUDGETABLE_CATEGORIES[0]);
  const [newLimit, setNewLimit] = useState("");
  const [newRollover, setNewRollover] = useState(true);
  const [newRolloverCap, setNewRolloverCap] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Calculate days remaining in current month for daily pace
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const lastDayOfMonth = new Date(year, month + 1, 0).getDate();
  const daysRemaining = Math.max(1, lastDayOfMonth - today.getDate() + 1);

  async function handleCreate() {
    const limit = Number(newLimit);
    if (!limit || limit <= 0) {
      setCreateError("Enter a monthly envelope limit greater than zero.");
      return;
    }
    setCreating(true);
    setCreateError(null);
    const category = newCategory;
    const cap = newRolloverCap ? Number(newRolloverCap) : undefined;

    budgets.mutate((prev) => [
      ...(prev ?? []).filter((b) => b.category !== category),
      {
        id: `tmp-${Date.now()}`,
        user_id: userId,
        category,
        monthly_limit: limit,
        rollover_enabled: newRollover,
        rollover_cap: cap,
      },
    ]);

    status.mutate((prev) => {
      const list = prev ?? [];
      const existing = list.find((s) => s.category === category);
      const spent = existing?.spent_so_far ?? 0;
      const next: BudgetStatus = {
        category,
        monthly_limit: limit,
        spent_so_far: spent,
        remaining: limit - spent,
        percent_used: limit > 0 ? (spent / limit) * 100 : 0,
        status: existing?.status ?? "under",
        rollover_enabled: newRollover,
        rollover_cap: cap,
        rollover_amount: 0,
        total_available: limit - spent,
      };
      return existing ? list.map((s) => (s.category === category ? next : s)) : [...list, next];
    });

    setNewLimit("");
    setNewRolloverCap("");
    try {
      await api.createBudget(userId, {
        category,
        monthly_limit: limit,
        rollover_enabled: newRollover,
        rollover_cap: cap,
      });
    } catch (err) {
      budgets.reload();
      status.reload();
      setNewLimit(String(limit));
      setCreateError(err instanceof Error ? err.message : "Could not create budget envelope");
    } finally {
      setCreating(false);
    }
  }

  async function handleToggleRollover(budgetId: string, currentVal: boolean) {
    budgets.mutate((prev) =>
      (prev ?? []).map((b) => (b.id === budgetId ? { ...b, rollover_enabled: !currentVal } : b))
    );
    try {
      await api.updateBudget(userId, budgetId, { rollover_enabled: !currentVal });
      status.reload();
    } catch {
      budgets.reload();
      status.reload();
    }
  }

  async function handleDelete(budgetId: string) {
    const category = (budgets.data ?? []).find((b) => b.id === budgetId)?.category;
    budgets.mutate((prev) => (prev ?? []).filter((b) => b.id !== budgetId));
    if (category) status.mutate((prev) => (prev ?? []).filter((s) => s.category !== category));
    try {
      await api.deleteBudget(userId, budgetId);
    } catch {
      budgets.reload();
      status.reload();
    }
  }

  const budgetStatuses = status.data ?? [];
  const totalLimit = budgetStatuses.reduce((acc, b) => acc + b.monthly_limit, 0);
  const totalRollover = budgetStatuses.reduce((acc, b) => acc + (b.rollover_amount ?? 0), 0);
  const totalSpent = budgetStatuses.reduce((acc, b) => acc + b.spent_so_far, 0);
  const totalAvailable = totalLimit + totalRollover - totalSpent;
  const overallUsedPct = (totalLimit + totalRollover) > 0
    ? Math.min(100, Math.round((totalSpent / (totalLimit + totalRollover)) * 100))
    : 0;

  // Identify over-budget and near-limit envelopes for the top alert banner
  const overEnvelopes = budgetStatuses.filter((b) => b.status === "over" || b.percent_used >= 100);
  const nearEnvelopes = budgetStatuses.filter((b) => b.status === "near");

  const chartData = budgetStatuses.map((b) => ({
    category: categoryLabel(b.category),
    spent: b.spent_so_far,
    limit: b.monthly_limit + (b.rollover_amount ?? 0),
    rollover: b.rollover_amount ?? 0,
    status: b.status,
  }));

  const budgetIdByCategory = new Map<string, string>(
    (budgets.data ?? []).map((b: Budget) => [b.category, b.id])
  );

  const loadingAll = (status.loading && !status.data) || (safeToSpend.loading && !safeToSpend.data);
  const anyError = status.error ?? budgets.error ?? safeToSpend.error;

  return (
    <div className="flex flex-col gap-8 pb-16 min-w-0 max-w-full">
      {/* Editorial Fraunces Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-black/[0.04]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              Cash-Flow Allocation
            </span>
            <span className="text-xs text-pewter font-medium">• Proactive Envelope Rollover</span>
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-medium text-ink mt-1.5 tracking-tight">
            Budgets & Rollover
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-graphite max-w-2xl leading-relaxed">
            Set monthly category envelopes, automatically roll over unspent surplus, and protect your discretionary liquidity.
          </p>
        </div>
      </div>

      {/* Live Over-Budget / Near-Limit Alert Banner */}
      {overEnvelopes.length > 0 && (
        <Card className="border border-rose-200 bg-rose-50/60 p-4 sm:p-5 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="h-8 w-8 rounded-full bg-rose-100 flex items-center justify-center text-rose-700 shrink-0 mt-0.5">
                <AlertTriangle className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-rose-900">
                  {overEnvelopes.length} Category Envelope{overEnvelopes.length > 1 ? "s" : ""} Exceeded
                </h3>
                <p className="text-xs text-rose-800 mt-0.5">
                  {overEnvelopes.map((e) => categoryLabel(e.category)).join(", ")} exceeded monthly limit + rollover buffer.
                </p>
              </div>
            </div>

            <Link
              href="/simulate"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-rose-800 hover:text-rose-950 bg-white/80 border border-rose-300 px-3 py-1.5 rounded-chip transition-colors self-start sm:self-center shrink-0"
            >
              <TrendingDown className="h-3.5 w-3.5" />
              <span>Simulate 15% Spend Cut</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </Card>
      )}

      {/* Hero "Safe-to-Spend" Tactile Card */}
      {safeToSpend.loading && !safeToSpend.data ? (
        <Card className="p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="flex flex-col gap-2.5 flex-1">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-10 w-52" />
              <Skeleton className="h-4 w-64" />
            </div>
            <div className="w-full sm:w-72 flex flex-col gap-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-full rounded-full" />
              <Skeleton className="h-4 w-48" />
            </div>
          </div>
        </Card>
      ) : safeToSpend.data ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="relative overflow-hidden p-6 sm:p-8 bg-gradient-to-br from-white via-white to-fog/60 border border-black/[0.08] shadow-[0_4px_24px_rgba(15,23,42,0.04)]">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Left Column: Metric & Daily Pace */}
              <div className="lg:col-span-7 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                  </span>
                  <span className="text-xs font-semibold text-graphite uppercase tracking-wider">
                    Safe-to-Spend Liquidity
                  </span>
                  <span className="text-xs text-pewter">
                    &middot; As of {formatDate(safeToSpend.data.as_of_date)}
                  </span>
                </div>

                <div className="flex items-baseline gap-3 mt-1">
                  <span className="font-display text-3xl sm:text-5xl font-bold text-ink tnum tracking-tight">
                    {formatCurrency(safeToSpend.data.amount)}
                  </span>
                  <Chip tone="success" className="text-xs font-semibold self-center">
                    Available Today
                  </Chip>
                </div>

                {/* Daily Allowable Pace Indicator */}
                <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-black/[0.04]">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs">
                    <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
                    <span className="tnum font-bold">
                      {formatCurrency(Math.max(0, Math.round(safeToSpend.data.amount / daysRemaining)))}/day
                    </span>
                    <span className="font-normal text-emerald-700">safe pace</span>
                  </span>
                  <span className="text-xs text-graphite font-medium">
                    for remaining <span className="text-ink font-semibold tnum">{daysRemaining} days</span> this month
                  </span>
                  {totalRollover > 0 && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-orange-50 text-ember border border-ember/20">
                      <RotateCcw className="h-3 w-3" />
                      +{formatCurrency(totalRollover)} total rollover surplus
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-pewter mt-1">
                  Basis: {safeToSpend.data.basis}
                </p>
              </div>

              {/* Right Column: Envelope Capacity Progress Meter */}
              <div className="lg:col-span-5 flex flex-col gap-3 rounded-surface border border-black/[0.06] bg-fog/60 p-4 sm:p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink">Total Envelope Utilization</span>
                  <span className="text-xs font-bold text-ink tnum">
                    {overallUsedPct}% utilized
                  </span>
                </div>

                {/* Visual Capacity Meter */}
                <div className="relative w-full h-3 rounded-full bg-mist/60 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${overallUsedPct}%` }}
                    transition={{ duration: 0.9, ease: "easeOut" }}
                    className={cn(
                      "h-full rounded-full transition-all",
                      overallUsedPct > 100
                        ? "bg-rose-500"
                        : overallUsedPct > 85
                          ? "bg-ember"
                          : "bg-emerald-600"
                    )}
                  />
                </div>

                <div className="flex items-center justify-between text-xs pt-1 border-t border-black/[0.04]">
                  <div>
                    <span className="text-[11px] text-pewter block">Total Spent</span>
                    <span className="font-semibold text-ink tnum">{formatCurrency(totalSpent)}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[11px] text-pewter block">
                      {totalAvailable >= 0 ? "Total Available Surplus" : "Deficit Overrun"}
                    </span>
                    <span
                      className={cn(
                        "font-semibold tnum",
                        totalAvailable >= 0 ? "text-emerald-700" : "text-rose-600"
                      )}
                    >
                      {totalAvailable >= 0 ? "+" : "-"}
                      {formatCurrency(Math.abs(totalAvailable))}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </motion.div>
      ) : null}

      {/* New Budget Envelope Card */}
      <Card className="p-6">
        <CardHeader className="mb-4">
          <div className="flex items-center justify-between w-full">
            <div>
              <CardTitle className="text-base font-semibold text-ink">Create Budget Envelope</CardTitle>
              <p className="text-xs text-graphite mt-0.5">
                Define a monthly spending cap with optional surplus rollover into next month.
              </p>
            </div>
            <span className="text-xs font-semibold text-pewter uppercase tracking-wider">
              {budgetStatuses.length} Envelopes Active
            </span>
          </div>
        </CardHeader>

        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
            <div className="sm:col-span-4 flex flex-col gap-1.5">
              <label htmlFor="budget-category" className="text-xs font-medium text-graphite">
                Category
              </label>
              <select
                id="budget-category"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as TxnCategory)}
                className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-sm text-ink focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember cursor-pointer"
              >
                {BUDGETABLE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {categoryLabel(c)}
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-3 flex flex-col gap-1.5">
              <label htmlFor="budget-limit" className="text-xs font-medium text-graphite">
                Monthly Limit (₹)
              </label>
              <input
                id="budget-limit"
                type="number"
                min={0}
                placeholder="e.g. 15000"
                value={newLimit}
                onChange={(e) => {
                  setNewLimit(e.target.value);
                  if (createError) setCreateError(null);
                }}
                className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-sm text-ink focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember tnum"
              />
            </div>

            <div className="sm:col-span-3 flex flex-col gap-1.5">
              <label htmlFor="budget-cap" className="text-xs font-medium text-graphite">
                Rollover Cap (₹, optional)
              </label>
              <input
                id="budget-cap"
                type="number"
                min={0}
                placeholder="e.g. 5000"
                value={newRolloverCap}
                onChange={(e) => setNewRolloverCap(e.target.value)}
                className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-sm text-ink focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember tnum"
              />
            </div>

            <div className="sm:col-span-2">
              <Button
                variant="primary"
                onClick={handleCreate}
                disabled={creating}
                className="w-full h-10 text-xs font-semibold bg-[#172554] hover:bg-[#1e3a8a] text-white"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>{creating ? "Adding..." : "Add Envelope"}</span>
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-black/[0.04]">
            {/* Quick preset amount chips */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-pewter font-medium">Quick Limit Presets:</span>
              {PRESET_AMOUNTS.map((amt) => (
                <button
                  key={amt}
                  type="button"
                  onClick={() => setNewLimit(String(amt))}
                  className="rounded-full px-2.5 py-0.5 text-xs font-medium text-graphite bg-fog border border-mist hover:bg-white hover:text-ink hover:border-black/[0.12] transition-colors cursor-pointer tnum"
                >
                  {formatCurrency(amt)}
                </button>
              ))}
            </div>

            {/* Rollover checkbox */}
            <label className="flex items-center gap-2 text-xs text-graphite cursor-pointer select-none">
              <input
                type="checkbox"
                checked={newRollover}
                onChange={(e) => setNewRollover(e.target.checked)}
                className="rounded border-mist text-ember focus:ring-ember h-3.5 w-3.5 cursor-pointer accent-ember"
              />
              <span>Enable surplus rollover from previous months</span>
            </label>
          </div>

          {createError && (
            <p className="text-xs font-semibold text-rose-700 bg-rose-50 px-3 py-2 rounded-chip border border-rose-200">
              {createError}
            </p>
          )}
        </div>
      </Card>

      {/* Error state */}
      {anyError && (
        <Card className="flex flex-col gap-3 border-rose-200 bg-rose-50/30 p-6">
          <p className="text-sm font-semibold text-rose-800">Could not load budget data: {anyError}</p>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              budgets.reload();
              status.reload();
              safeToSpend.reload();
            }}
            className="self-start text-xs"
          >
            Retry Loading
          </Button>
        </Card>
      )}

      {/* Empty State */}
      {budgetStatuses.length === 0 && !loadingAll && (
        <Card className="p-8">
          <EmptyState
            icon={<ShieldCheck className="h-10 w-10 text-pewter" />}
            title="No budget envelopes configured"
            body="Start taking control of your monthly cash flow by creating your first category envelope above."
          />
        </Card>
      )}

      {/* Budget Envelopes Grid & Bar Chart */}
      {budgetStatuses.length > 0 && (
        <>
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-ink">Category Envelopes ({budgetStatuses.length})</h2>
              <span className="text-xs text-pewter font-medium">
                Surplus Rollover & Burn Tracking
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {budgetStatuses.map((b) => (
                <BudgetEnvelopeCard
                  key={b.category}
                  status={b}
                  budgetId={budgetIdByCategory.get(b.category)}
                  onToggleRollover={handleToggleRollover}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          </div>

          {/* Upgraded Recharts Bar Chart */}
          <Card className="p-6">
            <CardHeader className="mb-4">
              <div className="flex items-center justify-between w-full">
                <div>
                  <CardTitle className="text-base font-semibold text-ink">
                    Envelope Utilization & Velocity
                  </CardTitle>
                  <p className="text-xs text-graphite mt-0.5">
                    Comparative actual spend vs. effective monthly limit (base limit + rollover surplus).
                  </p>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1.5 text-graphite">
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
                    <span>Safe</span>
                  </span>
                  <span className="flex items-center gap-1.5 text-graphite">
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                    <span>Near Cap (&gt;80%)</span>
                  </span>
                  <span className="flex items-center gap-1.5 text-graphite">
                    <span className="h-2.5 w-2.5 rounded-full bg-ember" />
                    <span>Over Budget</span>
                  </span>
                </div>
              </div>
            </CardHeader>

            <div className="h-80 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ left: 10, right: 20, top: 12, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.06)" vertical={false} />
                  <XAxis
                    dataKey="category"
                    tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                    height={60}
                    axisLine={{ stroke: "rgba(15, 23, 42, 0.08)" }}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(v: number) => formatCurrency(v)}
                    tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
                    width={85}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomGlassTooltip />} cursor={{ fill: "rgba(15, 23, 42, 0.02)" }} />
                  <Bar dataKey="spent" radius={[6, 6, 0, 0]} isAnimationActive={false}>
                    {chartData.map((entry, index) => {
                      const isOver = entry.spent > entry.limit;
                      const isNear = entry.spent > entry.limit * 0.8;
                      const fillColor = isOver ? "#ff5900" : isNear ? "#d97706" : "#059669";
                      return <Cell key={`cell-${index}`} fill={fillColor} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function BudgetEnvelopeCard({
  status,
  budgetId,
  onToggleRollover,
  onDelete,
}: {
  status: BudgetStatus;
  budgetId: string | undefined;
  onToggleRollover: (budgetId: string, currentVal: boolean) => void;
  onDelete: (budgetId: string) => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const rolloverAmt = status.rollover_amount ?? 0;
  const effectiveLimit = status.monthly_limit + rolloverAmt;
  const width = normalizePercent(status.percent_used);
  const isOver = status.status === "over" || (status.total_available !== undefined && status.total_available < 0);
  const isNear = status.status === "near";

  const config = CATEGORY_ICONS[status.category] || CATEGORY_ICONS.other;
  const CategoryIcon = config.icon;

  async function handleDelete() {
    if (!budgetId) return;
    setDeleting(true);
    try {
      await onDelete(budgetId);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Card
      hoverable
      className="p-5 sm:p-6 rounded-card border border-black/[0.08] bg-white shadow-[0_2px_10px_rgba(15,23,42,0.03)] flex flex-col justify-between gap-4 transition-all"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-xl border shrink-0",
              isOver
                ? "bg-orange-50 border-ember/20 text-ember-dark"
                : isNear
                  ? "bg-amber-50 border-amber-200 text-amber-700"
                  : "bg-emerald-50 border-emerald-200 text-emerald-700"
            )}
          >
            <CategoryIcon className="h-5 w-5" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-ink leading-tight">
                {categoryLabel(status.category)}
              </h4>
              {rolloverAmt > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <RotateCcw className="h-2.5 w-2.5" />
                  +{formatCurrency(rolloverAmt)} Rollover
                </span>
              )}
            </div>
            <p className="text-xs text-pewter mt-0.5 tnum">
              Base: {formatCurrency(status.monthly_limit)}
              {rolloverAmt > 0 && ` • Effective: ${formatCurrency(effectiveLimit)}`}
            </p>
          </div>
        </div>

        {/* Warning or Safe Status Badge */}
        <div className="flex items-center gap-2">
          {isOver ? (
            <Chip tone="accent" className="font-semibold text-xs">
              <AlertTriangle className="h-3 w-3 mr-0.5" />
              Over Limit
            </Chip>
          ) : isNear ? (
            <Chip tone="warning" className="font-semibold text-xs">
              Near Limit
            </Chip>
          ) : (
            <Chip tone="success" className="font-semibold text-xs">
              <CheckCircle2 className="h-3 w-3 mr-0.5" />
              Healthy
            </Chip>
          )}

          {budgetId && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="text-pewter hover:text-rose-600 transition-colors p-1.5 rounded-chip hover:bg-rose-50 cursor-pointer disabled:opacity-40"
              title="Delete envelope"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar Container with Animated Bar */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-pewter font-medium tnum">
            Spent {formatCurrency(status.spent_so_far)} of {formatCurrency(effectiveLimit)}
          </span>
          <span className="font-bold text-ink tnum">{width}%</span>
        </div>

        <div className="relative w-full h-2.5 rounded-full bg-fog overflow-hidden border border-black/[0.04]">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${width}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className={cn(
              "h-full rounded-full transition-all",
              isOver ? "bg-ember" : isNear ? "bg-amber-500" : "bg-emerald-600"
            )}
          />
        </div>

        {/* Exact Surplus / Deficit Callout & Rollover Toggle */}
        <div className="flex items-center justify-between text-xs pt-1">
          <div className="flex items-center gap-2">
            {budgetId && (
              <button
                type="button"
                onClick={() => onToggleRollover(budgetId, Boolean(status.rollover_enabled))}
                className={cn(
                  "inline-flex items-center gap-1 text-[11px] font-medium transition-colors cursor-pointer",
                  status.rollover_enabled ? "text-emerald-700 hover:text-emerald-900" : "text-pewter hover:text-ink"
                )}
                title="Toggle unspent surplus rollover into next month"
              >
                <RotateCcw className="h-3 w-3" />
                <span>{status.rollover_enabled ? "Rollover ON" : "Rollover OFF"}</span>
              </button>
            )}
          </div>

          <span
            className={cn(
              "font-bold tnum",
              isOver ? "text-rose-600 font-semibold" : "text-emerald-700 font-semibold"
            )}
          >
            {status.total_available !== undefined
              ? status.total_available >= 0
                ? `+${formatCurrency(status.total_available)} available`
                : `-${formatCurrency(Math.abs(status.total_available))} over`
              : status.remaining >= 0
                ? `+${formatCurrency(status.remaining)} remaining`
                : `-${formatCurrency(Math.abs(status.remaining))} over`}
          </span>
        </div>
      </div>
    </Card>
  );
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value?: number;
    payload?: {
      category: string;
      spent: number;
      limit: number;
      rollover: number;
      status: string;
    };
  }>;
}

function CustomGlassTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  const isOver = data.spent > data.limit;
  const diff = data.limit - data.spent;

  return (
    <div className="rounded-chip border border-black/[0.08] bg-white/95 p-3.5 shadow-xl backdrop-blur-md text-xs flex flex-col gap-2 min-w-[200px]">
      <div className="flex items-center justify-between border-b border-black/[0.06] pb-1.5">
        <span className="font-semibold text-ink">{data.category}</span>
        <span
          className={cn(
            "text-[10px] font-bold uppercase px-1.5 py-0.5 rounded-full border",
            isOver
              ? "bg-orange-50 text-ember-dark border-ember/20"
              : "bg-emerald-50 text-emerald-700 border-emerald-200"
          )}
        >
          {isOver ? "Over Budget" : "Healthy"}
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-graphite">Spent to Date:</span>
          <span className="font-bold text-ink tnum">{formatCurrency(data.spent)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-pewter">Effective Cap:</span>
          <span className="font-medium text-graphite tnum">{formatCurrency(data.limit)}</span>
        </div>
        {data.rollover > 0 && (
          <div className="flex items-center justify-between text-[11px] text-emerald-700">
            <span>Rollover Surplus:</span>
            <span className="font-semibold tnum">+{formatCurrency(data.rollover)}</span>
          </div>
        )}
        <div className="flex items-center justify-between border-t border-black/[0.04] pt-1">
          <span className="text-pewter">{isOver ? "Deficit Overrun:" : "Available Buffer:"}</span>
          <span className={cn("font-bold tnum", isOver ? "text-rose-600" : "text-emerald-700")}>
            {diff >= 0 ? `+${formatCurrency(diff)}` : `-${formatCurrency(Math.abs(diff))}`}
          </span>
        </div>
      </div>
    </div>
  );
}
