import React from 'react';
import { cn } from '../lib/cn';

export interface SectionIndexProps {
  index: string | number;
  label?: string;
  className?: string;
  withLine?: boolean;
}

/**
 * Editorial section index marker (e.g., '01', '02.A').
 * Renders technical monospace numerals with high-contrast infrastructure styling.
 */
export const SectionIndex: React.FC<SectionIndexProps> = ({
  index,
  label,
  className,
  withLine = false,
}) => {
  const formattedIndex = typeof index === 'number' ? String(index).padStart(2, '0') : index;

  return (
    <div className={cn('inline-flex items-center gap-2.5 section-index', className)}>
      <span className="font-mono text-section-index font-bold tracking-widest text-fg-tertiary">
        {formattedIndex}
      </span>
      {label ? (
        <span className="font-mono text-micro-label uppercase tracking-widest text-fg-muted">
          {label}
        </span>
      ) : null}
      {withLine ? (
        <span className="h-px w-8 bg-border/80" aria-hidden="true" />
      ) : null}
    </div>
  );
};
