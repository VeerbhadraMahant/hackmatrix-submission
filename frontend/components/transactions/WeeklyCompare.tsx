"use client";

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { Transaction } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const NON_SPEND = new Set(["transfer", "credit_card_payment", "income"]);

function mondayOf(d: Date): Date {
  const m = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  m.setDate(m.getDate() - ((m.getDay() + 6) % 7));
  return m;
}

const key = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** Spending day by day: this week against the week before. Days that haven't happened yet are left blank. */
export function WeeklyCompare({ txns }: { txns: Transaction[] }) {
  const { rows, thisTotal, lastTotal } = useMemo(() => {
    const spendByDay = new Map<string, number>();
    for (const t of txns) if (t.amount < 0 && !NON_SPEND.has(t.category)) spendByDay.set(t.date.slice(0, 10), (spendByDay.get(t.date.slice(0, 10)) ?? 0) - t.amount);
    const today = new Date();
    const start = mondayOf(today);
    let a = 0;
    let b = 0;
    const rows = DAYS.map((day, i) => {
      const cur = new Date(start);
      cur.setDate(start.getDate() + i);
      const prev = new Date(cur);
      prev.setDate(cur.getDate() - 7);
      const future = cur > today;
      const thisWeek = future ? null : Math.round(spendByDay.get(key(cur)) ?? 0);
      const lastWeek = Math.round(spendByDay.get(key(prev)) ?? 0);
      if (thisWeek !== null) a += thisWeek;
      b += lastWeek;
      return { day, thisWeek, lastWeek };
    });
    return { rows, thisTotal: a, lastTotal: b };
  }, [txns]);
  const up = thisTotal > lastTotal;

  return (
    <div className="rounded-card bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-graphite">Spent this week</p>
          <p className="font-display text-3xl font-semibold tnum text-ink">{formatCurrency(thisTotal)}</p>
        </div>
        <div className="flex flex-wrap gap-4 text-xs text-graphite">
          <span className="inline-flex items-center gap-1.5">
            <i className="size-2.5 rounded-full bg-[#3f7d5c]" /> This week {formatCurrency(thisTotal)}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <i className="size-2.5 rounded-full bg-[#4fb0e0]" /> Last week {formatCurrency(lastTotal)}
          </span>
          <span className={`inline-flex items-center gap-1 font-semibold ${up ? "text-rose-600" : "text-leaf"}`}>
            {up ? <ArrowUpRight className="size-4" /> : <ArrowDownRight className="size-4" />}
            {up ? "You spent" : "You saved"} {formatCurrency(Math.abs(thisTotal - lastTotal))} {up ? "more" : "less"}
          </span>
        </div>
      </div>
      <div className="mt-4 h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <defs>
              <linearGradient id="wkThis" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3f7d5c" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#3f7d5c" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="#eceee4" />
            <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#7b8070" }} />
            <YAxis tickLine={false} axisLine={false} width={48} tick={{ fontSize: 11, fill: "#7b8070" }} tickFormatter={(v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : String(v))} />
            <Tooltip formatter={(v, n) => [formatCurrency(Number(v)), n === "thisWeek" ? "This week" : "Last week"]} />
            <Area type="monotone" dataKey="lastWeek" stroke="#4fb0e0" strokeWidth={2.5} fill="none" dot={false} isAnimationActive={false} />
            <Area type="monotone" dataKey="thisWeek" stroke="#3f7d5c" strokeWidth={2.5} fill="url(#wkThis)" dot={false} connectNulls={false} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
