import type { CopilotInsight } from "./types";

const EVT = "copilot:insights";

export function publishCopilotInsights(insights: CopilotInsight[]) {
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(EVT, { detail: insights }));
}

export function subscribeCopilotInsights(fn: (i: CopilotInsight[]) => void): () => void {
  const h = (e: Event) => fn((e as CustomEvent<CopilotInsight[]>).detail);
  window.addEventListener(EVT, h);
  return () => window.removeEventListener(EVT, h);
}
