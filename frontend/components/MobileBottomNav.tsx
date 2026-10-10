"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  ReceiptText,
  Wallet,
  Target,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

interface MobileTabItem {
  href: string;
  label: string;
  icon: LucideIcon;
  badge?: boolean;
  isSpecial?: boolean;
}

const MOBILE_TABS: MobileTabItem[] = [
  {
    href: "/dashboard",
    label: "Overview",
    icon: LayoutDashboard,
  },
  {
    href: "/transactions",
    label: "Activity",
    icon: ReceiptText,
  },
  {
    href: "/budgets",
    label: "Budgets",
    icon: Wallet,
  },
  {
    href: "/goals",
    label: "Goals",
    icon: Target,
  },
  {
    href: "/copilot",
    label: "Copilot",
    icon: Sparkles,
    badge: true,
    isSpecial: true,
  },
];

/**
 * MobileBottomNav
 * Ergonomic, thumb-friendly bottom navigation bar for mobile and small tablet viewports.
 * Features:
 * - Direct 1-tap thumb access to the 5 primary financial operational workflows.
 * - Framer Motion spring pill indicator transitioning smoothly between active tabs.
 * - Safe-area inset aware (`env(safe-area-inset-bottom)`) for modern bezel-less devices.
 * - Touch-optimized target size (>= 48px) with responsive micro-tap haptic scaling.
 * - Live AI Copilot pulse indicator highlighting real-time intelligence availability.
 */
export function MobileBottomNav() {
  const pathname = usePathname();

  // Defensive: do not render on marketing landing page
  if (pathname === "/") {
    return null;
  }

  return (
    <nav
      role="navigation"
      aria-label="Mobile Navigation"
      className="fixed bottom-0 inset-x-0 z-40 lg:hidden bg-paper/92 backdrop-blur-xl border-t border-mist/80 shadow-[0_-4px_24px_rgba(0,0,0,0.06)] pb-[max(env(safe-area-inset-bottom,0px),10px)] pt-1 px-2.5"
    >
      <div className="flex items-center justify-between max-w-md mx-auto relative">
        {MOBILE_TABS.map((tab) => {
          const isActive = pathname?.startsWith(tab.href);
          const Icon = tab.icon;

          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "relative flex flex-1 flex-col items-center justify-center py-1.5 px-0.5 min-h-[52px] min-w-0 select-none touch-manipulation transition-colors rounded-xl",
                isActive ? "text-ink" : "text-pewter hover:text-carbon"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="mobile-nav-pill"
                  className="absolute inset-0 rounded-xl bg-fog border border-mist/70 shadow-[0_1px_3px_rgba(0,0,0,0.05)]"
                  transition={{ type: "spring", stiffness: 450, damping: 35 }}
                />
              )}

              <motion.div
                whileTap={{ scale: 0.88 }}
                className="relative z-10 flex flex-col items-center justify-center w-full"
              >
                <div className="relative flex items-center justify-center">
                  <Icon
                    className={cn(
                      "h-5 w-5 transition-transform duration-200",
                      isActive ? "scale-105" : "scale-100",
                      tab.isSpecial && isActive ? "text-ember" : ""
                    )}
                    strokeWidth={isActive ? 2.25 : 1.75}
                  />
                  {tab.badge && (
                    <span className="absolute -top-1 -right-1.5 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ember opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-ember shadow-[0_0_6px_rgba(255,89,0,0.6)]" />
                    </span>
                  )}
                </div>

                <span
                  className={cn(
                    "text-[10px] tracking-tight leading-none mt-1 transition-colors whitespace-nowrap",
                    isActive ? "font-semibold text-ink" : "font-medium text-pewter"
                  )}
                >
                  {tab.label}
                </span>
              </motion.div>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
