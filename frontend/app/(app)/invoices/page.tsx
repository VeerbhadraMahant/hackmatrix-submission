"use client";

import { useCallback, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync, useUserId } from "@/lib/hooks";
import type { Transaction } from "@/lib/types";
import { CATEGORY_META } from "@/lib/spend";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/shadcn/card";
import { MerchantLogo } from "@/components/dashboard/MerchantLogo";

const field = "w-full rounded-xl border border-mist bg-white px-3 py-2 text-sm text-ink outline-none focus:ring-2 focus:ring-lime";
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

export default function InvoicesPage() {
  const userId = useUserId();
  const fetchAll = useCallback(async () => {
    const all: Transaction[] = [];
    for (let page = 1; page <= 5; page++) {
      const res = await api.transactions(userId, { page, page_size: 200 });
      all.push(...res.items);
      if (all.length >= res.total) break;
    }
    return all;
  }, [userId]);
  const { data } = useAsync(fetchAll, [userId]);

  // One entry per company you have paid, with its most recent payment as the suggested amount.
  const companies = useMemo(() => {
    const m = new Map<string, Transaction>();
    for (const t of [...(data ?? [])].sort((a, b) => b.date.localeCompare(a.date))) if (t.amount < 0 && !m.has(t.merchant)) m.set(t.merchant, t);
    return [...m.values()].sort((a, b) => a.merchant.localeCompare(b.merchant));
  }, [data]);

  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [due, setDue] = useState(() => new Date(Date.now() + 14 * 864e5).toISOString().slice(0, 10));
  const [no] = useState(() => `INV-${Date.now().toString().slice(-6)}`);
  const picked = companies.find((c) => c.merchant === name);
  const value = Number(amount) || 0;

  function pick(merchant: string) {
    setName(merchant);
    const t = companies.find((c) => c.merchant === merchant);
    if (t) {
      setAmount(String(Math.abs(t.amount)));
      setNote(`Payment on ${t.date}`);
    }
  }

  function download() {
    const html = `<!doctype html><meta charset="utf-8"><title>${no}</title><body style="font-family:system-ui;max-width:640px;margin:40px auto;color:#1c1f14"><h1>Invoice ${no}</h1><p>To: <b>${esc(name)}</b><br>Due: ${due}</p><table style="width:100%;border-collapse:collapse"><tr><th align="left">Description</th><th align="right">Amount</th></tr><tr><td>${esc(note || "Services")}</td><td align="right">${esc(formatCurrency(value))}</td></tr></table><h2 align="right">Total ${esc(formatCurrency(value))}</h2></body>`;
    const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
    Object.assign(document.createElement("a"), { href: url, download: `${no}.html` }).click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="font-display text-lg">Create an invoice</CardTitle>
          <CardDescription>Pick a company from your transactions. Its logo and last amount are filled in for you.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <label className="grid gap-1 text-xs text-graphite">
            Company
            <select value={name} onChange={(e) => pick(e.target.value)} className={field}>
              <option value="">Choose a company</option>
              {companies.map((c) => (
                <option key={c.merchant} value={c.merchant}>
                  {c.merchant}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-xs text-graphite">
            Amount (₹)
            <input type="number" min={0} value={amount} onChange={(e) => setAmount(e.target.value)} className={field} />
          </label>
          <label className="grid gap-1 text-xs text-graphite">
            What is it for?
            <input value={note} onChange={(e) => setNote(e.target.value)} className={field} />
          </label>
          <label className="grid gap-1 text-xs text-graphite">
            Pay by
            <input type="date" value={due} onChange={(e) => setDue(e.target.value)} className={field} />
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="grid gap-5">
          <div className="rounded-2xl bg-tint-lime p-5">
            <div className="rounded-xl bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="font-display text-xl font-semibold text-ink">Invoice</p>
                <span className="text-xs text-pewter">{no}</span>
              </div>
              <div className="mt-4 flex items-center gap-3">
                {picked ? <MerchantLogo merchant={picked.merchant} color={CATEGORY_META[picked.category]?.color ?? "#9aa08a"} className="size-12" /> : <span className="size-12 rounded-lg bg-fog" />}
                <div>
                  <p className="text-xs text-pewter">Billed to</p>
                  <p className="text-sm font-semibold text-ink">{name || "Choose a company"}</p>
                </div>
                <div className="ml-auto text-right">
                  <p className="text-xs text-pewter">Pay by</p>
                  <p className="text-sm font-semibold tnum text-ink">{due}</p>
                </div>
              </div>
              <div className="mt-4 flex justify-between border-t border-fog pt-3 text-sm">
                <span className="text-graphite">{note || "Description"}</span>
                <span className="font-semibold tnum text-ink">{formatCurrency(value)}</span>
              </div>
            </div>
          </div>
          <p className="text-center font-display text-lg font-semibold text-ink">{name ? `Invoice for ${name}` : "Your invoice will show here"}</p>
          <Button onClick={download} disabled={!name || value <= 0} className="mx-auto rounded-full bg-lime text-ink hover:bg-lime/85">
            <Download /> Download invoice
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
