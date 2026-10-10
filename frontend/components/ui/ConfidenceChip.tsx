import { cn } from "@/lib/utils";

/**
 * Renders a 0-1 confidence as a small chip. Visual weight scales with
 * confidence: high confidence reads as a solid, filled chip; low confidence
 * reads as tentative (dashed border, lighter text).
 */
export function ConfidenceChip({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(value <= 1 ? value * 100 : value);
  const normalized = value <= 1 ? value : value / 100;
  const tier = normalized >= 0.75 ? "high" : normalized >= 0.45 ? "medium" : "low";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-chip px-2 py-0.5 text-[11px] font-semibold tracking-tight",
        tier === "high" && "border border-emerald-200 bg-emerald-50/80 text-emerald-800",
        tier === "medium" && "border border-black/[0.08] bg-fog text-graphite",
        tier === "low" && "border border-dashed border-black/[0.15] bg-white text-pewter",
        className
      )}
      title={`Confidence: ${pct}%`}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          tier === "high" ? "bg-emerald-500" : tier === "medium" ? "bg-amber-500" : "bg-steel"
        )}
      />
      <span className="tnum">{pct}% confidence</span>
    </span>
  );
}
