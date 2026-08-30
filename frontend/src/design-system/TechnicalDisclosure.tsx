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
    <div className={cn('border border-border bg-surface overflow-hidden transition-colors hover:border-fg-primary', className)}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between p-3.5 text-left transition-colors hover:bg-surface-elevated focus:outline-none"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2.5">
          {isOpen ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-fg-primary" />
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
          <span className="border border-border bg-surface px-2 py-0.5 font-mono text-micro-label uppercase text-fg-tertiary">
            {tag}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="border-t border-border p-3.5 bg-surface text-xs text-fg-secondary">
          {children}
        </div>
      ) : null}
    </div>
  );
};
