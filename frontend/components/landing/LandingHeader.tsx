"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SignInButton } from "@/components/SignInButton";
import { FinPilotLogo } from "@/components/FinPilotLogo";

/** Sticky glass header; hairline + shadow appear once the page scrolls. */
export function LandingHeader() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const link =
    "inline-flex min-h-11 items-center rounded-chip px-2.5 text-xs sm:text-sm font-medium text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ember";

  return (
    <header
      className={`sticky top-0 z-30 w-full backdrop-blur-xl transition-[background-color,box-shadow,border-color] duration-200 border-b ${
        scrolled
          ? "bg-white/85 border-black/[0.06] shadow-[0_4px_24px_rgba(9,10,15,0.05)]"
          : "bg-white/40 border-transparent"
      }`}
    >
      <div className="mx-auto flex w-full max-w-[1240px] items-center justify-between px-4 py-2 sm:px-8">
        <Link href="/" aria-label="FinPilot home" className="flex min-h-11 items-center gap-2">
          <FinPilotLogo variant="horizontal" size={28} showWordmark={true} />
        </Link>
        <div className="flex items-center gap-1 sm:gap-3">
          <Link href="/dashboard" className={link}>
            Dashboard
          </Link>
          <Link href="/copilot" className={link}>
            AI Copilot
          </Link>
          <SignInButton />
        </div>
      </div>
    </header>
  );
}
