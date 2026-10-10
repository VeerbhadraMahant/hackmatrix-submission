// Deterministic month-by-month scenario engine. No LLM arithmetic: every number on the
// comparison page comes from here.
//
// closing cash = opening + income - expenses - debt payments - savings transfers
// Savings transfers move cash into a separate balance (net worth is unchanged by them).
// Debt interest accrues monthly at APR/12 on the opening balance.

export interface Baseline {
  income: number;
  /** Non-debt monthly spending (essential + discretionary). */
  expenses: number;
  /** Part of `expenses` that can be cut. */
  discretionary: number;
  cash: number;
  debt: number;
  aprPct: number;
  /** Required monthly debt payment (paid under every scenario). */
  minPayment: number;
  /** Emergency reserve; months closing below it are flagged. */
  reserve: number;
}

export interface ScenarioActions {
  cutDiscretionary: number;
  extraDebt: number;
  extraSavings: number;
  incomeChange: number;
  /** First month (1-based) the actions apply. */
  startMonth: number;
}

export interface MonthRow {
  month: number;
  opening: number;
  income: number;
  expenses: number;
  debtPayment: number;
  interest: number;
  savingsTransfer: number;
  cash: number;
  debt: number;
  savings: number;
  belowReserve: boolean;
}

export interface SimResult {
  rows: MonthRow[];
  endCash: number;
  endDebt: number;
  endSavings: number;
  totalInterest: number;
  /** Cash + savings - debt. */
  netWorth: number;
  firstBreachMonth: number | null;
}

export function simulate(base: Baseline, a: ScenarioActions, months: number): SimResult {
  let cash = base.cash;
  let debt = base.debt;
  let savings = 0;
  let totalInterest = 0;
  let firstBreachMonth: number | null = null;
  const rows: MonthRow[] = [];

  for (let m = 1; m <= months; m++) {
    const on = m >= a.startMonth;
    const opening = cash;
    const income = base.income + (on ? a.incomeChange : 0);
    const cut = on ? Math.min(Math.max(a.cutDiscretionary, 0), base.discretionary) : 0;
    const expenses = base.expenses - cut;

    const interest = (debt * base.aprPct) / 100 / 12;
    totalInterest += interest;
    const owed = debt + interest;
    const required = Math.min(base.minPayment, owed);
    const extra = on ? Math.min(Math.max(a.extraDebt, 0), owed - required) : 0;
    const debtPayment = required + extra;
    const savingsTransfer = on ? Math.max(a.extraSavings, 0) : 0;

    cash = opening + income - expenses - debtPayment - savingsTransfer;
    debt = owed - debtPayment;
    savings += savingsTransfer;

    const belowReserve = cash < base.reserve;
    if (belowReserve && firstBreachMonth === null) firstBreachMonth = m;
    rows.push({ month: m, opening, income, expenses, debtPayment, interest, savingsTransfer, cash, debt, savings, belowReserve });
  }

  return {
    rows,
    endCash: cash,
    endDebt: debt,
    endSavings: savings,
    totalInterest,
    netWorth: cash + savings - debt,
    firstBreachMonth,
  };
}
