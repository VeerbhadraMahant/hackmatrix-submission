"use client";

import { useRef, useCallback } from "react";
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from "framer-motion";
import { Sparkles, CheckCircle2, Shield, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DeviceMockupSectionProps {
  title?: string;
  subtitle?: string;
  className?: string;
}

export function DeviceMockupSection({
  title = "On Every Device, Always in Sync",
  subtitle = "FinPilot operates seamlessly across desktop, tablet, and mobile. Review cash-flow projections on your laptop, or inspect safe-to-spend headroom on the go.",
  className,
}: DeviceMockupSectionProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();

  // Mouse coords normalized (-0.5 to 0.5)
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Parallax offsets with spring physics
  // Laptop layer (subtle depth)
  const laptopX = useSpring(useTransform(mouseX, [-0.5, 0.5], [-8, 8]), { stiffness: 220, damping: 24 });
  const laptopY = useSpring(useTransform(mouseY, [-0.5, 0.5], [-6, 6]), { stiffness: 220, damping: 24 });

  // Phone layer (foreground depth, moving faster)
  const phoneX = useSpring(useTransform(mouseX, [-0.5, 0.5], [16, -16]), { stiffness: 260, damping: 22 });
  const phoneY = useSpring(useTransform(mouseY, [-0.5, 0.5], [14, -14]), { stiffness: 260, damping: 22 });

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (shouldReduceMotion || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      mouseX.set(x);
      mouseY.set(y);
    },
    [mouseX, mouseY, shouldReduceMotion]
  );

  const handlePointerLeave = useCallback(() => {
    mouseX.set(0);
    mouseY.set(0);
  }, [mouseX, mouseY]);

  return (
    <div
      ref={containerRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      className={cn(
        "rounded-card border border-black/[0.08] bg-gradient-to-b from-white via-fog/40 to-white p-6 sm:p-10 shadow-sm flex flex-col items-center justify-center relative overflow-hidden select-none",
        className
      )}
    >
      {/* Background ambient lighting */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[350px] bg-gradient-to-r from-ember/10 via-amber-200/10 to-indigo-500/10 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Header */}
      <div className="text-center max-w-xl mb-12 z-10">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-black/[0.06] bg-white px-3 py-1 text-xs font-semibold text-graphite mb-3 shadow-sm">
          <Sparkles className="h-3.5 w-3.5 text-ember" />
          <span>Cross-Platform Parallax Experience</span>
        </div>
        <h3 className="font-display text-3xl sm:text-4xl text-ink font-medium tracking-tight">
          {title}
        </h3>
        <p className="text-xs sm:text-sm text-graphite mt-2 leading-relaxed">
          {subtitle}
        </p>
      </div>

      {/* Mockups Container */}
      <div className="relative w-full max-w-[880px] h-[400px] sm:h-[480px] md:h-[540px] flex items-center justify-center">
        {/* Layer 1: Laptop Frame (Background) */}
        <motion.div
          style={{
            x: shouldReduceMotion ? 0 : laptopX,
            y: shouldReduceMotion ? 0 : laptopY,
          }}
          className="relative w-[92%] sm:w-[80%] md:w-[720px] aspect-[16/10] rounded-[20px] border-[10px] sm:border-[14px] border-[#181a20] bg-white shadow-[0_25px_60px_-15px_rgba(15,23,42,0.18)] overflow-hidden flex flex-col shrink-0"
        >
          {/* Laptop Camera dot */}
          <div className="absolute top-1.5 left-1/2 -translate-x-1/2 h-1.5 w-1.5 rounded-full bg-sage-deep z-30" />

          {/* Laptop Screen Content (FinPilot Command Center Mockup) */}
          <div className="flex-1 bg-white flex flex-col text-left overflow-hidden">
            {/* Mock Header */}
            <div className="h-9 border-b border-black/[0.06] bg-fog/70 px-4 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="font-display font-bold text-ink ml-2">FinPilot</span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-pewter font-medium">
                <span className="text-ink font-semibold">Dashboard</span>
                <span>Copilot</span>
                <span>Simulate</span>
                <span>Timeline</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-white border border-black/[0.08] font-semibold text-graphite">
                Priya (Bengaluru)
              </span>
            </div>

            {/* Mock Dashboard Body */}
            <div className="p-4 flex flex-col gap-3 flex-1 bg-[#fafbfc]">
              {/* Top row metrics */}
              <div className="grid grid-cols-4 gap-2">
                <div className="p-2 rounded-lg bg-white border border-black/[0.06] shadow-2xs">
                  <span className="text-[9px] uppercase tracking-wider text-pewter block">Net Worth</span>
                  <span className="text-xs font-bold text-ink tnum">₹14,80,000</span>
                </div>
                <div className="p-2 rounded-lg bg-white border border-black/[0.06] shadow-2xs">
                  <span className="text-[9px] uppercase tracking-wider text-pewter block">Monthly In</span>
                  <span className="text-xs font-bold text-emerald-700 tnum">+₹95,000</span>
                </div>
                <div className="p-2 rounded-lg bg-white border border-black/[0.06] shadow-2xs">
                  <span className="text-[9px] uppercase tracking-wider text-pewter block">Monthly Out</span>
                  <span className="text-xs font-bold text-ink tnum">-₹62,600</span>
                </div>
                <div className="p-2 rounded-lg bg-white border border-black/[0.06] shadow-2xs">
                  <span className="text-[9px] uppercase tracking-wider text-pewter block">Health Index</span>
                  <span className="text-xs font-bold text-emerald-700 tnum">81/100</span>
                </div>
              </div>

              {/* Mock Cash-Flow Chart */}
              <div className="flex-1 rounded-xl bg-white border border-black/[0.06] p-3 flex flex-col justify-between">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-semibold text-ink">90-Day Cash-Flow Forecast</span>
                  <span className="text-[9px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                    Zero Shortfall
                  </span>
                </div>
                {/* SVG mock curve */}
                <svg className="w-full h-24" viewBox="0 0 400 90">
                  <path
                    d="M 10 75 C 60 70, 100 65, 150 55 C 200 45, 250 40, 300 28 C 350 20, 380 15, 390 12"
                    fill="none"
                    stroke="#ff5900"
                    strokeWidth="2.5"
                  />
                  <path
                    d="M 10 75 C 60 70, 100 65, 150 55 C 200 45, 250 40, 300 28 C 350 20, 380 15, 390 12 L 390 85 L 10 85 Z"
                    fill="rgba(255, 89, 0, 0.08)"
                  />
                  <line x1="10" y1="85" x2="390" y2="85" stroke="#e5e7eb" strokeWidth="1" />
                </svg>
              </div>
            </div>
          </div>

          {/* Laptop Base Stand Hint */}
          <div className="h-3 w-full bg-[#2a2d34] border-t border-white/10" />
        </motion.div>

        {/* Layer 2: Phone Frame (Floating Foreground Parallax) */}
        <motion.div
          style={{
            x: shouldReduceMotion ? 0 : phoneX,
            y: shouldReduceMotion ? 0 : phoneY,
          }}
          className="absolute -right-2 sm:right-6 md:right-12 bottom-0 sm:bottom-4 w-[170px] sm:w-[220px] aspect-[9/18.5] rounded-[36px] sm:rounded-[42px] border-[8px] sm:border-[10px] border-[#181a20] bg-white shadow-[0_30px_70px_rgba(0,0,0,0.28)] overflow-hidden flex flex-col z-20"
        >
          {/* Phone Dynamic Island / Notch */}
          <div className="absolute top-2 left-1/2 -translate-x-1/2 h-3.5 w-20 rounded-full bg-sage-deep z-30" />

          {/* Phone Screen UI Content */}
          <div className="flex-1 bg-white p-3 pt-7 flex flex-col justify-between text-left">
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-black/[0.04]">
                <span className="text-[10px] font-bold text-ink">FinPilot Mobile</span>
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </div>

              {/* Safe to Spend Header */}
              <div className="mt-3 p-2.5 rounded-xl bg-orange-50/50 border border-ember/20 text-center">
                <span className="text-[9px] uppercase tracking-wider text-pewter font-semibold block">
                  Safe To Spend
                </span>
                <span className="text-sm font-bold text-ink tnum mt-0.5 block">
                  ₹32,400
                </span>
                <span className="text-[8px] text-emerald-600 font-semibold block mt-0.5">
                  No Shortfall (90d)
                </span>
              </div>

              {/* Micro Subscriptions List */}
              <div className="mt-3 flex flex-col gap-1.5">
                <span className="text-[9px] font-bold text-graphite uppercase tracking-wider">
                  Upcoming (7d)
                </span>
                <div className="flex items-center justify-between p-1.5 rounded-lg bg-fog text-[9px]">
                  <span className="font-semibold text-ink">Netflix</span>
                  <span className="font-bold text-ink tnum">-₹649</span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded-lg bg-fog text-[9px]">
                  <span className="font-semibold text-ink">SIP Index</span>
                  <span className="font-bold text-emerald-700 tnum">+₹15,000</span>
                </div>
              </div>
            </div>

            {/* Bottom floating copilot prompt */}
            <div className="p-2 rounded-xl bg-sage text-ink text-[9px] flex items-center justify-between shadow-sm">
              <span>Ask FinPilot...</span>
              <ArrowUpRight className="h-3 w-3 text-ember" />
            </div>
          </div>
        </motion.div>
      </div>

      {/* Feature Pills */}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-xs text-pewter font-medium z-10">
        <span className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
          Real-time double-entry synchronization
        </span>
        <span className="flex items-center gap-1.5">
          <Shield className="h-3.5 w-3.5 text-emerald-600" />
          Independent second-factor TOTP
        </span>
        <span className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
          Adaptive touch & mouse navigation
        </span>
      </div>
    </div>
  );
}
