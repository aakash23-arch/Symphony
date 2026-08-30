import React from 'react';
import { cn } from '../lib/cn';

/** Small status pill. Used for bands, actions, expert statuses and severities. */
export const Badge: React.FC<{
  children: React.ReactNode;
  className?: string;
  title?: string;
}> = ({ children, className, title }) => (
  <span
    title={title}
    className={cn(
      'inline-flex items-center gap-1.5 whitespace-nowrap rounded border px-2 py-0.5',
      'font-mono text-micro uppercase',
      className,
    )}
  >
    {children}
  </span>
);
