"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { useConnectors } from "@/lib/connectors";

const EVERY_MS = 30_000;

/** Renders nothing: while a Google Sheet is connected, re-reads it every 30 seconds so edits show up. */
export function SheetAutoSync() {
  const { data, userId } = useConnectors();
  const linked = !!data?.find((c) => c.id === "google_sheets" && c.connected);
  useEffect(() => {
    if (!linked) return;
    const tick = () => api.syncSheet(userId).catch(() => {});
    const id = setInterval(tick, EVERY_MS);
    return () => clearInterval(id);
  }, [linked, userId]);
  return null;
}
