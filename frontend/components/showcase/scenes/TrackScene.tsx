"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { TRACK_TRANSACTIONS, type TrackTransaction } from "../showcaseData";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { Check, X, CreditCard, ShoppingBag, Laptop, FileText, Briefcase } from "lucide-react";

export function TrackScene() {
  const shouldReduceMotion = useReducedMotion();
  const [transactions, setTransactions] = useState<TrackTransaction[]>(TRACK_TRANSACTIONS);
  const [index, setIndex] = useState(0);
  const [transitionState, setTransitionState] = useState<"idle" | "reviewing">("idle");

  // Fetch real demo transactions from backend
  useEffect(() => {
    let isMounted = true;
    async function loadLiveTransactions() {
      try {
        const queue = await api.reviewQueue("demo-priya", 5);
        if (queue && queue.items && queue.items.length > 0 && isMounted) {
          const mapped: TrackTransaction[] = queue.items.map((tx) => ({
            merchant: tx.merchant,
            account: "HDFC Linked Account",
            amount: formatCurrency(Math.abs(tx.amount)),
            category: (tx.category ? tx.category.charAt(0).toUpperCase() + tx.category.slice(1) : "Miscellaneous") as any,
            tag: (tx.tags && tx.tags.length > 0 ? tx.tags[0] : "Other") as any,
            date: tx.date || "Today",
            notePlaceholder: tx.notes || "Add transaction notes...",
            swipeType: tx.review_status === "skipped" ? "skip" : "reviewed",
          }));
          setTransactions(mapped);
        }
      } catch {
        // Fallback to static data if offline
      }
    }
    loadLiveTransactions();
    return () => {
      isMounted = false;
    };
  }, []);

  const currentTx = transactions[index % transactions.length] || TRACK_TRANSACTIONS[0];

  useEffect(() => {
    if (shouldReduceMotion) return;

    const interval = setInterval(() => {
      setTransitionState("reviewing");

      const timeout = setTimeout(() => {
        setIndex((prev) => (prev + 1) % transactions.length);
        setTransitionState("idle");
      }, 700);

      return () => clearTimeout(timeout);
    }, 2800);

    return () => clearInterval(interval);
  }, [shouldReduceMotion, transactions.length]);

  const categories = [
    { label: "Shopping", icon: ShoppingBag },
    { label: "Electronics", icon: Laptop },
    { label: "Miscellaneous", icon: FileText },
    { label: "Business", icon: Briefcase },
  ] as const;

  const tags = [
    { label: "Subscription", dotColor: "bg-rose-500" },
    { label: "Home", dotColor: "bg-teal-500" },
    { label: "Tax", dotColor: "bg-amber-500" },
    { label: "Food", dotColor: "bg-orange-500" },
    { label: "Other", dotColor: "bg-indigo-500" },
  ] as const;

  return (
    <div className="relative flex flex-col items-center justify-center w-full max-w-[340px] select-none">
      {/* Phone-style Container */}
      <div className="relative w-full bg-white rounded-[22px] shadow-[0_18px_45px_rgba(26,24,20,0.09)] border border-[#E9E4DC] p-5 sm:p-6 overflow-hidden">
        {/* Header: Merchant + Amount */}
        <div className="flex items-start justify-between pb-4 border-b border-black/[0.05]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-orange-50 border border-[#EA5B14]/20 flex items-center justify-center text-[#EA5B14] shadow-xs">
              <CreditCard className="w-5 h-5" />
            </div>
            <div>
              <div className="font-semibold text-sm sm:text-base text-[#1c1b18] tracking-tight leading-snug">
                {currentTx.merchant}
              </div>
              <div className="text-[11px] text-[#78756d] font-medium flex items-center gap-1 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                {currentTx.account}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="font-tabular font-bold text-base sm:text-lg text-[#1c1b18]">
              {currentTx.amount}
            </div>
            <div className="text-[10px] text-[#938f87] uppercase tracking-wider font-medium">
              Cleared
            </div>
          </div>
        </div>

        {/* Section: Category */}
        <div className="mt-4">
          <label className="text-[11px] font-semibold tracking-wider text-[#8b877f] uppercase block mb-2">
            Category
          </label>
          <div className="grid grid-cols-2 gap-2">
            {categories.map((cat) => {
              const isSelected =
                currentTx.category?.toLowerCase() === cat.label.toLowerCase() ||
                (cat.label === "Miscellaneous" && !["Shopping", "Electronics", "Business"].includes(currentTx.category));
              const Icon = cat.icon;
              return (
                <div
                  key={cat.label}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-colors duration-200 border ${
                    isSelected
                      ? "bg-[#FDECE2] text-[#EA5B14] border-[#EA5B14] shadow-xs font-semibold"
                      : "bg-[#F7F5F0] text-[#5c5850] border-transparent"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 opacity-80" />
                  <span>{cat.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section: Tags */}
        <div className="mt-4">
          <label className="text-[11px] font-semibold tracking-wider text-[#8b877f] uppercase block mb-2">
            Tags
          </label>
          <div className="grid grid-cols-2 gap-2">
            {tags.slice(0, 4).map((t) => {
              const isSelected = currentTx.tag?.toLowerCase() === t.label.toLowerCase();
              return (
                <div
                  key={t.label}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-colors duration-200 border ${
                    isSelected
                      ? "bg-[#FDECE2] text-[#EA5B14] border-[#EA5B14] shadow-xs font-semibold"
                      : "bg-[#F7F5F0] text-[#5c5850] border-transparent"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${t.dotColor}`} />
                  <span>{t.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Note Placeholder */}
        <div className="mt-4 p-2.5 rounded-xl bg-[#FAF9F5] border border-black/[0.04] text-xs text-[#827e75] italic">
          {currentTx.notePlaceholder}
        </div>

        {/* Swipe Review Animation Overlay */}
        <AnimatePresence>
          {transitionState === "reviewing" && !shouldReduceMotion && (
            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.1 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className={`absolute inset-0 flex flex-col items-center justify-center backdrop-blur-xs z-20 ${
                currentTx.swipeType === "reviewed"
                  ? "bg-emerald-500/15 text-emerald-700"
                  : "bg-orange-500/15 text-[#EA5B14]"
              }`}
            >
              <div className="w-14 h-14 rounded-full bg-white shadow-lg flex items-center justify-center mb-2">
                {currentTx.swipeType === "reviewed" ? (
                  <Check className="w-7 h-7 text-emerald-600" />
                ) : (
                  <X className="w-7 h-7 text-[#EA5B14]" />
                )}
              </div>
              <span className="font-bold text-xs uppercase tracking-widest bg-white/90 px-3 py-1 rounded-full shadow-xs">
                {currentTx.swipeType === "reviewed" ? "Reviewed" : "Skipped"}
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
