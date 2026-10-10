"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ReceiptText,
  Wallet,
  Target,
  Users,
  Sparkles,
  FlaskConical,
  GitCompare,
  Route,
  Calculator,
  History,
  FileText,
  ShieldCheck,
  ShieldAlert,
  ScanSearch,
  Network,
  Database,
  FilePlus2,
  Link2,
  type LucideIcon,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/shadcn/sidebar";
import { FinPilotLogo } from "@/components/FinPilotLogo";
import { SignInButton } from "@/components/SignInButton";

export interface NavLink {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_GROUPS: { label: string; tone: string; links: NavLink[] }[] = [
  {
    label: "Copilot",
    tone: "text-[#e0540a]",
    links: [{ href: "/copilot", label: "FinPilot Copilot", icon: Sparkles }],
  },
  {
    label: "Track",
    tone: "text-[#0fb67a]",
    links: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/connect", label: "Connectors", icon: Link2 },
      { href: "/transactions", label: "Transactions", icon: ReceiptText },
      { href: "/invoices", label: "Invoices", icon: FilePlus2 },
      { href: "/budgets", label: "Budgets", icon: Wallet },
      { href: "/goals", label: "Goals", icon: Target },
      { href: "/household", label: "Household", icon: Users },
    ],
  },
  {
    label: "Intelligence",
    tone: "text-[#e0540a]",
    links: [
      { href: "/financial-security", label: "Financial Security", icon: ShieldAlert },
      { href: "/simulate", label: "Simulate", icon: FlaskConical },
      { href: "/plan", label: "Plan", icon: Route },
      { href: "/scenarios", label: "Compare", icon: GitCompare },
      { href: "/tax", label: "Tax", icon: Calculator },
      { href: "/timeline", label: "Timeline", icon: History },
    ],
  },
  {
    label: "Reports",
    tone: "text-[#3b6bff]",
    links: [
      { href: "/statement", label: "Statement", icon: FileText },
    ],
  },
  {
    label: "Security",
    tone: "text-[#d6336c]",
    links: [
      { href: "/security", label: "Security", icon: ShieldCheck },
      { href: "/evidence-room", label: "Evidence Room", icon: ScanSearch },
      { href: "/twin", label: "Twin Simulator", icon: Network },
      { href: "/my-data", label: "My Data", icon: Database },
    ],
  },
];

export function AppSidebar({ footer }: { footer?: ReactNode }) {
  const pathname = usePathname();
  const { setOpenMobile, state } = useSidebar();

  return (
    <Sidebar collapsible="icon" variant="floating">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild tooltip="FinPilot home">
              <Link href="/" aria-label="FinPilot home">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-mist bg-paper">
                  <FinPilotLogo size={20} />
                </div>
                <span className="font-display text-lg font-medium tracking-tight">FinPilot</span>
                <span className="ml-auto size-1.5 rounded-full bg-lime shadow-[0_0_8px_rgba(198,241,53,0.8)] animate-pulse" />
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {NAV_GROUPS.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.links.map(({ href, label, icon: Icon }) => {
                  const active = !!pathname?.startsWith(href);
                  return (
                    <SidebarMenuItem key={href}>
                      <SidebarMenuButton asChild isActive={active} tooltip={label}>
                        <Link
                          href={href}
                          aria-current={active ? "page" : undefined}
                          onClick={() => setOpenMobile(false)}
                        >
                          <Icon className={active ? "text-ink" : group.tone} />
                          <span>{label}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        {state === "expanded" && (
          <>
            {footer}
            <SignInButton />
          </>
        )}
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
