import React, { useEffect, useState } from 'react';
import { cn } from '../lib/cn';

export interface ScrollProgressProps {
  className?: string;
  showPercentage?: boolean;
}

/**
 * Precision technical scroll telemetry indicator.
 * Displays a hairline progress bar and optional monospace percentage readout.
 */
export const ScrollProgress: React.FC<ScrollProgressProps> = ({
  className,
  showPercentage = false,
}) => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (totalScroll <= 0) {
        setProgress(0);
        return;
      }
      const currentProgress = (window.scrollY / totalScroll) * 100;
      setProgress(Math.min(100, Math.max(0, currentProgress)));
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className={cn('fixed top-0 left-0 right-0 z-50 h-0.5 bg-border/40', className)}>
      <div
        className="h-full bg-accent transition-[width] duration-75 ease-out"
        style={{ width: `${progress}%` }}
      />
      {showPercentage ? (
        <span className="absolute right-4 top-2 font-mono text-micro-label text-fg-tertiary">
          {Math.round(progress)}%
        </span>
      ) : null}
    </div>
  );
};
