import { ArrowUpRight } from 'lucide-react';
import { ConnectionDot } from '../components/ConnectionDot';
import { useSession } from '../state/useSession';
import { MagneticButton } from '../design-system/MagneticButton';

export interface HeaderBarProps {
  viewMode?: 'narrative' | 'console';
  onToggleView?: (mode: 'narrative' | 'console') => void;
}

/**
 * Symphony's editorial header. Dual-mode switching between the narrative
 * scroll story and the live detection console, plus a discrete connection
 * indicator once a session is active.
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
    }
  };

  // ---------------------------------------------------------------------------
  // NARRATIVE HEADER
  // ---------------------------------------------------------------------------
  if (viewMode === 'narrative') {
    return (
      <header className="sticky top-0 z-50 w-full bg-background/80 backdrop-blur-md transition-all border-b border-transparent hover:border-border">
        <div className="max-w-[1600px] mx-auto flex items-center justify-between px-6 py-4">
          
          {/* Left: Brand Mark */}
          <div className="flex items-center">
            <button
              type="button"
              onClick={() => scrollTo('hero')}
              className="font-sans text-lg font-black tracking-tight text-fg focus:outline-none"
            >
              SYMPHONY
            </button>
          </div>

          {/* Center: Editorial Nav */}
          <nav className="hidden lg:flex items-center gap-10 font-mono text-micro-label uppercase text-fg-tertiary">
            <button
              type="button"
              onClick={() => scrollTo('hero')}
              className="hover:text-fg transition-colors"
            >
              Explore
            </button>
            <button
              type="button"
              onClick={() => scrollTo('forensics')}
              className="hover:text-fg transition-colors"
            >
              How it works
            </button>
            <button
              type="button"
              onClick={handleOpenConsole}
              className="hover:text-fg transition-colors"
            >
              Live Demo
            </button>
          </nav>

          {/* Right: Primary Action */}
          <div className="flex items-center gap-4">
            <MagneticButton
              type="button"
              onClick={handleOpenConsole}
              className="rounded-sm inline-flex items-center gap-2 border border-accent-bright bg-accent-bright px-4 py-2 font-mono text-micro-label font-bold uppercase tracking-wider text-accent-bright-ink hover:bg-accent-bright-hover transition-all duration-200 ease-out hover:-translate-y-[1px] active:translate-y-[1px]"
            >
              <span>RUN DETECTION</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </MagneticButton>
          </div>
        </div>
      </header>
    );
  }

  // ---------------------------------------------------------------------------
  // CONSOLE DEMO HEADER (Phase 9)
  // ---------------------------------------------------------------------------
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background transition-all">
      <div className="max-w-[1600px] mx-auto flex items-center justify-between px-6 py-4">
        
        {/* Left: Brand */}
        <div className="flex items-center gap-3">
          <span className="font-sans text-base font-black tracking-tight text-fg">
            SYMPHONY
          </span>
          <ConnectionDot connection={state.connection} attempt={state.reconnectAttempt} />
        </div>

        {/* Middle: Title */}
        <div className="absolute left-1/2 -translate-x-1/2 font-mono text-micro-label uppercase text-fg font-bold tracking-widest hidden sm:block">
          LIVE DETECTION
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-4">
          {/* Quick Active Session Reset / Stop */}
          {state.sessionId && (
            <div className="flex items-center gap-1.5 mr-2">
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

          {onToggleView && (
            <button
              type="button"
              onClick={() => onToggleView('narrative')}
              className="inline-flex items-center gap-2 font-mono text-micro-label font-bold uppercase tracking-wider text-fg-secondary hover:text-fg transition-colors"
            >
              <ArrowUpRight className="h-3.5 w-3.5 rotate-[180deg]" />
              <span>BACK TO STORY</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

