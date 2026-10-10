export function formatCurrency(value: number, currencyCode?: string): string {
  if (typeof window !== "undefined" && !currencyCode) {
    const saved = localStorage.getItem("finpilot_currency");
    if (saved && saved !== "INR") {
      const rates: Record<string, { rate: number; locale: string; code: string }> = {
        USD: { rate: 0.0116, locale: "en-US", code: "USD" },
        EUR: { rate: 0.0107, locale: "de-DE", code: "EUR" },
        GBP: { rate: 0.0090, locale: "en-GB", code: "GBP" },
        AED: { rate: 0.0425, locale: "ar-AE", code: "AED" },
        SGD: { rate: 0.0153, locale: "en-SG", code: "SGD" },
      };
      const cfg = rates[saved];
      if (cfg) {
        return new Intl.NumberFormat(cfg.locale, {
          style: "currency",
          currency: cfg.code,
          maximumFractionDigits: Math.abs(value * cfg.rate) >= 100 ? 0 : 2,
        }).format(value * cfg.rate);
      }
    }
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: currencyCode || "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/**
 * ImpactEstimate.metric is a free-text string from the backend (e.g.
 * "Interest paid (12mo)", "Emergency fund months", "Health score"), so we
 * can't know its unit precisely. Heuristic: metrics whose label suggests a
 * score/rate/percent or whose magnitude is small (months, ratios, score
 * points) render as a plain number; everything else renders as currency.
 */
// Word-boundary matches only -- "months"/"days" as a counted UNIT (e.g.
// "Emergency fund months", "days until first gap") are plain numbers, but
// "monthly" as an ADJECTIVE describing a rupee amount (e.g. "monthly free
// cash flow", "monthly 'dining' spend") must still render as currency. A
// plain substring check on "month" conflated these two and rendered rupee
// amounts like "monthly free cash flow" as a bare number instead of ₹.
const _PLAIN_NUMBER_METRIC_RE = /\b(score|rate|percent|months?|days?)\b/i;

export function formatImpactValue(metric: string, value: number): string {
  const looksLikePlainNumber = _PLAIN_NUMBER_METRIC_RE.test(metric);
  if (looksLikePlainNumber || Math.abs(value) < 50) {
    return Number.isInteger(value) ? value.toString() : value.toFixed(1);
  }
  return formatCurrency(value);
}
