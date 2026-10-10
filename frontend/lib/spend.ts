import type { Transaction, TxnCategory } from "@/lib/types";

/** Categories that move money between the user's own accounts, not real spend/income. */
const NON_SPEND: TxnCategory[] = ["transfer", "credit_card_payment", "income"];

export const CATEGORY_META: Record<TxnCategory, { label: string; color: string }> = {
  income: { label: "Income", color: "#12a56b" },
  rent_housing: { label: "Rent & housing", color: "#6d7cf5" },
  emi_loan: { label: "EMI & loans", color: "#e5484d" },
  groceries: { label: "Groceries", color: "#12a56b" },
  dining: { label: "Dining", color: "#ff7a2f" },
  transport: { label: "Transport", color: "#2f7cf6" },
  utilities: { label: "Utilities", color: "#12a5b8" },
  subscriptions: { label: "Subscriptions", color: "#8b5cf6" },
  shopping: { label: "Shopping", color: "#f0647e" },
  healthcare: { label: "Healthcare", color: "#5cc98b" },
  entertainment: { label: "Entertainment", color: "#ffc24b" },
  investment_sip: { label: "Investments", color: "#0e7490" },
  credit_card_payment: { label: "Card payments", color: "#a7a9b4" },
  transfer: { label: "Transfers", color: "#a7a9b4" },
  fees_interest: { label: "Fees & interest", color: "#c2410c" },
  other: { label: "Other", color: "#c9bfa8" },
};

export interface MonthTotals {
  month: string; // YYYY-MM
  label: string; // "Mar"
  income: number;
  spend: number;
  savings: number;
}

export interface CategoryTotal {
  category: TxnCategory;
  label: string;
  color: string;
  total: number;
  prev: number;
  /** % change vs previous month; null when there was no spend before. */
  change: number | null;
}

export interface MerchantTotal {
  merchant: string;
  total: number;
  count: number;
}

export interface SpendSummary {
  months: MonthTotals[];
  latestMonth: string | null;
  categories: CategoryTotal[];
  merchants: MerchantTotal[];
  totalSpend: number;
}

const MONTH_FMT = new Intl.DateTimeFormat("en", { month: "short" });

function monthLabel(month: string): string {
  return MONTH_FMT.format(new Date(`${month}-01T00:00:00`));
}

/** Aggregates raw transactions into monthly, category and merchant totals. Positive amount = inflow. */
export function summarizeSpend(txns: Transaction[], monthsBack = 6): SpendSummary {
  const byMonth = new Map<string, { income: number; spend: number }>();
  for (const t of txns) {
    const key = t.date.slice(0, 7);
    const m = byMonth.get(key) ?? { income: 0, spend: 0 };
    if (t.amount > 0 && t.category === "income") m.income += t.amount;
    else if (t.amount < 0 && !NON_SPEND.includes(t.category)) m.spend += -t.amount;
    byMonth.set(key, m);
  }

  const keys = [...byMonth.keys()].sort().slice(-monthsBack);
  const months: MonthTotals[] = keys.map((month) => {
    const m = byMonth.get(month)!;
    return { month, label: monthLabel(month), income: m.income, spend: m.spend, savings: m.income - m.spend };
  });

  const latestMonth = keys.at(-1) ?? null;
  const prevMonth = keys.at(-2) ?? null;

  const cat = new Map<TxnCategory, { total: number; prev: number }>();
  const merch = new Map<string, MerchantTotal>();
  for (const t of txns) {
    if (t.amount >= 0 || NON_SPEND.includes(t.category)) continue;
    const key = t.date.slice(0, 7);
    const c = cat.get(t.category) ?? { total: 0, prev: 0 };
    if (key === latestMonth) {
      c.total += -t.amount;
      const mm = merch.get(t.merchant) ?? { merchant: t.merchant, total: 0, count: 0 };
      mm.total += -t.amount;
      mm.count += 1;
      merch.set(t.merchant, mm);
    } else if (key === prevMonth) c.prev += -t.amount;
    cat.set(t.category, c);
  }

  const categories: CategoryTotal[] = [...cat.entries()]
    .filter(([, v]) => v.total > 0 || v.prev > 0)
    .map(([category, v]) => ({
      category,
      label: CATEGORY_META[category].label,
      color: CATEGORY_META[category].color,
      total: v.total,
      prev: v.prev,
      change: v.prev > 0 ? ((v.total - v.prev) / v.prev) * 100 : null,
    }))
    .sort((a, b) => b.total - a.total);

  return {
    months,
    latestMonth,
    categories,
    merchants: [...merch.values()].sort((a, b) => b.total - a.total).slice(0, 6),
    totalSpend: categories.reduce((n, c) => n + c.total, 0),
  };
}

export interface WeeklyStack {
  /** Stack segments, bottom to top: biggest categories first, the rest merged into "Other". */
  keys: { key: string; label: string; color: string }[];
  /** One row per Monday-start week: { week: "YYYY-MM-DD", total, [categoryKey]: amount }. */
  rows: ({ week: string; total: number } & Record<string, number | string>)[];
}

const DAY = 86_400_000;

/** Monday (UTC) of the week containing an ISO date, as YYYY-MM-DD. */
function weekStart(date: string): string {
  const d = new Date(`${date.slice(0, 10)}T00:00:00Z`);
  return new Date(d.getTime() - ((d.getUTCDay() + 6) % 7) * DAY).toISOString().slice(0, 10);
}

/** Real spend per week split by category (same spend rules as summarizeSpend), over the last `weeks` weeks of data. */
export function weeklyCategorySpend(txns: Transaction[], weeks = 26, topN = 6): WeeklyStack {
  const spend = txns.filter((t) => t.amount < 0 && !NON_SPEND.includes(t.category));
  if (spend.length === 0) return { keys: [], rows: [] };

  const lastWeek = weekStart(spend.reduce((m, t) => (t.date > m ? t.date : m), spend[0].date));
  const firstWeek = new Date(new Date(`${lastWeek}T00:00:00Z`).getTime() - (weeks - 1) * 7 * DAY).toISOString().slice(0, 10);

  const byWeek = new Map<string, Map<TxnCategory, number>>();
  const totals = new Map<TxnCategory, number>();
  for (const t of spend) {
    const w = weekStart(t.date);
    if (w < firstWeek || w > lastWeek) continue;
    const cats = byWeek.get(w) ?? new Map<TxnCategory, number>();
    cats.set(t.category, (cats.get(t.category) ?? 0) + -t.amount);
    byWeek.set(w, cats);
    totals.set(t.category, (totals.get(t.category) ?? 0) + -t.amount);
  }

  const ranked = [...totals.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c);
  const top = ranked.slice(0, topN);
  const hasOther = ranked.length > topN;
  const keys = top.map((c) => ({ key: c as string, label: CATEGORY_META[c].label, color: CATEGORY_META[c].color }));
  if (hasOther) keys.push({ key: "other_merged", label: "Everything else", color: "#c9bfa8" });

  const rows: WeeklyStack["rows"] = [];
  for (let t = new Date(`${firstWeek}T00:00:00Z`).getTime(); t <= new Date(`${lastWeek}T00:00:00Z`).getTime(); t += 7 * DAY) {
    const week = new Date(t).toISOString().slice(0, 10);
    const cats = byWeek.get(week) ?? new Map<TxnCategory, number>();
    const row: WeeklyStack["rows"][number] = { week, total: 0 };
    for (const k of keys) row[k.key] = 0;
    for (const [c, v] of cats) {
      const k = top.includes(c) ? (c as string) : "other_merged";
      row[k] = (row[k] as number) + v;
      row.total += v;
    }
    rows.push(row);
  }
  return { keys, rows };
}
