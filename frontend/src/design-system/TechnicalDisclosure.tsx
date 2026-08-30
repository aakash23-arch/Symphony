import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../lib/cn';

export interface TechnicalDisclosureProps {
  summary: React.ReactNode;
  label?: string;
  tag?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}

/**
 * Collapsible disclosure container for deep technical telemetry, parameters, and audits.
 */
export const TechnicalDisclosure: React.FC<TechnicalDisclosureProps> = ({
  summary,
  label,
  tag,
  defaultOpen = false,
  children,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={cn('rounded-xl border border-border/80 bg-surface-elevated/40 overflow-hidden', className)}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between p-3.5 text-left transition-colors hover:bg-surface-elevated/80 focus:outline-none"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2.5">
          {isOpen ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-accent" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-fg-tertiary" />
          )}
          <div>
            {label ? (
              <span className="font-mono text-micro-label uppercase text-fg-tertiary block">
                {label}
              </span>
            ) : null}
            <span className="font-mono text-technical-value font-medium text-fg">
              {summary}
            </span>
          </div>
        </div>

        {tag ? (
          <span className="rounded bg-surface-elevated px-2 py-0.5 font-mono text-micro-label uppercase text-fg-tertiary border border-border/60">
            {tag}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="border-t border-border/60 p-3.5 bg-background/50 text-xs text-fg-secondary">
          {children}
        </div>
      ) : null}
    </div>
  );
};
