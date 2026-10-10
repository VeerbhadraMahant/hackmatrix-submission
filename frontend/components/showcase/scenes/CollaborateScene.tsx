"use client";

import React, { useState, useEffect } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { COLLABORATE_DATA, type CollaborateData } from "../showcaseData";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { Wallet, Landmark, TrendingUp, ShieldCheck } from "lucide-react";

export function CollaborateScene() {
  const shouldReduceMotion = useReducedMotion();
  const [collabData, setCollabData] = useState<CollaborateData>(COLLABORATE_DATA);
  const [cycleKey, setCycleKey] = useState(0);

  // Fetch real live household data from backend
  useEffect(() => {
    let isMounted = true;
    async function loadLiveHousehold() {
      try {
        const hh = await api.household("demo-priya");
        if (hh && hh.household && isMounted) {
          const mappedUsers = hh.members.slice(0, 2).map((m, idx) => ({
            name: m.display_name || (idx === 0 ? "Priya" : "Arjun"),
            initials: m.avatar_letter || m.display_name?.slice(0, 1) || "P",
            avatarSrc: idx === 0 ? "/images/priya-avatar.jpg" : "/images/arjun-avatar.jpg",
          }));

          const accounts = await api.accounts("demo-priya");
          const mappedAccounts = accounts.slice(0, 3).map((acc, idx) => ({
            name: acc.name,
            institution: acc.name.includes("HDFC") ? "HDFC Bank" : acc.name.includes("ICICI") ? "ICICI Bank" : "Groww",
            balance: formatCurrency(acc.balance),
            updated: "Synced live",
            iconBg: idx === 0 ? "bg-emerald-50 text-emerald-600" : idx === 1 ? "bg-sky-50 text-sky-600" : "bg-purple-50 text-purple-600",
            iconColor: idx === 0 ? "#059669" : idx === 1 ? "#0284c7" : "#7c3aed",
          }));

          setCollabData({
            users: mappedUsers,
            netWorth: formatCurrency(hh.net_worth_summary.total_net_worth),
            accounts: mappedAccounts.length > 0 ? mappedAccounts : COLLABORATE_DATA.accounts,
          });

        }
      } catch {
        // Fallback to static data
      }
    }
    loadLiveHousehold();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (shouldReduceMotion) return;

    // Loop cycle: avatars join + net worth card slides up + accounts appear + hold = ~5s
    const timer = setInterval(() => {
      setCycleKey((prev) => prev + 1);
    }, 5200);

    return () => clearInterval(timer);
  }, [shouldReduceMotion]);

  const getAccountIcon = (name: string) => {
    if (name.includes("Savings") || name.includes("Joint")) return <Wallet className="w-4 h-4 text-emerald-600" />;
    if (name.includes("Checking") || name.includes("Bank")) return <Landmark className="w-4 h-4 text-sky-600" />;
    return <TrendingUp className="w-4 h-4 text-purple-600" />;
  };

  return (
    <div className="relative flex flex-col items-center justify-center w-full max-w-[340px] py-4 select-none min-h-[460px]">
      <div key={cycleKey} className="w-full flex flex-col items-center">
        {/* Avatars Card (Enters First) */}
        <motion.div
          initial={
            shouldReduceMotion
              ? { opacity: 1, scale: 1 }
              : { opacity: 0, scale: 0.88, y: 15 }
          }
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          className="z-10 bg-white rounded-[20px] px-6 py-3.5 shadow-[0_12px_32px_rgba(26,24,20,0.08)] border border-[#ECE7DF] flex items-center gap-6"
        >
          {collabData.users.map((user, idx) => (
            <motion.div
              key={user.name}
              initial={
                shouldReduceMotion
                  ? { x: 0 }
                  : { x: idx === 0 ? -12 : 12, opacity: 0 }
              }
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.15 + idx * 0.1, ease: "easeOut" }}
              className="flex flex-col items-center"
            >
              <div className="relative w-12 h-12 rounded-full p-[2px] bg-gradient-to-tr from-[#EA5B14] to-[#f99252] shadow-sm">
                <div className="w-full h-full rounded-full overflow-hidden bg-[#FAF7F2] flex items-center justify-center">
                  <span className="font-bold text-sm text-[#EA5B14]">
                    {user.initials}
                  </span>
                </div>
              </div>
              <span className="mt-1.5 text-xs font-semibold text-[#292621]">
                {user.name}
              </span>
            </motion.div>
          ))}
        </motion.div>

        {/* Net Worth & Accounts Card (Slides Up Tucked Beneath Avatars Card) */}
        <motion.div
          initial={
            shouldReduceMotion
              ? { opacity: 1, y: 0 }
              : { opacity: 0, y: 35, scale: 0.95 }
          }
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
          className="w-full -mt-3 pt-6 pb-5 px-5 bg-white rounded-[22px] shadow-[0_16px_40px_rgba(26,24,20,0.08)] border border-[#ECE7DF] z-0"
        >
          {/* Net Worth Header */}
          <div className="text-center pb-4 border-b border-black/[0.05]">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[#8a867d]">
              Total Household Net Worth
            </div>
            <div className="font-display text-2xl sm:text-3xl font-bold text-[#1c1b18] mt-0.5 tracking-tight font-tabular">
              {collabData.netWorth}
            </div>
            <div className="inline-flex items-center gap-1 mt-1 text-[11px] text-emerald-600 font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Real-Time Bi-Directional Sync</span>
            </div>
          </div>

          {/* Staggered Account Rows */}
          <div className="mt-3.5 flex flex-col gap-2.5">
            {collabData.accounts.map((acc, idx) => (
              <motion.div
                key={acc.name}
                initial={
                  shouldReduceMotion
                    ? { opacity: 1, x: 0 }
                    : { opacity: 0, x: -14 }
                }
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  duration: 0.38,
                  delay: shouldReduceMotion ? 0 : 0.65 + idx * 0.28,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="flex items-center justify-between p-2.5 rounded-xl bg-[#FAF9F5] border border-black/[0.03] hover:bg-[#F5F2EB] transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${acc.iconBg}`}>
                    {getAccountIcon(acc.name)}
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-[#1c1b18] leading-tight">
                      {acc.name}
                    </div>
                    <div className="text-[10px] text-[#837f76]">
                      {acc.institution} • {acc.updated}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="font-tabular font-semibold text-xs sm:text-sm text-[#1c1b18]">
                    {acc.balance}
                  </div>
                  <div className="text-[10px] text-emerald-600 font-medium">
                    Active
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
