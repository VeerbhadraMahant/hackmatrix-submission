"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

// First match wins. Merchants with no brand domain (rent, salary, EMIs of unnamed lenders) fall back to an initial.
const DOMAINS: [RegExp, string][] = [
  [/uber/i, "uber.com"],
  [/\bola\b/i, "olacabs.com"],
  [/rapido/i, "rapido.bike"],
  [/starbucks/i, "starbucks.in"],
  [/third wave/i, "thirdwavecoffee.in"],
  [/cafe coffee day/i, "cafecoffeeday.com"],
  [/dmart/i, "dmart.in"],
  [/bigbasket/i, "bigbasket.com"],
  [/blinkit/i, "blinkit.com"],
  [/zepto/i, "zeptonow.com"],
  [/nature'?s basket/i, "naturesbasket.co.in"],
  [/swiggy/i, "swiggy.com"],
  [/zomato/i, "zomato.com"],
  [/domino/i, "dominos.co.in"],
  [/barbeque/i, "barbequenation.com"],
  [/amazon prime/i, "primevideo.com"],
  [/amazon/i, "amazon.in"],
  [/netflix/i, "netflix.com"],
  [/spotify/i, "spotify.com"],
  [/hotstar/i, "hotstar.com"],
  [/apple/i, "apple.com"],
  [/myntra/i, "myntra.com"],
  [/nykaa/i, "nykaa.com"],
  [/meesho/i, "meesho.com"],
  [/ajio/i, "ajio.com"],
  [/decathlon/i, "decathlon.in"],
  [/croma/i, "croma.com"],
  [/reliance digital/i, "reliancedigital.in"],
  [/bookmyshow/i, "bookmyshow.com"],
  [/pvr/i, "pvrcinemas.com"],
  [/goibibo/i, "goibibo.com"],
  [/taj hotels/i, "tajhotels.com"],
  [/mumbai metro/i, "mumbaimetro.com"],
  [/indian oil/i, "iocl.com"],
  [/airtel/i, "airtel.in"],
  [/jiofiber|\bjio\b/i, "jio.com"],
  [/tata power/i, "tatapower.com"],
  [/hdfc/i, "hdfcbank.com"],
  [/icici/i, "icicibank.com"],
  [/kotak/i, "kotak.com"],
  [/\bsbi\b/i, "sbi.co.in"],
  [/zerodha/i, "zerodha.com"],
  [/groww/i, "groww.in"],
  [/apollo/i, "apollopharmacy.in"],
  [/pharmeasy/i, "pharmeasy.in"],
  [/practo/i, "practo.com"],
  [/cult\.?fit/i, "cult.fit"],
  [/podar/i, "podareducation.org"],
];

/** Brand logo for a merchant (favicon service by domain), with a coloured initial when none exists or it fails to load. */
export function MerchantLogo({
  merchant,
  color,
  className,
}: {
  merchant: string;
  color: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const domain = DOMAINS.find(([re]) => re.test(merchant))?.[1];
  const box = cn("flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-lg", className);

  if (!domain || failed) {
    return (
      <span className={cn(box, "text-xs font-semibold text-white")} style={{ background: color }}>
        {merchant.slice(0, 1).toUpperCase()}
      </span>
    );
  }
  return (
    <span className={cn(box, "bg-white ring-1 ring-black/[0.06]")}>
      {/* eslint-disable-next-line @next/next/no-img-element -- tiny third-party favicon, no optimisation needed */}
      <img
        src={`https://www.google.com/s2/favicons?domain=${domain}&sz=128`}
        alt=""
        loading="lazy"
        className="size-full object-contain p-1"
        onError={() => setFailed(true)}
      />
    </span>
  );
}
