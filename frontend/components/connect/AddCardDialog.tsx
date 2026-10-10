"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { CheckIcon, CreditCardIcon, WalletCardsIcon } from "@animateicons/react/lucide";
import { LockKeyholeIcon } from "@animateicons/react/huge";
import { Button } from "@/components/shadcn/button";
import { Input } from "@/components/shadcn/input";
import { Badge } from "@/components/shadcn/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/shadcn/dialog";
import { LoopIcon } from "@/components/ui/LoopIcon";

const digits = (s: string) => s.replace(/\D/g, "");
const fmtNumber = (s: string) => digits(s).slice(0, 16).replace(/(.{4})/g, "$1 ").trim();
const fmtExpiry = (s: string) => {
  const d = digits(s).slice(0, 4);
  return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
};

/** Demo "add a card" form with a live preview. Nothing typed here leaves this component or is stored. */
export function AddCardDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [number, setNumber] = useState("");
  const [name, setName] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvv, setCvv] = useState("");
  const [saved, setSaved] = useState(false);

  const month = Number(expiry.slice(0, 2));
  const valid = digits(number).length === 16 && name.trim() !== "" && expiry.length === 5 && month >= 1 && month <= 12 && cvv.length >= 3;

  function close(o: boolean) {
    onOpenChange(o);
    if (!o) {
      setNumber("");
      setName("");
      setExpiry("");
      setCvv("");
      setSaved(false);
    }
  }

  function save() {
    setSaved(true);
    toast.success(`Card ending ${digits(number).slice(-4)} added (demo)`);
    setTimeout(() => close(false), 1400);
  }

  const shown = (number + "•••• •••• •••• ••••".slice(number.length)).slice(0, 19);

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span className="flex size-10 items-center justify-center rounded-full bg-lime text-ink">
              <LoopIcon icon={WalletCardsIcon} size={22} />
            </span>
            <Badge variant="outline" className="border-ember/40 bg-tint-ember text-ember-dark">Demo</Badge>
          </div>
          <DialogTitle className="font-display text-xl">Add a card</DialogTitle>
          <DialogDescription>Demo only: card details stay on this screen and are not stored or sent anywhere.</DialogDescription>
        </DialogHeader>

        {saved ? (
          <motion.div
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 260, damping: 18 }}
            className="grid place-items-center gap-3 py-8"
          >
            <span className="flex size-16 items-center justify-center rounded-full bg-lime text-ink">
              <LoopIcon icon={CheckIcon} size={34} every={1200} />
            </span>
            <p className="font-display text-lg font-semibold text-ink">Card added</p>
          </motion.div>
        ) : (
          <form
            className="grid gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (valid) save();
            }}
          >
            <motion.div
              initial={{ y: 28, scale: 0.85, opacity: 0, rotate: -4 }}
              animate={{ y: 0, scale: 1, opacity: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 220, damping: 16 }}
              className="relative aspect-[1.7] w-full overflow-hidden rounded-2xl bg-lime p-5 text-ink shadow-lg"
            >
              <div className="absolute -right-10 -top-10 size-40 rounded-full bg-white/30" />
              <div className="relative flex h-full flex-col justify-between">
                <LoopIcon icon={CreditCardIcon} size={30} every={2400} />
                <p className="font-mono text-lg tracking-widest tnum">{shown}</p>
                <div className="flex items-end justify-between text-xs">
                  <span className="max-w-[60%] truncate font-medium uppercase">{name || "Name on card"}</span>
                  <span className="font-mono">{expiry || "MM/YY"}</span>
                </div>
              </div>
            </motion.div>

            <Input inputMode="numeric" autoComplete="off" placeholder="Card number" aria-label="Card number" value={fmtNumber(number)} onChange={(e) => setNumber(fmtNumber(e.target.value))} />
            <Input autoComplete="off" placeholder="Name on card" aria-label="Name on card" value={name} onChange={(e) => setName(e.target.value)} />
            <div className="grid grid-cols-2 gap-3">
              <Input inputMode="numeric" autoComplete="off" placeholder="MM/YY" aria-label="Expiry" value={expiry} onChange={(e) => setExpiry(fmtExpiry(e.target.value))} />
              <Input type="password" inputMode="numeric" autoComplete="off" placeholder="CVV" aria-label="CVV" value={cvv} onChange={(e) => setCvv(digits(e.target.value).slice(0, 4))} />
            </div>
            <div className="flex items-center gap-2 text-xs text-graphite">
              <LoopIcon icon={LockKeyholeIcon} size={16} every={3000} /> Encrypted in transit in a real build.
            </div>
            <Button type="submit" size="lg" disabled={!valid} className="rounded-full bg-lime text-ink hover:bg-lime-dark">
              Add card
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
