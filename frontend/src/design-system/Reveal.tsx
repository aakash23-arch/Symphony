import React from 'react';
import { cn } from '../lib/cn';

export interface RevealProps {
  children: React.ReactNode;
  animation?: 'fade' | 'slide-up' | 'none';
  delayMs?: number;
  className?: string;
}

/**
 * Restrained motion reveal wrapper.
 * Automatically respects `prefers-reduced-motion`.
 */
export const Reveal: React.FC<RevealProps> = ({
  children,
  animation = 'fade',
  delayMs = 0,
  className,
}) => {
  const animClasses = {
    fade: 'reveal-fade',
    'slide-up': 'reveal-slide-up',
    none: '',
  }[animation];

  return (
    <div
      className={cn(animClasses, className)}
      style={{ animationDelay: `${delayMs}ms` }}
    >
      {children}
    </div>
  );
};
