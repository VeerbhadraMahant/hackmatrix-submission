"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";
import {
  signInWithGoogle,
  signInWithEmail,
  signUpWithEmail,
  signOut,
  onAuthChange,
  getMfaResolver,
  finishTotpSignIn,
  authErrorMessage,
} from "@/lib/firebase/auth";
import type { MultiFactorResolver, User } from "firebase/auth";
import { Button } from "@/components/shadcn/button";
import { Input } from "@/components/shadcn/input";
import { FinPilotLogo } from "@/components/FinPilotLogo";

function GoogleIcon() {
  return (
    <svg className="size-5" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [resolver, setResolver] = useState<MultiFactorResolver | null>(null);
  const [mfaCode, setMfaCode] = useState("");

  useEffect(() => {
    const unsubscribe = onAuthChange((user) => {
      setCurrentUser(user);
    });
    return () => unsubscribe();
  }, []);

  async function handleGoogleSignIn() {
    setError(null);
    setLoading(true);
    try {
      await signInWithGoogle();
      router.push("/copilot");
    } catch (err: unknown) {
      const mfa = getMfaResolver(err);
      if (mfa) {
        setResolver(mfa);
        return;
      }
      setError(authErrorMessage(err, "Failed to sign in with Google."));
    } finally {
      setLoading(false);
    }
  }

  async function handleEmailAuth(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      if (isSignUp) {
        await signUpWithEmail(email, password);
        setSuccess("Account created successfully! Redirecting...");
      } else {
        await signInWithEmail(email, password);
        setSuccess("Signed in successfully! Redirecting...");
      }
      setTimeout(() => {
        router.push("/copilot");
      }, 1000);
    } catch (err: unknown) {
      const mfa = getMfaResolver(err);
      if (mfa) {
        setResolver(mfa);
        setSuccess(null);
        return;
      }
      setError(authErrorMessage(err, "Authentication failed."));
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaCode(e: React.FormEvent) {
    e.preventDefault();
    if (!resolver) return;
    setError(null);
    setLoading(true);
    try {
      await finishTotpSignIn(resolver, mfaCode.trim());
      router.push("/copilot");
    } catch (err: unknown) {
      setError(authErrorMessage(err, "Invalid code."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden overflow-hidden bg-sage p-10 text-ink lg:flex lg:flex-col lg:justify-start lg:gap-8">
        <Link
          href="/"
          aria-label="Back to home"
          className="relative flex size-10 items-center justify-center rounded-full bg-white/60 backdrop-blur-sm transition hover:bg-white/70"
        >
          <ArrowLeft className="size-5" />
        </Link>
        <div className="relative max-w-md">
          <h2 className="font-display text-4xl font-semibold leading-tight">
            Your money, on <span className="text-[#5f7f0c]">autopilot</span>.
          </h2>
          <p className="mt-3 text-ink/70">FinPilot connects to your accounts and does the rest.</p>
        </div>
        <div className="relative min-h-0 flex-1 overflow-hidden rounded-3xl">
          <video
            className="pointer-events-none size-full object-cover"
            src="/media/moov.mp4"
            autoPlay
            loop
            muted
            playsInline
            aria-hidden
          />
        </div>
        <p className="relative text-xs text-ink/60">Demo build. Sample data only.</p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6 rounded-3xl bg-white p-8 shadow-[0_24px_60px_-28px_rgba(15,23,42,0.35)]">
          <div className="space-y-2">
            <Link href="/" className="inline-block lg:hidden">
              <FinPilotLogo variant="horizontal" size={32} showWordmark={true} />
            </Link>
            <h1 className="font-display text-3xl font-semibold text-ink">
              {currentUser ? "You are signed in" : isSignUp ? "Create your account" : "Welcome back"}
            </h1>
            <p className="text-sm text-graphite">
              {currentUser ? (
                `Connected as ${currentUser.email || currentUser.uid}`
              ) : (
                <>
                  {isSignUp ? "Already have an account? " : "Don't have an account? "}
                  <button
                    type="button"
                    onClick={() => {
                      setIsSignUp(!isSignUp);
                      setError(null);
                      setSuccess(null);
                    }}
                    className="font-medium text-sky hover:underline"
                  >
                    {isSignUp ? "Sign in" : "Sign up"}
                  </button>
                </>
              )}
            </p>
          </div>

          {currentUser ? (
            <div className="space-y-4">
              <div className="rounded-2xl border border-mist bg-fog p-4 text-xs text-graphite">
                <p className="font-semibold text-ink">{currentUser.displayName || currentUser.email}</p>
                <p className="mt-1 text-[11px] text-pewter">UID: {currentUser.uid}</p>
              </div>
              <div className="flex gap-3">
                <Button size="lg" className="flex-1" onClick={() => router.push("/copilot")}>
                  Go to dashboard
                </Button>
                <Button size="lg" variant="outline" onClick={() => signOut()}>
                  Sign out
                </Button>
              </div>
            </div>
          ) : resolver ? (
            <form onSubmit={handleMfaCode} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="mfa" className="text-sm font-medium text-ink">
                  6-digit code from your authenticator app
                </label>
                <Input
                  id="mfa"
                  inputMode="numeric"
                  required
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="123456"
                  className="h-11 rounded-xl"
                />
              </div>
              {error && (
                <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                  {error}
                </div>
              )}
              <Button type="submit" size="lg" className="w-full" disabled={loading || mfaCode.length !== 6}>
                {loading ? "Verifying..." : "Verify"}
              </Button>
            </form>
          ) : (
            <>
              <form onSubmit={handleEmailAuth} className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-medium text-ink">
                    Email address
                  </label>
                  <Input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    className="h-11 rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="password" className="text-sm font-medium text-ink">
                    Password
                  </label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Password"
                      className="h-11 rounded-xl pr-11"
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-pewter hover:bg-fog"
                    >
                      {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                    {error}
                  </div>
                )}
                {success && (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-700">
                    {success}
                  </div>
                )}

                <Button type="submit" size="lg" className="w-full" disabled={loading}>
                  {loading ? "Authenticating..." : isSignUp ? "Create account" : "Sign in"}
                </Button>
              </form>

              <div className="relative flex items-center justify-center">
                <span className="h-px w-full bg-mist" />
                <span className="absolute bg-white px-2.5 text-xs text-pewter">or</span>
              </div>

              <Button
                type="button"
                variant="outline"
                size="lg"
                className="w-full gap-2.5"
                onClick={handleGoogleSignIn}
                disabled={loading}
              >
                <GoogleIcon />
                Continue with Google
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
