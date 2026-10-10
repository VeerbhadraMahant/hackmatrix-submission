"use client";

import React, { useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { FeatureId, SHOWCASE_FEATURES, SHOWCASE_HEADER } from "./showcaseData";
import { FeatureCard } from "./FeatureCard";
import { TrackScene } from "./scenes/TrackScene";
import { BudgetScene } from "./scenes/BudgetScene";
import { CollaborateScene } from "./scenes/CollaborateScene";
import { PlanScene } from "./scenes/PlanScene";

export function FeatureShowcase() {
  const [activeFeature, setActiveFeature] = useState<FeatureId>("track");
  const shouldReduceMotion = useReducedMotion();

  // Find cards by position
  const leftTop = SHOWCASE_FEATURES.find((f) => f.position === "left-top")!;
  const leftBottom = SHOWCASE_FEATURES.find((f) => f.position === "left-bottom")!;
  const rightTop = SHOWCASE_FEATURES.find((f) => f.position === "right-top")!;
  const rightBottom = SHOWCASE_FEATURES.find((f) => f.position === "right-bottom")!;

  const renderActiveScene = () => {
    switch (activeFeature) {
      case "track":
        return <TrackScene key="track-scene" />;
      case "budget":
        return <BudgetScene key="budget-scene" />;
      case "collaborate":
        return <CollaborateScene key="collaborate-scene" />;
      case "plan":
        return <PlanScene key="plan-scene" />;
      default:
        return <TrackScene key="default-scene" />;
    }
  };

  return (
    <div className="w-full bg-[#FEF9EB] py-12 sm:py-16 md:py-20 px-4 sm:px-6 lg:px-8">
      {/* Outer Rounded Container on Warm Beige Background (#F2EBD7) */}
      <div className="mx-auto w-full max-w-[1240px] bg-[#F2EBD7] rounded-[28px] sm:rounded-[36px] border border-[#E7DEC5] shadow-[0_12px_45px_rgba(26,24,20,0.04)] px-5 py-10 sm:px-10 sm:py-14 md:px-12 md:py-16">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-14">
          <h2 className="font-display text-3xl sm:text-4xl md:text-5xl text-[#1c1b18] tracking-tight leading-[1.12]">
            {SHOWCASE_HEADER.title}
          </h2>
          <p className="mt-4 text-sm sm:text-base md:text-[17px] text-[#4a4742] leading-relaxed max-w-2xl mx-auto">
            {SHOWCASE_HEADER.subtitle}
          </p>
        </div>

        {/* Desktop 3-Column Layout (Hidden on Mobile/Tablet <= 900px) */}
        <div className="hidden lg:grid lg:grid-cols-[1fr_360px_1fr] xl:grid-cols-[1fr_390px_1fr] items-center gap-6 xl:gap-8 min-h-[540px]">
          {/* LEFT Column: TRACK (Top) & BUDGET (Bottom) */}
          <div className="flex flex-col justify-between h-full py-4 gap-12">
            <FeatureCard
              feature={leftTop}
              isActive={activeFeature === leftTop.id}
              onActivate={() => setActiveFeature(leftTop.id)}
            />
            <FeatureCard
              feature={leftBottom}
              isActive={activeFeature === leftBottom.id}
              onActivate={() => setActiveFeature(leftBottom.id)}
            />
          </div>

          {/* CENTER Column: Interactive Stage */}
          <div
            id={`showcase-scene-${activeFeature}`}
            role="tabpanel"
            aria-labelledby={`showcase-tab-${activeFeature}`}
            className="relative flex items-center justify-center h-[540px] w-full overflow-visible"
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={activeFeature}
                initial={
                  shouldReduceMotion
                    ? { opacity: 1 }
                    : { opacity: 0, scale: 0.96 }
                }
                animate={{ opacity: 1, scale: 1 }}
                exit={
                  shouldReduceMotion
                    ? { opacity: 0 }
                    : { opacity: 0, scale: 0.96 }
                }
                transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
                className="w-full flex items-center justify-center"
              >
                {renderActiveScene()}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* RIGHT Column: COLLABORATE (Top) & PLAN (Bottom) */}
          <div className="flex flex-col justify-between h-full py-4 gap-12">
            <FeatureCard
              feature={rightTop}
              isActive={activeFeature === rightTop.id}
              onActivate={() => setActiveFeature(rightTop.id)}
            />
            <FeatureCard
              feature={rightBottom}
              isActive={activeFeature === rightBottom.id}
              onActivate={() => setActiveFeature(rightBottom.id)}
            />
          </div>
        </div>

        {/* Mobile / Tablet Layout (<= 900px / lg breakpoint) */}
        <div className="flex flex-col lg:hidden gap-8">
          {/* Stage Sits Above on Mobile */}
          <div
            id={`showcase-scene-mobile-${activeFeature}`}
            role="tabpanel"
            aria-labelledby={`showcase-tab-${activeFeature}`}
            className="relative flex items-center justify-center min-h-[480px] w-full bg-white/40 rounded-[24px] p-4 border border-black/[0.04]"
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={`mobile-${activeFeature}`}
                initial={
                  shouldReduceMotion
                    ? { opacity: 1 }
                    : { opacity: 0, scale: 0.96 }
                }
                animate={{ opacity: 1, scale: 1 }}
                exit={
                  shouldReduceMotion
                    ? { opacity: 0 }
                    : { opacity: 0, scale: 0.96 }
                }
                transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                className="w-full flex items-center justify-center"
              >
                {renderActiveScene()}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* 4 Cards Stacked Below */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5" role="tablist">
            {SHOWCASE_FEATURES.map((feature) => (
              <FeatureCard
                key={feature.id}
                feature={feature}
                isActive={activeFeature === feature.id}
                onActivate={() => setActiveFeature(feature.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
