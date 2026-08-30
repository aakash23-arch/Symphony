import React from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { NarrativeSection } from '../design-system/NarrativeSection';
import { MetricReadout } from '../design-system/MetricReadout';
import { formatUnit } from '../lib/risk';
import { useSession } from '../state/useSession';

export const BeliefTrajectorySection: React.FC = () => {
  const { state } = useSession();
  const evidence = state.evidence;
  const live = state.beliefLive;
  const belief = state.belief;

  const pSpoof = live ? live.P_spoof : (belief?.P_spoof ?? null);
  const quality = live ? live.q_call : (belief?.q_call ?? evidence?.audio_quality ?? null);

  const trajectory = (evidence?.belief_trajectory ?? belief?.trajectory ?? [])
    .slice(-120)
    .map((point) => ({
      t: point.t,
      p_spoof: point.p_spoof,
    }));

  const hasData = trajectory.length > 1;

  // Sample static points for demo when no live session exists
  const demoTrajectory = [
    { t: 0.0, p_spoof: 0.12 },
    { t: 0.4, p_spoof: 0.15 },
    { t: 0.8, p_spoof: 0.22 },
    { t: 1.2, p_spoof: 0.48 },
    { t: 1.6, p_spoof: 0.74 },
    { t: 2.0, p_spoof: 0.86 },
    { t: 2.4, p_spoof: 0.91 },
    { t: 2.8, p_spoof: 0.93 },
    { t: 3.2, p_spoof: 0.89 },
  ];

  const chartData = hasData ? trajectory : demoTrajectory;

  return (
    <NarrativeSection
      index="05"
      title="THE SIGNAL IS IN THE PATTERN."
      subtitle="A single isolated frame cannot prove impersonation. Symphony tracks the temporal belief trajectory as evidence accumulates over time."
      tag={hasData ? 'LIVE TEMPORAL BELIEF' : 'DEMO TRAJECTORY'}
    >
      <div className="rounded-2xl border border-border/80 bg-surface/90 p-6 shadow-xl backdrop-blur-sm">
        {/* Metric summary banner */}
        <div className="grid grid-cols-2 gap-4 border-b border-border/60 pb-5 sm:grid-cols-4">
          <MetricReadout
            label="Synthetic Speech Belief P_spoof"
            value={pSpoof !== null ? formatUnit(pSpoof) : (hasData ? null : '0.89')}
            tone={pSpoof !== null && pSpoof > 0.6 ? 'high' : 'default'}
          />
          <MetricReadout
            label="Audio Quality Index q_call"
            value={quality !== null ? formatUnit(quality) : (hasData ? null : '0.94')}
            tone="safe"
          />
          <MetricReadout
            label="Temporal Windows Evaluated"
            value={hasData ? trajectory.length : demoTrajectory.length}
            unit="FRAMES"
          />
          <MetricReadout
            label="Belief Convergence Status"
            value={pSpoof !== null ? (pSpoof > 0.7 ? 'CONVERGED' : 'ACCUMULATING') : 'DEMO CONVERGED'}
            tone="uncertain"
          />
        </div>

        {/* Trajectory Recharts Graph */}
        <div className="mt-6 space-y-2">
          <div className="flex items-center justify-between font-mono text-micro-label text-fg-tertiary">
            <span>SYNTHETIC-SPEECH EVIDENCE TRAJECTORY // TIME (SECONDS)</span>
            <span>SCALE 0.00 — 1.00</span>
          </div>

          <div className="h-44 w-full rounded-xl border border-border/70 bg-surface-elevated/30 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 12, bottom: 0, left: -24 }}>
                <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="t"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(v: number) => `${v.toFixed(1)}s`}
                  tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  stroke="#1E293B"
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 1]}
                  ticks={[0, 0.5, 1]}
                  tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  stroke="#1E293B"
                  tickLine={false}
                />
                {/* connectNulls={false} is critical to prevent interpolating over missing data */}
                <Line
                  type="monotone"
                  dataKey="p_spoof"
                  stroke="#818CF8"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#818CF8' }}
                  isAnimationActive={false}
                  connectNulls={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <p className="mt-4 border-t border-border/50 pt-3 font-mono text-micro-label text-fg-tertiary">
          Null values break line continuity explicitly: absent evidence is never fabricated or smoothed.
        </p>
      </div>
    </NarrativeSection>
  );
};
