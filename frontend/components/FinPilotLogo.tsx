import React from "react";
import { cn } from "@/lib/utils";

interface FinPilotLogoProps {
  variant?: "mark" | "horizontal" | "stacked";
  theme?: "default" | "white" | "black" | "ink";
  size?: number;
  className?: string;
  showWordmark?: boolean;
}

/**
 * FinPilotLogo
 * Official brand identity component rendering the "Financial Growth Compass Apex" mark.
 * Incorporates three compounding wealth pillars and the supersonic Ember navigation needle.
 */
export function FinPilotLogo({
  variant = "mark",
  theme = "default",
  size = 32,
  className,
  showWordmark = false,
}: FinPilotLogoProps) {
  const fgColor =
    theme === "white" || theme === "ink"
      ? "#ffffff"
      : theme === "black"
      ? "#090a0f"
      : "#090a0f";

  const accentColor =
    theme === "white"
      ? "#ffffff"
      : theme === "black"
      ? "#090a0f"
      : "#ff5900";

  if (variant === "horizontal" || showWordmark) {
    return (
      <div className={cn("inline-flex items-center gap-2.5 select-none", className)}>
        <svg
          viewBox="0 0 512 512"
          width={size}
          height={size}
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="shrink-0 transition-transform duration-200 group-hover:scale-105"
          aria-hidden="true"
        >
          {/* Grounded Baseline */}
          <path d="M72 440 L440 440 L424 424 L88 424 Z" fill={fgColor} />
          {/* 3 Compounding Financial Growth Bars */}
          <polygon points="144,424 200,424 200,344 144,382" fill={fgColor} />
          <polygon points="220,424 276,424 276,262 220,300" fill={fgColor} />
          <polygon points="296,424 352,424 352,180 296,218" fill={fgColor} />
          {/* Compass Needle (Left Facet - Ember) */}
          <polygon points="396,72 244,154 328,178" fill={accentColor} />
          {/* Compass Needle (Right Facet - Ink/White) */}
          <polygon points="396,72 328,178 356,260" fill={fgColor} />
        </svg>

        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              "font-display text-xl font-medium tracking-tight",
              theme === "white" ? "text-paper" : "text-ink"
            )}
          >
            FinPilot
          </span>
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full animate-pulse",
              theme === "white" ? "bg-white" : "bg-ember shadow-[0_0_6px_rgba(255,89,0,0.6)]"
            )}
          />
        </div>
      </div>
    );
  }

  // Standalone Mark
  return (
    <svg
      viewBox="0 0 512 512"
      width={size}
      height={size}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0", className)}
      role="img"
      aria-label="FinPilot Logo"
    >
      {/* Grounded Baseline */}
      <path d="M72 440 L440 440 L424 424 L88 424 Z" fill={fgColor} />
      {/* 3 Compounding Financial Growth Bars */}
      <polygon points="144,424 200,424 200,344 144,382" fill={fgColor} />
      <polygon points="220,424 276,424 276,262 220,300" fill={fgColor} />
      <polygon points="296,424 352,424 352,180 296,218" fill={fgColor} />
      {/* Compass Needle (Left Facet - Ember) */}
      <polygon points="396,72 244,154 328,178" fill={accentColor} />
      {/* Compass Needle (Right Facet - Ink/White) */}
      <polygon points="396,72 328,178 356,260" fill={fgColor} />
    </svg>
  );
}
