"use client";

import * as React from "react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Integration {
  name: string;
  description: string;
  icon: LucideIcon;
  /** Tailwind classes for the icon chip, e.g. "bg-tint-sky text-sky". */
  tone?: string;
}

export interface IntegrationShowcaseProps {
  /** Wrap the word to highlight in `~`, e.g. "Connect your ~favorite~ tools". */
  title: string;
  subtitle: string;
  /** Optional decorative element shown beside the heading. */
  illustration?: React.ReactNode;
  integrations: Integration[];
  className?: string;
}

const HighlightedTitle = ({ text }: { text: string }) => {
  const parts = text.split(/~/);
  return (
    <h2 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
      {parts.map((part, index) =>
        index === 1 ? (
          <span key={index} className="relative inline-block whitespace-nowrap">
            <span className="relative z-10">{part}</span>
            <svg
              aria-hidden="true"
              viewBox="0 0 260 18"
              fill="none"
              className="absolute -bottom-2 left-0 w-full h-[10px] text-lime-dark pointer-events-none select-none"
              preserveAspectRatio="none"
            >
              <path
                d="M 3 13 C 65 3, 195 4, 257 11"
                stroke="currentColor"
                strokeWidth="3.5"
                strokeLinecap="round"
              />
            </svg>
          </span>
        ) : (
          part
        ),
      )}
    </h2>
  );
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

export const IntegrationShowcase = React.forwardRef<HTMLElement, IntegrationShowcaseProps>(
  ({ title, subtitle, illustration, integrations, className }, ref) => (
    <section ref={ref} className={cn("w-full py-8", className)}>
      <div className="grid grid-cols-1 items-center gap-x-12 gap-y-6 lg:grid-cols-2">
        <div className="max-w-xl">
          <HighlightedTitle text={title} />
          <p className="mt-4 text-base text-muted-foreground sm:text-lg">{subtitle}</p>
        </div>
        {illustration && <div className="flex items-center justify-center">{illustration}</div>}
      </div>

      <motion.div
        className="mt-10 grid grid-cols-1 gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {integrations.map(({ name, description, icon: Icon, tone }) => (
          <motion.div key={name} variants={itemVariants} className="flex items-start gap-4">
            <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-xl", tone ?? "bg-fog text-graphite")}>
              <Icon className="size-5" />
            </span>
            <div>
              <h3 className="text-sm font-semibold text-foreground">{name}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{description}</p>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </section>
  ),
);

IntegrationShowcase.displayName = "IntegrationShowcase";
