"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheckIcon } from "@animateicons/react/lucide";
import { onAuthChange } from "@/lib/firebase/auth";
import { isDemoMode } from "@/lib/user";
import { LoadingMark } from "@/components/ui/LoopIcon";

/** Renders nothing of the app (no shell, no data fetches) until a Firebase user is signed in; otherwise sends the visitor to /login. */
export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<"checking" | "in" | "out">("checking");

  useEffect(() => onAuthChange((user) => setState(user || isDemoMode() ? "in" : "out")), []);
  useEffect(() => {
    if (state === "out") router.replace("/login");
  }, [state, router]);

  if (state !== "in") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingMark icon={ShieldCheckIcon} label={state === "out" ? "Redirecting to sign in" : "Checking your session"} />
      </div>
    );
  }
  return <>{children}</>;
}
