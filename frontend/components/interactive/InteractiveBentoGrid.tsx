"use client";

import { useState, useRef, MouseEvent, useCallback } from "react";
import { motion, AnimatePresence, type HTMLMotionProps } from "framer-motion";
import {
  ArrowUpRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  Coffee,
  Cloud,
  Home,
  Sparkles,
  DollarSign,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";

// --- Spotlight Card Wrapper ---
interface SpotlightCardProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  className?: string;
  spotlightColor?: string;
}

function SpotlightCard({
  children,
  className,
  spotlightColor = "rgba(230, 92, 43, 0.08)",
  ...props
}: SpotlightCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = useCallback((e: MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    setCoords({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  }, []);

  return (
    <motion.div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      whileHover={{ y: -3, transition: { duration: 0.2, ease: "easeOut" } }}
      className={cn(
        "relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 transition-all duration-300",
        "shadow-[0_2px_12px_rgba(20,20,19,0.04)] hover:shadow-[0_12px_32px_rgba(20,20,19,0.08)]",
        className
      )}
      {...props}
    >
      {/* Dynamic Cursor Spotlight Overlay */}
      <div
        className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition-opacity duration-300"
        style={{
          opacity: isHovered ? 1 : 0,
          background: `radial-gradient(380px circle at ${coords.x}px ${coords.y}px, ${spotlightColor}, transparent 65%)`,
        }}
      />
      {/* Content */}
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}

// --- Data Types & Defaults ---
interface Transaction {
  id: string;
  merchant: string;
  category: "Housing" | "Tech" | "Dining" | "Wellness" | "Income";
  amount: number;
  date: string;
  isPositive?: boolean;
}

const SAMPLE_TRANSACTIONS: Transaction[] = [
  { id: "tx-1", merchant: "Stripe Payout", category: "Income", amount: 4850.0, date: "Today, 10:24 AM", isPositive: true },
  { id: "tx-2", merchant: "Anthropic Claude Pro", category: "Tech", amount: -20.0, date: "Today, 8:15 AM" },
  { id: "tx-3", merchant: "Whole Foods Market", category: "Dining", amount: -84.62, date: "Yesterday" },
  { id: "tx-4", merchant: "Equinox Fitness", category: "Wellness", amount: -240.0, date: "Sep 26" },
  { id: "tx-5", merchant: "Vercel Enterprise", category: "Tech", amount: -150.0, date: "Sep 25" },
];

const BUDGET_CATEGORIES = [
  { name: "Housing & Utilities", spent: 1850, budget: 1900, color: "bg-lime-dark" },
  { name: "Tech & Infrastructure", spent: 390, budget: 350, over: true, color: "bg-ember" },
  { name: "Dining & Social", spent: 480, budget: 600, color: "bg-sage" },
  { name: "Health & Wellness", spent: 240, budget: 300, color: "bg-slate-500" },
];

export function InteractiveBentoGrid() {
  // Autopilot Toggles State
  const [autopilotRules, setAutopilotRules] = useState([
    {
      id: "rule-1",
      title: "Zombie Sub Tracker",
      desc: "Detected 2 unused subscriptions ($38/mo)",
      active: true,
      badge: "Saved $456/yr",
    },
    {
      id: "rule-2",
      title: "Yield Spillover",
      desc: "Auto-sweep balances > $5k to 5.1% APY",
      active: true,
      badge: "Next: $420",
    },
    {
      id: "rule-3",
      title: "Cash Gap Predictor",
      desc: "Simulate cash flow dips 90 days out",
      active: true,
      badge: "0 gaps found",
    },
  ]);

  // Transaction category filter
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const toggleRule = (id: string) => {
    setAutopilotRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, active: !r.active } : r))
    );
  };

  const filteredTransactions =
    activeCategory === "All"
      ? SAMPLE_TRANSACTIONS
      : SAMPLE_TRANSACTIONS.filter((t) => t.category === activeCategory);

  return (
    <section className="w-full py-12" aria-label="Interactive Financial Bento Grid">
      {/* Header */}
      <div className="mb-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-ember/20 bg-ember/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-ember">
            <Sparkles className="h-3.5 w-3.5" />
            Tactile Bento Architecture
          </div>
          <h2 className="mt-2 font-display text-2xl md:text-3xl font-bold tracking-tight text-[var(--foreground)]">
            Autonomous Financial Operations
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Explore live reactive telemetry, intelligent auto-pilot rules, and granular cash velocity.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          <span className="font-mono uppercase tracking-wider">Telemetry Live</span>
        </div>
      </div>

      {/* Grid Container */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* ========================================================
            CARD 1: Real-time Cash Velocity & Net Inflow (Span 2 on LG)
           ======================================================== */}
        <SpotlightCard className="lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  Velocity & Inflow
                </span>
                <h3 className="text-lg font-bold text-[var(--foreground)] mt-0.5">
                  Monthly Cash Velocity
                </h3>
              </div>
              <div className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                <TrendingUp className="h-3.5 w-3.5" />
                <span>+24.6% vs target</span>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-subtle)] p-3">
                <span className="text-xs text-[var(--muted)] block">Net Inflow (Sep)</span>
                <span className="text-xl sm:text-2xl font-bold tnum text-[var(--foreground)] mt-1 block">
                  {formatCurrency(12480)}
                </span>
                <span className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5 block">
                  ↑ +$1,200 rollover
                </span>
              </div>
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-subtle)] p-3">
                <span className="text-xs text-[var(--muted)] block">Total Outflow</span>
                <span className="text-xl sm:text-2xl font-bold tnum text-[var(--foreground)] mt-1 block">
                  {formatCurrency(5620)}
                </span>
                <span className="text-[11px] text-ember mt-0.5 block">
                  45.0% burn rate
                </span>
              </div>
              <div className="col-span-2 sm:col-span-1 rounded-xl border border-[var(--border)] bg-[var(--surface-subtle)] p-3">
                <span className="text-xs text-[var(--muted)] block">Net Capital Surplus</span>
                <span className="text-xl sm:text-2xl font-bold tnum text-emerald-600 dark:text-emerald-400 mt-1 block">
                  +{formatCurrency(6860)}
                </span>
                <span className="text-[11px] text-[var(--muted)] mt-0.5 block">
                  55.0% retained
                </span>
              </div>
            </div>

            {/* Mini Progress / Ratio Bar */}
            <div className="mt-6">
              <div className="flex justify-between text-xs text-[var(--muted)] mb-1.5">
                <span>Monthly Budget Utilization</span>
                <span className="font-semibold tnum text-[var(--foreground)]">45.0% of $12,480</span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-[var(--surface-subtle)] border border-[var(--border)]">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: "45%" }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="h-full rounded-full bg-gradient-to-r from-ember to-amber-500"
                />
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-[var(--border)] flex items-center justify-between text-xs text-[var(--muted)]">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              Runway extended to <strong className="text-[var(--foreground)]">8.4 months</strong>
            </span>
            <span className="font-mono text-[10px]">SYNCED 2M AGO</span>
          </div>
        </SpotlightCard>

        {/* ========================================================
            CARD 2: Autonomous Financial Health Ring Score (Span 1)
           ======================================================== */}
        <SpotlightCard className="flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                Resilience Engine
              </span>
              <span className="rounded-full bg-ember/10 border border-ember/20 px-2 py-0.5 text-[11px] font-semibold text-ember">
                Grade A+
              </span>
            </div>

            <div className="mt-4 flex items-center gap-5">
              {/* Radial Score Gauge */}
              <div className="relative flex items-center justify-center shrink-0">
                <svg className="h-24 w-24 -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-[var(--surface-subtle)]"
                    fill="transparent"
                  />
                  <motion.circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke="currentColor"
                    strokeWidth="8"
                    strokeDasharray={251.2}
                    initial={{ strokeDashoffset: 251.2 }}
                    animate={{ strokeDashoffset: 251.2 * (1 - 0.88) }}
                    transition={{ duration: 1.2, ease: "easeOut" }}
                    strokeLinecap="round"
                    className="text-ember"
                    fill="transparent"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold font-display text-[var(--foreground)]">88</span>
                  <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">/100</span>
                </div>
              </div>

              <div>
                <h4 className="font-bold text-[var(--foreground)]">Optimal Runway</h4>
                <p className="text-xs text-[var(--muted)] mt-1 leading-relaxed">
                  Your baseline resilience index outpaces 92% of peer households.
                </p>
              </div>
            </div>

            <div className="mt-5 space-y-2 text-xs">
              <div className="flex items-center justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--muted)]">High-Interest Debt</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">$0.00 (0%)</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--muted)]">Emergency Cushion</span>
                <span className="font-semibold text-[var(--foreground)] tnum">6.2 months</span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-[var(--muted)]">Predictability Score</span>
                <span className="font-semibold text-[var(--foreground)] tnum">94% Stable</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[var(--border)]">
            <button
              type="button"
              className="w-full flex items-center justify-between rounded-lg bg-[var(--surface-subtle)] px-3 py-2 text-xs font-semibold text-[var(--foreground)] hover:bg-[var(--border)] transition-colors"
            >
              <span>View Factor Breakdown</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </SpotlightCard>

        {/* ========================================================
            CARD 3: Tactile Transaction Stream (Span 1 or 2 on LG)
           ======================================================== */}
        <SpotlightCard className="lg:col-span-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                Live Ledger
              </span>
              <h3 className="text-lg font-bold text-[var(--foreground)] mt-0.5">
                Recent Ledger Activity
              </h3>
            </div>

            {/* Filter pills */}
            <div className="flex flex-wrap gap-1.5">
              {["All", "Income", "Tech", "Dining", "Wellness"].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setActiveCategory(cat)}
                  className={cn(
                    "rounded-full px-2.5 py-1 text-xs font-medium transition-all duration-200",
                    activeCategory === cat
                      ? "bg-[#172554] text-white shadow-sm hover:bg-[#1e3a8a]"
                      : "bg-[var(--surface-subtle)] text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--border)]"
                  )}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Transactions List */}
          <div className="space-y-2 mt-3">
            <AnimatePresence mode="popLayout">
              {filteredTransactions.map((tx) => (
                <motion.div
                  key={tx.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{ duration: 0.2 }}
                  className="group flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--surface-subtle)] p-3 hover:border-ember/30 hover:bg-[var(--surface)] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex h-9 w-9 items-center justify-center rounded-lg border text-sm font-semibold transition-transform group-hover:scale-105",
                        tx.isPositive
                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          : "border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)]"
                      )}
                    >
                      {tx.category === "Income" && <DollarSign className="h-4 w-4" />}
                      {tx.category === "Tech" && <Cloud className="h-4 w-4" />}
                      {tx.category === "Dining" && <Coffee className="h-4 w-4" />}
                      {tx.category === "Wellness" && <Zap className="h-4 w-4" />}
                      {tx.category === "Housing" && <Home className="h-4 w-4" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-[var(--foreground)]">
                          {tx.merchant}
                        </span>
                        <span className="rounded-full bg-[var(--border)] px-2 py-0.5 text-[10px] font-medium text-[var(--muted)]">
                          {tx.category}
                        </span>
                      </div>
                      <span className="text-xs text-[var(--muted)]">{tx.date}</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span
                      className={cn(
                        "font-bold text-sm tnum",
                        tx.isPositive
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-[var(--foreground)]"
                      )}
                    >
                      {tx.isPositive ? `+${formatCurrency(tx.amount)}` : formatCurrency(tx.amount)}
                    </span>
                    <span className="text-[10px] text-[var(--muted)] block">Settled</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </SpotlightCard>

        {/* ========================================================
            CARD 4: Autopilot Rules & Smart Toggles (Span 1)
           ======================================================== */}
        <SpotlightCard className="flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                Autonomous Rules
              </span>
              <span className="flex items-center gap-1 text-xs text-ember font-semibold">
                <Zap className="h-3.5 w-3.5 fill-ember" />
                Active
              </span>
            </div>

            <h3 className="text-lg font-bold text-[var(--foreground)] mt-1">
              FinPilot Copilot Rules
            </h3>
            <p className="text-xs text-[var(--muted)] mt-1">
              Tactile toggles for automated liquidity balance & subscription controls.
            </p>

            <div className="mt-4 space-y-3">
              {autopilotRules.map((rule) => (
                <div
                  key={rule.id}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface-subtle)] p-3 transition-colors hover:border-ember/20"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-[var(--foreground)]">
                          {rule.title}
                        </span>
                        <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                          {rule.badge}
                        </span>
                      </div>
                      <p className="text-xs text-[var(--muted)] mt-1 leading-snug">
                        {rule.desc}
                      </p>
                    </div>

                    {/* Tactile Toggle Switch */}
                    <button
                      type="button"
                      role="switch"
                      aria-checked={rule.active}
                      onClick={() => toggleRule(rule.id)}
                      className={cn(
                        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#172554] focus:ring-offset-2",
                        rule.active ? "bg-[#172554]" : "bg-[var(--border)]"
                      )}
                    >
                      <motion.span
                        layout
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        className={cn(
                          "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0",
                          rule.active ? "translate-x-5" : "translate-x-0"
                        )}
                      />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-5 pt-3 border-t border-[var(--border)]">
            <span className="text-xs text-[var(--muted)] flex items-center justify-between">
              <span>Next execution window</span>
              <strong className="text-[var(--foreground)] font-mono">Tomorrow 00:00 UTC</strong>
            </span>
          </div>
        </SpotlightCard>

        {/* ========================================================
            CARD 5: Category Rollover & Budget Breakdown (Full Width 3 cols)
           ======================================================== */}
        <SpotlightCard className="lg:col-span-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                Category Allocations
              </span>
              <h3 className="text-lg font-bold text-[var(--foreground)] mt-0.5">
                September Envelope Rollover Status
              </h3>
            </div>
            <div className="text-xs text-[var(--muted)]">
              Remaining Envelope Cap: <strong className="text-emerald-600 dark:text-emerald-400 tnum font-semibold">{formatCurrency(690)}</strong>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {BUDGET_CATEGORIES.map((cat) => {
              const pct = Math.round((cat.spent / cat.budget) * 100);
              const isOver = cat.spent > cat.budget;

              return (
                <div
                  key={cat.name}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface-subtle)] p-4 flex flex-col justify-between hover:border-[var(--border)] hover:bg-[var(--surface)] transition-all"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-[var(--muted)] truncate">
                        {cat.name}
                      </span>
                      {isOver ? (
                        <span className="rounded bg-ember/15 px-1.5 py-0.5 text-[10px] font-bold text-ember">
                          OVER
                        </span>
                      ) : (
                        <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                          {pct}%
                        </span>
                      )}
                    </div>

                    <div className="mt-3 flex items-baseline justify-between">
                      <span className="text-lg font-bold text-[var(--foreground)] tnum">
                        {formatCurrency(cat.spent)}
                      </span>
                      <span className="text-xs text-[var(--muted)] tnum">
                        / {formatCurrency(cat.budget)}
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[var(--border)]">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(pct, 100)}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                        className={cn(
                          "h-full rounded-full",
                          isOver ? "bg-ember" : "bg-emerald-500"
                        )}
                      />
                    </div>
                  </div>

                  <div className="mt-3 pt-2 border-t border-[var(--border)] flex items-center justify-between text-[11px]">
                    <span className="text-[var(--muted)]">Rollover Balance</span>
                    <span
                      className={cn(
                        "font-semibold tnum",
                        isOver
                          ? "text-ember"
                          : "text-emerald-600 dark:text-emerald-400"
                      )}
                    >
                      {isOver
                        ? `-${formatCurrency(cat.spent - cat.budget)}`
                        : `+${formatCurrency(cat.budget - cat.spent)}`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </SpotlightCard>
      </div>
    </section>
  );
}
