"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, CheckCheck, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { NotificationItem, NotificationSeverity } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Polished Notification Bell with tactile glassmorphism dropdown,
 * category/severity dots (Ember/graphite/steel), local "Mark all as read" capability,
 * and contextual actionable simulation links.
 */
export function NotificationBell({ userId, large = false }: { userId: string; large?: boolean }) {
  const [open, setOpen] = useState(false);
  const [readIds, setReadIds] = useState<Set<string>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = useCallback(() => api.notifications(userId), [userId]);
  const { data, error, loading } = useAsync(fetchNotifications, [userId]);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const items = data ?? [];
  const unreadCount = items.filter((item) => !readIds.has(item.id)).length;
  const badgeLabel = unreadCount > 9 ? "9+" : String(unreadCount);

  function handleMarkAllAsRead() {
    setReadIds(new Set(items.map((item) => item.id)));
  }

  function handleMarkSingleAsRead(id: string) {
    setReadIds((prev) => new Set([...prev, id]));
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
        aria-expanded={open}
        className={cn(
          large ? "h-11 w-11" : "h-9 w-9",
          "relative inline-flex items-center justify-center rounded-chip border transition-all duration-150 cursor-pointer select-none",
          open
            ? "border-navy/40 bg-navy/5 text-navy shadow-xs"
            : "border-mist text-graphite hover:bg-fog hover:text-ink hover:border-black/[0.15]"
        )}
      >
        <Bell className={large ? "h-5 w-5" : "h-4 w-4"} />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-ember px-1 text-[10px] font-bold text-white shadow-[0_0_8px_rgba(255,89,0,0.5)] animate-in fade-in">
            {badgeLabel}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            className="absolute right-0 z-50 mt-2 w-84 sm:w-96 rounded-surface border border-black/[0.08] bg-white/95 shadow-[0_16px_48px_rgba(15,23,42,0.14)] backdrop-blur-md overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-black/[0.06] bg-fog/70 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-ink">Notifications</span>
                {unreadCount > 0 ? (
                  <span className="rounded-full bg-ember/10 px-2 py-0.5 text-[10px] font-bold text-ember-dark tnum">
                    {unreadCount} unread
                  </span>
                ) : (
                  <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                    Caught up
                  </span>
                )}
              </div>

              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAllAsRead}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-graphite hover:text-ember transition-colors cursor-pointer"
                >
                  <CheckCheck className="h-3 w-3" />
                  <span>Mark all as read</span>
                </button>
              )}
            </div>

            {/* Notification List Container */}
            <div className="max-h-96 overflow-y-auto divide-y divide-black/[0.04]">
              {loading && !data && (
                <div className="flex flex-col gap-2 p-4 animate-pulse">
                  <div className="h-4 w-3/4 rounded bg-mist" />
                  <div className="h-3 w-1/2 rounded bg-mist" />
                </div>
              )}

              {error && (
                <div className="p-4 text-center">
                  <p className="text-xs text-rose-600 font-medium">Could not load notifications.</p>
                </div>
              )}

              {data && items.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-2 p-8 text-center">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100">
                    <CheckCircle2 className="h-5 w-5" />
                  </div>
                  <p className="text-xs font-semibold text-ink">You&apos;re all caught up</p>
                  <p className="text-[11px] text-pewter">
                    No active telemetry warnings or cash-flow alerts.
                  </p>
                </div>
              )}

              {items.map((item) => {
                const isRead = readIds.has(item.id);
                return (
                  <NotificationRow
                    key={item.id}
                    item={item}
                    isRead={isRead}
                    onMarkRead={() => handleMarkSingleAsRead(item.id)}
                    onClose={() => setOpen(false)}
                  />
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function severityDot(severity: NotificationSeverity) {
  if (severity === "critical") {
    return (
      <span className="relative flex h-2 w-2 shrink-0 mt-1.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ember opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-ember shadow-[0_0_6px_rgba(255,89,0,0.6)]" />
      </span>
    );
  }
  if (severity === "warning") {
    return <span className="h-2 w-2 shrink-0 rounded-full bg-graphite ring-2 ring-gray-100 mt-1.5" />;
  }
  return <span className="h-2 w-2 shrink-0 rounded-full bg-steel ring-2 ring-slate-100 mt-1.5" />;
}

interface ActionLinkConfig {
  href: string;
  label: string;
}

function getActionLink(item: NotificationItem): ActionLinkConfig | null {
  const text = item.text.toLowerCase();

  if (text.includes("deficit") || text.includes("gap") || text.includes("shortfall") || item.type === "cash_flow_gap") {
    return { href: "/simulate", label: "Simulate Fix →" };
  }
  if (text.includes("debt") || text.includes("loan") || text.includes("interest") || text.includes("emi")) {
    return { href: "/simulate", label: "Simulate Fix →" };
  }
  if (
    text.includes("subscription") ||
    text.includes("bill") ||
    text.includes("budget") ||
    text.includes("envelope") ||
    item.type === "upcoming_bill"
  ) {
    return { href: "/budgets", label: "Adjust Budget →" };
  }
  if (item.type === "recommendation") {
    return { href: "/simulate", label: "Review Simulation →" };
  }

  return null;
}

function NotificationRow({
  item,
  isRead,
  onMarkRead,
  onClose,
}: {
  item: NotificationItem;
  isRead: boolean;
  onMarkRead: () => void;
  onClose: () => void;
}) {
  const action = getActionLink(item);

  return (
    <div
      className={cn(
        "flex items-start gap-3 px-4 py-3 transition-colors hover:bg-fog/60",
        isRead ? "opacity-60 bg-paper" : "bg-white"
      )}
    >
      {severityDot(item.severity)}

      <div className="flex flex-col gap-1 flex-1 min-w-0">
        <p className={cn("text-xs leading-relaxed", isRead ? "text-graphite font-normal" : "text-ink font-medium")}>
          {item.text}
        </p>

        <div className="flex items-center justify-between gap-2 pt-0.5">
          <span className="text-[10px] text-pewter tnum">{formatDate(item.date)}</span>

          <div className="flex items-center gap-2">
            {action && (
              <Link
                href={action.href}
                onClick={() => {
                  onMarkRead();
                  onClose();
                }}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-ember hover:text-ember-dark transition-colors"
              >
                <span>{action.label}</span>
              </Link>
            )}

            {!isRead && (
              <button
                type="button"
                onClick={onMarkRead}
                className="text-[10px] text-pewter hover:text-ink transition-colors cursor-pointer"
                title="Mark as read"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
