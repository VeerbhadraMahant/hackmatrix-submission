"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  LayoutDashboard,
  ReceiptText,
  PieChart,
  Target,
  Users,
  Bot,
  SlidersHorizontal,
  FileSpreadsheet,
  FileText,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  Coins,
  User,
  PlusCircle,
  X,
  Keyboard,
  ListChecks,
} from "lucide-react";
import { useUserId } from "@/lib/hooks";
import { DEMO_PERSONAS, isDemoUserId, setUserId } from "@/lib/user";
import { useCurrency, CURRENCIES, type CurrencyCode } from "@/lib/currency";
import { triggerConfetti } from "@/components/ui/Confetti";

interface CommandItem {
  id: string;
  group: "navigation" | "actions" | "personas" | "currency";
  label: string;
  sublabel?: string;
  icon: React.ComponentType<{ className?: string }>;
  shortcut?: string;
  badge?: string;
  onSelect: () => void;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();
  const userId = useUserId();
  const { currency, setCurrency } = useCurrency();
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Keyboard shortcut listener: Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Custom event trigger
  useEffect(() => {
    const handleOpen = () => setOpen(true);
    window.addEventListener("finpilot:open-command-palette", handleOpen);
    return () => window.removeEventListener("finpilot:open-command-palette", handleOpen);
  }, []);

  // Auto focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  }, [open]);

  const allItems: CommandItem[] = useMemo(() => {
    const items: CommandItem[] = [
      // Navigation
      {
        id: "nav-dashboard",
        group: "navigation",
        label: "Dashboard",
        sublabel: "Overview, telemetry & net worth",
        icon: LayoutDashboard,
        shortcut: "G D",
        onSelect: () => router.push("/dashboard"),
      },
      {
        id: "nav-transactions",
        group: "navigation",
        label: "Transactions Ledger & Review",
        sublabel: "Review inbox, categorize & tags",
        icon: ReceiptText,
        shortcut: "G T",
        onSelect: () => router.push("/transactions"),
      },
      {
        id: "nav-budgets",
        group: "navigation",
        label: "Budgets & Envelopes",
        sublabel: "Rollover surplus & overspend alerts",
        icon: PieChart,
        shortcut: "G B",
        onSelect: () => router.push("/budgets"),
      },
      {
        id: "nav-goals",
        group: "navigation",
        label: "Financial Goals & Targets",
        sublabel: "Milestones, artwork & required monthly pace",
        icon: Target,
        shortcut: "G G",
        onSelect: () => router.push("/goals"),
      },
      {
        id: "nav-household",
        group: "navigation",
        label: "Household Co-Pilot Hub",
        sublabel: "Shared wealth split, partner invites & settlement",
        icon: Users,
        shortcut: "G H",
        onSelect: () => router.push("/household"),
      },
      {
        id: "nav-copilot",
        group: "navigation",
        label: "AI Wealth Advisor",
        sublabel: "Autonomous financial intelligence & advice",
        icon: Bot,
        shortcut: "G C",
        onSelect: () => router.push("/copilot"),
      },
      {
        id: "nav-simulate",
        group: "navigation",
        label: "Forecast & Scenario Simulator",
        sublabel: "Monte-Carlo projections & income shocks",
        icon: SlidersHorizontal,
        shortcut: "G S",
        onSelect: () => router.push("/simulate"),
      },
      {
        id: "nav-plan",
        group: "navigation",
        label: "Financial Plan",
        sublabel: "6-month constrained plan with probabilistic forecast",
        icon: ListChecks,
        shortcut: "G N",
        onSelect: () => router.push("/plan"),
      },
      {
        id: "nav-tax",
        group: "navigation",
        label: "Tax Analytics & Deductions",
        sublabel: "Regime analysis & 80C deductions",
        icon: FileSpreadsheet,
        shortcut: "G X",
        onSelect: () => router.push("/tax"),
      },
      {
        id: "nav-statement",
        group: "navigation",
        label: "Executive Statement Export",
        sublabel: "Printable PDF & financial summary",
        icon: FileText,
        shortcut: "G P",
        onSelect: () => router.push("/statement"),
      },
      {
        id: "nav-security",
        group: "navigation",
        label: "Security & Audit Logs",
        sublabel: "Tamper-proof mutation logs & RLS policies",
        icon: ShieldCheck,
        shortcut: "G L",
        onSelect: () => router.push("/security"),
      },

      // Quick Actions
      {
        id: "action-review",
        group: "actions",
        label: "Open Review Queue",
        sublabel: "Process unreviewed transactions",
        icon: ReceiptText,
        badge: "Action",
        onSelect: () => router.push("/transactions"),
      },
      {
        id: "action-budget",
        group: "actions",
        label: "Manage Budget Envelopes",
        sublabel: "Configure rollover & notifications",
        icon: PlusCircle,
        badge: "Action",
        onSelect: () => router.push("/budgets"),
      },
      {
        id: "action-invite",
        group: "actions",
        label: "Invite Partner to Household",
        sublabel: "Generate secure token invite",
        icon: Users,
        badge: "Action",
        onSelect: () => router.push("/household"),
      },
      {
        id: "action-confetti",
        group: "actions",
        label: "Celebrate Milestone!",
        sublabel: "Trigger celebratory particle burst",
        icon: Sparkles,
        badge: "Fun",
        onSelect: () => triggerConfetti({ count: 80 }),
      },
    ];

    // Personas
    if (isDemoUserId(userId)) {
      DEMO_PERSONAS.forEach((p) => {
        items.push({
          id: `persona-${p.id}`,
          group: "personas",
          label: `Switch Persona: ${p.label}`,
          sublabel: p.id === "demo-priya" ? "Bengaluru • ₹95k/mo" : p.id === "demo-arjun" ? "Mumbai • ₹160k/mo" : "Pune • ₹42k/mo",
          icon: User,
          badge: userId === p.id ? "Active" : undefined,
          onSelect: () => setUserId(p.id),
        });
      });
    }

    // Currencies
    (Object.keys(CURRENCIES) as CurrencyCode[]).forEach((code) => {
      const c = CURRENCIES[code];
      items.push({
        id: `currency-${code}`,
        group: "currency",
        label: `Set Currency: ${c.code} (${c.symbol}) — ${c.label}`,
        sublabel: `Rate: ${c.rateFromINR} × INR`,
        icon: Coins,
        badge: currency === code ? "Selected" : undefined,
        onSelect: () => setCurrency(code),
      });
    });

    return items;
  }, [router, userId, currency, setCurrency]);

  const filteredItems = useMemo(() => {
    if (!query.trim()) return allItems;
    const q = query.toLowerCase().trim();
    return allItems.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.sublabel?.toLowerCase().includes(q) ||
        item.group.toLowerCase().includes(q)
    );
  }, [allItems, query]);

  // Handle keyboard navigation within list
  const handleKeyDownInMenu = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].onSelect();
        setOpen(false);
      }
    }
  };

  const groupLabels: Record<string, string> = {
    navigation: "Navigation & Views",
    actions: "Quick Actions",
    personas: "Demo Personas",
    currency: "Global Currency & Formatting",
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-16 sm:pt-24 px-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            className="fixed inset-0 bg-sage/60 backdrop-blur-md transition-opacity"
            aria-hidden="true"
          />

          {/* Modal Card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="relative w-full max-w-xl rounded-2xl bg-paper shadow-2xl border border-mist overflow-hidden z-10 flex flex-col max-h-[75vh]"
            role="dialog"
            aria-modal="true"
            aria-label="FinPilot Command Palette"
          >
            {/* Search Input Bar */}
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-mist bg-paper">
              <Search className="h-5 w-5 text-pewter shrink-0" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Type a command, search pages, or switch currency..."
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                onKeyDown={handleKeyDownInMenu}
                className="w-full bg-transparent text-sm sm:text-base text-ink placeholder:text-pewter focus:outline-none"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  className="text-pewter hover:text-ink p-1 rounded hover:bg-fog cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
              <div className="hidden sm:flex items-center gap-1 text-[11px] font-semibold text-pewter bg-fog px-2 py-0.5 rounded border border-mist">
                <span>ESC</span>
              </div>
            </div>

            {/* Results List */}
            <div className="flex-1 overflow-y-auto p-2 divide-y divide-black/[0.04]">
              {filteredItems.length === 0 ? (
                <div className="py-12 text-center text-xs text-pewter">
                  No matching commands or pages for &quot;{query}&quot;
                </div>
              ) : (
                ["navigation", "actions", "personas", "currency"].map((grp) => {
                  const grpItems = filteredItems.filter((i) => i.group === grp);
                  if (grpItems.length === 0) return null;

                  return (
                    <div key={grp} className="py-1.5 first:pt-0">
                      <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-pewter">
                        {groupLabels[grp]}
                      </div>
                      <div className="flex flex-col gap-0.5 mt-0.5">
                        {grpItems.map((item) => {
                          const itemIndex = filteredItems.indexOf(item);
                          const isSelected = itemIndex === selectedIndex;
                          const Icon = item.icon;

                          return (
                            <button
                              key={item.id}
                              type="button"
                              onClick={() => {
                                item.onSelect();
                                setOpen(false);
                              }}
                              onMouseEnter={() => setSelectedIndex(itemIndex)}
                              className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl text-left transition-colors cursor-pointer ${
                                isSelected ? "bg-fog text-ink font-semibold" : "text-graphite hover:bg-fog/60"
                              }`}
                            >
                              <div className="flex items-center gap-3 min-w-0">
                                <div
                                  className={`flex h-7 w-7 items-center justify-center rounded-lg border transition-colors shrink-0 ${
                                    isSelected
                                      ? "bg-[#172554] text-white border-[#172554] shadow-xs"
                                      : "bg-paper text-pewter border-mist"
                                  }`}
                                >
                                  <Icon className="h-3.5 w-3.5" />
                                </div>
                                <div className="truncate">
                                  <span className="text-xs sm:text-sm text-ink block truncate">
                                    {item.label}
                                  </span>
                                  {item.sublabel && (
                                    <span className="text-[11px] text-pewter block truncate font-normal">
                                      {item.sublabel}
                                    </span>
                                  )}
                                </div>
                              </div>

                              <div className="flex items-center gap-2 shrink-0">
                                {item.badge && (
                                  <span
                                    className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full border ${
                                      item.badge === "Active" || item.badge === "Selected"
                                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                        : "bg-ember-soft text-ember border-ember/20"
                                    }`}
                                  >
                                    {item.badge}
                                  </span>
                                )}
                                {item.shortcut && (
                                  <span className="text-[10px] font-mono font-semibold text-pewter bg-paper px-1.5 py-0.5 rounded border border-mist">
                                    {item.shortcut}
                                  </span>
                                )}
                                {isSelected && <ArrowRight className="h-3.5 w-3.5 text-[#172554]" />}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer hint */}
            <div className="px-4 py-2.5 bg-fog/80 border-t border-mist flex items-center justify-between text-[11px] text-pewter">
              <div className="flex items-center gap-2">
                <Keyboard className="h-3.5 w-3.5" />
                <span>Use ↑ ↓ to navigate, ↵ to select</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-ink">FinPilot</span>
                <span>• Command Hub</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
