import { cn } from "@/lib/utils";

export function StatTile({
  label,
  value,
  sub,
  trend,
  className,
}: {
  label: string;
  value: string;
  sub?: string;
  trend?: { direction: "up" | "down" | "neutral"; text: string; positive?: boolean };
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col justify-between gap-2", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-pewter">
          {label}
        </span>
        {trend && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
              trend.positive
                ? "bg-emerald-50 text-emerald-700"
                : "bg-rose-50 text-rose-700"
            )}
          >
            {trend.direction === "up" ? "↑" : trend.direction === "down" ? "↓" : "→"}{" "}
            {trend.text}
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-1 mt-0.5">
        <span className="font-display text-2xl sm:text-3xl text-ink leading-tight tnum font-semibold">
          {value}
        </span>
      </div>

      {sub && <span className="text-xs text-graphite font-normal mt-0.5">{sub}</span>}
    </div>
  );
}
