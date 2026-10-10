"use client";

import React from "react";
import { FeatureItem } from "./showcaseData";

interface FeatureCardProps {
  feature: FeatureItem;
  isActive: boolean;
  onActivate: () => void;
}

export function FeatureCard({ feature, isActive, onActivate }: FeatureCardProps) {
  return (
    <div
      role="tab"
      tabIndex={0}
      aria-selected={isActive}
      aria-controls={`showcase-scene-${feature.id}`}
      id={`showcase-tab-${feature.id}`}
      onMouseEnter={onActivate}
      onFocus={onActivate}
      onClick={onActivate}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onActivate();
        }
      }}
      className={`group relative text-left rounded-[18px] p-5 sm:p-6 md:p-7 transition-all duration-300 ease-out outline-none cursor-pointer focus-visible:ring-2 focus-visible:ring-[#172554] focus-visible:ring-offset-2 ${
        isActive
          ? "bg-[#FBF9F7] shadow-[0_8px_24px_rgba(26,24,20,0.06)] border border-[#ECE6DC]"
          : "bg-transparent border border-transparent hover:bg-black/[0.015]"
      }`}
    >
      {/* Eyebrow Label */}
      <div
        className={`text-[11px] font-bold tracking-[0.08em] uppercase transition-colors duration-300 ${
          isActive ? "text-[#172554]" : "text-[#64748b]"
        }`}
      >
        {feature.eyebrow}
      </div>

      {/* Heading Line */}
      <h3
        className={`font-semibold text-lg sm:text-xl md:text-[22px] tracking-tight mt-1.5 transition-colors duration-300 ${
          isActive ? "text-[#1c1b18]" : "text-[#1c1b18]/45"
        }`}
      >
        {feature.title}
      </h3>

      {/* Paragraph */}
      <p
        className={`text-xs sm:text-sm leading-relaxed mt-2.5 transition-colors duration-300 max-w-[340px] ${
          isActive ? "text-[#4a4742]" : "text-[#4a4742]/45"
        }`}
      >
        {feature.description}
      </p>

      {/* Pill "Learn more" Button */}
      <div className="mt-4">
        <span
          className={`inline-flex items-center justify-center px-4 py-1.5 rounded-full text-xs font-medium text-white transition-all duration-300 shadow-2xs ${
            isActive
              ? "bg-[#172554] shadow-sm hover:bg-[#1e3a8a]"
              : "bg-[#475569]/70 opacity-90"
          }`}
        >
          {feature.ctaText}
        </span>
      </div>
    </div>
  );
}
