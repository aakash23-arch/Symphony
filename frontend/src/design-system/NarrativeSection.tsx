import React from 'react';
import { cn } from '../lib/cn';
import { SectionIndex } from './SectionIndex';

export interface NarrativeSectionProps {
  index: string | number;
  title: string;
  subtitle?: string;
  tag?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  containerClassName?: string;
  dense?: boolean;
}

/**
 * Editorial narrative section container.
 * Features prominent section indices, infrastructure grid borders, and generous whitespace.
 */
export const NarrativeSection: React.FC<NarrativeSectionProps> = ({
  index,
  title,
  subtitle,
  tag,
  actions,
  children,
  className,
  containerClassName,
  dense = false,
}) => {
  return (
    <section className={cn('relative border-t border-border/80 pt-8 pb-12', dense && 'pt-5 pb-8', className)}>
      {/* Section Header Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between pb-6 border-b border-border/40">
        <div>
          <div className="flex items-center gap-3">
            <SectionIndex index={index} withLine />
            {tag ? (
              <span className="rounded border border-border/60 bg-surface-elevated/40 px-2 py-0.5 font-mono text-micro-label uppercase text-fg-tertiary">
                {tag}
              </span>
            ) : null}
          </div>
          <h2 className="mt-2 text-section-title font-bold text-fg tracking-tight">{title}</h2>
          {subtitle ? (
            <p className="mt-1 body-sm text-fg-secondary max-w-2xl">{subtitle}</p>
          ) : null}
        </div>

        {actions ? <div className="shrink-0">{actions}</div> : null}
      </div>

      {/* Narrative Section Content */}
      <div className={cn('mt-6', containerClassName)}>{children}</div>
    </section>
  );
};
