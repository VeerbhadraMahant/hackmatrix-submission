"use client";

import React, { useState, useEffect } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { BUDGET_ITEMS, type BudgetItem } from "../showcaseData";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { ShoppingCart, Utensils, ShoppingBag, Car, Film, Sparkles } from "lucide-react";

export function BudgetScene() {
  const shouldReduceMotion = useReducedMotion();
  const [budgetItems, setBudgetItems] = useState<BudgetItem[]>(BUDGET_ITEMS);
  const [cycleKey, setCycleKey] = useState(0);

  // Fetch real budget data from backend
  useEffect(() => {
    let isMounted = true;
    async function loadLiveBudgets() {
      try {
        const statuses = await api.budgetStatus("demo-priya");
        if (statuses && statuses.length > 0 && isMounted) {
          const colorMap: Record<string, string> = {
            dining: "#0D9488",
            groceries: "#10B981",
            transport: "#EA580C",
            shopping: "#D946EF",
            subscriptions: "#6366F1",
          };

          const iconMap: Record<string, "grocery" | "dining" | "shopping" | "fitness"> = {
            groceries: "grocery",
            dining: "dining",
            shopping: "shopping",
            transport: "fitness",
            subscriptions: "fitness",
          };

          const mapped: BudgetItem[] = statuses.slice(0, 4).map((bs) => {
            const cat = String(bs.category).toLowerCase();
            const effectiveLimit = bs.total_available || (bs.monthly_limit + (bs.rollover_amount || 0));
            return {
              id: cat,
              name: `${cat.charAt(0).toUpperCase() + cat.slice(1)} Envelope`,
              spent: formatCurrency(bs.spent_so_far),
              total: formatCurrency(effectiveLimit),
              percent: Math.min(100, Math.round((bs.spent_so_far / Math.max(1, effectiveLimit)) * 100)),
              colorClass: colorMap[cat] || "#FF5900",
              iconType: iconMap[cat] || "grocery",
            };
          });
          setBudgetItems(mapped);
        }
      } catch {
        // Fallback to default mock items
      }
    }
    loadLiveBudgets();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (shouldReduceMotion) return;

    // Loop cycle: 4 cards stagger in (~1.6s) + hold (~2.8s) = ~4.4s total per loop
    const timer = setInterval(() => {
      setCycleKey((prev) => prev + 1);
    }, 4500);

    return () => clearInterval(timer);
  }, [shouldReduceMotion]);

  const getIcon = (type: string) => {
    switch (type) {
      case "grocery":
        return <ShoppingCart className="w-4 h-4 text-emerald-600" />;
      case "dining":
        return <Utensils className="w-4 h-4 text-teal-600" />;
      case "shopping":
        return <ShoppingBag className="w-4 h-4 text-fuchsia-600" />;
      case "fitness":
        return <Car className="w-4 h-4 text-amber-600" />;
      default:
        return <ShoppingCart className="w-4 h-4 text-emerald-600" />;
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center w-full max-w-[340px] py-4 select-none min-h-[460px]">
      <div key={cycleKey} className="w-full flex flex-col gap-3.5">
        {budgetItems.map((item, idx) => {
          const delay = shouldReduceMotion ? 0 : idx * 0.42;

          return (
            <motion.div
              key={item.id}
              initial={
                shouldReduceMotion
                  ? { opacity: 1, y: 0 }
                  : { opacity: 0, y: 24, scale: 0.96 }
              }
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{
                duration: 0.45,
                delay,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="bg-white rounded-[18px] p-4 sm:p-4.5 shadow-[0_10px_28px_rgba(26,24,20,0.07)] border border-[#ECE7DF] relative overflow-hidden"
            >
              <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center gap-2.5">
                  <div
                    className="w-8 h-8 rounded-xl flex items-center justify-center shadow-2xs"
                    style={{ backgroundColor: `${item.colorClass}15` }}
                  >
                    {getIcon(item.iconType)}
                  </div>
                  <span className="font-medium text-xs sm:text-sm text-[#1f1e1a] tracking-tight">
                    {item.name}
                  </span>
                </div>

                <div className="text-right">
                  <span className="font-tabular font-semibold text-xs sm:text-sm text-[#1f1e1a]">
                    {item.spent}
                  </span>
                  <span className="font-tabular text-[11px] text-[#858177] ml-1">
                    / {item.total}
                  </span>
                </div>
              </div>

              {/* Progress Bar Track */}
              <div className="w-full h-2 bg-[#EFECE6] rounded-full overflow-hidden relative">
                <motion.div
                  initial={shouldReduceMotion ? { width: `${item.percent}%` } : { width: 0 }}
                  animate={{ width: `${item.percent}%` }}
                  transition={{
                    duration: 0.75,
                    delay: delay + 0.15,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: item.colorClass }}
                />
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
