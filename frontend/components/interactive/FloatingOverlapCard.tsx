"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useInView,
  useReducedMotion,
} from "framer-motion";
import { Coffee, ShoppingBag, AlertCircle, ArrowUpRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";

export interface FloatingCardItem {
  id: string;
  icon: "coffee" | "shopping" | "alert" | "custom";
  title: string;
  subtext: string;
  amount: number;
  isCount?: boolean; // e.g. "8x" orders instead of currency
  countSuffix?: string;
  statusTone?: "positive" | "neutral" | "warning";
}

export interface FloatingOverlapCardProps {
  badge?: string;
  headline?: string;
  bodyText?: string;
  actionText?: string;
  onAction?: () => void;
  items?: FloatingCardItem[];
  className?: string;
}

const DEFAULT_ITEMS: FloatingCardItem[] = [
  {
    id: "coffee",
    icon: "coffee",
    title: "Dining & Coffee Budget",
    subtext: "₹650 under your 30-day pace",
    amount: 2450,
    statusTone: "positive",
  },
  {
    id: "shopping",
    icon: "shopping",
    title: "Amazon & E-Commerce",
    subtext: "Averaging ₹520 per transaction",
    amount: 8,
    isCount: true,
    countSuffix: " orders",
    statusTone: "neutral",
  },
  {
    id: "alert",
    icon: "alert",
    title: "Balance & Gap Alert",
    subtext: "Surplus healthy • Safe to save ₹12,000",
    amount: 32400,
    statusTone: "warning",
  },
];

/** Number count-up helper */
function CountUpNumber({
  value,
  isCount = false,
  countSuffix = "",
}: {
  value: number;
  isCount?: boolean;
  countSuffix?: string;
}) {
  const [animatedValue, setAnimatedValue] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true });
  const shouldReduceMotion = useReducedMotion();
  // Reduced-motion users get the final value straight away (no animation).
  const displayValue = shouldReduceMotion ? value : animatedValue;

  useEffect(() => {
    if (shouldReduceMotion) return;

    const duration = 1000; // ms
    const startTime = performance.now();
    let frame = 0;

    function update(time: number) {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setAnimatedValue(Math.round(ease * value));

      if (progress < 1) {
        frame = requestAnimationFrame(update);
      }
    }

    frame = requestAnimationFrame(update);
    return () => cancelAnimationFrame(frame);
  }, [isInView, value, shouldReduceMotion]);

  return (
    <span ref={ref} className="font-tabular tnum font-semibold text-ink">
      {isCount ? `${displayValue}${countSuffix}` : formatCurrency(displayValue)}
    </span>
  );
}

export function FloatingOverlapCard({
  badge = "Autonomous Spend Oversight",
  headline = "Stay on top of your everyday spending.",
  bodyText = "FinPilot continuously tags transactions, detects category pace shifts, and computes your safe-to-spend ceiling so you are never caught unprepared.",
  actionText = "Track My Spending",
  onAction,
  items = DEFAULT_ITEMS,
  className,
}: FloatingOverlapCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { amount: 0.2 });
  const shouldReduceMotion = useReducedMotion();

  // 3D Tilt Motion Values
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  // Springs for smooth snappy tilt recovery
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [6, -6]), {
    stiffness: 280,
    damping: 24,
  });
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-6, 6]), {
    stiffness: 280,
    damping: 24,
  });

  // Spotlight radial highlight position
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (shouldReduceMotion || !cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;

      // Normalized coordinates from -0.5 to 0.5
      const mouseXRel = (e.clientX - rect.left) / width - 0.5;
      const mouseYRel = (e.clientY - rect.top) / height - 0.5;

      x.set(mouseXRel);
      y.set(mouseYRel);

      // Local spotlight coordinates
      mouseX.set(e.clientX - rect.left);
      mouseY.set(e.clientY - rect.top);
    },
    [x, y, mouseX, mouseY, shouldReduceMotion]
  );

  const handlePointerLeave = useCallback(() => {
    x.set(0);
    y.set(0);
  }, [x, y]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center py-10",
        className
      )}
    >
      {/* Left Column: Contextual Copy & Action */}
      <div className="lg:col-span-5 flex flex-col items-start gap-5 z-10">
        {badge && (
          <div className="inline-flex items-center gap-1.5 rounded-full border border-black/[0.08] bg-fog/80 px-3 py-1 text-xs font-semibold text-graphite shadow-sm backdrop-blur-md">
            <Sparkles className="h-3.5 w-3.5 text-ember" />
            <span>{badge}</span>
          </div>
        )}

        <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl text-ink leading-[1.15] tracking-tight">
          {headline}
        </h2>

        <p className="text-sm sm:text-base text-graphite leading-relaxed max-w-lg">
          {bodyText}
        </p>

        <button
          type="button"
          onClick={onAction}
          className="mt-2 inline-flex items-center gap-2 rounded-chip bg-sage text-ink px-5 py-3 text-sm font-semibold hover:bg-carbon active:scale-[0.98] transition-all shadow-[0_2px_10px_rgba(0,0,0,0.15)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ember/40 cursor-pointer"
        >
          <span>{actionText}</span>
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </div>

      {/* Right Column: Rounded Graphic Frame with Overlapping Floating Card */}
      <div className="lg:col-span-7 relative flex items-center justify-center lg:justify-end min-h-[420px] sm:min-h-[480px]">
        {/* Abstract Rounded Frame (Layer 1) */}
        <div className="relative w-full max-w-[460px] h-[340px] sm:h-[400px] rounded-[32px] overflow-hidden border border-black/[0.08] bg-gradient-to-tr from-[#f3f4f6] via-[#f9fafb] to-[#f4f2ee] shadow-[0_20px_50px_-20px_rgba(15,23,42,0.08)]">
          {/* Subtle Abstract Wave / Mesh Pattern */}
          <div className="absolute inset-0 opacity-40 bg-[radial-gradient(#090a0f_0.75px,transparent_0.75px)] [background-size:16px_16px]" />

          {/* Abstract Geometric Warm Glow */}
          <div className="absolute -top-12 -right-12 w-64 h-64 rounded-full bg-gradient-to-br from-ember/15 to-amber-200/20 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-8 -left-8 w-60 h-60 rounded-full bg-gradient-to-tr from-emerald-100/30 to-teal-50/20 blur-2xl pointer-events-none" />

          {/* Decorative frame badge */}
          <div className="absolute top-5 right-5 flex items-center gap-2 px-3 py-1 rounded-full bg-white/80 border border-black/[0.06] backdrop-blur-md text-[11px] font-medium text-graphite shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span>Live Account Link</span>
          </div>
        </div>

        {/* Floating Overlap Card (Layer 2) */}
        <motion.div
          ref={cardRef}
          style={{
            rotateX: shouldReduceMotion ? 0 : rotateX,
            rotateY: shouldReduceMotion ? 0 : rotateY,
            transformStyle: "preserve-3d",
          }}
          animate={
            shouldReduceMotion || !isInView
              ? { y: 0, rotate: 0 }
              : {
                  y: [0, -10, 0],
                  rotate: [0, 0.6, 0],
                }
          }
          transition={{
            y: { duration: 8, repeat: Infinity, ease: "easeInOut" },
            rotate: { duration: 8, repeat: Infinity, ease: "easeInOut" },
          }}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          className="absolute left-1/2 -translate-x-1/2 lg:left-auto lg:translate-x-0 lg:-left-6 top-1/2 -translate-y-1/2 w-[92%] sm:w-[380px] rounded-card border border-black/[0.08] bg-white/95 backdrop-blur-xl p-4 sm:p-6 shadow-[0_20px_45px_-10px_rgba(15,23,42,0.12),0_1px_3px_rgba(15,23,42,0.04)] will-change-transform touch-none"
        >
          {/* Card Header */}
          <div className="flex items-center justify-between pb-3.5 border-b border-black/[0.06]">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-ember" />
              <span className="text-xs font-bold uppercase tracking-wider text-ink">
                Real-Time Telemetry
              </span>
            </div>
            <span className="text-[10px] text-pewter font-medium">Just now</span>
          </div>

          {/* Rows */}
          <div className="flex flex-col divide-y divide-black/[0.04] mt-1">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between gap-3 py-3.5 first:pt-3 last:pb-1 group hover:bg-fog/40 px-1 rounded-chip transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-full border shrink-0 transition-transform group-hover:scale-105",
                      item.statusTone === "positive" && "bg-emerald-50 text-emerald-700 border-emerald-200",
                      item.statusTone === "warning" && "bg-amber-50 text-amber-700 border-amber-200",
                      item.statusTone === "neutral" && "bg-fog text-graphite border-black/[0.06]"
                    )}
                  >
                    {item.icon === "coffee" && <Coffee className="h-4 w-4" />}
                    {item.icon === "shopping" && <ShoppingBag className="h-4 w-4" />}
                    {item.icon === "alert" && <AlertCircle className="h-4 w-4" />}
                    {item.icon === "custom" && <Sparkles className="h-4 w-4" />}
                  </div>

                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-ink leading-tight">
                      {item.title}
                    </span>
                    <span className="text-[11px] text-pewter mt-0.5 line-clamp-1">
                      {item.subtext}
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-sm font-semibold text-ink tnum">
                    <CountUpNumber
                      value={item.amount}
                      isCount={item.isCount}
                      countSuffix={item.countSuffix}
                    />
                  </div>
                  {item.statusTone === "positive" && (
                    <span className="text-[10px] text-emerald-600 font-semibold block">Under target</span>
                  )}
                  {item.statusTone === "warning" && (
                    <span className="text-[10px] text-amber-600 font-semibold block">Safe zone</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
