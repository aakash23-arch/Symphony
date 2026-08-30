import React from 'react';
import { cn } from '../lib/cn';

export interface DisplayHeadlineProps {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  size?: 'xl' | 'lg' | 'md';
  align?: 'left' | 'center';
  className?: string;
}

/**
 * Editorial headline with infrastructure-scale typography.
 * Supports eyebrow, title, and descriptive subtitle with controlled pacing.
 */
export const DisplayHeadline: React.FC<DisplayHeadlineProps> = ({
  title,
  subtitle,
  eyebrow,
  size = 'lg',
  align = 'left',
  className,
}) => {
  const sizeClasses = {
    xl: 'display-xl',
    lg: 'display-lg',
    md: 'display-md',
  };

  return (
    <div className={cn('space-y-2', align === 'center' ? 'text-center' : 'text-left', className)}>
      {eyebrow ? (
        <p className="font-mono text-section-index font-bold uppercase tracking-widest text-accent">
          {eyebrow}
        </p>
      ) : null}
      <h1 className={cn('text-fg tracking-tight', sizeClasses[size])}>{title}</h1>
      {subtitle ? (
        <p className="body-lg max-w-3xl text-fg-secondary leading-relaxed pt-1">
          {subtitle}
        </p>
      ) : null}
    </div>
  );
};
