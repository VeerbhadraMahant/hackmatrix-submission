"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { CheckCircle2, Loader2, Lock, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { ConnectProfile } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/shadcn/button";
import { Badge } from "@/components/shadcn/badge";
import { Progress } from "@/components/shadcn/progress";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/shadcn/dialog";
import { LockKeyholeIcon } from "@animateicons/react/huge";
import { LoopIcon } from "@/components/ui/LoopIcon";
import { GooglePayMark } from "@/components/connect/GooglePayMark";

const PROFILES: { id: ConnectProfile; name: string; blurb: string; color: string }[] = [
  { id: "priya", name: "Priya", blurb: "Bengaluru · salaried · ₹95k/mo", color: "bg-leaf" },
  { id: "arjun", name: "Arjun", blurb: "Mumbai · senior pro · ₹1.6L/mo", color: "bg-sky" },
  { id: "meera", name: "Meera", blurb: "Pune · early career · ₹42k/mo", color: "bg-ember" },
];

const STEPS = ["Authorising with Google", "Importing UPI payments", "Categorising merchants", "Building your dashboard"];

export function LinkGooglePayDialog({
  open,
  onOpenChange,
  userId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userId: string;
}) {
  const router = useRouter();
  const [profile, setProfile] = useState<ConnectProfile>("priya");
  const [step, setStep] = useState(-1); // -1 = choosing, 0..3 = working, 4 = done

  const working = step >= 0 && step < STEPS.length;

  async function link() {
    setStep(0);
    // Paced so the user sees the sync happen; the real request runs alongside.
    const ticker = setInterval(() => setStep((s) => (s >= 0 && s < STEPS.length - 1 ? s + 1 : s)), 650);
    try {
      const [res] = await Promise.all([
        api.connectConnector(userId, "google_pay", profile),
        new Promise((r) => setTimeout(r, 2200)),
      ]);
      setStep(STEPS.length);
      toast.success(`Google Pay linked: ${res.transactions} transactions imported`);
      setTimeout(() => {
        onOpenChange(false);
        setStep(-1);
        router.push("/dashboard");
      }, 900);
    } catch (e) {
      setStep(-1);
      toast.error(e instanceof Error ? e.message : "Could not link Google Pay");
    } finally {
      clearInterval(ticker);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !working && onOpenChange(o)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <GooglePayMark className="text-2xl" />
            <Badge variant="outline" className="border-ember/40 bg-tint-ember text-ember-dark">Demo</Badge>
          </div>
          <DialogTitle className="font-display text-xl">Link Google Pay</DialogTitle>
          <DialogDescription>
            Demo mode: no real Google account is accessed. Pick a sample profile to import.
          </DialogDescription>
        </DialogHeader>

        {step === -1 && (
          <div className="grid gap-4">
            <div role="radiogroup" aria-label="Sample profile" className="grid gap-2">
              {PROFILES.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  role="radio"
                  aria-checked={profile === p.id}
                  onClick={() => setProfile(p.id)}
                  className={cn(
                    "flex items-center gap-3 rounded-2xl border p-3 text-left transition-all",
                    profile === p.id ? "border-ink bg-tint-lime shadow-sm" : "border-border hover:bg-fog"
                  )}
                >
                  <span className={cn("flex size-10 items-center justify-center rounded-full font-display text-lg font-semibold text-white", p.color)}>
                    {p.name[0]}
                  </span>
                  <span className="flex-1">
                    <span className="block text-sm font-semibold text-ink">{p.name}</span>
                    <span className="block text-xs text-graphite">{p.blurb}</span>
                  </span>
                  {profile === p.id && <CheckCircle2 className="size-5 text-ink" />}
                </button>
              ))}
            </div>
            <ul className="grid gap-1.5 rounded-2xl bg-fog p-3 text-xs text-graphite">
              <li className="flex items-center gap-2"><ShieldCheck className="size-4 text-leaf" /> Read-only: payment history, merchants, balances</li>
              <li className="flex items-center gap-2"><Lock className="size-4 text-leaf" /> Cannot move money. Disconnect any time.</li>
            </ul>
            <Button size="lg" onClick={link} className="rounded-full bg-lime text-ink hover:bg-lime-dark">
              Allow &amp; connect
            </Button>
          </div>
        )}

        {step >= 0 && (
          <div className="grid gap-4 py-2">
            <div className="flex items-center gap-3 rounded-2xl bg-tint-lime p-3 text-sm text-ink">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-lime">
                <LoopIcon icon={LockKeyholeIcon} size={22} every={1600} />
              </span>
              Signing in securely. Your password is never shared with FinPilot.
            </div>
            <Progress value={Math.min(100, ((step + 0.5) / STEPS.length) * 100)} className="h-2" />
            <ul className="grid gap-2.5">
              {STEPS.map((label, i) => (
                <li key={label} className={cn("flex items-center gap-2.5 text-sm", i > step ? "text-pewter" : "text-ink")}>
                  {i < step || step >= STEPS.length ? (
                    <CheckCircle2 className="size-5 text-leaf" />
                  ) : i === step ? (
                    <Loader2 className="size-5 animate-spin text-sky" />
                  ) : (
                    <span className="size-5 rounded-full border border-mist" />
                  )}
                  {label}
                </li>
              ))}
            </ul>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
