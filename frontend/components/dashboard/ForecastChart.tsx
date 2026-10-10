"use client";

import {
  Bar,
  BarChart,
  Cell,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { CashFlowForecast } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

interface TooltipPayloadItem {
  value?: number | [number, number];
  dataKey?: string;
  payload?: {
    date: string;
    band: [number, number];
    p50: number;
    comparePoint?: number | null;
  };
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
  compareLabel?: string;
}

function CustomForecastTooltip({
  active,
  payload,
  compareLabel = "Baseline",
}: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="rounded-chip border border-black/[0.1] bg-white/95 p-3.5 shadow-xl backdrop-blur-md text-xs flex flex-col gap-2 min-w-[200px]">
      <div className="flex items-center justify-between border-b border-black/[0.06] pb-1.5">
        <span className="font-semibold text-ink">{formatDate(data.date)}</span>
        <span className="text-[10px] text-pewter uppercase font-medium">Trajectory</span>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-1.5 text-graphite">
            <span className="h-2 w-2 rounded-full bg-lime" />
            <span>P50 Expected</span>
          </span>
          <span className="font-bold text-ink tnum">{formatCurrency(data.p50)}</span>
        </div>

        {data.band && (
          <div className="flex items-center justify-between gap-3 text-pewter">
            <span>P10 - P90 Band</span>
            <span className="tnum font-medium text-graphite">
              {formatCurrency(data.band[0])} - {formatCurrency(data.band[1])}
            </span>
          </div>
        )}

        {data.comparePoint !== null && data.comparePoint !== undefined && (
          <div className="flex items-center justify-between gap-3 text-pewter pt-1 border-t border-black/[0.04]">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-graphite" />
              <span>{compareLabel}</span>
            </span>
            <span className="tnum font-medium text-ink">
              {formatCurrency(data.comparePoint)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export function ForecastChart({
  forecast,
  compareForecast,
  compareLabel = "Before",
  bars = false,
}: {
  forecast: CashFlowForecast;
  compareForecast?: CashFlowForecast;
  compareLabel?: string;
  /** Weekly end-of-week balance bars instead of the daily line (dashboard Outlook). */
  bars?: boolean;
}) {
  const data = forecast.points.map((p, i) => ({
    date: p.date,
    band: [p.p10, p.p90] as [number, number],
    p50: p.p50,
    comparePoint: compareForecast?.points[i]?.p50 ?? null,
  }));

  // One bar per 7 days: the balance at the end of the week, with that week's average P10-P90 band for the tooltip.
  const weekly: typeof data = [];
  for (let i = 0; i < data.length; i += 7) {
    const week = data.slice(i, i + 7);
    const last = week[week.length - 1];
    weekly.push({
      date: last.date,
      p50: last.p50,
      band: [
        week.reduce((s, d) => s + d.band[0], 0) / week.length,
        week.reduce((s, d) => s + d.band[1], 0) / week.length,
      ],
      comparePoint: null,
    });
  }

  const hasShortfall = Boolean(forecast.first_gap_date);
  const confidencePercent = Math.round(
    forecast.confidence <= 1
      ? forecast.confidence * 100
      : forecast.confidence
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Forecast Telemetry Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-black/[0.04]">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border",
              hasShortfall
                ? "bg-rose-50 text-rose-700 border-rose-200"
                : "bg-emerald-50 text-emerald-700 border-emerald-200"
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                hasShortfall ? "bg-rose-500 animate-pulse" : "bg-emerald-500"
              )}
            />
            {hasShortfall
              ? `Deficit projected around ${formatDate(forecast.first_gap_date!)}`
              : "No Cash Shortfall Projected (90 Days)"}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-pewter">Forecast Confidence:</span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-fog border border-black/[0.06] font-semibold text-ink tnum">
            {confidencePercent}%
          </span>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="h-56 sm:h-64 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          {bars ? (
            <BarChart data={weekly} margin={{ left: 8, right: 16, top: 12, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.05)" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(d: string) => formatDate(d)}
                tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
                axisLine={{ stroke: "rgba(15, 23, 42, 0.08)" }}
                tickLine={false}
                minTickGap={30}
              />
              <YAxis
                tickFormatter={(v: number) => formatCurrency(v)}
                tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
                axisLine={false}
                tickLine={false}
                width={82}
              />
              <Tooltip cursor={{ fill: "rgba(198, 241, 53, 0.18)" }} content={<CustomForecastTooltip compareLabel={compareLabel} />} />
              <Bar dataKey="p50" radius={[6, 6, 0, 0]} maxBarSize={44} isAnimationActive={false}>
                {weekly.map((w) => (
                  <Cell key={w.date} fill={w.p50 < 0 ? "#e11d48" : "#a6d11a"} />
                ))}
              </Bar>
            </BarChart>
          ) : (
          <ComposedChart data={data} margin={{ left: 8, right: 16, top: 12, bottom: 4 }}>
            <defs>
              <linearGradient id="emberForecastGlow" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#c6f135" stopOpacity={0.55} />
                <stop offset="95%" stopColor="#c6f135" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.05)" vertical={false} />

            <XAxis
              dataKey="date"
              tickFormatter={(d: string) => formatDate(d)}
              tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
              axisLine={{ stroke: "rgba(15, 23, 42, 0.08)" }}
              tickLine={false}
              minTickGap={45}
            />

            <YAxis
              tickFormatter={(v: number) => formatCurrency(v)}
              tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
              axisLine={false}
              tickLine={false}
              width={82}
            />

            <Tooltip content={<CustomForecastTooltip compareLabel={compareLabel} />} />

            {/* P10 - P90 Soft Confidence Band */}
            <Area
              dataKey="band"
              stroke="none"
              fill="rgba(15, 23, 42, 0.06)"
              isAnimationActive={false}
            />

            {/* Area glow under the expected line */}
            <Area
              dataKey="p50"
              stroke="none"
              fill="url(#emberForecastGlow)"
              isAnimationActive={false}
            />

            {/* Comparison line if simulation active */}
            {compareForecast && (
              <Line
                type="monotone"
                dataKey="comparePoint"
                stroke="var(--color-graphite)"
                strokeDasharray="4 4"
                dot={false}
                strokeWidth={2}
                isAnimationActive={false}
              />
            )}

            {/* P50 Main Line */}
            <Line
              type="monotone"
              dataKey="p50"
              stroke="#5f7f0c"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 6, fill: "#c6f135", stroke: "#5f7f0c", strokeWidth: 2 }}
              isAnimationActive={false}
            />

            {/* Gap shortfall alert line */}
            {forecast.first_gap_date && (
              <ReferenceLine
                x={forecast.first_gap_date}
                stroke="#e11d48"
                strokeDasharray="3 3"
                strokeWidth={2}
                label={{
                  value: "⚠️ Projected Gap",
                  position: "insideTopLeft",
                  fontSize: 11,
                  fill: "#e11d48",
                  fontWeight: 600,
                }}
              />
            )}
          </ComposedChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Legend & Guidance */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-xs text-pewter border-t border-black/[0.04]">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="h-0.5 w-4 bg-[#5f7f0c] rounded-full" />
            <span className="text-graphite font-medium">P50 Expected</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-4 bg-black/[0.08] rounded-sm" />
            <span>P10–P90 Range</span>
          </span>
          {compareForecast && (
            <span className="flex items-center gap-1.5">
              <span className="h-0.5 w-4 border-t-2 border-dashed border-graphite" />
              <span>{compareLabel}</span>
            </span>
          )}
        </div>
        <span>Calculated from real transaction volatility</span>
      </div>
    </div>
  );
}
