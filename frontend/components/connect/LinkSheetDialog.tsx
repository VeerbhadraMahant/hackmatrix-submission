"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/shadcn/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/shadcn/dialog";

/** Link a Google Sheet (shared as "Anyone with the link can view"); the app then re-reads it every 30 seconds. */
export function LinkSheetDialog({ open, onOpenChange, userId }: { open: boolean; onOpenChange: (open: boolean) => void; userId: string }) {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      await api.connectConnector(userId, "google_sheets", "priya", url);
      toast("Google Sheet connected. Edit the sheet and this app updates within 30 seconds.");
      onOpenChange(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message.replace(/^API .*? failed: \d+ /, "") : "Could not connect");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Connect a Google Sheet</DialogTitle>
          <DialogDescription>
            Your sheet needs columns Date, Description, Amount and (optional) Category. Money coming in is positive, money going out is negative. In Google Sheets
            choose Share, then &quot;Anyone with the link&quot; can view.
          </DialogDescription>
        </DialogHeader>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://docs.google.com/spreadsheets/d/..."
          className="w-full rounded-xl border border-fog bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-lime"
        />
        <Button disabled={busy || !url.trim()} onClick={submit} className="rounded-full bg-lime text-ink hover:bg-lime/85">
          {busy && <Loader2 className="animate-spin" />} Connect
        </Button>
      </DialogContent>
    </Dialog>
  );
}
