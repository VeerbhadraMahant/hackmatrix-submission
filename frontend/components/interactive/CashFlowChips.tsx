"use client";

import { useRef, useCallback, useEffect } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useInView,
  useReducedMotion,
} from "framer-motion";
import { ArrowUpRight, ArrowDownRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";

export interface CashFlowChipData {
  id: string;
  category: string;
  amount: number;
  type: "inflow" | "outflow";
  tone: "emerald" | "amber" | "rose" | "indigo" | "graphite";
  depth: number; // 0.8 to 1.4 for parallax scaling
  driftDuration: number; // 7s to 12s
}

export interface CashFlowChipsProps {
  chips?: CashFlowChipData[];
  title?: string;
  subtitle?: string;
  className?: string;
}

const DEFAULT_CHIPS: CashFlowChipData[] = [
  {
    id: "chip-1",
    category: "Corporate Payroll",
    amount: 95000,
    type: "inflow",
    tone: "emerald",
    depth: 1.2,
    driftDuration: 8,
  },
  {
    id: "chip-2",
    category: "Apartment Rent & PG",
    amount: -28500,
    type: "outflow",
    tone: "graphite",
    depth: 0.9,
    driftDuration: 10,
  },
  {
    id: "chip-3",
    category: "Index Fund SIP",
    amount: 15000,
    type: "inflow",
    tone: "emerald",
    depth: 1.3,
    driftDuration: 7.5,
  },
  {
    id: "chip-4",
    category: "Car Loan EMI",
    amount: -18200,
    type: "outflow",
    tone: "rose",
    depth: 1.0,
    driftDuration: 9,
  },
  {
    id: "chip-5",
    category: "Groceries & Supermarket",
    amount: -12400,
    type: "outflow",
    tone: "amber",
    depth: 1.15,
    driftDuration: 8.5,
  },
  {
    id: "chip-6",
    category: "Cloud & Subscriptions",
    amount: -1849,
    type: "outflow",
    tone: "indigo",
    depth: 0.85,
    driftDuration: 11,
  },
];

interface SingleDraggableChipProps {
  chip: CashFlowChipData;
  containerRef: React.RefObject<HTMLDivElement | null>;
  pointerX: ReturnType<typeof useMotionValue<number>>;
  pointerY: ReturnType<typeof useMotionValue<number>>;
  shouldReduceMotion: boolean | null;
  isInView: boolean;
}

function SingleDraggableChip({
  chip,
  containerRef,
  pointerX,
  pointerY,
  shouldReduceMotion,
  isInView,
}: SingleDraggableChipProps) {
  const chipRef = useRef<HTMLDivElement>(null);

  // Magnetic Repulsion motion values
  const repelX = useMotionValue(0);
  const repelY = useMotionValue(0);
  const springX = useSpring(repelX, { stiffness: 350, damping: 25 });
  const springY = useSpring(repelY, { stiffness: 350, damping: 25 });

  // Update repulsion vector via requestAnimationFrame
  useEffect(() => {
    if (shouldReduceMotion) return;

    let animId: number;
    const REPEL_RADIUS = 120; // px
    const MAX_PUSH = 28; // px

    function checkProximity() {
      if (!chipRef.current || !containerRef.current) return;

      const pX = pointerX.get();
      const pY = pointerY.get();

      // If pointer is off-screen / inactive
      if (pX < 0 || pY < 0) {
        repelX.set(0);
        repelY.set(0);
        animId = requestAnimationFrame(checkProximity);
        return;
      }

      const containerRect = containerRef.current.getBoundingClientRect();
      const chipRect = chipRef.current.getBoundingClientRect();

      // Chip center relative to container
      const chipCenterX = chipRect.left - containerRect.left + chipRect.width / 2;
      const chipCenterY = chipRect.top - containerRect.top + chipRect.height / 2;

      const dx = chipCenterX - pX;
      const dy = chipCenterY - pY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < REPEL_RADIUS && dist > 1) {
        const force = (1 - dist / REPEL_RADIUS) * MAX_PUSH;
        const nx = dx / dist;
        const ny = dy / dist;
        repelX.set(nx * force * chip.depth);
        repelY.set(ny * force * chip.depth);
      } else {
        repelX.set(0);
        repelY.set(0);
      }

      animId = requestAnimationFrame(checkProximity);
    }

    animId = requestAnimationFrame(checkProximity);
    return () => cancelAnimationFrame(animId);
  }, [chip.depth, containerRef, pointerX, pointerY, repelX, repelY, shouldReduceMotion]);

  const isInflow = chip.type === "inflow";

  return (
    <motion.div
      ref={chipRef}
      drag
      dragConstraints={{ left: -100, right: 100, top: -60, bottom: 60 }}
      dragElastic={0.4}
      dragTransition={{ bounceStiffness: 350, bounceDamping: 25 }}
      whileDrag={{ scale: 1.08, zIndex: 40, cursor: "grabbing" }}
      style={{
        x: springX,
        y: springY,
      }}
      animate={
        shouldReduceMotion || !isInView
          ? { translateY: 0, rotate: 0 }
          : {
              translateY: [0, -8 * chip.depth, 0],
              rotate: [0, (chip.depth > 1 ? 0.8 : -0.8), 0],
            }
      }
      transition={{
        duration: chip.driftDuration,
        repeat: Infinity,
        ease: "easeInOut",
      }}
      tabIndex={0}
      role="button"
      aria-label={`${chip.category}, ${isInflow ? "Inflow" : "Outflow"}: ${formatCurrency(Math.abs(chip.amount))}`}
      className={cn(
        "group relative flex items-center gap-2.5 px-4 py-2.5 rounded-full border bg-white/95 backdrop-blur-md shadow-[0_4px_16px_rgba(15,23,42,0.06),0_1px_2px_rgba(15,23,42,0.04)] cursor-grab select-none transition-shadow hover:shadow-[0_8px_24px_rgba(15,23,42,0.12)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ember/40 active:scale-[0.98]",
        chip.tone === "emerald" && "border-emerald-200/80 hover:border-emerald-400",
        chip.tone === "rose" && "border-rose-200/80 hover:border-rose-400",
        chip.tone === "amber" && "border-amber-200/80 hover:border-amber-400",
        chip.tone === "indigo" && "border-indigo-200/80 hover:border-indigo-400",
        chip.tone === "graphite" && "border-black/[0.08] hover:border-black/[0.18]"
      )}
    >
      {/* Icon Pill */}
      <span
        className={cn(
          "flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold shrink-0",
          isInflow ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
        )}
      >
        {isInflow ? (
          <ArrowUpRight className="h-3.5 w-3.5" />
        ) : (
          <ArrowDownRight className="h-3.5 w-3.5" />
        )}
      </span>

      {/* Category Name */}
      <span className="text-xs font-semibold text-ink whitespace-nowrap">
        {chip.category}
      </span>

      {/* Amount with Tabular Numerals */}
      <span
        className={cn(
          "text-xs font-bold tnum whitespace-nowrap pl-1 border-l border-black/[0.06]",
          isInflow ? "text-emerald-700" : "text-ink"
        )}
      >
        {isInflow ? "+" : ""}
        {formatCurrency(chip.amount)}
      </span>
    </motion.div>
  );
}

export function CashFlowChips({
  chips = DEFAULT_CHIPS,
  title = "Tactile Cash-Flow Streams",
  subtitle = "Interactive transaction tokens drifting at varied telemetry depths. Hover to repel or drag with inertial spring physics.",
  className,
}: CashFlowChipsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { amount: 0.2 });
  const shouldReduceMotion = useReducedMotion();

  // Pointer position within container for magnetic repel
  const pointerX = useMotionValue(-1000);
  const pointerY = useMotionValue(-1000);

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (shouldReduceMotion || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      pointerX.set(e.clientX - rect.left);
      pointerY.set(e.clientY - rect.top);
    },
    [pointerX, pointerY, shouldReduceMotion]
  );

  const handlePointerLeave = useCallback(() => {
    pointerX.set(-1000);
    pointerY.set(-1000);
  }, [pointerX, pointerY]);

  return (
    <div
      ref={containerRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      className={cn(
        "relative flex flex-col items-center justify-center p-6 sm:p-10 rounded-card border border-black/[0.08] bg-gradient-to-b from-white via-fog/50 to-white shadow-sm overflow-hidden",
        className
      )}
    >
      {/* Background ambient lighting */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[250px] bg-gradient-to-r from-emerald-500/5 via-ember/5 to-indigo-500/5 blur-3xl pointer-events-none -z-10" />

      {/* Header Info */}
      <div className="text-center max-w-lg mb-8 z-10">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-black/[0.06] bg-white px-3 py-0.5 text-[11px] font-semibold text-graphite mb-2.5 shadow-sm">
          <Sparkles className="h-3 w-3 text-ember" />
          <span>Framer Inertia Physics</span>
        </div>
        <h3 className="font-display text-2xl sm:text-3xl text-ink font-medium tracking-tight">
          {title}
        </h3>
        <p className="text-xs sm:text-sm text-graphite mt-1.5 leading-relaxed">
          {subtitle}
        </p>
      </div>

      {/* Floating Chips Canvas */}
      <div className="relative w-full max-w-4xl min-h-[220px] flex flex-wrap items-center justify-center gap-4 sm:gap-6 py-4">
        {chips.map((chip) => (
          <SingleDraggableChip
            key={chip.id}
            chip={chip}
            containerRef={containerRef}
            pointerX={pointerX}
            pointerY={pointerY}
            shouldReduceMotion={shouldReduceMotion}
            isInView={isInView}
          />
        ))}
      </div>

      {/* Instruction Caption */}
      <div className="mt-4 flex items-center gap-3 text-[11px] text-pewter font-medium z-10">
        <span>✨ Drag any chip to test spring inertia</span>
        <span>•</span>
        <span>Cursor proximity applies magnetic repulsion</span>
      </div>
    </div>
  );
}
