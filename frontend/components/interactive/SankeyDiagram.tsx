"use client";

import { useState, useRef, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { Info, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";

export interface SankeyNode {
  id: string;
  label: string;
  amount: number;
  level: 0 | 1 | 2;
  color: string;
}

export interface SankeyLink {
  id: string;
  source: string;
  target: string;
  amount: number;
  gradientId: string;
}

const TOTAL_INCOME = 95000;

const DEFAULT_NODES: SankeyNode[] = [
  // Level 0: Total Inflow
  { id: "income", label: "Monthly Income", amount: 95000, level: 0, color: "#059669" },

  // Level 1: Primary Allocation Pillars
  { id: "obligations", label: "Fixed Obligations", amount: 46700, level: 1, color: "#e11d48" },
  { id: "discretionary", label: "Living & Discretionary", amount: 28300, level: 1, color: "#d97706" },
  { id: "investments", label: "Wealth & Savings", amount: 20000, level: 1, color: "#4f46e5" },

  // Level 2: Granular Subcategories
  { id: "rent", label: "Apartment Rent & PG", amount: 28500, level: 2, color: "#e11d48" },
  { id: "car_loan", label: "Car Loan EMI", amount: 18200, level: 2, color: "#f43f5e" },

  { id: "groceries", label: "Groceries & Food", amount: 12400, level: 2, color: "#d97706" },
  { id: "dining", label: "Dining & Social", amount: 8500, level: 2, color: "#f59e0b" },
  { id: "utilities", label: "Utilities & Bills", amount: 7400, level: 2, color: "#fbbf24" },

  { id: "sip", label: "Mutual Fund SIP", amount: 15000, level: 2, color: "#4f46e5" },
  { id: "emergency", label: "Emergency Reserve", amount: 5000, level: 2, color: "#6366f1" },
];

const DEFAULT_LINKS: SankeyLink[] = [
  // Income to Pillars
  { id: "inc-ob", source: "income", target: "obligations", amount: 46700, gradientId: "grad-inc-ob" },
  { id: "inc-disc", source: "income", target: "discretionary", amount: 28300, gradientId: "grad-inc-disc" },
  { id: "inc-inv", source: "income", target: "investments", amount: 20000, gradientId: "grad-inc-inv" },

  // Obligations to Subcategories
  { id: "ob-rent", source: "obligations", target: "rent", amount: 28500, gradientId: "grad-ob-rent" },
  { id: "ob-car", source: "obligations", target: "car_loan", amount: 18200, gradientId: "grad-ob-car" },

  // Discretionary to Subcategories
  { id: "disc-groc", source: "discretionary", target: "groceries", amount: 12400, gradientId: "grad-disc-groc" },
  { id: "disc-din", source: "discretionary", target: "dining", amount: 8500, gradientId: "grad-disc-din" },
  { id: "disc-util", source: "discretionary", target: "utilities", amount: 7400, gradientId: "grad-disc-util" },

  // Investments to Subcategories
  { id: "inv-sip", source: "investments", target: "sip", amount: 15000, gradientId: "grad-inv-sip" },
  { id: "inv-emg", source: "investments", target: "emergency", amount: 5000, gradientId: "grad-inv-emg" },
];

export interface SankeyDiagramProps {
  title?: string;
  subtitle?: string;
  nodes?: SankeyNode[];
  links?: SankeyLink[];
  className?: string;
}

const colX = [60, 360, 680]; // X positions for level 0, 1, 2

export function SankeyDiagram({
  title = "Visualize the Flow of Money",
  subtitle = "Interactive Sankey flow model illustrating how monthly inflow distributes seamlessly across debt obligations, living expenses, and wealth accumulation channels.",
  nodes = DEFAULT_NODES,
  links = DEFAULT_LINKS,
  className,
}: SankeyDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const [activeElementId, setActiveElementId] = useState<string | null>(null);

  // SVG Geometry Constants
  const width = 860;
  const height = 440;
  const nodeWidth = 14;
  const totalScaleHeight = 360;

  // Compute node vertical coordinates
  const computedNodes = useMemo(() => {
    const map = new Map<string, { x: number; y: number; height: number; node: SankeyNode }>();

    // Level 0: Income (centered vertically)
    const l0Node = nodes.find((n) => n.level === 0)!;
    const l0Height = totalScaleHeight;
    map.set(l0Node.id, { x: colX[0], y: 40, height: l0Height, node: l0Node });

    // Level 1: 3 Pillars with gaps
    const l1Nodes = nodes.filter((n) => n.level === 1);
    const l1Gap = 16;
    const l1Available = totalScaleHeight - l1Gap * (l1Nodes.length - 1);
    let l1CurrentY = 40;
    l1Nodes.forEach((n) => {
      const h = Math.max(30, (n.amount / TOTAL_INCOME) * l1Available);
      map.set(n.id, { x: colX[1], y: l1CurrentY, height: h, node: n });
      l1CurrentY += h + l1Gap;
    });

    // Level 2: Subcategories grouped by parent
    const l2Nodes = nodes.filter((n) => n.level === 2);
    const l2Gap = 12;
    const l2Available = totalScaleHeight - l2Gap * (l2Nodes.length - 1);
    let l2CurrentY = 40;
    l2Nodes.forEach((n) => {
      const h = Math.max(22, (n.amount / TOTAL_INCOME) * l2Available);
      map.set(n.id, { x: colX[2], y: l2CurrentY, height: h, node: n });
      l2CurrentY += h + l2Gap;
    });

    return map;
  }, [nodes]);

  // Compute ribbon bezier shapes for links
  const computedLinks = useMemo(() => {
    // Keep track of stacking offsets on nodes
    const sourceOffsetMap = new Map<string, number>();
    const targetOffsetMap = new Map<string, number>();

    return links.map((link) => {
      const sNode = computedNodes.get(link.source);
      const tNode = computedNodes.get(link.target);

      if (!sNode || !tNode) return null;

      const sOffset = sourceOffsetMap.get(link.source) ?? 0;
      const tOffset = targetOffsetMap.get(link.target) ?? 0;

      // Ribbon height on source & target
      const sHeight = (link.amount / sNode.node.amount) * sNode.height;
      const tHeight = (link.amount / tNode.node.amount) * tNode.height;

      const x0 = sNode.x + nodeWidth;
      const x1 = tNode.x;
      const y0Top = sNode.y + sOffset;
      const y0Bot = y0Top + sHeight;
      const y1Top = tNode.y + tOffset;
      const y1Bot = y1Top + tHeight;

      sourceOffsetMap.set(link.source, sOffset + sHeight);
      targetOffsetMap.set(link.target, tOffset + tHeight);

      const midX = (x0 + x1) / 2;

      // Closed bezier ribbon path
      const path = `M ${x0} ${y0Top} C ${midX} ${y0Top}, ${midX} ${y1Top}, ${x1} ${y1Top} L ${x1} ${y1Bot} C ${midX} ${y1Bot}, ${midX} ${y0Bot}, ${x0} ${y0Bot} Z`;

      return {
        ...link,
        path,
        sourceColor: sNode.node.color,
        targetColor: tNode.node.color,
      };
    }).filter(Boolean) as (SankeyLink & { path: string; sourceColor: string; targetColor: string })[];
  }, [links, computedNodes]);

  // Tooltip details
  const activeDetails = useMemo(() => {
    if (!activeElementId) return null;
    const nodeItem = computedNodes.get(activeElementId);
    if (nodeItem) {
      const share = ((nodeItem.node.amount / TOTAL_INCOME) * 100).toFixed(1);
      return {
        title: nodeItem.node.label,
        amount: nodeItem.node.amount,
        share: `${share}% of monthly income`,
        color: nodeItem.node.color,
      };
    }
    const linkItem = computedLinks.find((l) => l.id === activeElementId);
    if (linkItem) {
      const share = ((linkItem.amount / TOTAL_INCOME) * 100).toFixed(1);
      const sNode = computedNodes.get(linkItem.source)?.node.label ?? "";
      const tNode = computedNodes.get(linkItem.target)?.node.label ?? "";
      return {
        title: `${sNode} → ${tNode}`,
        amount: linkItem.amount,
        share: `${share}% share`,
        color: linkItem.targetColor,
      };
    }
    return null;
  }, [activeElementId, computedNodes, computedLinks]);

  // Check if link or node is connected to activeElementId
  const isElementHighlighted = useCallback(
    (id: string, sourceId?: string, targetId?: string) => {
      if (!activeElementId) return true;
      if (activeElementId === id) return true;
      if (sourceId && (activeElementId === sourceId || activeElementId === targetId)) return true;
      return false;
    },
    [activeElementId]
  );

  return (
    <div
      ref={containerRef}
      className={cn(
        "rounded-card border border-black/[0.08] bg-white p-6 sm:p-8 shadow-sm flex flex-col gap-6 relative overflow-hidden",
        className
      )}
    >
      {/* Background ambient lighting */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-gradient-to-b from-emerald-500/5 via-indigo-500/5 to-transparent rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-black/[0.04]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ember bg-orange-50 px-2.5 py-0.5 rounded-full border border-ember/20">
              Cash-Flow Reports
            </span>
            <span className="text-xs text-pewter font-medium">• Double-Entry Flow Analysis</span>
          </div>
          <h3 className="font-display text-2xl sm:text-3xl font-medium text-ink mt-1.5 tracking-tight">
            {title}
          </h3>
          <p className="text-xs sm:text-sm text-graphite mt-1 max-w-2xl leading-relaxed">
            {subtitle}
          </p>
        </div>

        {/* Dynamic Tooltip Badge or Default Pill */}
        <div className="shrink-0">
          {activeDetails ? (
            <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-sage text-ink shadow-lg transition-all">
              <span
                className="h-2.5 w-2.5 rounded-full shrink-0"
                style={{ backgroundColor: activeDetails.color }}
              />
              <div className="flex flex-col text-left">
                <span className="text-xs font-semibold">{activeDetails.title}</span>
                <span className="text-[11px] text-graphite font-tabular tnum">
                  {formatCurrency(activeDetails.amount)} &middot; {activeDetails.share}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-black/[0.08] bg-fog text-xs font-medium text-graphite">
              <Info className="h-3.5 w-3.5 text-pewter" />
              <span>Hover or tap any flow node to inspect</span>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Scroll Indicator Banner (< 640px) */}
      <div className="flex sm:hidden items-center justify-between px-3 py-1.5 rounded-chip bg-fog text-[11px] text-pewter">
        <span>↔ Scroll horizontally to explore full allocation</span>
        <Eye className="h-3.5 w-3.5 text-graphite" />
      </div>

      {/* SVG Sankey Diagram Canvas (Horizontal scrollable on mobile) */}
      <div className="w-full overflow-x-auto select-none touch-pan-x py-2 -mx-2 px-2">
        <svg
          className="w-full min-w-[760px] h-[400px] overflow-visible"
          viewBox={`0 0 ${width} ${height}`}
          aria-label="Cash-Flow Topology Sankey Diagram: Inflows flowing into fixed obligations, living expenses, and wealth accumulation."
          role="img"
        >
          <defs>
            {computedLinks.map((link) => (
              <linearGradient
                key={link.gradientId}
                id={link.gradientId}
                x1="0%"
                y1="0%"
                x2="100%"
                y2="0%"
              >
                <stop offset="0%" stopColor={link.sourceColor} stopOpacity={0.65} />
                <stop offset="100%" stopColor={link.targetColor} stopOpacity={0.7} />
              </linearGradient>
            ))}
          </defs>

          {/* Ribbon Paths (Links) */}
          <g className="sankey-links">
            {computedLinks.map((link) => {
              const highlighted = isElementHighlighted(link.id, link.source, link.target);
              return (
                <motion.path
                  key={link.id}
                  d={link.path}
                  fill={`url(#${link.gradientId})`}
                  initial={{ opacity: 0 }}
                  animate={{
                    opacity: highlighted ? 0.75 : 0.12,
                    scale: highlighted ? 1 : 0.99,
                  }}
                  transition={{ duration: 0.3 }}
                  onPointerEnter={() => setActiveElementId(link.id)}
                  onPointerLeave={() => setActiveElementId(null)}
                  onClick={() => setActiveElementId(link.id)}
                  className="cursor-pointer transition-opacity duration-200"
                />
              );
            })}
          </g>

          {/* Nodes (Vertical Bars & Labels) */}
          <g className="sankey-nodes">
            {Array.from(computedNodes.values()).map(({ x, y, height: nodeH, node }) => {
              const highlighted = isElementHighlighted(node.id);
              const isSource = node.level === 0;
              const isTarget = node.level === 2;

              return (
                <g
                  key={node.id}
                  tabIndex={0}
                  role="button"
                  aria-label={`${node.label}: ${formatCurrency(node.amount)}`}
                  onPointerEnter={() => setActiveElementId(node.id)}
                  onPointerLeave={() => setActiveElementId(null)}
                  onClick={() => setActiveElementId(node.id)}
                  onFocus={() => setActiveElementId(node.id)}
                  onBlur={() => setActiveElementId(null)}
                  className="cursor-pointer outline-none"
                >
                  {/* Vertical Bar */}
                  <rect
                    x={x}
                    y={y}
                    width={nodeWidth}
                    height={nodeH}
                    rx={4}
                    fill={node.color}
                    className="transition-transform duration-200"
                    opacity={highlighted ? 1 : 0.25}
                  />

                  {/* Node Label Text */}
                  <text
                    x={isSource ? x - 12 : isTarget ? x + nodeWidth + 12 : x + nodeWidth / 2}
                    y={y + nodeH / 2}
                    textAnchor={isSource ? "end" : isTarget ? "start" : "middle"}
                    dominantBaseline="middle"
                    className={cn(
                      "font-sans transition-all duration-200",
                      node.level === 1 ? "hidden" : "block"
                    )}
                    fill={highlighted ? "#090a0f" : "#717786"}
                    fontWeight={highlighted ? "700" : "500"}
                    fontSize={node.level === 0 ? "13" : "11"}
                  >
                    {node.label}
                  </text>

                  {/* Amount Subtext */}
                  <text
                    x={isSource ? x - 12 : isTarget ? x + nodeWidth + 12 : x + nodeWidth / 2}
                    y={y + nodeH / 2 + 14}
                    textAnchor={isSource ? "end" : isTarget ? "start" : "middle"}
                    dominantBaseline="middle"
                    className="font-tabular tnum"
                    fill={highlighted ? "#4b5162" : "#9aa0b0"}
                    fontSize="10"
                    fontWeight="600"
                  >
                    {formatCurrency(node.amount)}
                  </text>

                  {/* Level 1 Specialized Header Banner */}
                  {node.level === 1 && (
                    <text
                      x={x + nodeWidth + 10}
                      y={y + 12}
                      textAnchor="start"
                      fill={highlighted ? "#090a0f" : "#717786"}
                      fontWeight="700"
                      fontSize="12"
                    >
                      {node.label} ({formatCurrency(node.amount)})
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* Footer Legend */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-black/[0.04] text-xs text-pewter">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-600" />
            <span className="text-graphite font-medium">Income Inflow</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-rose-500" />
            <span className="text-graphite font-medium">Fixed Obligations (49%)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span className="text-graphite font-medium">Living Expenses (30%)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-indigo-600" />
            <span className="text-graphite font-medium">Savings & Investments (21%)</span>
          </span>
        </div>
        <span>Double-entry balanced model</span>
      </div>

      {/* Screen Reader Visually Hidden Data Table Fallback */}
      <table className="sr-only">
        <caption>Monthly Cash-Flow Distribution Table</caption>
        <thead>
          <tr>
            <th scope="col">Category</th>
            <th scope="col">Type</th>
            <th scope="col">Monthly Amount</th>
            <th scope="col">Percentage Share</th>
          </tr>
        </thead>
        <tbody>
          {nodes.map((n) => (
            <tr key={n.id}>
              <td>{n.label}</td>
              <td>Level {n.level}</td>
              <td>{n.amount} INR</td>
              <td>{((n.amount / TOTAL_INCOME) * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
