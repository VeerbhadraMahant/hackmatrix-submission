"use client";

import { useRef, useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingDown, TrendingUp, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";

export interface LineChartPoint {
  day: number;
  dateStr: string;
  actual: number;
  budget: number;
  categoryNote?: string;
}

export interface InteractiveLineChartProps {
  title?: string;
  subtitle?: string;
  points?: LineChartPoint[];
  className?: string;
}

// Realistic 30-day cumulative spend vs budget curve for FinPilot
const DEFAULT_POINTS: LineChartPoint[] = [
  { day: 1, dateStr: "Oct 01", actual: 1800, budget: 2500, categoryNote: "Groceries" },
  { day: 3, dateStr: "Oct 03", actual: 4200, budget: 5500, categoryNote: "Fuel & Transit" },
  { day: 6, dateStr: "Oct 06", actual: 9100, budget: 11000, categoryNote: "Weekly Supermarket" },
  { day: 9, dateStr: "Oct 09", actual: 14800, budget: 16500, categoryNote: "Utility Bills" },
  { day: 12, dateStr: "Oct 12", actual: 21200, budget: 22000, categoryNote: "Dining with friends" },
  { day: 15, dateStr: "Oct 15", actual: 26500, budget: 27500, categoryNote: "Mid-month checkpoint" },
  { day: 18, dateStr: "Oct 18", actual: 34200, budget: 33000, categoryNote: "Festive electronics buy" }, // brief surge over budget
  { day: 21, dateStr: "Oct 21", actual: 37800, budget: 38500, categoryNote: "Spend pause recovered" }, // back under budget
  { day: 24, dateStr: "Oct 24", actual: 42100, budget: 44000, categoryNote: "Monthly medicines" },
  { day: 27, dateStr: "Oct 27", actual: 46900, budget: 49500, categoryNote: "Weekend groceries" },
  { day: 30, dateStr: "Oct 30", actual: 51200, budget: 55000, categoryNote: "End of month safe zone" },
];

export function InteractiveLineChart({
  title = "Follow the Line: Real-Time Spending Velocity",
  subtitle = "Start your day with an instant glance at your spending curve against your calibrated budget. Scrub or use arrow keys to inspect day-by-day variance.",
  points = DEFAULT_POINTS,
  className,
}: InteractiveLineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(points.length - 1);
  const [isScrubbing, setIsScrubbing] = useState(false);

  // SVG Geometry Dimensions
  const svgWidth = 720;
  const svgHeight = 280;
  const padding = { top: 30, right: 30, bottom: 40, left: 55 };

  const chartWidth = svgWidth - padding.left - padding.right;
  const chartHeight = svgHeight - padding.top - padding.bottom;

  // Max bounds
  const maxVal = useMemo(() => {
    const highest = Math.max(
      ...points.map((p) => Math.max(p.actual, p.budget))
    );
    return Math.ceil(highest / 10000) * 10000;
  }, [points]);

  // Scalers
  const getX = useCallback(
    (index: number) => padding.left + (index / (points.length - 1)) * chartWidth,
    [chartWidth, padding.left, points.length]
  );

  const getY = useCallback(
    (val: number) => padding.top + chartHeight - (val / maxVal) * chartHeight,
    [chartHeight, maxVal, padding.top]
  );

  // Active point
  const activePoint = points[selectedIndex];
  const delta = activePoint.budget - activePoint.actual;
  const isUnder = delta >= 0;

  // Build SVG Path for Actual Spending Line
  const linePath = useMemo(() => {
    return points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${getX(i).toFixed(1)} ${getY(p.actual).toFixed(1)}`)
      .join(" ");
  }, [points, getX, getY]);

  // Build SVG Path for Area under Actual Curve
  const areaPath = useMemo(() => {
    if (!points.length) return "";
    const firstX = getX(0);
    const lastX = getX(points.length - 1);
    const baselineY = padding.top + chartHeight;
    return `${linePath} L ${lastX} ${baselineY} L ${firstX} ${baselineY} Z`;
  }, [linePath, points, getX, padding.top, chartHeight]);

  // Build SVG Path for Target Budget (Dashed Line)
  const budgetPath = useMemo(() => {
    return points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${getX(i).toFixed(1)} ${getY(p.budget).toFixed(1)}`)
      .join(" ");
  }, [points, getX, getY]);

  // Pointer scrubbing logic
  const handlePointerScrub = useCallback(
    (clientX: number) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const relativeX = clientX - rect.left - padding.left;
      const clampedX = Math.max(0, Math.min(chartWidth, relativeX));
      const ratio = clampedX / chartWidth;
      const closestIndex = Math.round(ratio * (points.length - 1));
      setSelectedIndex(closestIndex);
    },
    [chartWidth, padding.left, points.length]
  );

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    setIsScrubbing(true);
    handlePointerScrub(e.clientX);
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isScrubbing || e.pointerType === "mouse") {
      handlePointerScrub(e.clientX);
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    setIsScrubbing(false);
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
  };

  // Keyboard accessibility
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(0, prev - 1));
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(points.length - 1, prev + 1));
    }
  };

  const activeX = getX(selectedIndex);
  const activeY = getY(activePoint.actual);

  return (
    <div
      className={cn(
        "rounded-card border border-black/[0.08] bg-white p-4 sm:p-8 shadow-sm flex flex-col gap-6",
        className
      )}
    >
      {/* Header with Title and Real-time Delta Pill */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-black/[0.04]">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display text-xl sm:text-2xl font-semibold text-ink">
              {title}
            </h3>
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <p className="text-xs sm:text-sm text-graphite mt-1 max-w-xl leading-relaxed">
            {subtitle}
          </p>
        </div>

        {/* Dynamic Delta Pill (Inspired by "$125 under" reference) */}
        <div
          className={cn(
            "self-start sm:self-auto inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-bold transition-all shadow-sm",
            isUnder
              ? "bg-emerald-50 text-emerald-800 border-emerald-300"
              : "bg-rose-50 text-rose-800 border-rose-300"
          )}
        >
          {isUnder ? (
            <TrendingDown className="h-4 w-4 text-emerald-600" />
          ) : (
            <TrendingUp className="h-4 w-4 text-rose-600" />
          )}
          <span className="tnum font-extrabold text-sm">
            {formatCurrency(Math.abs(delta))}
          </span>
          <span className="font-semibold uppercase tracking-wider text-[10px]">
            {isUnder ? "Under Target" : "Over Target"}
          </span>
        </div>
      </div>

      {/* Interactive Chart Area (touch-action: pan-y preserves vertical scroll) */}
      <div
        ref={containerRef}
        tabIndex={0}
        role="region"
        aria-label="Interactive 30-Day Spending Trajectory Chart. Use left and right arrow keys to scrub through daily checkpoints."
        onKeyDown={handleKeyDown}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        className="relative w-full overflow-hidden select-none outline-none focus-visible:ring-2 focus-visible:ring-ember/40 rounded-surface bg-fog/30 cursor-crosshair touch-pan-y py-2"
      >
        <svg
          className="w-full h-auto max-h-[320px] overflow-visible"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            {/* Smooth Emerald/Ember dynamic gradient under actual curve */}
            <linearGradient id="spendGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isUnder ? "#059669" : "#ff5900"} stopOpacity={0.25} />
              <stop offset="95%" stopColor={isUnder ? "#059669" : "#ff5900"} stopOpacity={0.0} />
            </linearGradient>

            {/* Line stroke gradient */}
            <linearGradient id="spendStroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#059669" />
              <stop offset="60%" stopColor="#ff5900" />
              <stop offset="100%" stopColor="#059669" />
            </linearGradient>
          </defs>

          {/* Horizontal Gridlines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
            const y = padding.top + chartHeight * (1 - ratio);
            const val = maxVal * ratio;
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={svgWidth - padding.right}
                  y2={y}
                  stroke="rgba(15, 23, 42, 0.06)"
                  strokeDasharray="4 4"
                />
                <text
                  x={padding.left - 10}
                  y={y + 4}
                  textAnchor="end"
                  fontSize="10"
                  fill="#717786"
                  className="font-tabular tnum"
                >
                  ₹{(val / 1000).toFixed(0)}k
                </text>
              </g>
            );
          })}

          {/* Area fill */}
          <path d={areaPath} fill="url(#spendGlow)" />

          {/* Dashed Budget Benchmark Line */}
          <path
            d={budgetPath}
            fill="none"
            stroke="#9aa0b0"
            strokeWidth="1.75"
            strokeDasharray="5 5"
          />

          {/* Actual Spending Line */}
          <path
            d={linePath}
            fill="none"
            stroke={isUnder ? "#059669" : "#ff5900"}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive Vertical Cursor Line */}
          <line
            x1={activeX}
            y1={padding.top}
            x2={activeX}
            y2={padding.top + chartHeight}
            stroke="#090a0f"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />

          {/* Target Milestone Indicator Circle */}
          <circle
            cx={activeX}
            cy={getY(activePoint.budget)}
            r="4"
            fill="#ffffff"
            stroke="#9aa0b0"
            strokeWidth="2"
          />

          {/* Active Point Glowing Ring */}
          <circle
            cx={activeX}
            cy={activeY}
            r="6"
            fill={isUnder ? "#059669" : "#ff5900"}
            stroke="#ffffff"
            strokeWidth="2.5"
          />

          {/* X Axis Labels */}
          {points.map((p, i) => {
            // Show every alternate point label to avoid crowding on mobile
            if (i % 2 !== 0 && i !== points.length - 1) return null;
            return (
              <text
                key={i}
                x={getX(i)}
                y={svgHeight - 12}
                textAnchor="middle"
                fontSize="11"
                fill={i === selectedIndex ? "#090a0f" : "#717786"}
                fontWeight={i === selectedIndex ? "700" : "500"}
              >
                {p.dateStr}
              </text>
            );
          })}
        </svg>

        {/* Floating Snapping Tooltip */}
        <AnimatePresence>
          <motion.div
            key={selectedIndex}
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.15 }}
            style={{
              left: `clamp(12px, calc(${(activeX / svgWidth) * 100}% - 90px), calc(100% - 190px))`,
              top: 12,
            }}
            className="absolute pointer-events-none rounded-chip border border-black/[0.1] bg-white/95 p-3 shadow-xl backdrop-blur-md text-xs flex flex-col gap-1.5 w-44 z-30"
          >
            <div className="flex items-center justify-between pb-1 border-b border-black/[0.06]">
              <span className="font-semibold text-ink flex items-center gap-1">
                <Calendar className="h-3 w-3 text-pewter" />
                <span>{activePoint.dateStr}</span>
              </span>
              <span
                className={cn(
                  "text-[10px] font-bold px-1.5 py-0.2 rounded",
                  isUnder ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
                )}
              >
                {isUnder ? "Under" : "Over"}
              </span>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="text-pewter">Actual Spent:</span>
                <span className="font-bold text-ink tnum">
                  {formatCurrency(activePoint.actual)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-pewter">Budget Limit:</span>
                <span className="font-medium text-graphite tnum">
                  {formatCurrency(activePoint.budget)}
                </span>
              </div>
              {activePoint.categoryNote && (
                <div className="pt-1 text-[10px] text-pewter border-t border-black/[0.04] line-clamp-1 italic">
                  Note: {activePoint.categoryNote}
                </div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Legend & Scrubbing Instructions */}
      <div className="flex flex-wrap items-center justify-between gap-4 text-xs text-pewter pt-1">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="h-1 w-4 bg-emerald-600 rounded-full" />
            <span className="text-graphite font-medium">Under Budget (Safe)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-1 w-4 bg-ember rounded-full" />
            <span className="text-graphite font-medium">Over Budget (Surge)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-0.5 w-4 border-t-2 border-dashed border-steel" />
            <span>Target Ceiling</span>
          </span>
        </div>
        <span className="text-[11px]">
          Drag or swipe horizontally to scrub &middot; Arrow keys for fine-step
        </span>
      </div>

      {/* Visually Hidden Screen Reader Data Table Fallback */}
      <table className="sr-only">
        <caption>30-Day Cumulative Spending vs Budget Data Table</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Actual Spend</th>
            <th scope="col">Budget Target</th>
            <th scope="col">Variance</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => {
            const v = p.budget - p.actual;
            return (
              <tr key={p.day}>
                <td>{p.dateStr}</td>
                <td>{p.actual} INR</td>
                <td>{p.budget} INR</td>
                <td>{v >= 0 ? `${v} INR under` : `${Math.abs(v)} INR over`}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
