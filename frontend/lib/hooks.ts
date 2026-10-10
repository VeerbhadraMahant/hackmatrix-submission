"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { DEFAULT_USER_ID, getUserId, USER_ID_CHANGE_EVENT } from "@/lib/user";

function subscribeToUserIdChanges(onStoreChange: () => void) {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(USER_ID_CHANGE_EVENT, onStoreChange);
  return () => window.removeEventListener(USER_ID_CHANGE_EVENT, onStoreChange);
}

/**
 * Returns the current demo/real user id. Uses useSyncExternalStore so the
 * server snapshot (SSR: no localStorage) and client snapshot can differ
 * without triggering the "setState inside effect" lint rule or a hydration
 * mismatch warning -- the id itself is never rendered into DOM text. The
 * persona switcher (components/NavShell.tsx) calls setUserId(), which
 * dispatches USER_ID_CHANGE_EVENT so every subscriber here re-renders with
 * the new id -- and any useAsync() keyed on userId refetches automatically.
 */
export function useUserId(): string {
  return useSyncExternalStore(subscribeToUserIdChanges, getUserId, () => DEFAULT_USER_ID);
}

interface AsyncState<T> {
  data: T | null;
  error: string | null;
  /** True only for a first/blank load (no data to show yet). Background
   * refreshes keep the current data on screen and leave this false. */
  loading: boolean;
}

/** Fired on `window` after any successful write through lib/api.ts, so
 * every mounted useAsync() quietly refetches and no panel is left stale. */
export const DATA_CHANGED_EVENT = "finpilot:data_changed";

function sameDeps(a: unknown[], b: unknown[]) {
  return a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
}

/**
 * Minimal fetch-on-mount hook -- no react-query dependency needed for this scope.
 *
 * Stale-while-revalidate: changing `deps` (e.g. switching user) resets to a
 * blank loading state, but `reload()` and the global data-changed event keep
 * the current data visible while refetching, so the UI never flashes back to
 * a skeleton after an edit. `mutate` lets callers apply optimistic updates.
 *
 * `options.identity`: when given, only a change of *that* value blanks the
 * view (e.g. the user id); other dep changes (filters, page) keep the
 * previous rows on screen until the new ones arrive.
 */
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: unknown[],
  options?: { identity?: unknown }
): AsyncState<T> & { reload: () => void; mutate: (update: (prev: T | null) => T | null) => void } {
  const [state, setState] = useState<AsyncState<T>>({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  const prevDeps = useRef<unknown[] | null>(null);
  const prevIdentity = useRef<unknown>(options?.identity);

  useEffect(() => {
    let cancelled = false;
    // Only a real deps change (not a tick-only refresh) blanks the view.
    const depsChanged = prevDeps.current !== null && !sameDeps(prevDeps.current, deps);
    prevDeps.current = deps;
    const identityChanged = !Object.is(prevIdentity.current, options?.identity);
    prevIdentity.current = options?.identity;
    const mustBlank = options && "identity" in options ? identityChanged : depsChanged;
    if (mustBlank) {
      setState({ data: null, error: null, loading: true });
    }

    fn()
      .then((data) => {
        if (!cancelled) setState({ data, error: null, loading: false });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState((prev) => ({
            data: mustBlank ? null : prev.data,
            error: err instanceof Error ? err.message : "Something went wrong",
            loading: false,
          }));
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  useEffect(() => {
    const refresh = () => setTick((t) => t + 1);
    window.addEventListener(DATA_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(DATA_CHANGED_EVENT, refresh);
  }, []);

  return {
    ...state,
    reload: () => setTick((t) => t + 1),
    mutate: (update) => setState((prev) => ({ ...prev, data: update(prev.data), error: null })),
  };
}

/** Returns `value` after it has stopped changing for `delayMs` (e.g. search-as-you-type). */
export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}
