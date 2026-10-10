"use client";

import React, { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  rotation: number;
  vRot: number;
  shape: "rect" | "circle";
  alpha: number;
}

const COLORS = [
  "#ff5900", // Ember
  "#059669", // Emerald
  "#4f46e5", // Indigo
  "#f59e0b", // Amber
  "#ec4899", // Rose
  "#06b6d4", // Cyan
  "#10b981", // Mint
];

export function triggerConfetti(options?: { count?: number; originX?: number; originY?: number }) {
  if (typeof window === "undefined") return;

  // Dispatch event to canvas
  window.dispatchEvent(
    new CustomEvent("finpilot:confetti", {
      detail: {
        count: options?.count ?? 70,
        originX: options?.originX ?? window.innerWidth / 2,
        originY: options?.originY ?? window.innerHeight * 0.35,
      },
    })
  );
}

export function ConfettiCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let particles: Particle[] = [];
    let animationId: number;

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    handleResize();
    window.addEventListener("resize", handleResize);

    const onTrigger = (e: Event) => {
      const custom = e as CustomEvent<{ count: number; originX: number; originY: number }>;
      const count = custom.detail?.count || 60;
      const originX = custom.detail?.originX || canvas.width / 2;
      const originY = custom.detail?.originY || canvas.height * 0.35;

      // Check reduced motion preference
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return;
      }

      for (let i = 0; i < count; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = Math.random() * 9 + 4;
        particles.push({
          x: originX,
          y: originY,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed - 5,
          size: Math.random() * 6 + 4,
          color: COLORS[Math.floor(Math.random() * COLORS.length)],
          rotation: Math.random() * 360,
          vRot: (Math.random() - 0.5) * 15,
          shape: Math.random() > 0.4 ? "rect" : "circle",
          alpha: 1,
        });
      }

      if (!animationId) {
        render();
      }
    };

    window.addEventListener("finpilot:confetti", onTrigger);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.22; // gravity
        p.vx *= 0.98; // air resistance
        p.rotation += p.vRot;
        p.alpha -= 0.008;

        if (p.alpha <= 0 || p.y > canvas.height + 20) {
          particles.splice(i, 1);
          continue;
        }

        ctx.save();
        ctx.globalAlpha = Math.max(0, p.alpha);
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;

        if (p.shape === "rect") {
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 1.6);
        } else {
          ctx.beginPath();
          ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }

      if (particles.length > 0) {
        animationId = requestAnimationFrame(render);
      } else {
        animationId = 0;
      }
    };

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("finpilot:confetti", onTrigger);
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-[9999] h-full w-full"
      aria-hidden="true"
    />
  );
}
