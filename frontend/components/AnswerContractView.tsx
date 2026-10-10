import type { ReactNode } from "react";
import Link from "next/link";
import type { AnswerContract } from "@/lib/types";
import { ConfidenceChip } from "@/components/ui/ConfidenceChip";
import { Chip } from "@/components/ui/Chip";
import { formatCurrency, formatImpactValue } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Renders an AnswerContract as three visually distinct, clearly labeled
 * lanes -- Observed / Predicted / Recommended. Shared by the dashboard
 * insights panel and the copilot chat so the "facts vs predictions vs
 * recommendations, always labeled" behavior is identical everywhere.
 * Never blend lanes into a single paragraph.
 */
export function AnswerContractView({ answer }: { answer: AnswerContract }) {
  const { facts, predictions, recommendations, data_gaps, narrative } = answer;
  const isEmpty =
    facts.length === 0 && predictions.length === 0 && recommendations.length === 0 && !narrative;

  if (isEmpty) {
    return <p className="text-sm text-pewter">No insights available yet.</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      {narrative && (
        <div className="rounded-surface border border-black/[0.06] bg-fog/60 p-4 text-sm leading-relaxed text-graphite">
          {narrative}
        </div>
      )}

      {/* Lane 1: Observed Facts */}
      {facts.length > 0 && (
        <Lane
          title="Observed Facts"
          hint="Grounded in your actual transactions"
          badgeColor="bg-leaf"
          icon="✓"
        >
          <div className="rounded-surface border border-black/[0.08] bg-white p-4 shadow-sm">
            <ul className="flex flex-col divide-y divide-black/[0.04]">
              {facts.map((f, i) => {
                const textAlreadyHasValue = /[₹%]|\d+\s*\/\s*\d+/.test(f.text);
                return (
                  <li key={i} className="flex items-start justify-between gap-3 py-2.5 first:pt-0 last:pb-0 text-sm text-ink">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs text-pewter">•</span>
                      <span>{f.text}</span>
                    </div>
                    {f.value !== null && !textAlreadyHasValue ? (
                      <span className="font-semibold text-ink tnum shrink-0">
                        {formatCurrency(f.value)}
                      </span>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </div>
        </Lane>
      )}

      {/* Lane 2: Predicted Modeling */}
      {predictions.length > 0 && (
        <Lane
          title="Model Predictions"
          hint="Forward-looking cash flow and volatility estimates"
          badgeColor="bg-indigo-600"
          icon="↗"
        >
          <div className="rounded-surface border border-indigo-100 bg-indigo-50/20 p-4 shadow-sm">
            <ul className="flex flex-col gap-3">
              {predictions.map((p, i) => (
                <li key={i} className="flex flex-col gap-1.5 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-ink">{p.text}</span>
                    <ConfidenceChip value={p.confidence} />
                  </div>
                  {(p.range_low !== null || p.range_high !== null) && (
                    <div className="inline-flex items-center gap-1.5 text-xs text-graphite">
                      <span className="text-pewter">Confidence interval:</span>
                      <span className="tnum font-medium text-ink bg-white px-2 py-0.5 rounded border border-black/[0.06]">
                        {p.range_low !== null ? formatCurrency(p.range_low) : "?"} &ndash;{" "}
                        {p.range_high !== null ? formatCurrency(p.range_high) : "?"}
                      </span>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </Lane>
      )}

      {/* Lane 3: Recommended Actions */}
      {recommendations.length > 0 && (
        <Lane
          title="Recommended Actions"
          hint="Simulated impact on your net worth and health score"
          badgeColor="bg-ember"
          icon="✦"
        >
          <div className="flex flex-col gap-3.5">
            {recommendations.map((r, i) => (
              <div
                key={i}
                className="rounded-surface border border-ember/25 bg-gradient-to-b from-white to-orange-50/25 p-4 shadow-[0_2px_12px_rgba(255,89,0,0.04)]"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-sm font-bold text-ink flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-ember shrink-0" />
                    <span>{r.text}</span>
                  </p>
                  <ConfidenceChip value={r.confidence} />
                </div>

                <p className="mt-1 text-xs text-graphite pl-3.5">{r.rationale}</p>

                {/* Before vs After Impact Visual Pill */}
                <div className="mt-3.5 flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-black/[0.06] text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-pewter">{r.impact.metric}:</span>
                    <span className="text-graphite line-through tnum">
                      {formatImpactValue(r.impact.metric, r.impact.before)}
                    </span>
                    <span className="text-pewter">→</span>
                    <span className="font-bold text-ink tnum">
                      {formatImpactValue(r.impact.metric, r.impact.after)}
                    </span>
                    <span
                      className={cn(
                        "font-bold tnum px-1.5 py-0.5 rounded",
                        r.impact.delta >= 0
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-rose-50 text-rose-700"
                      )}
                    >
                      ({r.impact.delta >= 0 ? "+" : ""}
                      {formatImpactValue(r.impact.metric, r.impact.delta)})
                    </span>
                  </div>

                  <div className="flex items-center gap-2 ml-auto">
                    <Chip tone="outline" className="text-[10px]">
                      Horizon: {r.impact.horizon}
                    </Chip>
                    <Link
                      href="/simulate"
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-ember hover:underline"
                    >
                      Simulate Decision →
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Lane>
      )}

      {/* Data Gaps Section */}
      {data_gaps.length > 0 && (
        <div className="rounded-surface border border-dashed border-black/[0.12] bg-fog/70 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-pewter flex items-center gap-1.5">
            <span>ℹ</span>
            <span>Identified Data Gaps & Model Caveats</span>
          </p>
          <ul className="mt-2.5 flex flex-col gap-1.5">
            {data_gaps.map((g, i) => (
              <li key={i} className="text-xs text-graphite">
                <span className="font-medium text-ink">{g.text}</span>
                <span className="text-pewter"> — {g.what_would_help}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Lane({
  title,
  hint,
  badgeColor,
  icon,
  children,
}: {
  title: string;
  hint: string;
  badgeColor: string;
  icon: string;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-2">
      <header className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "flex h-4 w-4 items-center justify-center rounded-full text-[10px] text-white font-bold",
              badgeColor
            )}
            aria-hidden
          >
            {icon}
          </span>
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink">{title}</h4>
        </div>
        <span className="text-[11px] text-pewter">{hint}</span>
      </header>
      {children}
    </section>
  );
}
