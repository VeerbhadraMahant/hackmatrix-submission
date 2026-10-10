"use client";

import { useCallback, useMemo, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { Check, ExternalLink, PiggyBank, ShieldCheck, TrendingUp, Landmark, type LucideIcon } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { Debt } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/shadcn/card";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";

const HIGH_APR = 12; // % — paying this off beats the typical long-run equity return after tax
const EMERGENCY_MONTHS = 6;

type Risk = "cautious" | "balanced" | "growth";
type Bucket = { key: string; label: string; color: string; link: { label: string; href: string } };

const BUCKETS: Record<string, Bucket> = {
  index: { key: "index", label: "Nifty 50 index fund", color: "#5f7f0c", link: { label: "Start a SIP on Groww", href: "https://groww.in/mutual-funds" } },
  flexi: { key: "flexi", label: "Flexi-cap fund", color: "#a6d11a", link: { label: "Browse on Zerodha Coin", href: "https://coin.zerodha.com" } },
  debt: { key: "debt", label: "Liquid / short-term debt fund", color: "#4fe0b0", link: { label: "Compare on Kuvera", href: "https://kuvera.in" } },
  ppf: { key: "ppf", label: "PPF / NPS (tax-saving)", color: "#3f7d5c", link: { label: "Open NPS (eNPS)", href: "https://enps.nsdl.com" } },
  gold: { key: "gold", label: "Gold (sovereign / ETF)", color: "#cddaa6", link: { label: "Gold ETFs on Zerodha Coin", href: "https://coin.zerodha.com" } },
};

// Illustrative starting splits (% of the monthly investable surplus), not personalised advice.
const SPLITS: Record<Risk, Record<string, number>> = {
  cautious: { index: 25, flexi: 10, debt: 35, ppf: 25, gold: 5 },
  balanced: { index: 40, flexi: 20, debt: 15, ppf: 20, gold: 5 },
  growth: { index: 50, flexi: 30, debt: 5, ppf: 10, gold: 5 },
};

function Step({ icon: Icon, title, body, state }: { icon: LucideIcon; title: string; body: string; state: "done" | "now" | "next" }) {
  return (
    <li className={cn("flex gap-3 rounded-2xl p-3", state === "now" ? "bg-tint-lime ring-1 ring-lime-dark/50" : "bg-fog/60")}>
      <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-full", state === "done" ? "bg-leaf text-white" : state === "now" ? "bg-lime text-ink" : "bg-white text-pewter")}>
        {state === "done" ? <Check className="size-4" /> : <Icon className="size-4" />}
      </span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-ink">
          {title} {state === "now" && <span className="ml-1 rounded-full bg-lime px-2 py-0.5 text-[10px] font-semibold uppercase">Do this now</span>}
        </p>
        <p className="text-xs text-graphite">{body}</p>
      </div>
    </li>
  );
}

/** Recomputed from live dashboard numbers on every refresh: debt first, then emergency fund, then a SIP split. */
export function InvestGuide({ userId, income, expenses, debts }: { userId: string; income: number; expenses: number; debts: Debt[] }) {
  const [risk, setRisk] = useState<Risk>("balanced");
  const fetchAccounts = useCallback(() => api.accounts(userId), [userId]);
  const { data: accounts } = useAsync(fetchAccounts, [userId]);

  const plan = useMemo(() => {
    const cash = (accounts ?? []).filter((a) => a.type === "checking" || a.type === "savings").reduce((s, a) => s + Math.max(a.balance, 0), 0);
    const surplus = Math.max(0, income - expenses);
    const target = EMERGENCY_MONTHS * expenses;
    const costly = debts.filter((d) => d.interest_rate_apr >= HIGH_APR);
    const costlyOwed = costly.reduce((s, d) => s + d.principal, 0);
    const worst = costly.reduce((m, d) => Math.max(m, d.interest_rate_apr), 0);
    const emergencyGap = Math.max(0, target - cash);
    const stage: 0 | 1 | 2 = costly.length > 0 ? 0 : emergencyGap > 0 ? 1 : 2;
    return { cash, surplus, target, costlyOwed, worst, emergencyGap, stage, monthsCovered: expenses > 0 ? cash / expenses : 0 };
  }, [accounts, income, expenses, debts]);

  const split = Object.entries(SPLITS[risk]).map(([k, pct]) => ({ ...BUCKETS[k], pct, amount: Math.round((plan.surplus * pct) / 100) }));
  const state = (i: number) => (plan.stage > i ? "done" : plan.stage === i ? "now" : "next");

  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 font-display text-lg">
          <span className="flex size-8 items-center justify-center rounded-full bg-lime">
            <TrendingUp className="size-4" />
          </span>
          What should I invest in?
        </CardTitle>
        <CardDescription>
          Updates with your income, spending, cash and debts. Surplus now: <b className="text-ink">{formatCurrency(plan.surplus)}</b> a month.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5 lg:grid-cols-2">
        <ol className="grid content-start gap-2">
          <Step
            icon={Landmark}
            state={state(0)}
            title="Clear costly debt"
            body={plan.costlyOwed > 0 ? `${formatCurrency(plan.costlyOwed)} is borrowed at ${plan.worst.toFixed(1)}% or more. Paying it back is a guaranteed return.` : `No debt above ${HIGH_APR}% APR.`}
          />
          <Step
            icon={ShieldCheck}
            state={state(1)}
            title={`Build a ${EMERGENCY_MONTHS}-month safety fund`}
            body={`Cash covers ${plan.monthsCovered.toFixed(1)} months. ${plan.emergencyGap > 0 ? `${formatCurrency(plan.emergencyGap)} more reaches ${formatCurrency(plan.target)}. Keep it in a savings account or liquid fund.` : "Target reached."}`}
          />
          <Step
            icon={PiggyBank}
            state={state(2)}
            title="Invest the surplus monthly"
            body={plan.surplus > 0 ? "Start a SIP with the split on the right. Small and regular beats large and rare." : "No monthly surplus yet, so trim spending first."}
          />
          <li className="mt-1 flex flex-wrap gap-2 text-xs">
            {[
              ["SEBI investor guide", "https://investor.sebi.gov.in"],
              ["AMFI: mutual funds 101", "https://www.amfiindia.com/investor-corner"],
            ].map(([label, href]) => (
              <a key={href} href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-full bg-fog px-3 py-1.5 font-medium text-ink hover:bg-lime/40">
                {label} <ExternalLink className="size-3" />
              </a>
            ))}
          </li>
        </ol>

        <div className="grid gap-3">
          <div className="flex gap-1 rounded-full bg-fog p-1 text-xs font-medium">
            {(["cautious", "balanced", "growth"] as Risk[]).map((r) => (
              <button key={r} type="button" onClick={() => setRisk(r)} className={cn("flex-1 rounded-full py-1.5 capitalize transition", risk === r ? "bg-lime text-ink shadow-sm" : "text-graphite hover:bg-white")}>
                {r}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-4">
            <div className="relative size-36 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={split} dataKey="pct" innerRadius={42} outerRadius={66} paddingAngle={2} stroke="none" isAnimationActive={false}>
                    {split.map((b) => (
                      <Cell key={b.key} fill={b.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-[10px] text-pewter">per month</span>
                <span className="font-display text-sm font-semibold tnum text-ink">{formatCurrency(plan.surplus)}</span>
              </div>
            </div>
            <ul className="grid min-w-0 flex-1 gap-1.5 text-xs">
              {split.map((b) => (
                <li key={b.key} className="flex items-center justify-between gap-2">
                  <a href={b.link.href} target="_blank" rel="noopener noreferrer" title={b.link.label} className="flex min-w-0 items-center gap-2 text-graphite hover:text-ink">
                    <i className="size-2.5 shrink-0 rounded-full" style={{ background: b.color }} />
                    <span className="truncate underline-offset-2 hover:underline">{b.label}</span>
                    <ExternalLink className="size-3 shrink-0 text-pewter" />
                  </a>
                  <span className="font-semibold tnum text-ink">{b.pct}% · {formatCurrency(b.amount)}</span>
                </li>
              ))}
            </ul>
          </div>
          <p className="text-[11px] leading-snug text-pewter">
            An illustrative starting split from general rules of thumb, not personal advice. Check fund details and fees on the platform, and consider a SEBI-registered adviser for your situation.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
