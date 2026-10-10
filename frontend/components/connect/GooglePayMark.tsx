/** Lightweight Google Pay wordmark (coloured G + "Pay") for the dummy connector. */
export function GooglePayMark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-baseline gap-0.5 font-display font-semibold tracking-tight ${className}`}>
      <span className="bg-gradient-to-br from-[#4285f4] via-[#ea4335] to-[#34a853] bg-clip-text text-transparent">G</span>
      <span className="text-graphite">Pay</span>
    </span>
  );
}
