"use client";

import React, { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type CurrencyCode = "INR" | "USD" | "EUR" | "GBP" | "AED" | "SGD";

export interface CurrencyConfig {
  code: CurrencyCode;
  symbol: string;
  label: string;
  flag: string;
  rateFromINR: number; // 1 INR in this currency
  locale: string;
}

export const CURRENCIES: Record<CurrencyCode, CurrencyConfig> = {
  INR: {
    code: "INR",
    symbol: "₹",
    label: "Indian Rupee",
    flag: "🇮🇳",
    rateFromINR: 1,
    locale: "en-IN",
  },
  USD: {
    code: "USD",
    symbol: "$",
    label: "US Dollar",
    flag: "🇺🇸",
    rateFromINR: 0.0116, // $1 ≈ ₹86.20
    locale: "en-US",
  },
  EUR: {
    code: "EUR",
    symbol: "€",
    label: "Euro",
    flag: "🇪🇺",
    rateFromINR: 0.0107, // €1 ≈ ₹93.45
    locale: "de-DE",
  },
  GBP: {
    code: "GBP",
    symbol: "£",
    label: "British Pound",
    flag: "🇬🇧",
    rateFromINR: 0.0090, // £1 ≈ ₹111.10
    locale: "en-GB",
  },
  AED: {
    code: "AED",
    symbol: "د.إ",
    label: "UAE Dirham",
    flag: "🇦🇪",
    rateFromINR: 0.0425, // 1 AED ≈ ₹23.53
    locale: "ar-AE",
  },
  SGD: {
    code: "SGD",
    symbol: "S$",
    label: "Singapore Dollar",
    flag: "🇸🇬",
    rateFromINR: 0.0153, // 1 SGD ≈ ₹65.35
    locale: "en-SG",
  },
};

interface CurrencyContextType {
  currency: CurrencyCode;
  setCurrency: (currency: CurrencyCode) => void;
  config: CurrencyConfig;
  formatAmount: (amountInINR: number, options?: { showCents?: boolean }) => string;
}

const CurrencyContext = createContext<CurrencyContextType>({
  currency: "INR",
  setCurrency: () => {},
  config: CURRENCIES.INR,
  formatAmount: (amountInINR: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amountInINR);
  },
});

const STORAGE_KEY = "finpilot_currency";

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<CurrencyCode>("INR");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY) as CurrencyCode | null;
      if (saved && CURRENCIES[saved]) {
        setCurrencyState(saved);
      }
    }
  }, []);

  const setCurrency = (next: CurrencyCode) => {
    setCurrencyState(next);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, next);
      // Dispatch custom event for cross-component sync
      window.dispatchEvent(new CustomEvent("finpilot:currency-change", { detail: next }));
    }
  };

  const config = CURRENCIES[currency] || CURRENCIES.INR;

  const formatAmount = (amountInINR: number, options?: { showCents?: boolean }): string => {
    const converted = amountInINR * config.rateFromINR;
    const isINR = config.code === "INR";
    const maxDigits = options?.showCents ? 2 : isINR || Math.abs(converted) >= 100 ? 0 : 2;

    try {
      return new Intl.NumberFormat(config.locale, {
        style: "currency",
        currency: config.code,
        maximumFractionDigits: maxDigits,
        minimumFractionDigits: options?.showCents ? 2 : 0,
      }).format(converted);
    } catch {
      return `${config.symbol}${Math.round(converted).toLocaleString()}`;
    }
  };

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency, config, formatAmount }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  return useContext(CurrencyContext);
}
