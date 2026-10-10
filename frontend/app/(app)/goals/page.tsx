"use client";

import { useCallback, useState } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import {
  Car,
  CheckCircle2,
  ChevronDown,
  Clock,
  Coins,
  GraduationCap,
  Heart,
  Home,
  Image as ImageIcon,
  Laptop,
  Link2,
  Palmtree,
  Plane,
  Plus,
  ShieldCheck,
  Sliders,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAsync, useUserId } from "@/lib/hooks";
import type { Account, GoalProgress } from "@/lib/types";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { triggerConfetti } from "@/components/ui/Confetti";
import { formatCurrency, formatDate } from "@/lib/format";

export interface CoverOption {
  key: string;
  label: string;
  icon: LucideIcon;
  path: string;
  category: string;
}

const GOAL_COVERS: CoverOption[] = [
  { key: "emergency_fund", label: "Emergency Runway", icon: ShieldCheck, path: "/goal-covers/emergency_fund.svg", category: "Safety & Reserves" },
  { key: "dream_car", label: "Dream Car / EV", icon: Car, path: "/goal-covers/dream_car.svg", category: "Major Purchase" },
  { key: "luxury_travel", label: "Luxury Travel", icon: Plane, path: "/goal-covers/luxury_travel.svg", category: "Leisure & Experience" },
  { key: "home_downpayment", label: "Home Downpayment", icon: Home, path: "/goal-covers/home_downpayment.svg", category: "Real Estate" },
  { key: "higher_education", label: "Higher Education", icon: GraduationCap, path: "/goal-covers/higher_education.svg", category: "Education" },
  { key: "tech_setup", label: "Pro Tech Setup", icon: Laptop, path: "/goal-covers/tech_setup.svg", category: "Equipment & Tools" },
  { key: "retirement", label: "Financial Freedom", icon: Palmtree, path: "/goal-covers/retirement.svg", category: "Long-term Wealth" },
  { key: "wedding", label: "Celebration / Wedding", icon: Heart, path: "/goal-covers/wedding.svg", category: "Life Milestones" },
  { key: "general", label: "Capital Target", icon: Target, path: "/goal-covers/general.svg", category: "General Growth" },
];

function getCover(key?: string): CoverOption {
  const match = GOAL_COVERS.find((c) => c.key === key);
  return match || GOAL_COVERS[GOAL_COVERS.length - 1];
}

const GOAL_TEMPLATES = [
  { name: "6-Month Emergency Runway", amount: 500000, cover: "emergency_fund" },
  { name: "Dream Car (EV)", amount: 1800000, cover: "dream_car" },
  { name: "Japan Cherry Blossom Trip", amount: 350000, cover: "luxury_travel" },
  { name: "Home Down Payment", amount: 2500000, cover: "home_downpayment" },
];

export default function GoalsPage() {
  const userId = useUserId();
  const fetchGoals = useCallback(() => api.goals(userId), [userId]);
  const fetchAccounts = useCallback(() => api.accounts(userId), [userId]);

  const { data: goalsData, error, loading, reload, mutate } = useAsync(fetchGoals, [userId]);
  const { data: accountsData } = useAsync(fetchAccounts, [userId]);

  const patchGoals = (fn: (goals: GoalProgress[]) => GoalProgress[]) => mutate((prev) => fn(prev ?? []));

  // Form State
  const [name, setName] = useState("");
  const [targetAmount, setTargetAmount] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [coverKey, setCoverKey] = useState("emergency_fund");
  const [fundingAccountId, setFundingAccountId] = useState("");
  const [autoTrack, setAutoTrack] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [showCoverPicker, setShowCoverPicker] = useState(false);

  const accounts: Account[] = accountsData ?? [];
  const goals: GoalProgress[] = goalsData ?? [];

  async function handleCreate() {
    const amount = Number(targetAmount);
    if (!name.trim()) {
      setCreateError("Give the goal a descriptive name.");
      return;
    }
    if (!amount || amount <= 0) {
      setCreateError("Enter a target amount greater than zero.");
      return;
    }
    setCreating(true);
    setCreateError(null);

    const draft = {
      name: name.trim(),
      amount,
      date: targetDate || undefined,
      coverKey,
      fundingAccountId: fundingAccountId || undefined,
      autoTrack,
    };

    setName("");
    setTargetAmount("");
    setTargetDate("");
    setFundingAccountId("");
    setAutoTrack(false);

    try {
      await api.createGoal(userId, {
        name: draft.name,
        target_amount: draft.amount,
        target_date: draft.date,
        cover_key: draft.coverKey,
        funding_account_id: draft.fundingAccountId,
        auto_track: draft.autoTrack,
      });
      triggerConfetti({ count: 65 });
      reload();
    } catch (err) {
      reload();
      setName(draft.name);
      setTargetAmount(String(draft.amount));
      setTargetDate(draft.date || "");
      setCoverKey(draft.coverKey);
      setFundingAccountId(draft.fundingAccountId || "");
      setAutoTrack(draft.autoTrack);
      setCreateError(err instanceof Error ? err.message : "Could not create goal");
    } finally {
      setCreating(false);
    }
  }

  function handleSelectTemplate(tpl: { name: string; amount: number; cover: string }) {
    setName(tpl.name);
    setTargetAmount(String(tpl.amount));
    setCoverKey(tpl.cover);
    if (createError) setCreateError(null);
  }

  // Calculate live preview of required monthly for create form
  let previewRequiredMonthly = 0;
  if (targetAmount && targetDate) {
    const today = new Date();
    const tgt = new Date(targetDate);
    const months = (tgt.getFullYear() - today.getFullYear()) * 12 + (tgt.getMonth() - today.getMonth());
    const validMonths = Math.max(1, months);
    previewRequiredMonthly = Math.round(Number(targetAmount) / validMonths);
  }

  return (
    <div className="flex flex-col gap-8 pb-16">
      {/* Editorial Fraunces Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-black/[0.04]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              Wealth Horizons
            </span>
            <span className="text-xs text-pewter font-medium">• Automated Goal Milestones & Cover Art</span>
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-medium text-ink mt-1.5 tracking-tight">
            Savings Goals & Milestones
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-graphite max-w-2xl leading-relaxed">
            Define aspirational capital milestones with visual cover art, auto-track bank balances, and tune monthly savings velocity.
          </p>
        </div>
      </div>

      {/* New Goal Creation Card */}
      <Card className="p-6 border border-black/[0.08] shadow-xs">
        <CardHeader className="mb-4">
          <div className="flex items-center justify-between w-full">
            <div>
              <CardTitle className="text-base font-semibold text-ink">Set New Financial Goal</CardTitle>
              <p className="text-xs text-graphite mt-0.5">
                Configure milestone targets, auto-sync funding accounts, and tune required monthly pace.
              </p>
            </div>
            <span className="text-xs font-semibold text-pewter uppercase tracking-wider">
              {goals.length} Goals Active
            </span>
          </div>
        </CardHeader>

        <div className="flex flex-col gap-4">
          {/* Main Form Fields */}
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
            <div className="sm:col-span-4 flex flex-col gap-1.5">
              <label htmlFor="goal-name" className="text-xs font-medium text-graphite">
                Goal Name
              </label>
              <input
                id="goal-name"
                type="text"
                placeholder="e.g. Dream Car (EV)"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (createError) setCreateError(null);
                }}
                className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-sm text-ink placeholder:text-pewter focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
              />
            </div>

            <div className="sm:col-span-3 flex flex-col gap-1.5">
              <label htmlFor="goal-amount" className="text-xs font-medium text-graphite">
                Target Amount (₹)
              </label>
              <input
                id="goal-amount"
                type="number"
                min={0}
                placeholder="e.g. 1800000"
                value={targetAmount}
                onChange={(e) => {
                  setTargetAmount(e.target.value);
                  if (createError) setCreateError(null);
                }}
                className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-sm text-ink placeholder:text-pewter focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember tnum"
              />
            </div>

            <div className="sm:col-span-3 flex flex-col gap-1.5">
              <label htmlFor="goal-date" className="text-xs font-medium text-graphite">
                Target Date
              </label>
              <input
                id="goal-date"
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-sm text-ink focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
              />
            </div>

            {/* Cover Picker Trigger Button */}
            <div className="sm:col-span-2 flex flex-col gap-1.5">
              <label className="text-xs font-medium text-graphite">Cover Style</label>
              <button
                type="button"
                onClick={() => setShowCoverPicker(!showCoverPicker)}
                className="w-full flex items-center justify-between rounded-chip border border-mist bg-white px-3 py-2 text-xs font-medium text-ink hover:border-black/[0.14] transition-colors cursor-pointer"
              >
                <span className="truncate">{getCover(coverKey).label}</span>
                <ChevronDown className="h-3.5 w-3.5 text-pewter ml-1 shrink-0" />
              </button>
            </div>
          </div>

          {/* Cover Selection Dropdown Modal */}
          {showCoverPicker && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-surface bg-fog border border-black/[0.08] grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5"
            >
              {GOAL_COVERS.map((cov) => {
                const Icon = cov.icon;
                const isSelected = cov.key === coverKey;
                return (
                  <button
                    key={cov.key}
                    type="button"
                    onClick={() => {
                      setCoverKey(cov.key);
                      setShowCoverPicker(false);
                    }}
                    className={`flex items-center gap-2.5 p-2 rounded-chip text-left transition-all border cursor-pointer ${
                      isSelected
                        ? "bg-white border-ember shadow-xs text-ink"
                        : "bg-white/60 border-black/[0.04] text-graphite hover:bg-white hover:border-black/[0.1]"
                    }`}
                  >
                    <div className="w-8 h-8 rounded-lg overflow-hidden shrink-0 relative bg-black/5 flex items-center justify-center">
                      <Image src={cov.path} alt={cov.label} width={32} height={32} className="object-cover w-full h-full" />
                    </div>
                    <div className="truncate">
                      <p className="text-xs font-semibold leading-tight truncate">{cov.label}</p>
                      <p className="text-[10px] text-pewter leading-tight truncate">{cov.category}</p>
                    </div>
                  </button>
                );
              })}
            </motion.div>
          )}

          {/* Funding Account & Auto-Track Configuration */}
          <div className="p-3.5 rounded-surface bg-fog/80 border border-black/[0.04] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <div className="flex items-center gap-2">
                <Link2 className="h-4 w-4 text-pewter shrink-0" />
                <label htmlFor="funding-account" className="text-xs font-medium text-graphite whitespace-nowrap">
                  Link Account:
                </label>
                <select
                  id="funding-account"
                  value={fundingAccountId}
                  onChange={(e) => setFundingAccountId(e.target.value)}
                  className="rounded-chip border border-mist bg-white px-2.5 py-1 text-xs text-ink focus:border-ember focus:outline-none"
                >
                  <option value="">No linked account (Manual tracker)</option>
                  {accounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({formatCurrency(acc.balance)})
                    </option>
                  ))}
                </select>
              </div>

              {fundingAccountId && (
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={autoTrack}
                    onChange={(e) => setAutoTrack(e.target.checked)}
                    className="rounded border-mist text-ember focus:ring-ember h-3.5 w-3.5"
                  />
                  <span className="text-xs font-medium text-ink">Auto-track balance from account</span>
                </label>
              )}
            </div>

            {previewRequiredMonthly > 0 && (
              <div className="text-xs text-graphite font-medium">
                Pace preview: <span className="font-bold text-ember tnum">{formatCurrency(previewRequiredMonthly)}/mo</span> needed
              </div>
            )}
          </div>

          {/* Starter Blueprints & Submit Action */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] text-pewter font-medium">Starter Blueprints:</span>
              {GOAL_TEMPLATES.map((tpl) => (
                <button
                  key={tpl.name}
                  type="button"
                  onClick={() => handleSelectTemplate(tpl)}
                  className="rounded-full px-2.5 py-0.5 text-xs font-medium text-graphite bg-fog border border-mist hover:bg-white hover:text-ink hover:border-black/[0.12] transition-colors cursor-pointer"
                >
                  {tpl.name}
                </button>
              ))}
            </div>

            <Button
              variant="primary"
              onClick={handleCreate}
              disabled={creating}
              className="h-10 text-xs font-semibold px-5"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>{creating ? "Adding Goal..." : "Add Goal"}</span>
            </Button>
          </div>

          {createError && (
            <p className="text-xs font-semibold text-rose-700 bg-rose-50 px-3 py-2 rounded-chip border border-rose-200">
              {createError}
            </p>
          )}
        </div>
      </Card>

      {/* Loading Skeleton */}
      {loading && !goalsData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {Array.from({ length: 2 }).map((_, i) => (
            <Card key={i} className="flex flex-col gap-4 animate-pulse overflow-hidden">
              <Skeleton className="h-36 w-full" />
              <div className="p-6 flex flex-col gap-3">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-3 w-full rounded-full" />
                <Skeleton className="h-4 w-28" />
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <Card className="flex flex-col gap-3 border-rose-200 bg-rose-50/30 p-6">
          <p className="text-sm font-semibold text-rose-800">Could not load goals: {error}</p>
          <Button variant="secondary" size="sm" onClick={reload} className="self-start text-xs">
            Retry Loading
          </Button>
        </Card>
      )}

      {/* Empty State */}
      {goals.length === 0 && !loading && (
        <Card className="p-8">
          <EmptyState
            icon={<Target className="h-10 w-10 text-pewter" />}
            title="No savings goals yet"
            body="Start mapping your financial milestones by adding an emergency fund, major purchase, or retirement target above."
          />
        </Card>
      )}

      {/* Goals Grid */}
      {goals.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {goals.map((gp) => (
            <CoverGoalCard
              key={gp.goal.id}
              progress={gp}
              userId={userId}
              accounts={accounts}
              onChanged={reload}
              patchGoals={patchGoals}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CoverGoalCard({
  progress,
  userId,
  accounts,
  onChanged,
  patchGoals,
}: {
  progress: GoalProgress;
  userId: string;
  accounts: Account[];
  onChanged: () => void;
  patchGoals: (fn: (goals: GoalProgress[]) => GoalProgress[]) => void;
  }) {
  const { goal, monthly_contribution, projected_completion_date, on_track, months_remaining, required_monthly } = progress;
  const pct = goal.target_amount > 0 ? Math.min(100, Math.round((goal.current_amount / goal.target_amount) * 100)) : 0;
  const remainingGap = Math.max(0, goal.target_amount - goal.current_amount);

  const [contribution, setContribution] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showTuning, setShowTuning] = useState(false);
  const [tuningAmount, setTuningAmount] = useState(goal.target_amount);

  const cover = getCover(goal.cover_key);
  const linkedAccount = accounts.find((a) => a.id === goal.funding_account_id);

  async function handleContribute(customAmount?: number) {
    const amount = customAmount ?? Number(contribution);
    if (!amount || amount <= 0) return;
    setSaving(true);
    const nextAmount = goal.current_amount + amount;
    patchGoals((goals) =>
      goals.map((g) => (g.goal.id === goal.id ? { ...g, goal: { ...g.goal, current_amount: nextAmount } } : g))
    );
    setContribution("");
    try {
      await api.updateGoal(userId, goal.id, { current_amount: nextAmount });
    } catch {
      onChanged();
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleAutoTrack() {
    const nextVal = !goal.auto_track;
    patchGoals((goals) =>
      goals.map((g) => (g.goal.id === goal.id ? { ...g, goal: { ...g.goal, auto_track: nextVal } } : g))
    );
    try {
      await api.updateGoal(userId, goal.id, { auto_track: nextVal });
      onChanged();
    } catch {
      onChanged();
    }
  }

  async function handleSaveTunedTarget() {
    setSaving(true);
    try {
      await api.updateGoal(userId, goal.id, { target_amount: tuningAmount });
      setShowTuning(false);
      onChanged();
    } catch {
      onChanged();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    patchGoals((goals) => goals.filter((g) => g.goal.id !== goal.id));
    try {
      await api.deleteGoal(userId, goal.id);
    } catch {
      onChanged();
    } finally {
      setDeleting(false);
    }
  }

  // Pace projection text
  let paceProjectionText = "";
  if (projected_completion_date && goal.target_date) {
    const projDate = new Date(projected_completion_date);
    const tgtDate = new Date(goal.target_date);
    const monthsDiff = Math.round((tgtDate.getTime() - projDate.getTime()) / (1000 * 60 * 60 * 24 * 30.4375));

    if (monthsDiff > 0) {
      paceProjectionText = `On track to complete by ${formatDate(projected_completion_date)} (${monthsDiff} mo ahead of target)`;
    } else if (monthsDiff === 0) {
      paceProjectionText = `On track to complete by ${formatDate(projected_completion_date)} (right on target)`;
    } else {
      paceProjectionText = `Projected completion ${formatDate(projected_completion_date)} (${Math.abs(monthsDiff)} mo behind target)`;
    }
  } else if (projected_completion_date) {
    paceProjectionText = `At current pace (${formatCurrency(monthly_contribution)}/mo), projected ${formatDate(projected_completion_date)}`;
  } else if (months_remaining !== null) {
    paceProjectionText = `${months_remaining} months remaining at current velocity`;
  } else {
    paceProjectionText = "No regular contribution velocity recorded yet";
  }

  return (
    <Card
      hoverable
      className="rounded-card border border-black/[0.08] bg-white shadow-[0_2px_12px_rgba(15,23,42,0.03)] hover:shadow-[0_8px_24px_rgba(15,23,42,0.07)] hover:border-black/[0.14] transition-all flex flex-col justify-between overflow-hidden relative group"
    >
      {/* Visual Cover Photo Header */}
      <div className="relative h-32 w-full bg-slate-900 overflow-hidden shrink-0">
        <Image
          src={cover.path}
          alt={goal.name}
          fill
          className="object-cover opacity-90 transition-transform duration-500 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />

        {/* Top Badges over image */}
        <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-white/90 bg-[#3f7d5c]/70 backdrop-blur-md px-2.5 py-0.5 rounded-full border border-white/20">
            {cover.category}
          </span>

          <Chip
            tone={on_track ? "success" : "warning"}
            className="text-xs font-semibold backdrop-blur-md shadow-xs"
          >
            {on_track ? (
              <>
                <CheckCircle2 className="h-3 w-3 mr-0.5" />
                On Track
              </>
            ) : (
              <>
                <Clock className="h-3 w-3 mr-0.5" />
                Pace Needed
              </>
            )}
          </Chip>
        </div>

        {/* Title over bottom of cover */}
        <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between">
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight drop-shadow-sm leading-tight">
              {goal.name}
            </h3>
            <p className="text-[11px] text-white/80 drop-shadow-sm mt-0.5">
              {goal.target_date ? `Target Date: ${formatDate(goal.target_date)}` : "Open-ended horizon"}
            </p>
          </div>

          <span className="text-sm font-bold text-white bg-white/20 backdrop-blur-md px-2.5 py-0.5 rounded-full tnum">
            {pct}%
          </span>
        </div>
      </div>

      {/* Card Content Body */}
      <div className="p-5 sm:p-6 flex flex-col gap-4">
        {/* Linked Funding Account Pill if exists */}
        {linkedAccount && (
          <div className="flex items-center justify-between px-3 py-1.5 rounded-chip bg-fog border border-black/[0.04]">
            <div className="flex items-center gap-2">
              <Link2 className="h-3.5 w-3.5 text-ember" />
              <span className="text-xs font-medium text-ink">
                Linked: <strong className="font-semibold">{linkedAccount.name}</strong>
              </span>
            </div>
            <button
              type="button"
              onClick={handleToggleAutoTrack}
              className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border transition-colors cursor-pointer ${
                goal.auto_track
                  ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                  : "bg-white text-pewter border-mist"
              }`}
            >
              {goal.auto_track ? "Auto-Tracking Active" : "Auto-Track Paused"}
            </button>
          </div>
        )}

        {/* Progress Bar Container with Milestones (25%, 50%, 75%, 100%) */}
        <div className="flex flex-col gap-1.5">
          <div className="relative w-full h-2.5 rounded-full bg-fog overflow-hidden border border-black/[0.04]">
            <div className="absolute inset-0 flex justify-between pointer-events-none px-0.5 z-10">
              <span className="h-full w-0.5 bg-black/[0.1]" style={{ left: "25%", position: "absolute" }} />
              <span className="h-full w-0.5 bg-black/[0.1]" style={{ left: "50%", position: "absolute" }} />
              <span className="h-full w-0.5 bg-black/[0.1]" style={{ left: "75%", position: "absolute" }} />
            </div>

            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="h-full rounded-full bg-ember relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent w-full animate-pulse" />
            </motion.div>
          </div>

          <div className="flex justify-between items-center text-[10px] text-pewter font-medium px-0.5 select-none">
            <span>0%</span>
            <span>25%</span>
            <span className="font-semibold text-graphite">50% Midpoint</span>
            <span>75%</span>
            <span className="font-bold text-ink tnum">{formatCurrency(goal.current_amount)}</span>
          </div>
        </div>

        {/* Metrics Grid: Current, Target, Required Monthly */}
        <div className="grid grid-cols-3 gap-2 p-3 rounded-surface bg-fog/60 border border-black/[0.04]">
          <div>
            <span className="text-[10px] font-medium text-pewter block uppercase tracking-wide">Saved</span>
            <span className="font-display text-sm sm:text-base font-bold text-ink block tnum leading-tight mt-0.5">
              {formatCurrency(goal.current_amount)}
            </span>
          </div>
          <div>
            <span className="text-[10px] font-medium text-pewter block uppercase tracking-wide">Target</span>
            <span className="font-display text-sm sm:text-base font-bold text-graphite block tnum leading-tight mt-0.5">
              {formatCurrency(goal.target_amount)}
            </span>
          </div>
          <div className="text-right">
            <span className="text-[10px] font-medium text-pewter block uppercase tracking-wide">Required Pace</span>
            <span className="font-display text-sm sm:text-base font-bold text-ember block tnum leading-tight mt-0.5">
              {required_monthly && required_monthly > 0 ? `${formatCurrency(required_monthly)}/mo` : "On Target"}
            </span>
          </div>
        </div>

        {/* Dynamic Pace Projection Badge */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-chip bg-white border border-black/[0.06] text-xs">
          <Sparkles className="h-3.5 w-3.5 text-ember shrink-0" />
          <span className="text-graphite font-medium leading-relaxed truncate">
            {paceProjectionText}
          </span>
        </div>

        {/* Interactive Tune Targets Slider Drawer */}
        {showTuning && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="p-3.5 rounded-surface bg-fog border border-mist flex flex-col gap-2.5"
          >
            <div className="flex items-center justify-between text-xs font-semibold text-ink">
              <span>Tune Target Capital:</span>
              <span className="font-bold text-ember tnum">{formatCurrency(tuningAmount)}</span>
            </div>
            <input
              type="range"
              min={goal.current_amount}
              max={Math.max(goal.target_amount * 2, 1000000)}
              step={10000}
              value={tuningAmount}
              onChange={(e) => setTuningAmount(Number(e.target.value))}
              className="w-full accent-ember cursor-pointer"
            />
            <div className="flex items-center justify-between pt-1">
              <span className="text-[11px] text-pewter">
                New pace: ~{formatCurrency(Math.round(Math.max(0, tuningAmount - goal.current_amount) / Math.max(1, months_remaining || 12)))}/mo
              </span>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveTunedTarget}
                disabled={saving}
                className="h-7 text-xs px-3"
              >
                Save Target
              </Button>
            </div>
          </motion.div>
        )}

        {/* Contribution & Management Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-black/[0.06] pt-3">
          <div className="flex items-center gap-1.5 flex-1 min-w-[170px]">
            <input
              type="number"
              min={0}
              placeholder="Add amount"
              value={contribution}
              onChange={(e) => setContribution(e.target.value)}
              className="w-24 sm:w-28 rounded-chip border border-mist bg-white px-2.5 py-1.5 text-xs text-ink placeholder:text-pewter focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember tnum"
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleContribute()}
              disabled={saving || !contribution}
              className="h-8 text-xs font-semibold px-2.5"
            >
              {saving ? "Saving..." : "Add"}
            </Button>
            <button
              type="button"
              onClick={() => handleContribute(5000)}
              disabled={saving}
              className="hidden sm:inline-flex rounded-full px-2 py-1 text-[11px] font-medium text-graphite bg-fog hover:bg-white border border-mist cursor-pointer tnum"
            >
              +₹5k
            </button>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setShowTuning(!showTuning)}
              className="text-xs font-medium text-graphite hover:text-ink px-2.5 py-1.5 rounded-chip hover:bg-fog border border-mist transition-colors cursor-pointer flex items-center gap-1"
              title="Tune target amount"
            >
              <Sliders className="h-3 w-3 text-pewter" />
              <span>Tune</span>
            </button>

            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="text-pewter hover:text-rose-600 transition-colors p-1.5 rounded-chip hover:bg-rose-50 cursor-pointer disabled:opacity-40"
              title="Delete goal"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </Card>
  );
}
