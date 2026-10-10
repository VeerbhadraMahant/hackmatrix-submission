"use client";

import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/shadcn/card";
import { MerchantLogo } from "@/components/dashboard/MerchantLogo";
import { formatCurrency } from "@/lib/format";
import type { SpendSummary } from "@/lib/spend";

const TOOLTIP_STYLE = {
  borderRadius: 14,
  border: "1.5px solid var(--color-mist)",
  background: "var(--color-surface-card)",
  fontSize: 12,
  boxShadow: "0 8px 0 rgba(20,33,61,0.05)",
};

const compact = (v: number) =>
  v >= 100000 ? `₹${(v / 100000).toFixed(1)}L` : v >= 1000 ? `₹${Math.round(v / 1000)}k` : `₹${v}`;

function Empty({ children }: { children: string }) {
  return <p className="py-10 text-center text-sm text-pewter">{children}</p>;
}

export function CategoryDonut({ summary }: { summary: SpendSummary }) {
  const top = summary.categories.filter((c) => c.total > 0).slice(0, 7);
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="font-display text-lg">Where your money went</CardTitle>
        <CardDescription>Spending by category this month</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-center">
        {top.length === 0 ? (
          <Empty>No spending recorded this month.</Empty>
        ) : (
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-8">
            <div className="relative h-56 w-56 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={top} dataKey="total" nameKey="label" innerRadius={66} outerRadius={104} paddingAngle={3} cornerRadius={6} stroke="none" isAnimationActive={false}>
                    {top.map((c) => (
                      <Cell key={c.category} fill={c.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-pewter">Spent</span>
                <span className="font-display text-base font-bold tnum text-ink">{formatCurrency(summary.totalSpend)}</span>
              </div>
            </div>
            <ul className="grid w-full min-w-0 flex-1 gap-2">
              {top.map((c) => (
                <li key={c.category} className="flex items-center gap-2.5 text-sm">
                  <span className="size-3 shrink-0 rounded-full" style={{ background: c.color }} />
                  <span className="flex-1 truncate text-graphite">{c.label}</span>
                  <span className="font-semibold tnum text-ink">{formatCurrency(c.total)}</span>
                  <span className="w-10 text-right text-xs tnum text-pewter">
                    {Math.round((c.total / summary.totalSpend) * 100)}%
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function IncomeVsSpend({ summary }: { summary: SpendSummary }) {
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="font-display text-lg">Money in vs. money out</CardTitle>
        <CardDescription>Last {summary.months.length} months</CardDescription>
      </CardHeader>
      <CardContent>
        {summary.months.length === 0 ? (
          <Empty>Not enough history yet.</Empty>
        ) : (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary.months} barGap={4} margin={{ left: -8, right: 4, top: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--color-mist)" strokeDasharray="4 4" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "var(--color-pewter)" }} />
                <YAxis tickLine={false} axisLine={false} tickFormatter={compact} tick={{ fontSize: 11, fill: "var(--color-pewter)" }} width={52} />
                <Tooltip
                  cursor={{ fill: "rgba(20,33,61,0.05)" }}
                  formatter={(v, name) => [formatCurrency(Number(v)), name === "income" ? "Income" : "Spent"]}
                  contentStyle={TOOLTIP_STYLE}
                />
                <Bar dataKey="income" fill="#12a56b" radius={[8, 8, 0, 0]} maxBarSize={22} />
                <Bar dataKey="spend" fill="#ff7a2f" radius={[8, 8, 0, 0]} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        <div className="mt-2 flex gap-4 text-xs text-graphite">
          <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-full bg-leaf" /> Income</span>
          <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-full bg-ember" /> Spent</span>
        </div>
      </CardContent>
    </Card>
  );
}

export function TopMerchants({ summary }: { summary: SpendSummary }) {
  const max = summary.merchants[0]?.total ?? 1;
  const colors = ["#ff7a2f", "#2f7cf6", "#12a56b", "#ffc24b", "#8b5cf6", "#f0647e"];
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="font-display text-lg">Top merchants</CardTitle>
        <CardDescription>Biggest spend this month</CardDescription>
      </CardHeader>
      <CardContent>
        {summary.merchants.length === 0 ? (
          <Empty>No merchants yet.</Empty>
        ) : (
          <ul className="grid gap-3.5">
            {summary.merchants.map((m, i) => (
              <li key={m.merchant}>
                <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
                  <span className="flex min-w-0 items-center gap-2">
                    <MerchantLogo merchant={m.merchant} color={colors[i % colors.length]} className="size-6 rounded-md" />
                    <span className="truncate font-medium text-ink">{m.merchant}</span>
                  </span>
                  <span className="shrink-0 font-semibold tnum text-ink">{formatCurrency(m.total)}</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-fog">
                  <div className="h-full rounded-full" style={{ width: `${(m.total / max) * 100}%`, background: colors[i % colors.length] }} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function SpendingShifts({ summary }: { summary: SpendSummary }) {
  const shifts = summary.categories
    .filter((c) => c.change !== null && Math.abs(c.change) >= 10 && Math.max(c.total, c.prev) > 0)
    .sort((a, b) => Math.abs(b.total - b.prev) - Math.abs(a.total - a.prev))
    .slice(0, 4);
  return (
    <Card className="min-w-0 bg-tint-sun">
      <CardHeader>
        <CardTitle className="font-display text-lg">Spending: last month and this month</CardTitle>
        <CardDescription>The biggest changes</CardDescription>
      </CardHeader>
      <CardContent>
        {shifts.length === 0 ? (
          <Empty>Your spending is steady — no big shifts.</Empty>
        ) : (
          <ul className="grid gap-2.5">
            {shifts.map((c) => {
              const up = (c.change ?? 0) > 0;
              const Icon = up ? ArrowUpRight : ArrowDownRight;
              return (
                <li key={c.category} className="flex items-center gap-3 rounded-2xl bg-surface-card/80 p-3">
                  <span
                    className="flex size-9 shrink-0 items-center justify-center rounded-xl text-white"
                    style={{ background: up ? "#e5484d" : "#12a56b" }}
                  >
                    <Icon className="size-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink">
                      {c.label}: {up ? "spent more" : "spent less"}
                    </p>
                    <p className="text-xs text-graphite tnum">
                      Last month {formatCurrency(c.prev)}, this month {formatCurrency(c.total)}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
