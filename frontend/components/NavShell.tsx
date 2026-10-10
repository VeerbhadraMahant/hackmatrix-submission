"use client";

import { useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { Eye, EyeOff, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { NotificationBell } from "@/components/NotificationBell";
import { CurrencySelector } from "@/components/ui/CurrencySelector";
import { CommandPalette } from "@/components/ui/CommandPalette";
import { ConfettiCanvas } from "@/components/ui/Confetti";
import { AppSidebar, NAV_GROUPS } from "@/components/AppSidebar";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/shadcn/sidebar";
import { TooltipProvider } from "@/components/shadcn/tooltip";
import { Separator } from "@/components/shadcn/separator";
import { Button } from "@/components/shadcn/button";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/shadcn/breadcrumb";
import { useUserId } from "@/lib/hooks";
import { DEMO_PERSONAS, isDemoUserId, setUserId } from "@/lib/user";

const PERSONA_DETAILS: Record<string, { city: string; tag: string }> = {
  "demo-priya": { city: "Bengaluru", tag: "₹95k/mo" },
  "demo-arjun": { city: "Mumbai", tag: "₹160k/mo" },
  "demo-meera": { city: "Pune", tag: "₹42k/mo" },
};

/** Segmented control for switching between the seeded demo personas */
function PersonaSwitcher() {
  const userId = useUserId();
  // Signed-in users only see their own data -- no demo personas.
  if (!isDemoUserId(userId)) return null;

  return (
    <div
      role="radiogroup"
      aria-label="Demo persona"
      className="flex items-center gap-1 rounded-full border border-mist bg-paper/70 p-1 backdrop-blur-md shadow-[0_1px_3px_rgba(0,0,0,0.03)]"
    >
      {DEMO_PERSONAS.map((persona) => {
        const active = userId === persona.id;
        const details = PERSONA_DETAILS[persona.id];
        return (
          <button
            key={persona.id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => setUserId(persona.id)}
            className={cn(
              "relative px-3 py-1.5 text-xs font-medium cursor-pointer rounded-full transition-colors whitespace-nowrap flex items-center gap-1.5",
              active ? "text-ink font-semibold" : "text-graphite hover:text-ink"
            )}
          >
            {active && (
              <motion.div
                layoutId="active-persona-pill"
                className="absolute inset-0 rounded-full bg-paper shadow-[0_1px_4px_rgba(0,0,0,0.08),0_2px_8px_rgba(0,0,0,0.04)] border border-mist"
                transition={{ type: "spring", stiffness: 450, damping: 35 }}
              />
            )}
            <span className="relative z-10 flex items-center gap-1">
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  active ? "bg-ember" : "bg-steel/50"
                )}
              />
              <span>{persona.label}</span>
              {details && (
                <span className="text-[10px] text-pewter font-normal hidden min-[1700px]:inline">
                  {details.tag}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function NavShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const userId = useUserId();
  const isDashboard = pathname?.startsWith("/dashboard") ?? false;
  const [hidden, setHidden] = useState(false);
  const current = NAV_GROUPS.flatMap((g) => g.links).find((l) => pathname?.startsWith(l.href));

  return (
    <TooltipProvider delayDuration={0}>
      <SidebarProvider>
        <AppSidebar
          footer={
            <div className="xl:hidden">
              <PersonaSwitcher />
            </div>
          }
        />
        <SidebarInset className="min-w-0 overflow-x-hidden bg-transparent">
          <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-2 bg-background/70 px-4 backdrop-blur-md">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
            <Breadcrumb className="min-w-0">
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbPage className={cn("truncate font-display font-semibold text-ink", isDashboard ? "text-3xl sm:text-4xl" : "text-2xl")}>{current?.label ?? "FinPilot"}</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>

            <div className="ml-auto flex shrink-0 items-center gap-2">
              <button
                type="button"
                onClick={() => window.dispatchEvent(new CustomEvent("finpilot:open-command-palette"))}
                className="hidden h-9 w-64 items-center gap-2 rounded-xl bg-white px-3 text-sm text-muted-foreground shadow-sm md:flex"
                title="Search (Ctrl+K)"
                aria-label="Open search"
              >
                <Search className="size-4" />
                <span>Search...</span>
                <kbd className="ml-auto rounded border bg-muted px-1.5 text-[10px] font-semibold">⌘ K</kbd>
              </button>
              <Button variant="outline" size="icon" className="md:hidden" onClick={() => window.dispatchEvent(new CustomEvent("finpilot:open-command-palette"))} aria-label="Open search">
                <Search className="size-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setHidden((h) => { document.documentElement.classList.toggle("hide-amounts", !h); return !h; })}
                aria-label={hidden ? "Show amounts" : "Hide amounts"}
                title={hidden ? "Show amounts" : "Hide amounts"}
              >
                {hidden ? <Eye className="size-4" /> : <EyeOff className="size-4" />}
              </Button>
              <div className="hidden sm:block">
                <CurrencySelector />
              </div>
              <div className="hidden xl:block">
                <PersonaSwitcher />
              </div>
              <NotificationBell userId={userId} large={isDashboard} />
            </div>
          </header>

          <main className="mx-auto w-full max-w-[1600px] min-w-0 flex-1 px-4 py-4 pb-[calc(1.5rem+env(safe-area-inset-bottom,0px))] sm:px-6 sm:py-5 lg:px-8">
            {children}
          </main>
        </SidebarInset>

        <CommandPalette />
        <ConfettiCanvas />
      </SidebarProvider>
    </TooltipProvider>
  );
}
