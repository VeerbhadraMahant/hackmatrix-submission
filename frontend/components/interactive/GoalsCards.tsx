"use client";

import { useState, useRef } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { ShieldCheck, Zap, Plane, Home, Sliders, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";

export interface FinancialGoal {
  id: string;
  title: string;
  category: string;
  targetDate: string;
  currentAmount: number;
  targetAmount: number;
  icon: "shield" | "debt" | "vacation" | "home";
  accentColor: string;
}

const DEFAULT_GOALS: FinancialGoal[] = [
  {
    id: "goal-1",
    title: "6-Month Emergency Runway",
    category: "Financial Safety",
    targetDate: "Dec 2026",
    currentAmount: 384000,
    targetAmount: 480000,
    icon: "shield",
    accentColor: "#059669", // Emerald
  },
  {
    id: "goal-2",
    title: "Car Loan Avalanche Prepayment",
    category: "Debt Elimination",
    targetDate: "Aug 2027",
    currentAmount: 175000,
    targetAmount: 250000,
    icon: "debt",
    accentColor: "#ff5900", // Ember
  },
  {
    id: "goal-3",
    title: "Annual Family Vacation",
    category: "Leisure & Travel",
    targetDate: "May 2027",
    currentAmount: 72000,
    targetAmount: 120000,
    icon: "vacation",
    accentColor: "#0891b2", // Cyan
  },
  {
    id: "goal-4",
    title: "Home Down Payment Fund",
    category: "Long-Term Wealth",
    targetDate: "Dec 2030",
    currentAmount: 450000,
    targetAmount: 1500000,
    icon: "home",
    accentColor: "#4f46e5", // Indigo
  },
];

export interface GoalsCardsProps {
  title?: string;
  subtitle?: string;
  initialGoals?: FinancialGoal[];
  className?: string;
}

export function GoalsCards({
  title = "Your Goals, On Track",
  subtitle = "Set customized targets, track automated SIP allocations, and simulate milestone achievements with live interactive progress tuning.",
  initialGoals = DEFAULT_GOALS,
  className,
}: GoalsCardsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { amount: 0.2, once: true });
  const shouldReduceMotion = useReducedMotion();

  const [goals, setGoals] = useState<FinancialGoal[]>(initialGoals);
  const [isEditing, setIsEditing] = useState(false);

  const handleTargetChange = (id: string, newTarget: number) => {
    setGoals((prev) =>
      prev.map((g) => (g.id === id ? { ...g, targetAmount: Math.max(g.currentAmount, newTarget) } : g))
    );
  };

  return (
    <div
      ref={containerRef}
      className={cn(
        "rounded-card border border-black/[0.08] bg-white p-6 sm:p-8 shadow-sm flex flex-col gap-6",
        className
      )}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-black/[0.04]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              Wealth Horizons
            </span>
            <span className="text-xs text-pewter font-medium">• Automated Goal Tracking</span>
          </div>
          <h3 className="font-display text-2xl sm:text-3xl font-medium text-ink mt-1.5 tracking-tight">
            {title}
          </h3>
          <p className="text-xs sm:text-sm text-graphite mt-1 max-w-2xl leading-relaxed">
            {subtitle}
          </p>
        </div>

        {/* Edit Mode Toggle Button */}
        <button
          type="button"
          onClick={() => setIsEditing(!isEditing)}
          className={cn(
            "self-start sm:self-auto inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-semibold cursor-pointer transition-all active:scale-[0.98]",
            isEditing
              ? "bg-lime text-ink border-lime-dark shadow-sm"
              : "bg-fog text-graphite border-black/[0.08] hover:bg-white hover:text-ink"
          )}
        >
          {isEditing ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Sliders className="h-3.5 w-3.5" />}
          <span>{isEditing ? "Finish Editing" : "Tune Targets"}</span>
        </button>
      </div>

      {/* Goal Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {goals.map((goal, index) => {
          const progressPct = Math.min(100, Math.round((goal.currentAmount / goal.targetAmount) * 100));

          return (
            <motion.div
              key={goal.id}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 1.01 }}
              transition={{ duration: 0.2 }}
              className="p-5 sm:p-6 rounded-card border border-black/[0.08] bg-white shadow-[0_2px_12px_rgba(15,23,42,0.03)] hover:shadow-[0_8px_24px_rgba(15,23,42,0.07)] hover:border-black/[0.14] transition-all flex flex-col justify-between gap-5 relative group"
            >
              {/* Card Top Row: Thumbnail + Title + Current vs Target */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3.5">
                  {/* Thumbnail Art Icon */}
                  <div
                    className="flex h-12 w-12 items-center justify-center rounded-2xl border text-white shadow-sm shrink-0"
                    style={{ backgroundColor: goal.accentColor, borderColor: "rgba(0,0,0,0.06)" }}
                  >
                    {goal.icon === "shield" && <ShieldCheck className="h-6 w-6" />}
                    {goal.icon === "debt" && <Zap className="h-6 w-6" />}
                    {goal.icon === "vacation" && <Plane className="h-6 w-6" />}
                    {goal.icon === "home" && <Home className="h-6 w-6" />}
                  </div>

                  <div>
                    <h4 className="text-base font-semibold text-ink leading-snug">
                      {goal.title}
                    </h4>
                    <p className="text-xs text-pewter mt-0.5">
                      Target: {goal.targetDate} &middot;{" "}
                      <span className="text-graphite font-medium">{goal.category}</span>
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="font-display text-lg sm:text-xl font-bold text-ink block tnum leading-tight">
                    {formatCurrency(goal.currentAmount)}
                  </span>
                  <span className="text-[11px] text-pewter font-medium tnum">
                    of {formatCurrency(goal.targetAmount)} target
                  </span>
                </div>
              </div>

              {/* Progress Bar Container with Milestones */}
              <div className="flex flex-col gap-2">
                <div className="relative w-full h-3 rounded-full bg-fog overflow-hidden">
                  {/* Milestone Tick Marks (25%, 50%, 75%) */}
                  <div className="absolute inset-0 flex justify-between pointer-events-none px-0.5 z-10">
                    <span className="h-full w-0.5 bg-black/[0.08]" style={{ left: "25%", position: "absolute" }} />
                    <span className="h-full w-0.5 bg-black/[0.08]" style={{ left: "50%", position: "absolute" }} />
                    <span className="h-full w-0.5 bg-black/[0.08]" style={{ left: "75%", position: "absolute" }} />
                  </div>

                  {/* Animated Progress Fill with Shimmer Pulse */}
                  <motion.div
                    initial={{ width: 0 }}
                    animate={isInView ? { width: `${progressPct}%` } : { width: 0 }}
                    transition={shouldReduceMotion ? { duration: 0.1 } : { duration: 1.1, delay: 0.15 * index, ease: "easeOut" }}
                    className="h-full rounded-full relative overflow-hidden"
                    style={{ backgroundColor: goal.accentColor }}
                  >
                    {/* Subtle entrance shimmer sweep */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent w-full animate-pulse" />
                  </motion.div>
                </div>

                {/* Milestone Labels Row */}
                <div className="flex justify-between items-center text-[10px] text-pewter font-medium px-0.5">
                  <span>0%</span>
                  <span className="hidden sm:inline">25%</span>
                  <span className="font-semibold text-graphite">50% Midpoint</span>
                  <span className="hidden sm:inline">75%</span>
                  <span className="font-bold text-ink">{progressPct}% Complete</span>
                </div>
              </div>

              {/* Edit Mode Interactive Slider */}
              {isEditing && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="pt-2 border-t border-black/[0.06] flex flex-col gap-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-pewter">Adjust Target:</span>
                    <span className="font-semibold text-ink tnum">
                      {formatCurrency(goal.targetAmount)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={goal.currentAmount}
                    max={goal.targetAmount * 2}
                    step={10000}
                    value={goal.targetAmount}
                    onChange={(e) => handleTargetChange(goal.id, Number(e.target.value))}
                    className="w-full accent-ember cursor-pointer h-1.5 bg-mist rounded-lg"
                  />
                </motion.div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Footer Notes */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-black/[0.04] text-xs text-pewter">
        <span>Milestone checkpoints at 25%, 50%, 75% and 100%</span>
        <span className="text-emerald-700 font-medium">Automatic monthly SIP contributions linked</span>
      </div>
    </div>
  );
}
