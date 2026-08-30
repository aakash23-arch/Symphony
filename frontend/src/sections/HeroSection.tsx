import React from 'react';
import { ArrowDown, ArrowRight, Play } from 'lucide-react';
import { VoiceSignalVisualizer } from '../components/visualizations/VoiceSignalVisualizer';
import { useSession } from '../state/useSession';

export interface HeroSectionProps {
  onScrollToLive?: () => void;
  onScrollToExplore?: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onScrollToLive,
  onScrollToExplore,
}) => {
  const { state } = useSession();
  const isStreaming = Boolean(state.sessionId && state.sourceType);

  const handleLiveClick = () => {
    if (onScrollToLive) {
      onScrollToLive();
    } else {
      const el = document.getElementById('live-console');
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
    <section id="hero" className="relative pt-12 pb-16 lg:pt-16 lg:pb-24">
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-12 items-center">
        {/* Left Editorial Narrative Column */}
        <div className="space-y-6 lg:col-span-6">
          <div className="inline-flex items-center gap-2 rounded-md border border-accent/30 bg-accent/10 px-3 py-1 font-mono text-micro-label uppercase tracking-widest text-accent">
            <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse-dot" />
            <span>REAL-TIME VOICE SECURITY INFRASTRUCTURE</span>
          </div>

          <div className="space-y-1">
            <h1 className="display-xl tracking-tight text-fg">
              THE VOICE<br />
              <span className="text-fg">SOUNDS REAL.</span>
            </h1>
            <h2 className="display-lg tracking-tight text-fg-tertiary">
              THAT DOESN'T MEAN<br />
              <span className="text-fg-secondary">IT IS.</span>
            </h2>
          </div>

          <p className="body-lg max-w-xl text-fg-secondary leading-relaxed">
            Symphony analyses voice signals in real time, combines acoustic, speaker and
            contextual evidence, and turns uncertainty into a defensible security decision.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-4 pt-2">
            <button
              type="button"
              onClick={handleLiveClick}
              className="inline-flex items-center gap-2.5 rounded-xl bg-accent px-6 py-3.5 font-mono text-technical-value font-bold text-white shadow-lg shadow-accent/25 transition-all hover:bg-accent-hover hover:scale-[1.02] active:scale-[0.98]"
            >
              <Play className="h-4 w-4 fill-current" />
              <span>RUN LIVE DETECTION</span>
            </button>

            <button
              type="button"
              onClick={handleExploreClick}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface-elevated/60 px-5 py-3.5 font-mono text-technical-value font-semibold text-fg-secondary transition-all hover:bg-surface-elevated hover:text-fg hover:border-border-strong"
            >
              <span>SEE HOW SYMPHONY WORKS</span>
              <ArrowDown className="h-4 w-4" />
            </button>
          </div>

          {/* Ingestion & Telemetry Badges */}
          <div className="flex items-center gap-4 pt-4 font-mono text-micro-label text-fg-tertiary border-t border-border/40">
            <span>VOICE</span>
            <ArrowRight className="h-3 w-3 text-fg-muted" />
            <span>SIGNAL</span>
            <ArrowRight className="h-3 w-3 text-fg-muted" />
            <span className="text-accent font-bold">ANALYSIS</span>
          </div>
        </div>

        {/* Right Technical Signal Visualizer Column */}
        <div className="lg:col-span-6">
          <VoiceSignalVisualizer isStreaming={isStreaming} />
        </div>
      </div>
    </section>
  );
};
