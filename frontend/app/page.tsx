"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { AnswerContractView } from "@/components/AnswerContractView";
import { setUserId, startDemo } from "@/lib/user";
import type { AnswerContract } from "@/lib/types";
import { FloatingOverlapCard } from "@/components/interactive/FloatingOverlapCard";
import { CashFlowChips } from "@/components/interactive/CashFlowChips";
import { InteractiveLineChart } from "@/components/interactive/InteractiveLineChart";
import { SankeyDiagram } from "@/components/interactive/SankeyDiagram";
import { GoalsCards } from "@/components/interactive/GoalsCards";
import { DeviceMockupSection } from "@/components/interactive/DeviceMockupSection";
import { InteractiveBentoGrid } from "@/components/interactive/InteractiveBentoGrid";
import { FeatureShowcase } from "@/components/showcase/FeatureShowcase";
import { FinPilotLogo } from "@/components/FinPilotLogo";
import { LandingHeader } from "@/components/landing/LandingHeader";
import { Reveal } from "@/components/landing/Reveal";
import { ShieldCheck, TrendingUp, Sparkles, CheckCircle2 } from "lucide-react";
import type { ReactNode } from "react";

const PREVIEW_ANSWER: AnswerContract = {
  query: "Can I afford to increase my SIP by ₹3,000/month?",
  narrative:
    "Yes, with room to spare -- your free cash flow comfortably covers the increase, and it meaningfully improves your 12-month trajectory.",
  facts: [
    { text: "Average monthly free cash flow over the last 90 days is ₹18,400.", value: null, source_txn_ids: [] },
    { text: "Current SIP contribution is ₹6,000/month across 2 funds.", value: null, source_txn_ids: [] },
  ],
  predictions: [
    {
      text: "Projected free cash flow next month, after fixed obligations",
      value: 17200,
      range_low: 14800,
      range_high: 19600,
      confidence: 0.81,
      basis: "90-day rolling average, adjusted for known upcoming bills",
    },
  ],
  recommendations: [
    {
      action: "increase_sip",
      text: "Increase SIP by ₹3,000/month",
      rationale: "Stays well within your observed cash-flow buffer even in a below-average month.",
      impact: { metric: "Net worth (5yr projected)", before: 842000, after: 1024000, delta: 182000, horizon: "5 years" },
      confidence: 0.78,
      action_params: {},
    },
  ],
  data_gaps: [],
};

function Section({ children, band = false, className = "" }: { children: ReactNode; band?: boolean; className?: string }) {
  return (
    <section className={`w-full ${band ? "bg-fog/70 border-y border-black/[0.04]" : ""}`}>
      <div className={`mx-auto w-full max-w-[1240px] px-4 py-16 sm:px-8 sm:py-24 ${className}`}>
        <Reveal>{children}</Reveal>
      </div>
    </section>
  );
}

const ICON = "flex h-11 w-11 items-center justify-center rounded-xl mb-5 border";

const PERSONAS = [
  {
    id: "demo-priya",
    initial: "P",
    name: "Priya",
    city: "Bengaluru",
    tag: "High Debt APR",
    avatar: "bg-orange-100 text-ember",
    chip: "text-ember bg-orange-50",
    text: "₹95,000/mo salary with ₹42,000 car loan + high APR credit card balance. Needs debt avalanche strategy.",
  },
  {
    id: "demo-arjun",
    initial: "A",
    name: "Arjun",
    city: "Mumbai",
    tag: "Strong Savings",
    avatar: "bg-emerald-100 text-emerald-700",
    chip: "text-emerald-700 bg-emerald-50",
    text: "₹160,000/mo salary with home loan EMI and twin education obligations. Strong emergency fund.",
  },
  {
    id: "demo-meera",
    initial: "M",
    name: "Meera",
    city: "Pune",
    tag: "Tight Cash Flow",
    avatar: "bg-indigo-100 text-indigo-700",
    chip: "text-indigo-700 bg-indigo-50",
    text: "₹42,000/mo salary with shared rent and student loan. Thin margin for unexpected cash shocks.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col overflow-x-clip">
      <LandingHeader />

      {/* Hero Section */}
      <section className="relative isolate w-full overflow-hidden">
        <div className="landing-grid absolute inset-0 -z-10" aria-hidden />
        <div className="landing-orb absolute -top-24 left-1/2 -z-10 h-[420px] w-[min(900px,100%)] -translate-x-1/2 rounded-full bg-ember-soft blur-3xl pointer-events-none" aria-hidden />
        <div className="mx-auto flex w-full max-w-[1240px] flex-col items-center text-center px-4 pt-16 pb-16 sm:px-8 sm:pt-28 sm:pb-24">
          {/* Status Pill */}
          <Reveal>
            <div className="inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-white/80 px-3.5 py-1.5 text-xs font-medium text-graphite shadow-[0_1px_3px_rgba(0,0,0,0.03)] backdrop-blur-md mb-8">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Fintech Intelligence Engine • 90-Day Cash-Flow Modeling</span>
            </div>
          </Reveal>

          {/* Editorial Headline */}
          <Reveal delay={0.05}>
            <h1 className="font-display max-w-5xl text-[2.5rem] sm:text-6xl md:text-7xl lg:text-[5.5rem] leading-[1.05] text-ink tracking-tight text-balance">
              Your financial health, <br className="hidden sm:block" />
              <span className="italic font-normal text-ember">explained</span> — not just reported.
            </h1>
          </Reveal>

          {/* Subtitle */}
          <Reveal delay={0.1}>
            <p className="mt-7 max-w-2xl text-base sm:text-xl text-graphite leading-relaxed text-pretty">
              FinPilot reads your transactions, forecasts 90-day cash flow with P10/P90 confidence bands,
              and shows the simulated before → after impact of every financial recommendation.
            </p>
          </Reveal>

          {/* CTA Group */}
          <Reveal delay={0.15} className="w-full">
            <div className="mt-10 flex flex-col sm:flex-row flex-wrap items-center justify-center gap-3.5 w-full">
              <Link href="/dashboard" onClick={startDemo} className="w-full sm:w-auto">
                <Button variant="primary" size="lg" className="w-full sm:w-auto px-8 py-3.5 text-base">
                  Explore Live Demo
                  <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </Button>
              </Link>
              <Link href="/simulate" className="w-full sm:w-auto">
                <Button variant="secondary" size="lg" className="w-full sm:w-auto px-6 py-3.5 text-base">
                  Run What-If Simulator
                </Button>
              </Link>
            </div>
          </Reveal>

          {/* Trust Badges */}
          <Reveal delay={0.2}>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3 text-xs text-graphite font-medium">
              {["Zero signup required", "Offline rule router fallback", "Three-lane verified insights"].map((t) => (
                <span key={t} className="flex items-center gap-1.5 rounded-full border border-black/[0.06] bg-white/70 px-3 py-1.5 backdrop-blur">
                  <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  {t}
                </span>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Feature Showcase (Interactive 3-Column Center Stage) */}
      <section className="w-full bg-gradient-to-b from-transparent via-fog/80 to-transparent py-4 sm:py-8">
        <Reveal>
          <FeatureShowcase />
        </Reveal>
      </section>

      {/* Device Mockup Section (Desktop + Phone) */}
      <Section>
        <DeviceMockupSection />
      </Section>

      {/* Floating Overlap Card Section */}
      <Section band>
        <FloatingOverlapCard
          badge="Everyday Spend Intelligence"
          headline="Stay on top of your everyday spending."
          bodyText="Get an effortless breakdown of your finances to see where your money is going and how to improve. We notify you of important pace changes and balance alerts so you are never caught off guard."
          actionText="Track My Spending"
        />
      </Section>

      {/* Interactive Line Chart Section */}
      <Section>
        <InteractiveLineChart
          title="Follow the Line: Real-Time Spending Velocity"
          subtitle="Start your day with a quick look at your spending curve, pending transactions, and budget margin. Scrub across points to inspect daily variance."
        />
      </Section>

      {/* Sankey Cash-Flow Section */}
      <Section band>
        <SankeyDiagram />
      </Section>

      {/* Goals Cards Section */}
      <Section>
        <GoalsCards />
      </Section>

      {/* Cash-Flow Floating Chips Section */}
      <Section band>
        <CashFlowChips
          title="Tactile Cash-Flow Streams"
          subtitle="Explore live inflows, fixed loan obligations, and investment channels. Hover to trigger magnetic repulsion, or drag any chip with spring return physics."
        />
      </Section>

      {/* Interactive Bento Grid Section */}
      <Section>
        <InteractiveBentoGrid />
      </Section>

      {/* Three-Lane Integrity Live Component Preview */}
      <Section band>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-14 lg:items-start">
          <div className="max-w-xl lg:sticky lg:top-28">
            <span className="text-xs font-semibold text-ember uppercase tracking-wider">
              Verified Decision Engine
            </span>
            <h2 className="font-display text-3xl sm:text-4xl text-ink mt-2 text-balance">
              Observed Facts, Predictions &amp; Recommendations
            </h2>
            <p className="mt-3 text-sm sm:text-base text-graphite">
              Every answer is decomposed into three distinct lanes. Zero blurred claims.
            </p>
          </div>
          <Card className="p-6 sm:p-8 min-w-0">
            <AnswerContractView answer={PREVIEW_ANSWER} />
          </Card>
        </div>
      </Section>

      {/* Feature Bento Grid (System Architecture) */}
      <Section>
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="font-display text-3xl sm:text-5xl text-ink text-balance">
            Engineered for financial precision.
          </h2>
          <p className="mt-4 text-sm sm:text-base text-graphite">
            Four specialized engines working in concert to consolidate, forecast, and optimize your wealth.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6">
          {/* Bento 1: 90-Day Forecast */}
          <Card hoverable className="flex flex-col justify-between lg:col-span-2 lg:p-10 bg-gradient-to-br from-white to-ember-soft">
            <div>
              <div className={`${ICON} bg-orange-50 text-ember border-ember/20`}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h3 className="text-lg lg:text-2xl font-semibold text-ink">90-Day Cash-Flow Forecast</h3>
              <p className="mt-2 text-sm lg:text-base text-graphite leading-relaxed lg:max-w-md">
                P10/P50/P90 bootstrap-resampled trajectories. Detects upcoming deficit days weeks before they strike.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-black/[0.04] text-xs font-semibold text-ember">
              P10/P50/P90 Quantiles →
            </div>
          </Card>

          {/* Bento 2: Three-Lane Answer Contract */}
          <Card hoverable className="flex flex-col justify-between">
            <div>
              <div className={`${ICON} bg-blue-50 text-indigo-600 border-indigo-200`}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-ink">Three-Lane Integrity</h3>
              <p className="mt-2 text-sm text-graphite leading-relaxed">
                Every claim is strictly delineated: Observed facts, model Predictions, and actionable Recommendations.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-black/[0.04] text-xs font-semibold text-indigo-600">
              Zero Blurred Claims →
            </div>
          </Card>

          {/* Bento 3: What-If Simulation Engine */}
          <Card hoverable className="flex flex-col justify-between">
            <div>
              <div className={`${ICON} bg-emerald-50 text-emerald-600 border-emerald-200`}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-ink">What-If Simulation</h3>
              <p className="mt-2 text-sm text-graphite leading-relaxed">
                Simulate 8 real financial decisions: prepay loans, cancel subscriptions, or boost SIPs with live before/after deltas.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-black/[0.04] text-xs font-semibold text-emerald-600">
              Live Before & After Diff →
            </div>
          </Card>

          {/* Bento 4: Privacy & Offline Mode */}
          <Card hoverable className="flex flex-col justify-between md:col-span-2 lg:p-10 bg-gradient-to-br from-white to-purple-50/70">
            <div>
              <div className={`${ICON} bg-purple-50 text-purple-600 border-purple-200`}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-lg lg:text-2xl font-semibold text-ink">Complete Data Privacy</h3>
              <p className="mt-2 text-sm lg:text-base text-graphite leading-relaxed lg:max-w-md">
                NVIDIA-hosted AI with a 100% offline rule-based mode toggle. Your financial data stays local.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-black/[0.04] text-xs font-semibold text-purple-600">
              Offline Opt-Out Verified →
            </div>
          </Card>
        </div>
      </Section>

      {/* Demo Personas Section */}
      <Section band>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-12">
          <div>
            <span className="text-xs font-semibold text-ember uppercase tracking-wider">
              Immediate Exploration
            </span>
            <h2 className="font-display text-3xl sm:text-4xl text-ink mt-2 text-balance">
              Test drive on 3 curated personas.
            </h2>
          </div>
          <p className="text-sm text-graphite max-w-md">
            Each persona is pre-loaded with 12 months of realistic transactions, distinct debt structures, and cash-flow characteristics.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 sm:gap-6">
          {PERSONAS.map((p) => (
            <Card key={p.id} hoverable className="flex flex-col justify-between bg-white">
              <div>
                <div className="flex items-center justify-between">
                  <span className={`h-8 w-8 rounded-full font-bold text-xs flex items-center justify-center ${p.avatar}`}>
                    {p.initial}
                  </span>
                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${p.chip}`}>{p.tag}</span>
                </div>
                <h4 className="text-lg font-semibold text-ink mt-3">
                  {p.name} • {p.city}
                </h4>
                <p className="text-xs text-graphite mt-1">{p.text}</p>
              </div>
              <Link
                href="/dashboard"
                onClick={() => setUserId(p.id)}
                className="mt-6 inline-flex min-h-11 items-center gap-1.5 text-xs font-semibold text-ink hover:text-ember transition-colors"
              >
                Load {p.name}&apos;s Snapshot →
              </Link>
            </Card>
          ))}
        </div>
      </Section>

      {/* Bottom CTA Banner */}
      <section className="mx-auto w-full max-w-[1240px] px-4 pt-16 pb-16 sm:px-8 sm:pt-24 sm:pb-24">
        <Reveal>
          <div className="rounded-card border border-ink/10 bg-sage text-ink p-8 sm:p-12 lg:p-14 relative overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.12)]">
            <div className="landing-grid-dark absolute inset-0 pointer-events-none opacity-40" aria-hidden />
            <div className="absolute -right-10 -bottom-10 w-96 h-96 bg-ember/15 rounded-full blur-3xl pointer-events-none" aria-hidden />

            <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
              {/* Left Column: Heading, readable dark text & action buttons */}
              <div className="lg:col-span-7 flex flex-col items-start">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/70 border border-ink/10 text-xs font-bold text-ink uppercase tracking-wider backdrop-blur-sm shadow-xs">
                  <Sparkles className="h-3.5 w-3.5 text-ember" />
                  No Installation Needed
                </span>

                <h2 className="font-display text-3xl sm:text-5xl text-ink mt-4 text-balance font-bold leading-[1.12]">
                  Ready to see FinPilot in action?
                </h2>

                <p className="mt-4 text-sm sm:text-base text-graphite leading-relaxed max-w-xl font-medium">
                  Explore real-time health scoring, 90-day cash-flow forecasting with confidence bands, and simulated impact recommendations now.
                </p>

                <div className="mt-8 flex flex-col sm:flex-row gap-3.5 w-full sm:w-auto">
                  <Link href="/dashboard" className="w-full sm:w-auto">
                    <Button variant="primary" size="lg" className="w-full sm:w-auto px-7 py-3 text-base">
                      Launch Dashboard
                    </Button>
                  </Link>
                  <Link href="/copilot" className="w-full sm:w-auto">
                    <Button variant="secondary" size="lg" className="w-full sm:w-auto bg-white/80 text-ink border-ink/15 hover:bg-white text-base shadow-xs">
                      Ask FinPilot Copilot
                    </Button>
                  </Link>
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-4 text-xs font-semibold text-graphite">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                    Zero setup required
                  </span>
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                    100% Client-side safe
                  </span>
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                    Instant persona load
                  </span>
                </div>
              </div>

              {/* Right Column: Fulfilling Live Metric / Telemetry Snapshot Card */}
              <div className="lg:col-span-5 flex justify-center lg:justify-end">
                <div className="w-full max-w-sm rounded-2xl border border-black/[0.08] bg-white/90 p-5 shadow-[0_12px_32px_rgba(13,13,13,0.08)] backdrop-blur-md">
                  <div className="flex items-center justify-between pb-3 border-b border-black/[0.06]">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-800">
                        <TrendingUp className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-ink leading-tight">Live Forecast Health</p>
                        <p className="text-[10px] text-graphite">Autonomous engine</p>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-bold text-emerald-700 border border-emerald-200">
                      <span className="size-1.5 rounded-full bg-emerald-600 animate-pulse" />
                      94 / 100
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2.5 my-4">
                    <div className="rounded-xl border border-black/[0.06] bg-fog/80 p-2.5">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-pewter block">
                        90-Day Runway
                      </span>
                      <span className="text-base font-bold text-ink tnum mt-0.5 block">
                        8.4 Months
                      </span>
                      <span className="text-[10px] text-emerald-700 font-semibold">
                        Stable buffer
                      </span>
                    </div>

                    <div className="rounded-xl border border-black/[0.06] bg-fog/80 p-2.5">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-pewter block">
                        Safe-to-Spend
                      </span>
                      <span className="text-base font-bold text-ink tnum mt-0.5 block">
                        ₹1,420/day
                      </span>
                      <span className="text-[10px] text-navy font-semibold">
                        Calibrated
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-black/[0.06] bg-fog/60 p-3 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 text-graphite font-medium">
                      <ShieldCheck className="h-4 w-4 text-emerald-700 shrink-0" />
                      <span>Decision integrity verification</span>
                    </div>
                    <span className="font-mono text-[11px] font-bold text-ink">ACTIVE</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* Footer */}
      <footer className="w-full border-t border-black/[0.06]">
        <div className="mx-auto flex w-full max-w-[1240px] flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row sm:px-8">
          <Link href="/" aria-label="FinPilot home" className="flex min-h-11 items-center">
            <FinPilotLogo variant="horizontal" size={24} showWordmark={true} />
          </Link>
          <nav className="flex items-center gap-1 text-sm text-graphite">
            {[
              ["/dashboard", "Dashboard"],
              ["/copilot", "AI Copilot"],
              ["/simulate", "What-If Simulator"],
            ].map(([href, label]) => (
              <Link key={href} href={href} className="inline-flex min-h-11 items-center rounded-chip px-3 hover:text-ink transition-colors">
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>
    </div>
  );
}
