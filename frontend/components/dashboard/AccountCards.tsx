"use client";

import { useCallback } from "react";
import { Landmark, CreditCard, PiggyBank, TrendingUp, type LucideIcon } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import { Button } from "@/components/shadcn/button";
import { formatCurrency } from "@/lib/format";

const TYPE_ICON: Record<string, LucideIcon> = {
  credit_card: CreditCard,
  loan: Landmark,
  savings: PiggyBank,
  investment: TrendingUp,
};

/**
 * Standalone, self-fetching -- takes only userId so the lead can drop this
 * into dashboard/page.tsx in one line without threading data through it.
 */
export function AccountCards({ userId }: { userId: string }) {
  const fetchAccounts = useCallback(() => api.accounts(userId), [userId]);
  const { data, error, loading, reload } = useAsync(fetchAccounts, [userId]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Accounts</CardTitle>
      </CardHeader>
      <CardContent>
        {loading && !data && <p className="text-sm text-muted-foreground">Loading accounts...</p>}
        {error && (
          <div className="flex flex-col items-start gap-2">
            <p className="text-sm">Could not load accounts: {error}</p>
            <Button variant="outline" size="sm" onClick={reload}>
              Retry
            </Button>
          </div>
        )}
        {data && data.length === 0 && <p className="text-sm text-muted-foreground">No linked accounts yet.</p>}
        {data && data.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data.map((account) => {
              const Icon = TYPE_ICON[account.type] ?? Landmark;
              return (
                <div key={account.id} className="rounded-lg border bg-muted/40 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <Icon className="size-4 shrink-0 text-muted-foreground" />
                      <p className="truncate text-sm font-medium">{account.name}</p>
                    </div>
                    <Badge variant="outline" className="capitalize">
                      {account.type.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <p className="mt-3 text-xl font-semibold tnum">{formatCurrency(account.balance)}</p>
                  {account.interest_rate_apr != null && (account.type === "credit_card" || account.type === "loan") && (
                    <p className="mt-1 text-xs text-muted-foreground">{account.interest_rate_apr.toFixed(1)}% APR</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
