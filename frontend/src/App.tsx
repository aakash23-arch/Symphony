import React, { useState } from 'react';
import { motion, useScroll, useSpring } from 'framer-motion';

import { HeaderBar } from './panels/HeaderBar';
import { ProblemSection } from './sections/01_ProblemSection';
import { SignalSection } from './sections/02_SignalSection';
import { TransformationSection } from './sections/03_TransformationSection';
import { ForensicsSection } from './sections/04_ForensicsSection';
import { DecisionSection } from './sections/05_DecisionSection';
import { LiveDetectionSection } from './sections/LiveDetectionSection';
import { SessionProvider } from './state/SessionProvider';

const Dashboard: React.FC = () => {
  const [viewMode, setViewMode] = useState<'narrative' | 'console'>('narrative');
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  });

  return (
    <div className="flex min-h-screen flex-col bg-background text-fg selection:bg-fg selection:text-background">
      {/* Global Scroll Progress Bar */}
      <motion.div
        className="fixed top-0 left-0 right-0 h-1 bg-fg origin-left z-50"
        style={{ scaleX }}
      />
      
      <HeaderBar viewMode={viewMode} onToggleView={setViewMode} />

      <main className="flex-1 w-full mx-auto">
        {viewMode === 'narrative' ? (
          <div className="relative">
            <ProblemSection onScrollToLive={() => setViewMode('console')} />
            <SignalSection />
            <TransformationSection />
            <ForensicsSection />
            <DecisionSection onScrollToLive={() => setViewMode('console')} />
          </div>
        ) : (
          <div className="max-w-[1500px] mx-auto px-4 sm:px-8 py-8 space-y-8">
            <LiveDetectionSection />
          </div>
        )}
      </main>
    </div>
  );
};

export const App: React.FC = () => (
  <SessionProvider>
    <Dashboard />
  </SessionProvider>
);
