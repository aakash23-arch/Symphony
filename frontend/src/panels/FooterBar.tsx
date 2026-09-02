import React from 'react';
import { GhostWordmark } from '../design-system/GhostWordmark';

/**
 * Editorial footer: oversized ghost wordmark, CTA, tagline, copyright.
 */
export const FooterBar: React.FC = () => {
  return (
    <footer className="relative w-full border-t border-border bg-background overflow-hidden">
      <div className="relative h-40 sm:h-56 flex items-center justify-center">
        <GhostWordmark words={['SYMPHONY']} className="opacity-70" />
        <a
          href="#hero"
          className="rounded-sm relative z-10 inline-flex items-center gap-2 bg-accent-bright text-accent-bright-ink px-6 py-3 font-mono text-sm font-bold uppercase tracking-wider hover:bg-accent-bright-hover transition-all duration-200 ease-out hover:scale-[1.03] active:scale-[0.98]"
        >
          Get in touch →
        </a>
      </div>

      <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 px-6 py-8 border-t border-border">
        <div>
          <div className="font-sans text-base font-black tracking-tight text-fg">
            SYMPHONY
          </div>
          <p className="text-sm text-fg-tertiary mt-1">
            The complete voice authenticity analyser.
          </p>
        </div>
        <div className="text-right font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
          <div>FORENSIC INFRASTRUCTURE</div>
          <div>&copy; {new Date().getFullYear()} Symphony. All Rights Reserved.</div>
        </div>
      </div>
    </footer>
  );
};
