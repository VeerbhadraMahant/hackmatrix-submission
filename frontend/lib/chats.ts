"use client";

import { useCallback, useEffect, useState } from "react";
import type { AnswerContract } from "@/lib/types";

export interface Turn {
  role: "user" | "assistant";
  message: string;
  answer?: AnswerContract;
}

export interface Chat {
  id: string;
  title: string;
  updatedAt: number;
  turns: Turn[];
}

const EMPTY: Chat[] = [];
const key = (userId: string) => `finpilot-chats:${userId}`;

function read(userId: string): Chat[] {
  try {
    const raw = localStorage.getItem(key(userId));
    return raw ? (JSON.parse(raw) as Chat[]) : [];
  } catch {
    return [];
  }
}

/** Saved conversations for one user. Kept in this browser (localStorage), newest first. */
export function useChats(userId: string) {
  const [state, setState] = useState<{ userId: string; chats: Chat[] } | null>(null);
  const chats = state?.userId === userId ? state.chats : EMPTY;
  const loaded = state?.userId === userId;
  const setChats = useCallback((next: Chat[]) => setState({ userId, chats: next }), [userId]);

  useEffect(() => {
    // localStorage only exists in the browser, so it is read after mount
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setChats(read(userId));
  }, [userId, setChats]);

  const persist = useCallback(
    (next: Chat[]) => {
      const sorted = [...next].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, 50);
      setChats(sorted);
      try {
        localStorage.setItem(key(userId), JSON.stringify(sorted));
      } catch {
        // storage full or blocked: the chat still works for this visit
      }
    },
    [userId, setChats],
  );

  const save = useCallback(
    (chat: Chat) => persist([...chats.filter((c) => c.id !== chat.id), chat]),
    [chats, persist],
  );
  const remove = useCallback((id: string) => persist(chats.filter((c) => c.id !== id)), [chats, persist]);

  return { chats, loaded, save, remove };
}

export const newChatId = () => `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

export const titleFrom = (message: string) => (message.length > 42 ? message.slice(0, 41) + "…" : message);
