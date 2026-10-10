"use client";

import { useEffect, useRef, type ComponentType, type Ref } from "react";
import { cn } from "@/lib/utils";

type Handle = { startAnimation: () => void; stopAnimation: () => void };
type AnimatedIcon = ComponentType<{ ref?: Ref<Handle>; size?: number; className?: string; color?: string }>;

/** Plays an @animateicons icon on a repeating timer (they only animate on hover by default). */
export function LoopIcon({
  icon: Icon,
  size = 28,
  every = 1800,
  className,
}: {
  icon: AnimatedIcon;
  size?: number;
  every?: number;
  className?: string;
}) {
  const ref = useRef<Handle>(null);
  useEffect(() => {
    const play = () => ref.current?.startAnimation();
    play();
    const t = setInterval(play, every);
    return () => clearInterval(t);
  }, [every]);
  return <Icon ref={ref} size={size} className={className} />;
}

/** Round lime badge holding a looping icon, with an optional caption: the app's loading mark. */
export function LoadingMark({ icon, label, className }: { icon: AnimatedIcon; label?: string; className?: string }) {
  return (
    <div className={cn("flex items-center gap-3 self-start rounded-full bg-white px-3 py-2 shadow-sm", className)} role="status">
      <span className="flex size-10 items-center justify-center rounded-full bg-lime text-ink">
        <LoopIcon icon={icon} size={22} />
      </span>
      {label && <span className="pr-2 text-sm font-medium text-graphite">{label}</span>}
    </div>
  );
}
