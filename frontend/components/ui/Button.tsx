import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
}

/**
 * primary = Refined Navy Blue fill with ambient shadow, exactly one CTA per view.
 * secondary = Refined hairline border, Ink text with subtle hover tint.
 * ghost = no border, for tertiary actions (e.g. nav, example prompts).
 */
export function Button({
  className,
  variant = "secondary",
  size = "md",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-chip font-medium cursor-pointer transition-all duration-150 active:scale-[0.98]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy focus-visible:ring-offset-2 focus-visible:ring-offset-paper",
        "disabled:cursor-not-allowed disabled:opacity-40 disabled:pointer-events-none disabled:active:scale-100",
        size === "sm" && "min-h-9 px-3 py-1.5 text-xs",
        size === "md" && "min-h-11 px-4 py-2 text-sm",
        size === "lg" && "min-h-12 px-6 py-3 text-base font-semibold",
        variant === "primary" &&
          "bg-navy text-white shadow-[0_2px_10px_rgba(23,37,84,0.22)] hover:bg-navy-light hover:shadow-[0_4px_16px_rgba(23,37,84,0.32)] border border-navy-dark/30",
        variant === "secondary" &&
          "border border-mist bg-paper text-ink shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:bg-fog hover:border-black/[0.12]",
        variant === "ghost" && "text-graphite hover:bg-fog hover:text-ink",
        className
      )}
      {...props}
    />
  );
}
