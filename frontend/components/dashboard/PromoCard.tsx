import Link from "next/link";
import { Button } from "@/components/shadcn/button";

/** Big lime call-out: a savings idea once connected, or the connect prompt before that. */
export function PromoCard({ connected, topCategory }: { connected: boolean; topCategory?: string }) {
  return (
    <div className="relative flex h-full min-h-56 flex-col justify-between overflow-hidden rounded-card bg-lime p-6 text-ink shadow-sm">
      <div className="pointer-events-none absolute -bottom-10 -right-10 size-40 rounded-full border-[14px] border-ink/10" />
      <div className="pointer-events-none absolute -bottom-2 right-8 size-16 rounded-full border-[8px] border-ink/10" />
      <h3 className="relative font-display text-3xl font-semibold leading-tight">
        {connected ? (
          <>
            How to trim {topCategory ? topCategory.toLowerCase() : "spending"} by{" "}
            <span className="inline-block rounded-full border-2 border-ink px-2.5">25%</span>?
          </>
        ) : (
          <>
            Connect once.
            <br />
            Save <span className="inline-block rounded-full border-2 border-ink px-2.5">automatically</span>.
          </>
        )}
      </h3>
      <Button asChild className="relative mt-6 w-full rounded-full bg-white text-ink hover:bg-white/80">
        <Link href={connected ? "/copilot" : "/connect"}>{connected ? "Ask the copilot" : "Connect Google Pay"}</Link>
      </Button>
    </div>
  );
}
