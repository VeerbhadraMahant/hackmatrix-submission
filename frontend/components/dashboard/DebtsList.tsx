import type { Debt } from "@/lib/types";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import { Progress } from "@/components/shadcn/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/shadcn/table";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";

export function DebtsList({ debts }: { debts: Debt[] }) {
  const totalPrincipal = debts.reduce((acc, d) => acc + d.principal, 0);
  const totalMinPayment = debts.reduce((acc, d) => acc + d.minimum_payment, 0);

  // Highest APR is the avalanche-strategy target.
  const highestAprId = debts.length
    ? debts.reduce((max, d) => (d.interest_rate_apr > max.interest_rate_apr ? d : max), debts[0]).id
    : null;

  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Debts & Loans
          <Badge variant="outline">{debts.length} accounts</Badge>
        </CardTitle>
        <CardDescription>
          {formatCurrency(totalPrincipal)} owed · {formatCurrency(totalMinPayment)}/mo minimum
        </CardDescription>
      </CardHeader>
      <CardContent>
        {debts.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No debt accounts on record.</p>
        ) : (
          <div className="overflow-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Balance</TableHead>
                  <TableHead>APR</TableHead>
                  <TableHead className="hidden sm:table-cell">Due</TableHead>
                  <TableHead className="text-right">Min / month</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {debts.map((d) => {
                  const isHighApr = d.interest_rate_apr >= 20;
                  const isAvalancheTarget = d.id === highestAprId && debts.length > 1;
                  const share = totalPrincipal ? (d.principal / totalPrincipal) * 100 : 0;
                  return (
                    <TableRow key={d.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="font-medium tnum">{formatCurrency(d.principal)}</span>
                          {isAvalancheTarget && (
                            <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
                              Avalanche target
                            </Badge>
                          )}
                        </div>
                        <Progress value={share} className="mt-1.5 h-1" aria-label="Share of total debt" />
                      </TableCell>
                      <TableCell className={cn("font-semibold tnum", isHighApr ? "text-rose-600" : "text-muted-foreground")}>
                        {d.interest_rate_apr.toFixed(1)}%
                      </TableCell>
                      <TableCell className="hidden text-muted-foreground sm:table-cell">Day {d.due_day_of_month}</TableCell>
                      <TableCell className="text-right font-semibold tnum">{formatCurrency(d.minimum_payment)}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
      <CardFooter className="justify-between text-xs text-muted-foreground">
        <span>Avalanche & snowball strategies evaluated</span>
        <span className="font-medium text-ember">Zero-penalty prepayment eligible</span>
      </CardFooter>
    </Card>
  );
}
