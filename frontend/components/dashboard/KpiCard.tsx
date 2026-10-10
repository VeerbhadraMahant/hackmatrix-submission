import type { LucideIcon } from "lucide-react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";

export interface KpiProps {
  label: string;
  value: string;
  sub: string;
  icon: LucideIcon;
  /** Card fill: white (default), lime accent, or black. */
  variant?: "white" | "lime" | "ink";
  series?: number[];
  badge?: { text: string; positive: boolean };
  className?: string;
}

const SURFACE = {
  white: { card: "bg-white text-ink", muted: "text-graphite", chip: "bg-fog text-ink", stroke: "#5f7f0c" },
  lime: { card: "bg-lime text-ink", muted: "text-ink/65", chip: "bg-white/60 text-ink", stroke: "#5f7f0c" },
  ink: { card: "bg-sage text-ink", muted: "text-ink/60", chip: "bg-white/12 text-ink", stroke: "#5f7f0c" },
} as const;

/** Bento stat card: big number, icon chip and a tiny trend sparkline. */
export function KpiCard({ label, value, sub, icon: Icon, variant = "white", series, badge, className }: KpiProps) {
  const s = SURFACE[variant];
  const data = (series ?? []).map((v, i) => ({ i, v }));
  const gradId = `spark-${label.replace(/\W/g, "")}`;
  return (
    <div className={cn("relative flex flex-col overflow-hidden rounded-card p-5 shadow-sm", s.card, className)}>
      <div className="flex items-start justify-between gap-2">
        <span className={cn("text-sm font-medium", s.muted)}>{label}</span>
        <span className={cn("flex size-9 items-center justify-center rounded-full", s.chip)}>
          <Icon className="size-[18px]" />
        </span>
      </div>
      <div className="mt-2 font-display text-3xl font-semibold tnum">{value}</div>
      <div className={cn("mt-1 flex flex-wrap items-center gap-2 text-xs", s.muted)}>
        {badge && (
          <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold", s.chip)}>
            {badge.positive ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
            {badge.text}
          </span>
        )}
        <span>{sub}</span>
      </div>
      {data.length > 1 && (
        <div className="pointer-events-none -mx-5 -mb-5 mt-auto h-14 pt-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, bottom: 0, left: 0, right: 0 }}>
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.stroke} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={s.stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke={s.stroke} strokeWidth={2} fill={`url(#${gradId})`} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
