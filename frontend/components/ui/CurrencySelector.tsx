"use client";

import React, { useState, useRef, useEffect } from "react";
import { Coins, ChevronDown, Check } from "lucide-react";
import { useCurrency, CURRENCIES, type CurrencyCode } from "@/lib/currency";
import { cn } from "@/lib/utils";

export function CurrencySelector() {
  const { currency, setCurrency } = useCurrency();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const active = CURRENCIES[currency] || CURRENCIES.INR;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border border-mist bg-paper/80 backdrop-blur-md text-xs font-semibold text-ink shadow-[0_1px_3px_rgba(0,0,0,0.03)] hover:border-black/20 transition-all cursor-pointer",
          open && "border-navy ring-1 ring-navy/30"
        )}
        aria-label="Select currency"
        aria-expanded={open}
      >
        <span className="text-xs">{active.flag}</span>
        <span className="font-bold text-ink">{active.code}</span>
        <span className="text-[11px] text-pewter font-normal hidden sm:inline">({active.symbol})</span>
        <ChevronDown className="h-3 w-3 text-pewter transition-transform" />
      </button>

      {open && (
        <div className="absolute right-0 mt-1.5 w-48 rounded-xl border border-mist bg-paper shadow-xl p-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-pewter border-b border-black/[0.04] mb-1">
            Display Currency
          </div>
          <div className="flex flex-col gap-0.5">
            {(Object.keys(CURRENCIES) as CurrencyCode[]).map((code) => {
              const item = CURRENCIES[code];
              const isSelected = item.code === currency;

              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => {
                    setCurrency(code);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex items-center justify-between w-full px-2.5 py-1.5 rounded-lg text-xs transition-colors text-left cursor-pointer",
                    isSelected
                      ? "bg-fog font-bold text-ink"
                      : "text-graphite hover:bg-fog/60 hover:text-ink font-medium"
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{item.flag}</span>
                    <div>
                      <span className="font-semibold text-ink">{item.code}</span>
                      <span className="text-[10px] text-pewter ml-1 font-normal">
                        ({item.symbol})
                      </span>
                    </div>
                  </div>
                  {isSelected && <Check className="h-3.5 w-3.5 text-ember" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
