"use client";

import { useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown } from "lucide-react";
import type { RecurringObligation } from "@/lib/types";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import { Button } from "@/components/shadcn/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/shadcn/table";
import { ConfidenceChip } from "@/components/ui/ConfidenceChip";
import { formatCurrency, formatDate } from "@/lib/format";

function SortHeader({
  label,
  column,
  align = "left",
}: {
  label: string;
  column: { toggleSorting: (desc?: boolean) => void; getIsSorted: () => false | "asc" | "desc" };
  align?: "left" | "right";
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className={align === "right" ? "-mr-3 ml-auto flex" : "-ml-3"}
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      {label}
      <ArrowUpDown className="size-3.5 opacity-60" />
    </Button>
  );
}

const columns: ColumnDef<RecurringObligation>[] = [
  {
    accessorKey: "merchant",
    header: ({ column }) => <SortHeader label="Merchant" column={column} />,
    cell: ({ row }) => (
      <div className="min-w-0">
        <p className="truncate font-medium text-foreground">{row.original.merchant}</p>
        <p className="text-xs capitalize text-muted-foreground">{row.original.frequency}</p>
      </div>
    ),
  },
  {
    accessorKey: "next_expected_date",
    header: ({ column }) => <SortHeader label="Next due" column={column} />,
    cell: ({ row }) => <span className="whitespace-nowrap">{formatDate(row.original.next_expected_date)}</span>,
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }) => (
      <Badge variant="secondary" className="hidden capitalize sm:inline-flex">
        {row.original.category.replace(/_/g, " ")}
      </Badge>
    ),
  },
  {
    accessorKey: "confidence",
    header: "Confidence",
    cell: ({ row }) => <ConfidenceChip value={row.original.confidence} />,
  },
  {
    accessorFn: (o) => Math.abs(o.amount),
    id: "amount",
    header: ({ column }) => <SortHeader label="Amount" column={column} align="right" />,
    cell: ({ row }) => (
      <div className="text-right font-semibold tnum">{formatCurrency(Math.abs(row.original.amount))}</div>
    ),
  },
];

export function RecurringList({ obligations }: { obligations: RecurringObligation[] }) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "amount", desc: true }]);
  const table = useReactTable({
    data: obligations,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowId: (o) => o.group_id,
  });
  const totalMonthly = obligations.reduce((acc, o) => acc + Math.abs(o.amount), 0);

  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Recurring Obligations
          <Badge variant="outline">{obligations.length} active</Badge>
        </CardTitle>
        <CardDescription>{formatCurrency(totalMonthly)} / month</CardDescription>
      </CardHeader>
      <CardContent>
        {obligations.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No recurring commitments detected.</p>
        ) : (
          <div className="max-h-80 overflow-auto rounded-md border">
            <Table>
              <TableHeader className="sticky top-0 bg-card">
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id}>
                    {hg.headers.map((h) => (
                      <TableHead key={h.id}>
                        {flexRender(h.column.columnDef.header, h.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
      <CardFooter className="justify-between text-xs text-muted-foreground">
        <span>Subscriptions & bills auto-detected</span>
        <span className="font-medium text-ember">Synced with transactions</span>
      </CardFooter>
    </Card>
  );
}
