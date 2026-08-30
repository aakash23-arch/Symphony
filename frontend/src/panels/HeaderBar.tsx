import React from 'react';
import { ArrowUpRight, LayoutDashboard, Sparkles } from 'lucide-react';
import { ConnectionDot } from '../components/ConnectionDot';
import { useSession } from '../state/useSession';

export interface HeaderBarProps {
  viewMode?: 'narrative' | 'console';
  onToggleView?: (mode: 'narrative' | 'console') => void;
}

/**
 * Symphony Minimalist Editorial Header.
 *
 * Provides monochrome SignalIQ branding, discrete live connection indicator,
 * dual-mode switching between Editorial Narrative & Operational Testing Console,
 * and direct testing action triggers.
 */
export const HeaderBar: React.FC<HeaderBarProps> = ({
  viewMode = 'narrative',
  onToggleView,
}) => {
  const { state, stopSession, reset, busy } = useSession();
  const isStreaming = Boolean(state.sessionId && state.sourceType);

  const scrollTo = (id: string) => {
    if (viewMode === 'console' && onToggleView) {
      onToggleView('narrative');
      setTimeout(() => {
        const el = document.getElementById(id);
        el?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else {
      const el = document.getElementById(id);
      el?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleOpenConsole = () => {
    if (onToggleView) {
      onToggleView('console');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      scrollTo('live-detection');
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur-md transition-all">
      <div className="max-w-[1600px] mx-auto flex items-center justify-between px-4 sm:px-8 py-3.5 sm:py-4">
        {/* Left: Brand Mark */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              if (onToggleView) onToggleView('narrative');
              scrollTo('hero');
            }}
            className="flex items-center gap-2.5 text-left focus:outline-none group"
          >
            <span className="font-sans text-base sm:text-lg font-black tracking-tight text-fg">
              SYMPHONY
            </span>
            <span className="hidden sm:inline-block border-l border-border pl-2.5 font-mono text-[0.625rem] font-semibold text-fg-tertiary tracking-widest uppercase">
              VOICE INTEGRITY &amp; DEFENSE
            </span>
          </button>
        </div>

        {/* Center: Editorial Nav / View Switcher */}
        {viewMode === 'narrative' ? (
          <nav className="hidden lg:flex items-center gap-6 font-mono text-micro-label uppercase text-fg-tertiary">
            <button
              type="button"
              onClick={() => scrollTo('problem')}
              className="hover:text-fg transition-colors"
            >
              Threat
            </button>
            <button
              type="button"
              onClick={() => scrollTo('signal')}
              className="hover:text-fg transition-colors"
            >
              Signal
            </button>
            <button
              type="button"
              onClick={() => scrollTo('how-it-works')}
              className="hover:text-fg transition-colors"
            >
              How It Works
            </button>
            <button
              type="button"
              onClick={() => scrollTo('protection')}
              className="hover:text-fg transition-colors"
            >
              Protection
            </button>
            <button
              type="button"
              onClick={() => scrollTo('faq')}
              className="hover:text-fg transition-colors"
            >
              FAQ
            </button>
          </nav>
        ) : (
          <div className="hidden sm:flex items-center gap-2 font-mono text-micro-label uppercase text-fg-tertiary">
            <span className="font-bold text-fg">OPERATIONAL TESTING TERMINAL</span>
            <span className="text-border-strong">/</span>
            <span>REAL-TIME TELEMETRY &amp; EXPERT INFERENCE</span>
          </div>
        )}

        {/* Right: Mode Switcher & Primary Action */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="flex items-center gap-2 font-mono text-micro-label text-fg-tertiary">
            <ConnectionDot connection={state.connection} attempt={state.reconnectAttempt} />
            <span className="hidden md:inline uppercase">
              {state.sourceType === 'mic'
                ? 'MIC ACTIVE'
                : isStreaming
                ? 'STREAMING'
                : 'STANDBY'}
            </span>
          </div>

          {/* Quick Active Session Reset / Stop */}
          {state.sessionId && (
            <div className="flex items-center gap-1.5">
              {isStreaming ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void stopSession()}
                  className="border border-red-500 bg-surface px-2 py-1 font-mono text-[0.625rem] uppercase font-bold text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  Stop
                </button>
              ) : (
                <button
                  type="button"
                  onClick={reset}
                  className="border border-border bg-surface px-2 py-1 font-mono text-[0.625rem] uppercase font-bold text-fg-secondary hover:text-fg"
                >
                  Reset
                </button>
              )}
            </div>
          )}

          {/* Dedicated View Switcher & Action */}
          {onToggleView && (
            <button
              type="button"
              onClick={() => onToggleView(viewMode === 'narrative' ? 'console' : 'narrative')}
              className="inline-flex items-center gap-1.5 border border-border bg-surface px-3 py-1.5 sm:py-2 font-mono text-micro-label font-bold uppercase tracking-wider text-fg hover:border-fg transition-all"
            >
              {viewMode === 'narrative' ? (
                <>
                  <LayoutDashboard className="h-3.5 w-3.5 text-fg-secondary" />
                  <span className="hidden sm:inline">DASHBOARD</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5 text-fg-secondary" />
                  <span className="hidden sm:inline">NARRATIVE</span>
                </>
              )}
            </button>
          )}

          <button
            type="button"
            onClick={handleOpenConsole}
            className="inline-flex items-center gap-1.5 border border-fg bg-fg px-3 sm:px-4 py-1.5 sm:py-2 font-mono text-micro-label font-bold uppercase tracking-wider text-background hover:bg-fg/90 transition-all shadow-sm"
          >
            <span>RUN DETECTION</span>
            <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
};
