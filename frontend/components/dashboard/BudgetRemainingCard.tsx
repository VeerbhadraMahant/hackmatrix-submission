"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { CATEGORY_META, type SpendSummary } from "@/lib/spend";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";

const BAR_TONES = ["bg-[#3f7d5c] text-white", "bg-lime text-ink", "bg-[#4fe0b0] text-ink"];

/** "Remaining monthly": share of the monthly budgets still unspent, with the three biggest budgets as bars. */
export function BudgetRemainingCard({ userId, spend }: { userId: string; spend: SpendSummary }) {
  const { data: budgets } = useAsync(() => api.budgets(userId), [userId]);
  const rows = (budgets ?? [])
    .map((b) => {
      const used = spend.categories.find((c) => c.category === b.category)?.total ?? 0;
      return { b, used, pct: b.monthly_limit > 0 ? used / b.monthly_limit : 0 };
    })
    .sort((a, b) => b.b.monthly_limit - a.b.monthly_limit)
    .slice(0, 3);
  const limit = rows.reduce((s, r) => s + r.b.monthly_limit, 0);
  const used = rows.reduce((s, r) => s + r.used, 0);
  const remaining = limit > 0 ? Math.max(0, Math.round((1 - used / limit) * 100)) : null;
  const message =
    remaining === null
      ? "Set monthly budgets to see how much room you have left."
      : remaining >= 40
        ? "You are in great shape. Your monthly usage is still very safe."
        : remaining >= 15
          ? "Keep an eye on it. Some budgets are getting tight."
          : "You are close to your limits this month.";

  return (
    <div className="flex h-full flex-col gap-4 rounded-card bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between text-sm font-medium text-ink">
        <span>Remaining Monthly</span>
        <Link href="/budgets" className="inline-flex items-center gap-1 hover:underline">
          Budget setting <ArrowUpRight className="size-4" />
        </Link>
      </div>
      <div className="flex items-end justify-between gap-4">
        <p className="font-display text-6xl font-semibold tnum text-ink">
          {remaining ?? "--"}
          <span className="text-3xl text-ink/45">%</span>
        </p>
        <p className="max-w-[11rem] text-right text-xs text-graphite">{message}</p>
      </div>
      {rows.length > 0 && (
        <div className="mt-auto grid grid-cols-3 items-end gap-2">
          {rows.map((r, i) => (
            <div
              key={r.b.id}
              className={cn("flex flex-col justify-between rounded-2xl p-3", BAR_TONES[i])}
              style={{ height: `${Math.max(96, Math.min(180, 60 + r.pct * 110))}px` }}
              title={`${formatCurrency(r.used)} of ${formatCurrency(r.b.monthly_limit)}`}
            >
              <span className="font-display text-2xl font-semibold tnum">{Math.round(r.pct * 100)}%</span>
              <span className="text-xs opacity-80">{CATEGORY_META[r.b.category].label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
