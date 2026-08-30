import React, { useEffect, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { VoiceSignalMotif } from '../components/storytelling/VoiceSignalMotif';

export interface HeroSectionProps {
  onScrollToLive?: () => void;
  onScrollToExplore?: () => void;
}

/**
 * Symphony Hero Section with SignalIQ Animated Green Scroll Aura.
 *
 * Visual Components:
 *  - Animated Emerald / Mint Radiance Field that responds to user scroll depth
 *  - Massive display-giant typography
 *  - Central Voice Signal Motif with listening state
 *  - Crisp single-action CTA
 */
export const HeroSection: React.FC<HeroSectionProps> = ({
  onScrollToLive,
  onScrollToExplore,
}) => {
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Compute scroll-linked aura dynamics (diffuses from 0.85 down to 0.05 over 600px scroll)
  const auraScale = 1 + Math.min(scrollY / 800, 0.4);
  const auraOpacity = Math.max(0.1, 1 - scrollY / 650);
  const auraTranslateY = scrollY * 0.25;

  const handleLiveClick = () => {
    if (onScrollToLive) {
      onScrollToLive();
    } else {
      const el = document.getElementById('live-detection');
      el?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleExploreClick = () => {
    if (onScrollToExplore) {
      onScrollToExplore();
    } else {
      const el = document.getElementById('problem');
      el?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section
      id="hero"
      className="relative min-h-[90vh] flex flex-col justify-center pt-8 pb-16 sm:pt-14 sm:pb-24 border-b border-border overflow-hidden"
    >
      {/* 1. Signature SignalIQ Emerald Animated Green Scroll Aura Field */}
      <div
        className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-150"
        style={{ opacity: auraOpacity }}
        aria-hidden="true"
      >
        <div
          className="absolute -top-[15%] left-1/2 -translate-x-1/2 w-[120vw] sm:w-[900px] h-[650px] rounded-full blur-[90px] green-aura-mesh"
          style={{
            transform: `translate(-50%, ${auraTranslateY}px) scale(${auraScale})`,
          }}
        />
        <div
          className="absolute top-[25%] right-[10%] w-[450px] h-[450px] rounded-full blur-[110px] bg-emerald-400/10"
          style={{
            transform: `scale(${auraScale})`,
          }}
        />
      </div>

      <div className="max-w-[1500px] mx-auto w-full px-4 sm:px-8 relative z-10">
        {/* Top Infrastructure Label */}
        <div className="flex items-center gap-3 font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-6 sm:mb-10">
          <span className="h-2 w-2 rounded-full bg-emerald-600 animate-pulse-dot" />
          <span>INFRASTRUCTURE-GRADE AI</span>
          <span className="text-border-strong">/</span>
          <span className="serif-italic lowercase text-base text-fg tracking-normal font-normal">
            introducing
          </span>
        </div>

        {/* 2-Column Hero Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
          {/* Left Column: Massive Editorial Display Typography */}
          <div className="lg:col-span-7 space-y-6 sm:space-y-8">
            <h1 className="display-giant text-fg font-black tracking-tight leading-[0.94]">
              THE VOICE<br />
              <span className="serif-italic font-normal tracking-tight">SOUNDS REAL.</span><br />
              THAT DOESN’T MEAN<br />
              <span className="text-fg-secondary">IT IS.</span>
            </h1>

            <p className="text-lg sm:text-xl text-fg-secondary max-w-xl font-normal leading-relaxed">
              AI-generated voices can sound authentic. Symphony analyses the signal behind the voice,
              combining forensic evidence and call context to challenge trust before loss occurs.
            </p>

            {/* Minimal High-Contrast CTA */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                type="button"
                onClick={handleLiveClick}
                className="group inline-flex items-center gap-3 bg-fg text-background px-7 py-4 font-mono text-xs sm:text-sm font-bold uppercase tracking-wider transition-all hover:bg-fg/90 shadow-md"
              >
                <span>RUN A LIVE DETECTION</span>
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </button>

              <button
                type="button"
                onClick={handleExploreClick}
                className="font-mono text-xs sm:text-sm font-semibold text-fg-secondary hover:text-fg uppercase tracking-wider px-3 py-4 transition-colors"
              >
                HOW SYMPHONY WORKS ↓
              </button>
            </div>
          </div>

          {/* Right Column: Central Symbolic Voice Motif */}
          <div className="lg:col-span-5 flex items-center justify-center lg:justify-end">
            <VoiceSignalMotif variant="hero" state="listening" />
          </div>
        </div>

        {/* Bottom Calibration Ribbon */}
        <div className="mt-14 sm:mt-20 pt-6 border-t border-border flex flex-wrap items-center justify-between gap-4 font-mono text-micro-label uppercase text-fg-tertiary">
          <div className="flex items-center gap-3">
            <span>01 // REAL-TIME INGESTION</span>
            <span className="text-border-strong">──</span>
            <span>02 // 6-MODEL FORENSICS</span>
            <span className="text-border-strong">──</span>
            <span>03 // DISBURSEMENT INTERVENTION</span>
          </div>

          <div>
            <span>16.0 kHz TELEPHONY PCM // SHA-256 ASSURANCE</span>
          </div>
        </div>
      </div>
    </section>
  );
};
