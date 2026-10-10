"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Banknote, Download, FileText, Link2, LineChart, Sheet, Unlink, type LucideIcon } from "lucide-react";
import { api } from "@/lib/api";
import type { Connector } from "@/lib/types";
import { useConnectors } from "@/lib/connectors";
import { formatDate } from "@/lib/format";
import { Button } from "@/components/shadcn/button";
import { Badge } from "@/components/shadcn/badge";
import { Card, CardContent } from "@/components/shadcn/card";
import { Skeleton } from "@/components/shadcn/skeleton";
import { LinkGooglePayDialog } from "@/components/connect/LinkGooglePayDialog";
import { LinkSheetDialog } from "@/components/connect/LinkSheetDialog";
import { AddCardDialog } from "@/components/connect/AddCardDialog";
import { WalletCardsIcon } from "@animateicons/react/lucide";
import { LoopIcon } from "@/components/ui/LoopIcon";
import { GooglePayMark } from "@/components/connect/GooglePayMark";

const ICONS: Record<string, { icon: LucideIcon; tone: string }> = {
  bank: { icon: Banknote, tone: "bg-tint-sky text-sky" },
  invoices: { icon: FileText, tone: "bg-tint-ember text-ember-dark" },
  investments: { icon: LineChart, tone: "bg-tint-leaf text-leaf" },
  google_sheets: { icon: Sheet, tone: "bg-tint-leaf text-leaf" },
};

function ConnectorCard({
  c,
  onLink,
  onUnlink,
  onExport,
}: {
  c: Connector;
  onLink: () => void;
  onUnlink: () => void;
  onExport: () => void;
}) {
  const meta = ICONS[c.id];
  return (
    <Card className="relative gap-4 overflow-hidden py-5">
      {c.connected && <div className="absolute inset-x-0 top-0 h-1 bg-lime" />}
      <CardContent className="grid gap-4 px-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex h-12 min-w-12 items-center justify-center rounded-2xl bg-fog px-3">
            {c.id === "google_pay" ? (
              <GooglePayMark className="text-lg" />
            ) : (
              meta && <meta.icon className={`size-6 ${meta.tone.split(" ")[1]}`} />
            )}
          </div>
          {c.connected ? (
            <Badge className="bg-leaf/15 text-leaf hover:bg-leaf/15">Connected</Badge>
          ) : c.available ? (
            <Badge variant="outline">Ready</Badge>
          ) : (
            <Badge variant="secondary">Coming soon</Badge>
          )}
        </div>
        <div>
          <h3 className="font-display text-lg font-semibold text-ink">{c.name}</h3>
          <p className="text-sm text-graphite">{c.description}</p>
          {c.connected && c.connected_at && (
            <p className="mt-1 text-xs text-pewter">
              {c.detail ? `${c.detail} · ` : ""}linked {formatDate(c.connected_at)}
            </p>
          )}
        </div>
        {c.connected ? (
          <div className="flex gap-2">
            <Button variant="outline" className="flex-1 rounded-full" onClick={onExport}>
              <Download /> Export
            </Button>
            <Button variant="outline" className="flex-1 rounded-full" onClick={onUnlink}>
              <Unlink /> Disconnect
            </Button>
          </div>
        ) : (
          <Button
            disabled={!c.available}
            onClick={onLink}
            className="rounded-full bg-lime text-ink hover:bg-lime/85 disabled:bg-fog disabled:text-pewter"
          >
            <Link2 /> {c.available ? "Connect" : "Coming soon"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export function ConnectorsGrid() {
  const { data, loading, error, userId } = useConnectors();
  const [dialog, setDialog] = useState(false);
  const [cardDialog, setCardDialog] = useState(false);
  const [sheetDialog, setSheetDialog] = useState(false);

  async function unlink(c: Connector) {
    try {
      await api.disconnectConnector(userId, c.id);
      toast(`${c.name} disconnected. Imported data was removed.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not disconnect");
    }
  }

  async function link(c: Connector) {
    if (c.id === "google_pay") return setDialog(true);
    if (c.id === "google_sheets") return setSheetDialog(true);
    try {
      await api.connectConnector(userId, c.id, "priya");
      toast(`${c.name} connected.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not connect");
    }
  }

  async function exportData(c: Connector) {
    try {
      await api.exportConnector(userId, c.id);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not export");
    }
  }

  if (error) return <p className="text-sm text-rose-badge">Could not load connectors: {error}</p>;
  if (loading && !data)
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-52 rounded-card" />
        ))}
      </div>
    );

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {data?.map((c) => (
          <ConnectorCard key={c.id} c={c} onLink={() => link(c)} onUnlink={() => unlink(c)} onExport={() => exportData(c)} />
        ))}
        <button
          type="button"
          onClick={() => setCardDialog(true)}
          className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed border-lime-dark/60 bg-tint-lime p-5 text-ink transition hover:bg-lime/40"
        >
          <span className="flex size-14 items-center justify-center rounded-full bg-lime">
            <LoopIcon icon={WalletCardsIcon} size={28} />
          </span>
          <span className="font-display text-lg font-semibold">Add a card</span>
          <span className="text-xs text-graphite">Credit or debit, demo only</span>
        </button>
      </div>
      <AddCardDialog open={cardDialog} onOpenChange={setCardDialog} />
      <LinkSheetDialog open={sheetDialog} onOpenChange={setSheetDialog} userId={userId} />
      <LinkGooglePayDialog open={dialog} onOpenChange={setDialog} userId={userId} />
    </>
  );
}
