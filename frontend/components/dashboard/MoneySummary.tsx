"use client";

import { useCallback } from "react";
import Link from "next/link";
import { ArrowUpRight, Landmark, Repeat, Sparkles, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { AnswerContract, Debt, RecurringObligation, RecurrenceFrequency } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/shadcn/card";
import { formatCurrency } from "@/lib/format";

const TONES = ["#5f7f0c", "#a6d11a", "#4fe0b0", "#3f7d5c", "#cddaa6"];
const ASSET_TYPES = ["checking", "savings", "investment"];
const PER_MONTH: Record<RecurrenceFrequency, number> = {
  weekly: 52 / 12,
  biweekly: 26 / 12,
  monthly: 1,
  quarterly: 1 / 3,
  annual: 1 / 12,
  irregular: 0,
};

/** Segmented bar: each part's width is its share of the total. */
function ShareBar({ parts }: { parts: { key: string; value: number }[] }) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  return (
    <div className="flex h-3 w-full gap-0.5 overflow-hidden rounded-full" aria-hidden>
      {parts.map((p, i) => (
        <span key={p.key} style={{ width: `${(p.value / total) * 100}%`, background: TONES[i % TONES.length] }} />
      ))}
    </div>
  );
}

function SummaryCard({
  icon: Icon,
  title,
  intro,
  href,
  children,
}: {
  icon: typeof Wallet;
  title: string;
  intro: string;
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2 font-display text-lg">
          <span className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-full bg-lime">
              <Icon className="size-4" />
            </span>
            {title}
          </span>
          <Link href={href} aria-label={`Open ${title}`} className="rounded-full p-1.5 text-pewter hover:bg-fog">
            <ArrowUpRight className="size-4" />
          </Link>
        </CardTitle>
        <CardDescription>{intro}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-end gap-3">{children}</CardContent>
    </Card>
  );
}

function Legend({ rows }: { rows: { key: string; label: string; value: string }[] }) {
  return (
    <ul className="grid gap-1.5 text-xs">
      {rows.map((r, i) => (
        <li key={r.key} className="flex items-center justify-between gap-2">
          <span className="flex min-w-0 items-center gap-2 text-graphite">
            <i className="size-2.5 shrink-0 rounded-full" style={{ background: TONES[i % TONES.length] }} />
            <span className="truncate">{r.label}</span>
          </span>
          <span className="font-semibold tnum text-ink">{r.value}</span>
        </li>
      ))}
    </ul>
  );
}

const Big = ({ children }: { children: React.ReactNode }) => (
  <p className="font-display text-3xl font-semibold tnum text-ink">{children}</p>
);

/** Four side-by-side summaries replacing the long accounts / debts / recurring / insights sections. */
export function MoneySummary({
  userId,
  debts,
  obligations,
  insights,
  connected,
}: {
  userId: string;
  debts: Debt[];
  obligations: RecurringObligation[];
  insights: AnswerContract;
  connected: boolean;
}) {
  const fetchAccounts = useCallback(() => api.accounts(userId), [userId]);
  const { data: accounts } = useAsync(fetchAccounts, [userId]);

  const assets = (accounts ?? []).filter((a) => ASSET_TYPES.includes(a.type) && a.balance > 0);
  const assetTotal = assets.reduce((s, a) => s + a.balance, 0);

  const owed = debts.reduce((s, d) => s + d.principal, 0);
  const minPay = debts.reduce((s, d) => s + d.minimum_payment, 0);
  const topApr = debts.reduce((m, d) => Math.max(m, d.interest_rate_apr), 0);

  const monthly = obligations
    .map((o) => ({ o, m: o.amount * PER_MONTH[o.frequency] }))
    .filter((x) => x.m > 0)
    .sort((a, b) => b.m - a.m);
  const recurringTotal = monthly.reduce((s, x) => s + x.m, 0);

  const actions = insights.recommendations.slice(0, 3);

  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="font-display text-xl font-semibold text-ink">Your money, summarised</h2>
        <p className="text-sm text-graphite">What you hold, what you owe, what repeats each month, and what to do next.</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard icon={Wallet} title="Total amount" intro={`Cash and investments across ${assets.length} accounts.`} href="/connect">
          {assets.length === 0 ? (
            <p className="text-sm text-pewter">Link an account to see your balances.</p>
          ) : (
            <>
              <Big>{formatCurrency(assetTotal)}</Big>
              <ShareBar parts={assets.map((a) => ({ key: a.id, value: a.balance }))} />
              <Legend rows={assets.slice(0, 4).map((a) => ({ key: a.id, label: a.name, value: formatCurrency(a.balance) }))} />
            </>
          )}
        </SummaryCard>

        <SummaryCard icon={Landmark} title="Debts & loans" intro={`${debts.length} accounts. The highest rate is paid down first.`} href="/simulate">
          {debts.length === 0 ? (
            <p className="text-sm text-pewter">No debt on record.</p>
          ) : (
            <>
              <Big>{formatCurrency(owed)}</Big>
              <ShareBar parts={debts.map((d) => ({ key: d.id, value: d.principal }))} />
              <Legend
                rows={[
                  { key: "min", label: "Minimum per month", value: formatCurrency(minPay) },
                  { key: "apr", label: "Highest APR", value: `${topApr.toFixed(1)}%` },
                  { key: "n", label: "Accounts", value: String(debts.length) },
                ]}
              />
            </>
          )}
        </SummaryCard>

        <SummaryCard icon={Repeat} title="Recurring" intro="Bills and subscriptions, as a monthly average." href="/timeline">
          {monthly.length === 0 ? (
            <p className="text-sm text-pewter">No recurring payments found yet.</p>
          ) : (
            <>
              <Big>{formatCurrency(recurringTotal)}</Big>
              <ShareBar parts={monthly.slice(0, 5).map((x) => ({ key: x.o.group_id, value: x.m }))} />
              <Legend rows={monthly.slice(0, 4).map((x) => ({ key: x.o.group_id, label: x.o.merchant, value: formatCurrency(x.m) }))} />
            </>
          )}
        </SummaryCard>

        <SummaryCard icon={Sparkles} title="Recommended actions" intro="The highest-impact next steps from your data." href="/copilot">
          {!connected || actions.length === 0 ? (
            <p className="text-sm text-pewter">Actions show up once your data is connected.</p>
          ) : (
            <ul className="grid gap-2">
              {actions.map((r, i) => (
                <li key={i} className="rounded-2xl bg-tint-lime p-3">
                  <p className="line-clamp-2 text-sm font-medium text-ink">{r.text}</p>
                  <p className="mt-1 text-[11px] text-graphite">{Math.round(r.confidence * 100)}% confidence</p>
                </li>
              ))}
            </ul>
          )}
        </SummaryCard>
      </div>
    </section>
  );
}
