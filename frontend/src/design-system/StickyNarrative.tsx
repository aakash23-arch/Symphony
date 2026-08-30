import React from 'react';
import { cn } from '../lib/cn';

export interface StickyNarrativeProps {
  narrative: React.ReactNode;
  content: React.ReactNode;
  stickyTopOffset?: string;
  reverseOnDesktop?: boolean;
  className?: string;
}

/**
 * Editorial dual-column split layout.
 * Narrative side is pinned/sticky while granular technical evidence scrolls alongside.
 */
export const StickyNarrative: React.FC<StickyNarrativeProps> = ({
  narrative,
  content,
  stickyTopOffset = 'top-6',
  reverseOnDesktop = false,
  className,
}) => {
  return (
    <div className={cn('grid grid-cols-1 gap-8 lg:grid-cols-12 items-start', className)}>
      {/* Sticky Narrative Hero Column */}
      <div
        className={cn(
          'lg:col-span-5 self-start',
          stickyTopOffset,
          'lg:sticky',
          reverseOnDesktop ? 'lg:order-2' : 'lg:order-1',
        )}
      >
        {narrative}
      </div>

      {/* Scrolling Telemetry / Evidence Column */}
      <div
        className={cn(
          'lg:col-span-7 space-y-6',
          reverseOnDesktop ? 'lg:order-1' : 'lg:order-2',
        )}
      >
        {content}
      </div>
    </div>
  );
};
