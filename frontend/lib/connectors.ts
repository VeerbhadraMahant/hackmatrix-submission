"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { useAsync, useUserId } from "@/lib/hooks";

/** Connector list for the active user; refetches automatically after any write. */
export function useConnectors() {
  const userId = useUserId();
  const fetchConnectors = useCallback(() => api.connectors(userId), [userId]);
  const state = useAsync(fetchConnectors, [userId]);
  const connectedCount = state.data?.filter((c) => c.connected).length ?? 0;
  return { ...state, userId, connectedCount, hasConnection: connectedCount > 0 };
}
