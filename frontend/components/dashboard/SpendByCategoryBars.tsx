"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Transaction } from "@/lib/types";
import { weeklyCategorySpend, type WeeklyStack } from "@/lib/spend";
import { formatCurrency, formatDate } from "@/lib/format";

const compact = (v: number) =>
  v >= 100000 ? `₹${(v / 100000).toFixed(1)}L` : v >= 1000 ? `₹${Math.round(v / 1000)}k` : `₹${v}`;

function StackTooltip({
  active,
  payload,
  keys,
}: {
  active?: boolean;
  payload?: { payload: WeeklyStack["rows"][number] }[];
  keys: WeeklyStack["keys"];
}) {
  const row = active ? payload?.[0]?.payload : null;
  if (!row) return null;
  const parts = keys.filter((k) => Number(row[k.key]) > 0).sort((a, b) => Number(row[b.key]) - Number(row[a.key]));
  return (
    <div className="flex min-w-[200px] flex-col gap-1.5 rounded-chip border border-black/[0.1] bg-white/95 p-3.5 text-xs shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-black/[0.06] pb-1.5">
        <span className="font-semibold text-ink">Week of {formatDate(row.week)}</span>
        <span className="font-bold tnum text-ink">{formatCurrency(row.total)}</span>
      </div>
      {parts.map((k) => (
        <div key={k.key} className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-1.5 text-graphite">
            <i className="size-2 rounded-full" style={{ background: k.color }} />
            {k.label}
          </span>
          <span className="tnum font-medium text-ink">{formatCurrency(Number(row[k.key]))}</span>
        </div>
      ))}
    </div>
  );
}

/** Weekly spending as stacked bars: each week's bar is split into its real category amounts. */
export function SpendByCategoryBars({ txns }: { txns: Transaction[] }) {
  const { keys, rows } = useMemo(() => weeklyCategorySpend(txns), [txns]);
  if (rows.length === 0) return <p className="py-10 text-center text-sm text-pewter">Weekly spending will chart here.</p>;

  return (
    <div className="flex flex-col gap-3">
      <div className="h-64 w-full sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ left: 8, right: 16, top: 12, bottom: 4 }} barCategoryGap="12%">
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.05)" vertical={false} />
            <XAxis
              dataKey="week"
              tickFormatter={(d: string) => formatDate(d)}
              tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
              axisLine={{ stroke: "rgba(15, 23, 42, 0.08)" }}
              tickLine={false}
              minTickGap={28}
            />
            <YAxis
              tickFormatter={compact}
              tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
              axisLine={false}
              tickLine={false}
              width={52}
            />
            <Tooltip cursor={{ fill: "rgba(198, 241, 53, 0.18)" }} content={<StackTooltip keys={keys} />} />
            {keys.map((k) => (
              <Bar key={k.key} dataKey={k.key} stackId="spend" fill={k.color} isAnimationActive={false} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-black/[0.04] pt-3 text-xs text-graphite">
        {keys.map((k) => (
          <span key={k.key} className="flex items-center gap-1.5">
            <i className="size-2.5 rounded-sm" style={{ background: k.color }} />
            {k.label}
          </span>
        ))}
        <span className="ml-auto text-pewter">Weekly totals from your transactions</span>
      </div>
    </div>
  );
}
