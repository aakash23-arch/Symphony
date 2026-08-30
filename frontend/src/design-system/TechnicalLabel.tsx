import React from 'react';
import { cn } from '../lib/cn';

export interface TechnicalLabelProps {
  label: string;
  value?: string | number | React.ReactNode;
  variant?: 'subtle' | 'outline' | 'ghost' | 'active';
  size?: 'micro' | 'sm' | 'base';
  className?: string;
  badgeTone?: string;
}

/**
 * Infrastructure-grade technical label with monospace formatting and crisp border geometry.
 */
export const TechnicalLabel: React.FC<TechnicalLabelProps> = ({
  label,
  value,
  variant = 'subtle',
  size = 'sm',
  className,
  badgeTone,
}) => {
  const variantStyles = {
    subtle: 'bg-surface-elevated/60 border-border/70 text-fg-secondary',
    outline: 'bg-transparent border-border text-fg-secondary',
    ghost: 'bg-transparent border-transparent text-fg-tertiary',
    active: 'bg-accent/10 border-accent/30 text-accent font-semibold',
  };

  const sizeStyles = {
    micro: 'text-micro-label px-1.5 py-0.5',
    sm: 'text-technical-label px-2 py-0.5',
    base: 'text-technical-value px-2.5 py-1',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded border font-mono uppercase tracking-wider',
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
    >
      <span className="text-fg-tertiary">{label}</span>
      {value !== undefined ? (
        <>
          <span className="text-border-strong font-normal">/</span>
          <span className={cn('font-semibold text-fg', badgeTone)}>{value}</span>
        </>
      ) : null}
    </div>
  );
};
