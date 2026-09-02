import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export const SignalStabilityGraph = () => {
  const [points, setPoints] = useState<number[]>(Array.from({ length: 20 }, () => 50));

  useEffect(() => {
    const interval = setInterval(() => {
      setPoints(prev => {
        const next = [...prev.slice(1)];
        // Create a slightly jittery baseline around 50
        next.push(50 + (Math.random() * 10 - 5));
        return next;
      });
    }, 100);
    return () => clearInterval(interval);
  }, []);

  const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${i * 5} ${p}`).join(' ');

  return (
    <div className="flex flex-col gap-1 w-24">
      <div className="font-mono text-[0.5rem] uppercase tracking-widest text-fg-tertiary">
        SIGNAL STABILITY
      </div>
      <svg viewBox="0 0 100 100" className="w-full h-8 overflow-visible">
        <path d={pathData} fill="none" stroke="currentColor" strokeWidth="1" className="text-fg-secondary" />
      </svg>
    </div>
  );
};

export const SpectralProfileGraph = () => {
  return (
    <div className="flex flex-col gap-1 w-24 group">
      <div className="font-mono text-[0.5rem] uppercase tracking-widest text-fg-tertiary">
        SPECTRAL PROFILE
      </div>
      <div className="flex items-end h-8 gap-0.5">
        {[40, 70, 85, 60, 45, 90, 30, 50, 75, 40].map((h, i) => (
          <motion.div
            key={i}
            className="flex-1 bg-fg-secondary group-hover:bg-fg transition-colors"
            initial={{ height: "10%" }}
            animate={{ height: `${h}%` }}
            transition={{ duration: 1.5, repeat: Infinity, repeatType: "reverse", delay: i * 0.1 }}
          />
        ))}
      </div>
      {/* Hover reveal */}
      <div className="hidden group-hover:flex justify-between font-mono text-[0.45rem] text-fg-tertiary mt-0.5">
        <span>LOW</span>
        <span>MID</span>
        <span>HIGH</span>
      </div>
    </div>
  );
};

export const ModelAgreementGraph = () => {
  return (
    <div className="flex flex-col gap-1 w-24">
      <div className="font-mono text-[0.5rem] uppercase tracking-widest text-fg-tertiary">
        MODEL CONSENSUS
      </div>
      <svg viewBox="0 0 100 40" className="w-full h-8 overflow-visible">
        {/* Three lines converging to a point */}
        <motion.path 
          d="M0,5 C40,5 60,20 100,20" 
          fill="none" stroke="currentColor" strokeWidth="1" className="text-fg-secondary opacity-50"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2, ease: "easeInOut" }}
        />
        <motion.path 
          d="M0,20 C40,20 60,20 100,20" 
          fill="none" stroke="currentColor" strokeWidth="1.5" className="text-fg"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2, ease: "easeInOut", delay: 0.2 }}
        />
        <motion.path 
          d="M0,35 C40,35 60,20 100,20" 
          fill="none" stroke="currentColor" strokeWidth="1" className="text-fg-secondary opacity-50"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2, ease: "easeInOut", delay: 0.4 }}
        />
        <circle cx="100" cy="20" r="2" className="fill-fg" />
      </svg>
    </div>
  );
};
