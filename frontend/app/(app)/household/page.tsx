"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowRightLeft,
  Check,
  CheckCircle2,
  Clock,
  Coins,
  Copy,
  CreditCard,
  Heart,
  Link2,
  Mail,
  Plus,
  Receipt,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  Wallet,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAsync, useUserId } from "@/lib/hooks";
import type { HouseholdRole, HouseholdSummary } from "@/lib/types";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { Skeleton } from "@/components/ui/Skeleton";
import { triggerConfetti } from "@/components/ui/Confetti";
import { formatCurrency, formatDate } from "@/lib/format";

export default function HouseholdPage() {
  const userId = useUserId();
  const fetchHousehold = useCallback(() => api.household(userId), [userId]);

  const { data: householdData, error, loading, reload } = useAsync(fetchHousehold, [userId]);

  // Create Household State
  const [householdName, setHouseholdName] = useState("");
  const [creatingHh, setCreatingHh] = useState(false);
  const [createHhError, setCreateHhError] = useState<string | null>(null);

  // Accept Token State
  const [acceptToken, setAcceptToken] = useState("");
  const [acceptingToken, setAcceptingToken] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

  // Invite Member State
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<HouseholdRole>("editor");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [generatedInviteLink, setGeneratedInviteLink] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  // Member & Invite Management Actions
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [removingUserId, setRemovingUserId] = useState<string | null>(null);

  // Shared Expense Split State ("Who Owes Who")
  const [sharedExpenses, setSharedExpenses] = useState<
    Array<{
      id: string;
      title: string;
      amount: number;
      paidBy: string;
      paidByUserId: string;
      splitRatio: string;
      category: string;
      date: string;
    }>
  >([
    { id: "se-1", title: "Apartment Rent & Society Maintenance", amount: 48000, paidBy: "Priya", paidByUserId: "demo-priya", splitRatio: "50/50", category: "Housing", date: "2026-10-01" },
    { id: "se-2", title: "Monthly Organic Groceries", amount: 16400, paidBy: "Arjun", paidByUserId: "demo-arjun", splitRatio: "50/50", category: "Groceries", date: "2026-10-02" },
    { id: "se-3", title: "High-speed Fiber & Power Utilities", amount: 4200, paidBy: "Arjun", paidByUserId: "demo-arjun", splitRatio: "50/50", category: "Utilities", date: "2026-10-03" },
    { id: "se-4", title: "Weekend Dining & Entertainment", amount: 6800, paidBy: "Priya", paidByUserId: "demo-priya", splitRatio: "50/50", category: "Dining", date: "2026-10-03" },
  ]);

  const [newExpTitle, setNewExpTitle] = useState("");
  const [newExpAmount, setNewExpAmount] = useState("");
  const [newExpPayer, setNewExpPayer] = useState("Priya");
  const [newExpCategory, setNewExpCategory] = useState("Groceries");
  const [settledSuccess, setSettledSuccess] = useState<string | null>(null);

  async function handleCreateHousehold() {
    if (!householdName.trim()) {
      setCreateHhError("Please enter a household name.");
      return;
    }
    setCreatingHh(true);
    setCreateHhError(null);
    try {
      await api.createHousehold(userId, { name: householdName.trim() });
      setHouseholdName("");
      triggerConfetti({ count: 70 });
      reload();
    } catch (err) {
      setCreateHhError(err instanceof Error ? err.message : "Failed to create household");
    } finally {
      setCreatingHh(false);
    }
  }

  async function handleAcceptInvite() {
    if (!acceptToken.trim()) {
      setAcceptError("Please enter an invitation token.");
      return;
    }
    setAcceptingToken(true);
    setAcceptError(null);
    try {
      await api.acceptInvite(userId, acceptToken.trim());
      setAcceptToken("");
      triggerConfetti({ count: 80 });
      reload();
    } catch (err) {
      setAcceptError(err instanceof Error ? err.message : "Could not accept invite. Invalid or expired token.");
    } finally {
      setAcceptingToken(false);
    }
  }

  function handleAddSharedExpense(e: React.FormEvent) {
    e.preventDefault();
    const amt = Number(newExpAmount);
    if (!newExpTitle.trim() || !amt || amt <= 0) return;

    const newId = `se-${Date.now()}`;
    const payerUserId = newExpPayer === "Arjun" ? "demo-arjun" : "demo-priya";

    setSharedExpenses((prev) => [
      {
        id: newId,
        title: newExpTitle.trim(),
        amount: amt,
        paidBy: newExpPayer,
        paidByUserId: payerUserId,
        splitRatio: "50/50",
        category: newExpCategory,
        date: new Date().toISOString().split("T")[0],
      },
      ...prev,
    ]);

    setNewExpTitle("");
    setNewExpAmount("");
  }

  function handleSettleUp(debtorName: string, creditorName: string, amount: number) {
    triggerConfetti({ count: 90 });
    setSettledSuccess(`Settlement of ${formatCurrency(amount)} recorded between ${debtorName} and ${creditorName}! 🎉`);
    setTimeout(() => setSettledSuccess(null), 5000);
  }

  async function handleCreateInvite() {
    if (!inviteEmail.trim() || !inviteEmail.includes("@")) {
      setInviteError("Please enter a valid partner email address.");
      return;
    }
    setInviting(true);
    setInviteError(null);
    setGeneratedInviteLink(null);
    try {
      const res = await api.createInvite(userId, { email: inviteEmail.trim(), role: inviteRole });
      setInviteEmail("");
      if (res.token) {
        const fullLink = `${typeof window !== "undefined" ? window.location.origin : ""}/household?invite=${res.token}`;
        setGeneratedInviteLink(fullLink);
      }
      reload();
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : "Failed to generate invite");
    } finally {
      setInviting(false);
    }
  }

  function handleCopyInviteLink() {
    if (!generatedInviteLink) return;
    navigator.clipboard.writeText(generatedInviteLink);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  }

  async function handleRevokeInvite(inviteId: string) {
    setRevokingId(inviteId);
    try {
      await api.revokeInvite(userId, inviteId);
      reload();
    } catch (err) {
      console.error("Revoke error:", err);
    } finally {
      setRevokingId(null);
    }
  }

  async function handleRemoveMember(targetUserId: string) {
    setRemovingUserId(targetUserId);
    try {
      await api.removeMember(userId, targetUserId);
      reload();
    } catch (err) {
      console.error("Remove member error:", err);
    } finally {
      setRemovingUserId(null);
    }
  }

  const household = householdData?.household;
  const members = householdData?.members ?? [];
  const invites = householdData?.invites ?? [];
  const nwSummary = householdData?.net_worth_summary;
  const userRole = householdData?.user_role ?? "viewer";
  const isOwner = userRole === "owner";
  const canInvite = userRole === "owner" || userRole === "editor";

  return (
    <div className="flex flex-col gap-8 pb-16 max-w-6xl mx-auto">
      {/* Editorial Fraunces Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-black/[0.04]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded-full border border-rose-200 flex items-center gap-1">
              <Heart className="h-3 w-3 fill-rose-600 text-rose-600 inline" />
              Co-Piloting Hub
            </span>
            <span className="text-xs text-pewter font-medium">• Multi-Player Household Clarity</span>
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-medium text-ink mt-1.5 tracking-tight">
            {household ? household.name : "Household Financial Co-Pilot"}
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-graphite max-w-2xl leading-relaxed">
            Consolidate net worth across partners, assign granular permissions, and share unified financial visibility with cryptographic invitation security.
          </p>
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && !householdData && (
        <div className="flex flex-col gap-5 animate-pulse">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} className="p-6 flex flex-col gap-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-8 w-40" />
              </Card>
            ))}
          </div>
          <Card className="p-8">
            <Skeleton className="h-40 w-full" />
          </Card>
        </div>
      )}

      {/* No Household State (Setup / Join) */}
      {!loading && !household && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Create New Household Card */}
          <Card className="p-6 border border-black/[0.08] shadow-xs flex flex-col justify-between gap-5">
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-rose-50 border border-rose-200 text-rose-600">
                  <Users className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-ink">Create a Household</h3>
                  <p className="text-xs text-graphite">Start a shared co-pilot hub for your family or partnership.</p>
                </div>
              </div>

              <div className="flex flex-col gap-1.5 mt-2">
                <label htmlFor="hh-name" className="text-xs font-medium text-graphite">
                  Household Name
                </label>
                <input
                  id="hh-name"
                  type="text"
                  placeholder="e.g. Priya & Partner Family"
                  value={householdName}
                  onChange={(e) => {
                    setHouseholdName(e.target.value);
                    if (createHhError) setCreateHhError(null);
                  }}
                  className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-sm text-ink placeholder:text-pewter focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
                />
              </div>

              {createHhError && (
                <p className="text-xs font-semibold text-rose-700 bg-rose-50 px-3 py-2 rounded-chip border border-rose-200">
                  {createHhError}
                </p>
              )}
            </div>

            <Button
              variant="primary"
              onClick={handleCreateHousehold}
              disabled={creatingHh}
              className="h-10 text-xs font-semibold"
            >
              <Plus className="h-4 w-4" />
              <span>{creatingHh ? "Creating..." : "Establish Household"}</span>
            </Button>
          </Card>

          {/* Accept Invitation Code Card */}
          <Card className="p-6 border border-black/[0.08] shadow-xs flex flex-col justify-between gap-5">
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-600">
                  <UserPlus className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-ink">Join Existing Household</h3>
                  <p className="text-xs text-graphite">Enter the secure invite token or link provided by your partner.</p>
                </div>
              </div>

              <div className="flex flex-col gap-1.5 mt-2">
                <label htmlFor="invite-token" className="text-xs font-medium text-graphite">
                  Invitation Token
                </label>
                <input
                  id="invite-token"
                  type="text"
                  placeholder="e.g. demo-partner-token-rohan"
                  value={acceptToken}
                  onChange={(e) => {
                    setAcceptToken(e.target.value);
                    if (acceptError) setAcceptError(null);
                  }}
                  className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-sm text-ink placeholder:text-pewter focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                />
              </div>

              {acceptError && (
                <p className="text-xs font-semibold text-rose-700 bg-rose-50 px-3 py-2 rounded-chip border border-rose-200">
                  {acceptError}
                </p>
              )}
            </div>

            <Button
              variant="secondary"
              onClick={handleAcceptInvite}
              disabled={acceptingToken}
              className="h-10 text-xs font-semibold"
            >
              <UserCheck className="h-4 w-4" />
              <span>{acceptingToken ? "Verifying..." : "Accept & Join Household"}</span>
            </Button>
          </Card>
        </div>
      )}

      {/* Active Household Dashboard View */}
      {household && nwSummary && (
        <div className="flex flex-col gap-8">
          {/* Top Hero KPI Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-5 border border-black/[0.08] shadow-xs">
              <span className="text-[11px] font-bold uppercase tracking-wider text-pewter block">
                Combined Net Worth
              </span>
              <span className="font-display text-2xl sm:text-3xl font-bold text-ink block mt-1 tnum">
                {formatCurrency(nwSummary.total_net_worth)}
              </span>
              <div className="flex items-center gap-3 text-xs text-graphite mt-2">
                <span className="text-emerald-700 font-semibold tnum">
                  +{formatCurrency(nwSummary.total_assets)} assets
                </span>
                <span className="text-rose-700 font-semibold tnum">
                  -{formatCurrency(nwSummary.total_liabilities)} debt
                </span>
              </div>
            </Card>

            <Card className="p-5 border border-black/[0.08] shadow-xs">
              <span className="text-[11px] font-bold uppercase tracking-wider text-pewter block">
                Active Co-Pilots
              </span>
              <span className="font-display text-2xl sm:text-3xl font-bold text-ink block mt-1">
                {members.length} {members.length === 1 ? "Member" : "Members"}
              </span>
              <p className="text-xs text-graphite mt-2">
                Unified visibility across {members.map((m) => m.display_name).join(" & ")}
              </p>
            </Card>

            <Card className="p-5 border border-black/[0.08] shadow-xs flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-pewter block">
                  Your Access Tier
                </span>
                <div className="flex items-center gap-2 mt-1.5">
                  <Chip
                    tone={isOwner ? "accent" : userRole === "editor" ? "success" : "neutral"}
                    className="text-xs font-bold uppercase tracking-wider"
                  >
                    {userRole === "owner" && <ShieldCheck className="h-3 w-3 mr-1" />}
                    {userRole === "editor" && <Shield className="h-3 w-3 mr-1" />}
                    {userRole.toUpperCase()} ROLE
                  </Chip>
                </div>
              </div>
              <p className="text-[11px] text-pewter mt-2">
                {isOwner
                  ? "Full administrative control, invite creation & member management"
                  : userRole === "editor"
                  ? "Can edit shared envelopes, goals, and generate partner invites"
                  : "Read-only access to household financial reports"}
              </p>
            </Card>
          </div>

          {/* Shared Wealth Contribution Split */}
          <Card className="p-6 border border-black/[0.08] shadow-xs flex flex-col gap-5">
            <CardHeader className="mb-0">
              <div className="flex items-center justify-between w-full">
                <div>
                  <CardTitle className="text-base font-semibold text-ink">
                    Household Wealth Split & Contributions
                  </CardTitle>
                  <p className="text-xs text-graphite mt-0.5">
                    Proportional balance contributed across member savings, investments, and liabilities.
                  </p>
                </div>
              </div>
            </CardHeader>

            {/* Split Progress Bar */}
            <div className="flex flex-col gap-2">
              <div className="h-3 w-full rounded-full bg-fog overflow-hidden flex border border-black/[0.04]">
                {nwSummary.members_breakdown.map((mb, idx) => {
                  const colors = ["#ff5900", "#059669", "#4f46e5", "#d97706"];
                  const barColor = colors[idx % colors.length];
                  return (
                    <motion.div
                      key={mb.user_id}
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.max(5, mb.pct_of_household)}%` }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      className="h-full relative first:rounded-l-full last:rounded-r-full"
                      style={{ backgroundColor: barColor }}
                      title={`${mb.display_name}: ${mb.pct_of_household}%`}
                    />
                  );
                })}
              </div>

              {/* Legend Row */}
              <div className="flex flex-wrap items-center gap-4 text-xs select-none">
                {nwSummary.members_breakdown.map((mb, idx) => {
                  const colors = ["#ff5900", "#059669", "#4f46e5", "#d97706"];
                  const barColor = colors[idx % colors.length];
                  return (
                    <div key={mb.user_id} className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: barColor }} />
                      <span className="font-semibold text-ink">{mb.display_name}</span>
                      <span className="text-pewter font-medium tnum">({mb.pct_of_household}%)</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Individual Member Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-2">
              {nwSummary.members_breakdown.map((mb) => (
                <div
                  key={mb.user_id}
                  className="p-4 rounded-surface bg-fog/70 border border-black/[0.04] flex flex-col justify-between gap-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-lime text-ink font-bold flex items-center justify-center text-xs">
                        {mb.display_name.slice(0, 1)}
                      </div>
                      <div>
                        <p className="text-xs font-bold text-ink leading-tight">{mb.display_name}</p>
                        <p className="text-[10px] text-pewter uppercase font-semibold">{mb.role}</p>
                      </div>
                    </div>
                    <span className="text-xs font-bold text-ink bg-white px-2 py-0.5 rounded-full border border-black/[0.06] tnum">
                      {mb.pct_of_household}%
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-black/[0.04]">
                    <div>
                      <span className="text-[10px] text-pewter block uppercase font-medium">Assets</span>
                      <span className="font-bold text-emerald-700 tnum">{formatCurrency(mb.assets)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-pewter block uppercase font-medium">Liabilities</span>
                      <span className="font-bold text-rose-700 tnum">{formatCurrency(mb.liabilities)}</span>
                    </div>
                  </div>

                  <div className="text-xs pt-1 border-t border-black/[0.04] flex items-center justify-between">
                    <span className="text-[10px] text-pewter font-medium uppercase">Net Contributed</span>
                    <span className="font-bold text-ink tnum">{formatCurrency(mb.net_worth)}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Members Table & Invite Partner Row */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Active Members Table (7 cols) */}
            <Card className="lg:col-span-7 p-6 border border-black/[0.08] shadow-xs flex flex-col gap-4">
              <CardHeader className="mb-0">
                <div className="flex items-center justify-between w-full">
                  <div>
                    <CardTitle className="text-base font-semibold text-ink">Household Co-Pilots</CardTitle>
                    <p className="text-xs text-graphite mt-0.5">
                      Active participants with access to this household ledger.
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-pewter uppercase tracking-wider">
                    {members.length} Members
                  </span>
                </div>
              </CardHeader>

              <div className="divide-y divide-black/[0.04]">
                {members.map((m) => {
                  const isCurrent = m.user_id === userId;
                  return (
                    <div key={m.id} className="py-3.5 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-mist text-ink font-bold flex items-center justify-center text-xs shrink-0">
                          {m.avatar_letter || m.display_name?.slice(0, 1) || "U"}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-xs font-bold text-ink">{m.display_name}</p>
                            {isCurrent && (
                              <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded-full border border-emerald-200">
                                You
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-pewter">Joined {formatDate(m.joined_at)}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <Chip
                          tone={m.role === "owner" ? "accent" : m.role === "editor" ? "success" : "neutral"}
                          className="text-[11px] font-semibold capitalize"
                        >
                          {m.role}
                        </Chip>

                        {isOwner && !isCurrent && (
                          <button
                            type="button"
                            onClick={() => handleRemoveMember(m.user_id)}
                            disabled={removingUserId === m.user_id}
                            className="text-pewter hover:text-rose-600 transition-colors p-1.5 rounded-chip hover:bg-rose-50 cursor-pointer disabled:opacity-40"
                            title="Remove member from household"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Invite New Partner Card (5 cols) */}
            <Card className="lg:col-span-5 p-6 border border-black/[0.08] shadow-xs flex flex-col justify-between gap-4">
              <div>
                <CardHeader className="mb-2">
                  <CardTitle className="text-base font-semibold text-ink">Invite Co-Pilot</CardTitle>
                  <p className="text-xs text-graphite mt-0.5">
                    Generate an encrypted invite link for your partner or accountant.
                  </p>
                </CardHeader>

                <div className="flex flex-col gap-3 mt-3">
                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="invite-email" className="text-xs font-medium text-graphite">
                      Partner Email
                    </label>
                    <div className="relative">
                      <Mail className="h-4 w-4 text-pewter absolute left-3 top-2.5 pointer-events-none" />
                      <input
                        id="invite-email"
                        type="email"
                        placeholder="partner@example.com"
                        value={inviteEmail}
                        onChange={(e) => {
                          setInviteEmail(e.target.value);
                          if (inviteError) setInviteError(null);
                        }}
                        className="w-full rounded-chip border border-mist bg-white pl-9 pr-3 py-2 text-xs text-ink placeholder:text-pewter focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
                      />
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="invite-role" className="text-xs font-medium text-graphite">
                      Permission Level
                    </label>
                    <select
                      id="invite-role"
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value as HouseholdRole)}
                      className="w-full rounded-chip border border-mist bg-white px-3 py-2 text-xs text-ink focus:border-ember focus:outline-none"
                    >
                      <option value="editor">Editor — Can manage budgets, goals, and categorize txns</option>
                      <option value="viewer">Viewer — Read-only access to household reports</option>
                    </select>
                  </div>

                  {inviteError && (
                    <p className="text-xs font-semibold text-rose-700 bg-rose-50 px-3 py-2 rounded-chip border border-rose-200">
                      {inviteError}
                    </p>
                  )}

                  {generatedInviteLink && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="p-3 rounded-surface bg-emerald-50/70 border border-emerald-200 flex flex-col gap-2"
                    >
                      <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        <span>Invite Link Generated!</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          readOnly
                          value={generatedInviteLink}
                          className="w-full text-[11px] bg-white border border-emerald-300 rounded px-2 py-1 text-ink select-all"
                        />
                        <button
                          type="button"
                          onClick={handleCopyInviteLink}
                          className="px-2.5 py-1 text-xs font-semibold text-white bg-emerald-700 rounded hover:bg-emerald-800 transition-colors flex items-center gap-1 shrink-0 cursor-pointer"
                        >
                          {copiedLink ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                          <span>{copiedLink ? "Copied" : "Copy"}</span>
                        </button>
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>

              <Button
                variant="primary"
                onClick={handleCreateInvite}
                disabled={inviting || !canInvite}
                className="h-10 text-xs font-semibold w-full mt-2"
              >
                <UserPlus className="h-4 w-4" />
                <span>{inviting ? "Generating..." : "Generate Invite Token"}</span>
              </Button>
            </Card>
          </div>

          {/* Shared Expenses Split & Settlement ("Who Owes Who") */}
          <Card className="p-6 border border-black/[0.08] shadow-xs flex flex-col gap-6">
            <CardHeader className="mb-0">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 w-full">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200 flex items-center gap-1">
                      <ArrowRightLeft className="h-3 w-3" />
                      Shared Expense Ledger
                    </span>
                    <span className="text-xs text-pewter font-medium">• Fairness & Settle-Up Engine</span>
                  </div>
                  <CardTitle className="text-lg font-bold text-ink mt-1">
                    Shared Expenses & Who Owes Who
                  </CardTitle>
                  <p className="text-xs text-graphite mt-0.5">
                    Track recurring shared household expenses, calculate fair splits, and settle balances instantly.
                  </p>
                </div>
              </div>
            </CardHeader>

            {/* Settlement Status Banner */}
            {(() => {
              const totalShared = sharedExpenses.reduce((sum, e) => sum + e.amount, 0);
              const priyaTotal = sharedExpenses.filter((e) => e.paidBy === "Priya").reduce((sum, e) => sum + e.amount, 0);
              const arjunTotal = sharedExpenses.filter((e) => e.paidBy === "Arjun").reduce((sum, e) => sum + e.amount, 0);
              const fairShare = Math.round(totalShared / Math.max(1, members.length || 2));
              const priyaDiff = priyaTotal - fairShare;

              const debtor = priyaDiff > 0 ? "Arjun" : "Priya";
              const creditor = priyaDiff > 0 ? "Priya" : "Arjun";
              const diffAmount = Math.abs(priyaDiff);

              return (
                <div className="flex flex-col gap-4">
                  {settledSuccess && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="p-3.5 rounded-surface bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-900 flex items-center gap-2"
                    >
                      <Sparkles className="h-4 w-4 text-emerald-600" />
                      <span>{settledSuccess}</span>
                    </motion.div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-surface bg-fog/80 border border-black/[0.04] flex flex-col justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-pewter">
                        Total Shared This Cycle
                      </span>
                      <span className="font-display text-xl sm:text-2xl font-bold text-ink mt-1 tnum">
                        {formatCurrency(totalShared)}
                      </span>
                      <span className="text-[11px] text-pewter mt-1">
                        Split 50/50 across {members.length || 2} members ({formatCurrency(fairShare)}/each)
                      </span>
                    </div>

                    <div className="p-4 rounded-surface bg-fog/80 border border-black/[0.04] flex flex-col justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-pewter">
                        Contributions by Payer
                      </span>
                      <div className="flex items-center justify-between text-xs mt-1.5">
                        <span className="font-semibold text-ink">Priya paid:</span>
                        <span className="font-bold text-emerald-700 tnum">{formatCurrency(priyaTotal)}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs mt-1">
                        <span className="font-semibold text-ink">Arjun paid:</span>
                        <span className="font-bold text-indigo-700 tnum">{formatCurrency(arjunTotal)}</span>
                      </div>
                    </div>

                    <div className="p-4 rounded-surface bg-indigo-50/60 border border-indigo-200 flex flex-col justify-between">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-800">
                          Net Settlement Due
                        </span>
                        <div className="font-display text-lg sm:text-xl font-bold text-ink mt-1">
                          {debtor} owes {creditor} <span className="text-indigo-900 tnum">{formatCurrency(diffAmount)}</span>
                        </div>
                      </div>
                      <Button
                        variant="primary"
                        onClick={() => handleSettleUp(debtor, creditor, diffAmount)}
                        className="h-8 text-xs font-semibold mt-3"
                      >
                        <Coins className="h-3.5 w-3.5" />
                        <span>Settle Up {formatCurrency(diffAmount)}</span>
                      </Button>
                    </div>
                  </div>

                  {/* Add Shared Expense Form & Table */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2">
                    {/* Log Shared Expense Form */}
                    <form
                      onSubmit={handleAddSharedExpense}
                      className="lg:col-span-5 p-4 rounded-surface bg-fog/40 border border-black/[0.04] flex flex-col justify-between gap-3"
                    >
                      <div className="flex flex-col gap-2.5">
                        <span className="text-xs font-bold text-ink flex items-center gap-1.5">
                          <Receipt className="h-3.5 w-3.5 text-ember" />
                          Log Shared Household Expense
                        </span>

                        <div className="flex flex-col gap-1">
                          <label className="text-[11px] font-medium text-graphite">Expense Description</label>
                          <input
                            type="text"
                            placeholder="e.g. Electricity Bill, Weekly Market"
                            value={newExpTitle}
                            onChange={(e) => setNewExpTitle(e.target.value)}
                            className="w-full rounded-chip border border-mist bg-white px-3 py-1.5 text-xs text-ink focus:border-ember focus:outline-none"
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] font-medium text-graphite">Amount (₹)</label>
                            <input
                              type="number"
                              placeholder="₹ Amount"
                              value={newExpAmount}
                              onChange={(e) => setNewExpAmount(e.target.value)}
                              className="w-full rounded-chip border border-mist bg-white px-3 py-1.5 text-xs text-ink focus:border-ember focus:outline-none"
                            />
                          </div>

                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] font-medium text-graphite">Paid By</label>
                            <select
                              value={newExpPayer}
                              onChange={(e) => setNewExpPayer(e.target.value)}
                              className="w-full rounded-chip border border-mist bg-white px-2.5 py-1.5 text-xs text-ink focus:border-ember focus:outline-none"
                            >
                              <option value="Priya">Priya</option>
                              <option value="Arjun">Arjun</option>
                            </select>
                          </div>
                        </div>

                        <div className="flex flex-col gap-1">
                          <label className="text-[11px] font-medium text-graphite">Category</label>
                          <select
                            value={newExpCategory}
                            onChange={(e) => setNewExpCategory(e.target.value)}
                            className="w-full rounded-chip border border-mist bg-white px-2.5 py-1.5 text-xs text-ink focus:border-ember focus:outline-none"
                          >
                            <option value="Housing">Housing & Rent</option>
                            <option value="Groceries">Groceries & Household</option>
                            <option value="Utilities">Utilities & Wifi</option>
                            <option value="Dining">Dining & Entertainment</option>
                            <option value="Travel">Travel & Transport</option>
                          </select>
                        </div>
                      </div>

                      <Button type="submit" variant="secondary" className="h-8 text-xs font-semibold w-full mt-1">
                        <Plus className="h-3.5 w-3.5" />
                        <span>Add to Shared Ledger</span>
                      </Button>
                    </form>

                    {/* Shared Expenses Table */}
                    <div className="lg:col-span-7 overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-black/[0.06] text-pewter font-semibold uppercase text-[10px] tracking-wider">
                            <th className="pb-2">Description</th>
                            <th className="pb-2">Payer</th>
                            <th className="pb-2">Split</th>
                            <th className="pb-2 text-right">Amount</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-black/[0.04]">
                          {sharedExpenses.map((exp) => (
                            <tr key={exp.id} className="py-2">
                              <td className="py-2.5">
                                <span className="font-semibold text-ink block">{exp.title}</span>
                                <span className="text-[10px] text-pewter capitalize">{exp.category} • {formatDate(exp.date)}</span>
                              </td>
                              <td className="py-2.5">
                                <span className="font-medium text-ink bg-fog px-2 py-0.5 rounded-full border border-black/[0.04]">
                                  {exp.paidBy}
                                </span>
                              </td>
                              <td className="py-2.5 text-pewter text-[11px]">{exp.splitRatio}</td>
                              <td className="py-2.5 text-right font-bold text-ink tnum">
                                {formatCurrency(exp.amount)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              );
            })()}
          </Card>

          {/* Pending Invitations Table */}
          {invites.length > 0 && (
            <Card className="p-6 border border-black/[0.08] shadow-xs flex flex-col gap-4">
              <CardHeader className="mb-0">
                <div className="flex items-center justify-between w-full">
                  <div>
                    <CardTitle className="text-base font-semibold text-ink">Invitations Sent</CardTitle>
                    <p className="text-xs text-graphite mt-0.5">
                      Pending partner invitations with SHA-256 cryptographic verification.
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-pewter uppercase tracking-wider">
                    {invites.length} Invites
                  </span>
                </div>
              </CardHeader>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-black/[0.06] text-pewter font-semibold uppercase text-[10px] tracking-wider">
                      <th className="pb-2">Invited Email</th>
                      <th className="pb-2">Assigned Role</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2">Sent Date</th>
                      <th className="pb-2">Expires</th>
                      <th className="pb-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-black/[0.04]">
                    {invites.map((inv) => (
                      <tr key={inv.id} className="py-2.5">
                        <td className="py-3 font-semibold text-ink">{inv.invited_email}</td>
                        <td className="py-3 capitalize text-graphite">{inv.role}</td>
                        <td className="py-3">
                          <Chip
                            tone={
                              inv.status === "accepted"
                                ? "success"
                                : inv.status === "pending"
                                ? "warning"
                                : "neutral"
                            }
                            className="text-[10px] font-bold uppercase tracking-wider"
                          >
                            {inv.status}
                          </Chip>
                        </td>
                        <td className="py-3 text-pewter">{formatDate(inv.created_at)}</td>
                        <td className="py-3 text-pewter">{formatDate(inv.expires_at)}</td>
                        <td className="py-3 text-right">
                          {inv.status === "pending" && canInvite && (
                            <button
                              type="button"
                              onClick={() => handleRevokeInvite(inv.id)}
                              disabled={revokingId === inv.id}
                              className="text-xs font-medium text-rose-600 hover:text-rose-800 transition-colors px-2 py-1 rounded hover:bg-rose-50 cursor-pointer disabled:opacity-40"
                            >
                              Revoke
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
