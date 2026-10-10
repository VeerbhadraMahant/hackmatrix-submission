"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { motion, useReducedMotion } from "framer-motion";
import { PLAN_GOALS, type PlanGoal } from "../showcaseData";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { Shield, Palmtree, Car as CarIcon, GraduationCap, Target } from "lucide-react";

export function PlanScene() {
  const shouldReduceMotion = useReducedMotion();
  const [goals, setGoals] = useState<PlanGoal[]>(PLAN_GOALS);
  const [cycleKey, setCycleKey] = useState(0);

  // Fetch real goals data from backend
  useEffect(() => {
    let isMounted = true;
    async function loadLiveGoals() {
      try {
        const liveGoals = await api.goals("demo-priya");
        if (liveGoals && liveGoals.length > 0 && isMounted) {
          const mapped: PlanGoal[] = liveGoals.slice(0, 3).map((gp) => {
            const g = gp.goal;
            const coverKey = g.cover_key || "emergency_fund";
            return {
              id: g.id,
              title: g.name,
              current: `${formatCurrency(g.current_amount)} / ${formatCurrency(g.target_amount)}`,
              target: formatCurrency(g.target_amount),
              percent: g.target_amount > 0 ? Math.min(100, Math.round((g.current_amount / g.target_amount) * 100)) : 0,
              institution: "HDFC Primary Reserve",
              tag: "Auto-Track Active",
              image: `/goal-covers/${coverKey}.svg`,
            };
          });
          setGoals(mapped);
        }

      } catch {
        // Fallback to static goals
      }
    }
    loadLiveGoals();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (shouldReduceMotion) return;

    // Loop cycle: 3 cards stagger in (~1.2s) + hold (~3.6s) = ~4.8s total
    const timer = setInterval(() => {
      setCycleKey((prev) => prev + 1);
    }, 5000);

    return () => clearInterval(timer);
  }, [shouldReduceMotion]);

  const getInstitutionLogo = (title: string) => {
    const lower = title.toLowerCase();
    if (lower.includes("emergency") || lower.includes("reserve") || lower.includes("safety")) {
      return (
        <div className="w-6 h-6 rounded-full bg-emerald-600 flex items-center justify-center text-white text-[10px] font-bold shadow-xs">
          <Shield className="w-3.5 h-3.5" />
        </div>
      );
    }
    if (lower.includes("vacation") || lower.includes("travel") || lower.includes("trip")) {
      return (
        <div className="w-6 h-6 rounded-full bg-cyan-700 flex items-center justify-center text-white text-[10px] font-bold shadow-xs">
          <Palmtree className="w-3.5 h-3.5" />
        </div>
      );
    }
    if (lower.includes("car") || lower.includes("ev") || lower.includes("vehicle")) {
      return (
        <div className="w-6 h-6 rounded-full bg-orange-600 flex items-center justify-center text-white text-[10px] font-bold shadow-xs">
          <CarIcon className="w-3.5 h-3.5" />
        </div>
      );
    }
    if (lower.includes("education") || lower.includes("school")) {
      return (
        <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-white text-[10px] font-bold shadow-xs">
          <GraduationCap className="w-3.5 h-3.5" />
        </div>
      );
    }
    return (
      <div className="w-6 h-6 rounded-full bg-rose-600 flex items-center justify-center text-white text-[10px] font-bold shadow-xs">
        <Target className="w-3.5 h-3.5" />
      </div>
    );
  };

  return (
    <div className="relative flex flex-col items-center justify-center w-full max-w-[320px] py-2 select-none min-h-[460px]">
      <div key={cycleKey} className="w-full flex flex-col gap-3.5">
        {goals.map((goal, idx) => {
          const delay = shouldReduceMotion ? 0 : idx * 0.32;

          return (
            <motion.div
              key={goal.id}
              initial={
                shouldReduceMotion
                  ? { opacity: 1, y: 0 }
                  : { opacity: 0, y: 30, scale: 0.96 }
              }
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{
                duration: 0.45,
                delay,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="bg-white rounded-[18px] shadow-[0_10px_28px_rgba(26,24,20,0.07)] border border-[#ECE7DF] overflow-hidden"
            >
              {/* Photo Header */}
              <div className="relative h-20 sm:h-22 w-full bg-[#EAE5DC] overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={goal.image}
                  alt={goal.title}
                  className="w-full h-full object-cover"
                  loading="eager"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = "none";
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />
              </div>

              {/* Card Body */}
              <div className="p-3.5 sm:p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h4 className="font-semibold text-xs sm:text-sm text-[#1c1b18] tracking-tight">
                      {goal.title}
                    </h4>
                    <div className="font-tabular font-bold text-xs sm:text-sm text-[#1c1b18] mt-0.5">
                      {goal.current}
                    </div>
                  </div>
                  <div>{getInstitutionLogo(goal.title)}</div>
                </div>

                {/* Orange Progress Bar (Frame 12) */}
                <div className="w-full h-2 bg-[#EFECE6] rounded-full overflow-hidden relative mt-1.5">
                  <motion.div
                    initial={
                      shouldReduceMotion
                        ? { width: `${goal.percent}%` }
                        : { width: 0 }
                    }
                    animate={{ width: `${goal.percent}%` }}
                    transition={{
                      duration: 0.8,
                      delay: delay + 0.15,
                      ease: [0.16, 1, 0.3, 1],
                    }}
                    className="h-full bg-[#EA5B14] rounded-full"
                  />
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
