"use client";

import { useCallback, useMemo } from "react";
import { ArrowDownToLine, ArrowUpFromLine, Equal } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync, useUserId } from "@/lib/hooks";
import { summarizeSpend } from "@/lib/spend";
import type { Transaction } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { WeeklyCompare } from "@/components/transactions/WeeklyCompare";
import { BigAmount } from "@/components/dashboard/BigAmount";

const GRADIENTS = [
  "radial-gradient(circle at 80% 30%, #ffc9e6 0, transparent 45%), radial-gradient(circle at 60% 70%, #c9b8ff 0, transparent 50%), linear-gradient(135deg, #d8f1ff, #e8eaff)",
  "radial-gradient(circle at 85% 25%, #ffd2a8 0, transparent 45%), radial-gradient(circle at 55% 75%, #a8f0d6 0, transparent 50%), linear-gradient(135deg, #d6f7ff, #e6ffe9)",
  "radial-gradient(circle at 85% 30%, #ffc8a0 0, transparent 45%), radial-gradient(circle at 55% 70%, #e2b8ff 0, transparent 50%), linear-gradient(135deg, #ffe0ee, #ece2ff)",
];

function Bar({ parts }: { parts: { pct: number; color: string }[] }) {
  return (
    <div className="flex h-9 gap-1" aria-hidden>
      {parts.map((p, i) => (
        <i key={i} className="rounded-md" style={{ width: `${Math.max(p.pct, 2)}%`, background: p.color }} />
      ))}
    </div>
  );
}

function BreakdownCard({ title, total, parts, line, name, pct, accent }: { title: string; total: number; parts: { pct: number; color: string }[]; line: string; name: string; pct: number; accent: string }) {
  return (
    <div className="grid gap-3 rounded-card bg-white p-5 shadow-sm">
      <p className="text-sm text-graphite">{title}</p>
      <BigAmount value={total} className="text-3xl" />
      <Bar parts={parts} />
      <p className="text-xs text-graphite">
        {line} <b style={{ color: accent }}>{name}</b>
        <span className="ml-2 font-semibold tnum text-ink">{pct.toFixed(1)}%</span>
      </p>
    </div>
  );
}

/** This month at a glance: three gradient totals plus a "who it came from / where it went" bar for money in and money out. */
export function TxnSummary() {
  const userId = useUserId();
  const fetchAll = useCallback(async () => {
    const all: Transaction[] = [];
    for (let page = 1; page <= 5; page++) {
      const res = await api.transactions(userId, { page, page_size: 200 });
      all.push(...res.items);
      if (all.length >= res.total) break;
    }
    return all;
  }, [userId]);
  const { data } = useAsync(fetchAll, [userId]);
  const txns = useMemo(() => data ?? [], [data]);
  const spend = useMemo(() => summarizeSpend(txns), [txns]);
  const latest = spend.months.at(-1);
  const income = latest?.income ?? 0;
  const out = latest?.spend ?? 0;

  const topIncome = useMemo(() => {
    const m = new Map<string, number>();
    for (const t of txns) if (t.category === "income" && t.amount > 0 && latest && t.date.startsWith(latest.month)) m.set(t.merchant, (m.get(t.merchant) ?? 0) + t.amount);
    return [...m].sort((a, b) => b[1] - a[1])[0];
  }, [txns, latest]);
  const topCat = [...spend.categories].filter((c) => c.total > 0).sort((a, b) => b.total - a.total)[0];

  const inPct = topIncome && income > 0 ? (topIncome[1] / income) * 100 : 0;
  const outPct = topCat && out > 0 ? (topCat.total / out) * 100 : 0;
  const cards = [
    { icon: Equal, label: "Money left this month", value: income - out },
    { icon: ArrowDownToLine, label: "Money in this month", value: income },
    { icon: ArrowUpFromLine, label: "Money out this month", value: -out },
  ];

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 md:grid-cols-3">
        {cards.map((c, i) => (
          <div key={c.label} className="flex h-36 flex-col justify-between rounded-card p-5 shadow-sm" style={{ background: GRADIENTS[i] }}>
            <span className="flex size-8 items-center justify-center rounded-lg bg-white/80 text-ink">
              <c.icon className="size-4" />
            </span>
            <div>
              <p className="font-display text-2xl font-semibold tnum text-ink">
                {c.value > 0 && i > 0 ? "+" : ""}
                {c.value < 0 ? "-" : ""}
                {formatCurrency(Math.abs(c.value))}
              </p>
              <p className="text-xs text-graphite">{c.label}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <BreakdownCard
          title="Money in"
          total={income}
          parts={[{ pct: inPct, color: "#3f7d5c" }, { pct: Math.min(8, 100 - inPct), color: "#a6d11a" }, { pct: Math.max(0, 92 - inPct), color: "#eceee4" }]}
          line="Most of it came from"
          name={topIncome?.[0] ?? "no income yet"}
          pct={inPct}
          accent="#3f7d5c"
        />
        <BreakdownCard
          title="Money out"
          total={out}
          parts={[{ pct: outPct, color: "#e5484d" }, { pct: Math.min(12, 100 - outPct), color: "#e0540a" }, { pct: Math.max(0, 88 - outPct), color: "#eceee4" }]}
          line="Most of it went to"
          name={topCat?.label ?? "nothing yet"}
          pct={outPct}
          accent="#e0540a"
        />
      </div>
      <WeeklyCompare txns={txns} />
    </div>
  );
}
