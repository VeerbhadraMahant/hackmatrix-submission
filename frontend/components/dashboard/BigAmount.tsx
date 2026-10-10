import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Big figure with a muted, smaller fractional part, e.g. ₹74,503.00 */
export function BigAmount({ value, className }: { value: number; className?: string }) {
  const abs = Math.abs(value);
  const cents = String(Math.round((abs % 1) * 100) % 100).padStart(2, "0");
  return (
    <span className={cn("font-display font-semibold tnum text-ink", className)}>
      {value < 0 && "-"}
      {formatCurrency(Math.trunc(abs))}
      <span className="text-[0.55em] font-medium text-ink/45">.{cents}</span>
    </span>
  );
}
