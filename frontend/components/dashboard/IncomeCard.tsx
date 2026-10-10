import { TrendingDown, TrendingUp, Zap } from "lucide-react";
import type { Transaction } from "@/lib/types";
import type { MonthTotals } from "@/lib/spend";
import { formatCurrency } from "@/lib/format";
import { BigAmount } from "@/components/dashboard/BigAmount";

const SOURCE_COLORS = ["border-[#3f7d5c]", "border-lime-dark", "border-[#4fe0b0]"];
const ROWS = 5;

/** "My Income": latest month total, a squares sparkline of recent months, and the top income sources. */
export function IncomeCard({ months, txns }: { months: MonthTotals[]; txns: Transaction[] }) {
  const latest = months.at(-1);
  const prev = months.at(-2);
  const total = latest?.income ?? 0;
  const delta = prev ? total - prev.income : 0;
  const pct = prev && prev.income > 0 ? (delta / prev.income) * 100 : null;
  const max = Math.max(1, ...months.map((m) => m.income));

  const bySource = new Map<string, number>();
  for (const t of txns) {
    if (t.category === "income" && t.amount > 0 && latest && t.date.startsWith(latest.month))
      bySource.set(t.merchant, (bySource.get(t.merchant) ?? 0) + t.amount);
  }
  const sources = [...bySource].sort((a, b) => b[1] - a[1]).slice(0, 3);
  const tone = delta >= 0 ? "text-leaf" : "text-rose-600";

  return (
    <div className="flex h-full flex-col justify-between gap-4 rounded-card bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between text-sm font-medium text-ink">
        <span>My Income</span>
        <span className="text-graphite">
          {latest ? new Date(`${latest.month}-01`).toLocaleDateString("en", { month: "long", year: "numeric" }) : "No data"}
        </span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-sm text-graphite">Money you earned this month</p>
          <BigAmount value={total} className="mt-1 block text-3xl" />
        </div>
        <div className="flex items-end gap-1" aria-hidden>
          {months.map((m) => {
            const filled = Math.max(1, Math.round((m.income / max) * ROWS));
            return (
              <div key={m.month} className="flex flex-col-reverse gap-0.5">
                {Array.from({ length: ROWS }, (_, r) => (
                  <i key={r} className={`size-2.5 rounded-[3px] ${r < filled ? "bg-lime-dark" : "bg-fog"}`} />
                ))}
              </div>
            );
          })}
        </div>
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-graphite">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-fog px-3 py-2">
          {delta >= 0 ? <TrendingUp className="size-4 text-ink" /> : <TrendingDown className="size-4 text-ink" />}
          Last month <span className="font-semibold tnum text-ink">{prev ? formatCurrency(prev.income) : "--"}</span>
          This month <span className="font-semibold tnum text-ink">{formatCurrency(total)}</span>
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-fog px-3 py-2">
          <Zap className="size-4 text-ink" />
          {delta >= 0 ? "Up by" : "Down by"}
          <span className={`font-semibold tnum ${tone}`}>
            {formatCurrency(Math.abs(delta))}{pct !== null && ` (${Math.abs(pct).toFixed(1)}%)`}
          </span>
        </span>
      </div>
      {sources.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {sources.map(([name, amt], i) => (
            <div key={name} className={`min-w-0 border-l-2 pl-3 ${SOURCE_COLORS[i]}`}>
              <p className="truncate text-xs text-graphite">{name}</p>
              <p className="text-sm font-semibold tnum text-ink">{formatCurrency(amt)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
