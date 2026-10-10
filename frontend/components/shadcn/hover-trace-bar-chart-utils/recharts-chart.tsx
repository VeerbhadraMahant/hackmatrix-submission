"use client";

import * as React from "react";
import { ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";

export type ChartConfig = Record<
  string,
  { label?: string; colors: { light: string[]; dark: string[] } }
>;

/** Emits `--color-<key>-<i>` CSS variables per series, with light/dark variants. */
export function ChartContainer({
  config,
  className,
  children,
}: {
  config: ChartConfig;
  className?: string;
  children: React.ReactElement;
}) {
  const id = React.useId().replace(/:/g, "");
  const vars = (mode: "light" | "dark") =>
    Object.entries(config)
      .flatMap(([key, c]) => c.colors[mode].map((v, i) => `--color-${key}-${i}:${v};`))
      .join("");
  const css = `[data-chart="${id}"]{${vars("light")}}.dark [data-chart="${id}"]{${vars("dark")}}`;

  return (
    <div data-chart={id} className={cn("h-full min-h-48 w-full flex-1", className)}>
      <style dangerouslySetInnerHTML={{ __html: css }} />
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}
