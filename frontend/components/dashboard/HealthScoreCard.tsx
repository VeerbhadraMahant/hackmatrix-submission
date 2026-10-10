"use client";

import { motion } from "framer-motion";
import type { HealthScore } from "@/lib/types";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { cn } from "@/lib/utils";

function getScoreTier(score: number): { label: string; color: string; bg: string; border: string } {
  if (score >= 75) {
    return {
      label: "Optimal Health",
      color: "text-emerald-700",
      bg: "bg-emerald-50",
      border: "border-emerald-200",
    };
  }
  if (score >= 55) {
    return {
      label: "Moderate Stability",
      color: "text-amber-700",
      bg: "bg-amber-50",
      border: "border-amber-200",
    };
  }
  return {
    label: "Attention Required",
    color: "text-rose-700",
    bg: "bg-rose-50",
    border: "border-rose-200",
  };
}

export function HealthScoreCard({ score }: { score: HealthScore }) {
  const rounded = Math.round(score.overall);
  const tier = getScoreTier(rounded);
  const trend = score.trend_30d;
  const trendUp = trend !== null && trend > 0;
  const trendDown = trend !== null && trend < 0;

  // Arc calculation for SVG circular meter
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  // Use a 270 degree arc for a gauge look
  const strokeDashoffset = circumference - (rounded / 100) * circumference * 0.75;

  return (
    <Card className="relative overflow-hidden">
      {/* Background ambient corner glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-ember-soft/30 rounded-full blur-3xl pointer-events-none -z-10" />

      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle>Financial Health Index</CardTitle>
          <span
            className={cn(
              "px-2.5 py-0.5 rounded-full text-xs font-semibold border whitespace-nowrap",
              tier.bg,
              tier.color,
              tier.border
            )}
          >
            {tier.label}
          </span>
        </div>
        <span className="text-xs text-pewter">Weighted 5-Pillar Model</span>
      </CardHeader>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-8 items-center pt-1 pb-2">
        {/* Left Column: Radial Gauge + Trend */}
        <div className="lg:col-span-4 flex flex-col items-center justify-center p-4 rounded-3xl bg-sage text-ink">
          <div className="relative flex items-center justify-center w-36 h-36 lg:w-40 lg:h-40">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 140 140">
              {/* Background circle */}
              <circle
                cx="70"
                cy="70"
                r={radius}
                className="stroke-white/70"
                strokeWidth="10"
                fill="transparent"
                strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
                strokeLinecap="round"
              />
              {/* Animated Progress arc */}
              <motion.circle
                cx="70"
                cy="70"
                r={radius}
                className={cn(
                  rounded >= 75
                    ? "stroke-[#5f7f0c]"
                    : rounded >= 55
                    ? "stroke-amber-400"
                    : "stroke-ember"
                )}
                strokeWidth="10"
                fill="transparent"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset }}
                transition={{ duration: 1.2, ease: "easeOut" }}
                strokeLinecap="round"
              />
            </svg>

            {/* Score inside circular gauge */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="font-display text-5xl font-semibold text-ink leading-none tnum">
                {rounded}
              </span>
              <span className="text-xs font-medium text-ink/60 mt-1">out of 100</span>
            </div>
          </div>

          {/* 30-Day Trend Badge */}
          {trend !== null && (
            <div
              className={cn(
                "mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border",
                trendUp
                  ? "bg-lime/40 text-ink border-lime-dark/50"
                  : trendDown
                  ? "bg-rose-500/15 text-rose-300 border-rose-400/30"
                  : "bg-white/55 text-ink/70 border-ink/10"
              )}
            >
              <span>{trendUp ? "↑" : trendDown ? "↓" : "→"}</span>
              <span>
                {Math.abs(trend).toFixed(1)} pts {trendUp ? "gain" : trendDown ? "drop" : ""} over 30d
              </span>
            </div>
          )}
        </div>

        {/* Right Column: 5 Sub-Score Breakdown Bars */}
        <div className="lg:col-span-8 flex flex-col gap-2.5">
          <div className="flex items-center justify-between text-xs text-pewter font-medium px-1">
            <span>Health Sub-Category</span>
            <span>Weight & Score</span>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-2">
            {score.sub_scores.map((sub, i) => {
              const subRounded = Math.round(sub.score);
              const isStrong = subRounded >= 70;
              const isModerate = subRounded >= 50 && subRounded < 70;

              return (
                <div
                  key={i}
                  className="flex flex-col gap-1 px-3 py-2 rounded-chip border border-black/[0.04] bg-white hover:bg-fog/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-ink">{sub.name}</span>
                      <span className="text-[10px] text-pewter font-medium bg-fog px-1.5 py-0.5 rounded border border-black/[0.04]">
                        Weight: {Math.round(sub.weight * 100)}%
                      </span>
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-sm font-bold text-ink tnum">{subRounded}</span>
                      <span className="text-[11px] text-pewter">/100</span>
                    </div>
                  </div>

                  {/* Visual Progress Bar */}
                  <div className="w-full bg-fog rounded-full h-2 overflow-hidden">
                    <motion.div
                      className={cn(
                        "h-full rounded-full",
                        isStrong
                          ? "bg-emerald-500"
                          : isModerate
                          ? "bg-amber-500"
                          : "bg-ember"
                      )}
                      initial={{ width: 0 }}
                      animate={{ width: `${subRounded}%` }}
                      transition={{ duration: 0.8, delay: 0.1 * i, ease: "easeOut" }}
                    />
                  </div>

                  {sub.detail && (
                    <span className="text-[11px] text-graphite line-clamp-1 mt-0.5">
                      {sub.detail}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Card>
  );
}
