import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface ChipProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "accent" | "outline" | "success" | "warning" | "danger" | "info";
}

/** 8px-radius chip for categories, tags, status labels. */
export function Chip({ className, tone = "neutral", ...props }: ChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-chip px-2.5 py-0.5 text-xs font-medium tracking-tight transition-colors duration-150",
        tone === "neutral" && "bg-fog text-graphite border border-black/[0.04]",
        tone === "accent" && "bg-orange-50 text-ember-dark border border-ember/20 font-semibold",
        tone === "outline" && "border border-mist bg-white text-graphite",
        tone === "success" && "bg-emerald-50 text-emerald-700 border border-emerald-200",
        tone === "warning" && "bg-amber-50 text-amber-700 border border-amber-200",
        tone === "danger" && "bg-rose-50 text-rose-700 border border-rose-200",
        tone === "info" && "bg-indigo-50 text-indigo-700 border border-indigo-200",
        className
      )}
      {...props}
    />
  );
}
