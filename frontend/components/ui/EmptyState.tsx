import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Shared "nothing here yet" placeholder -- icon/illustration slot, a heading,
 * body copy, and an optional action. Available for any page to adopt in
 * place of a bare "No data" string; not retrofitted everywhere by this
 * change, just made available.
 */
export function EmptyState({
  icon,
  title,
  body,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  body?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 rounded-surface border border-dashed border-mist px-6 py-10 text-center",
        className
      )}
    >
      {icon ? <div className="text-steel" aria-hidden>{icon}</div> : null}
      <p className="text-sm font-semibold text-ink">{title}</p>
      {body ? <p className="max-w-sm text-sm text-graphite">{body}</p> : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
