import React, { useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { FileCheck, UserCheck } from 'lucide-react';

import { Badge } from '../components/Badge';
import { ForensicDossierModal } from '../components/ForensicDossierModal';
import { Metric, MetricBar } from '../components/Metric';
import { LoadingState } from '../components/PanelStates';
import { Panel } from '../components/Panel';
import { cn } from '../lib/cn';
import { formatClock, humanise } from '../lib/format';
import { expertNames, expertStatusTone, formatUnit } from '../lib/risk';
import { isStale } from '../state/sessionReducer';
import { useSession } from '../state/useSession';

const ALL_EXPERTS = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6'];
const ACOUSTIC = new Set(['E1', 'E2', 'E3']);

export const EvidencePanel: React.FC = () => {
  const { state, health } = useSession();
  const [showDossier, setShowDossier] = useState(false);
  const [showBiometricInfo, setShowBiometricInfo] = useState(false);
  const stale = isStale(state);
  const evidence = state.evidence;
  const live = state.beliefLive;
  const belief = state.belief;

  const pSpoof = live ? live.P_spoof : (belief?.P_spoof ?? null);
  const quality = live ? live.q_call : (belief?.q_call ?? evidence?.audio_quality ?? null);

  const rows =
    evidence && evidence.experts.length > 0
      ? evidence.experts
      : ALL_EXPERTS.map((id) => ({
          expert_id: id,
          status: (health?.expert_models?.[id]?.status ?? 'UNKNOWN') as string,
          p: null as number | null,
          confidence: null as number | null,
          latency_ms: 0,
        }));

  const speaker = rows.find((row) => row.expert_id === 'E4');
  const prosody = rows.find((row) => row.expert_id === 'E5');
  const acousticScores = rows
    .filter((row) => ACOUSTIC.has(row.expert_id) && row.p !== null)
    .map((row) => row.p as number);

  const trajectory = (evidence?.belief_trajectory ?? belief?.trajectory ?? [])
    .slice(-120)
    .map((point) => ({
      t: point.t,
      p_spoof: point.p_spoof,
    }));

  return (
    <Panel
      title="Evidence"
      sectionNumber="03"
      tag={evidence?.record_type ?? 'L3 Forensics'}
      subtitle="Neural Verification & Biometrics"
      stale={stale}
      staleLabel={stale ? `Last update ${formatClock(state.lastMessageAt)}` : undefined}
    >
      {state.evidenceStatus === 'loading' && !evidence ? (
        <LoadingState rows={4} />
      ) : (
        <>
          {/* Key Forensic Evidence Indicators */}
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3.5 sm:grid-cols-4">
            <Metric
              label="Synthetic speech"
              value={pSpoof === null ? null : formatUnit(pSpoof)}
              nullLabel="no evidence"
            />
            <Metric
              label="Speaker consistency"
              value={speaker && speaker.p !== null ? formatUnit(1 - speaker.p) : null}
              nullLabel={speaker?.status === 'ABSTAIN' ? 'not enrolled' : 'no evidence'}
            />
            <Metric
              label="Prosody"
              value={prosody && prosody.p !== null ? formatUnit(prosody.p) : null}
              nullLabel={prosody?.status === 'DEFERRED' ? 'deferred' : 'no evidence'}
            />
            <Metric
              label="Audio quality"
              value={quality === null ? null : formatUnit(quality)}
              nullLabel="not measured"
            />
          </dl>

          {/* Fused Acoustic Evidence Progress Meter */}
          <div className="mt-4 rounded-xl border border-border/80 bg-surface-elevated/40 p-3">
            <MetricBar
              label="Acoustic Evidence (E1–E3 Ensemble Mean)"
              value={
                acousticScores.length > 0
                  ? acousticScores.reduce((a, b) => a + b, 0) / acousticScores.length
                  : null
              }
              nullLabel="no acoustic expert produced a score"
              tone="bg-accent"
            />
          </div>

          {/* Belief Trajectory Graph */}
          {trajectory.length > 1 ? (
            <div className="mt-5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
                  Synthetic Speech Belief Trajectory
                </span>
                <span className="font-mono text-[0.625rem] text-accent">TEMPORAL BELIEF</span>
              </div>
              <div
                className="h-28 rounded-xl border border-border/70 bg-surface-elevated/30 p-2"
                aria-label="Synthetic speech belief over time"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trajectory} margin={{ top: 6, right: 8, bottom: 0, left: -24 }}>
                    <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="t"
                      type="number"
                      domain={['dataMin', 'dataMax']}
                      tickFormatter={(value: number) => `${value.toFixed(1)}s`}
                      tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                      stroke="#1E293B"
                      tickLine={false}
                      minTickGap={28}
                    />
                    <YAxis
                      domain={[0, 1]}
                      ticks={[0, 0.5, 1]}
                      tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                      stroke="#1E293B"
                      tickLine={false}
                    />
                    {/* connectNulls={false} MUST remain false to prevent fabricating fake lines */}
                    <Line
                      type="monotone"
                      dataKey="p_spoof"
                      stroke="#818CF8"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : null}

          {/* Neural Expert Models Scorecard */}
          <div className="mt-5 border-t border-border/80 pt-3.5">
            <div className="flex items-center justify-between">
              <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
                Neural Expert Models (L3 Ensemble)
              </span>
              <span className="font-mono text-[0.625rem] text-fg-tertiary">6 MODELS</span>
            </div>
            <ul className="mt-2.5 space-y-2">
              {rows.map((row) => (
                <li
                  key={row.expert_id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-surface-elevated/30 px-3 py-2 text-xs"
                >
                  <span className="flex items-center gap-2 min-w-0 truncate text-fg-secondary">
                    <span className="font-mono font-bold text-accent">{row.expert_id}</span>
                    <span className="truncate">{expertNames[row.expert_id] ?? ''}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2.5">
                    {row.p !== null ? (
                      <span className="font-mono font-bold tnum text-fg">{formatUnit(row.p)}</span>
                    ) : null}
                    <Badge className={cn('border-border text-[0.625rem]', expertStatusTone(row.status))}>
                      {row.status}
                    </Badge>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Enrolled Biometric Voiceprint Inspector */}
          <div className="mt-3.5 border-t border-border/80 pt-3">
            <button
              type="button"
              onClick={() => setShowBiometricInfo((prev) => !prev)}
              className="flex w-full items-center justify-between rounded-xl bg-surface-elevated/70 px-3 py-2 text-left text-xs text-fg-secondary transition-all hover:bg-surface-hover hover:text-fg border border-border/60"
            >
              <span className="inline-flex items-center gap-2 font-mono text-[0.75rem]">
                <UserCheck className="h-4 w-4 text-accent" />
                <span>Enrolled Speaker: <strong className="text-fg">Ananya Sharma (CFO)</strong></span>
              </span>
              <span className="font-mono text-[0.6875rem] font-semibold text-accent">
                {showBiometricInfo ? 'Hide Voiceprint' : 'Inspect Voiceprint'}
              </span>
            </button>

            {showBiometricInfo ? (
              <div className="mt-2 rounded-xl border border-border bg-surface-elevated/90 p-3 text-xs space-y-2">
                <div className="grid grid-cols-2 gap-3 text-[0.6875rem]">
                  <div>
                    <span className="text-fg-tertiary">Voiceprint Identifier:</span>
                    <p className="font-mono font-bold text-fg">VP-CFO-8842</p>
                  </div>
                  <div>
                    <span className="text-fg-tertiary">Feature Embedding:</span>
                    <p className="font-mono font-bold text-fg">512-dim (WavLM-SV)</p>
                  </div>
                  <div>
                    <span className="text-fg-tertiary">Enrollment Standard:</span>
                    <p className="font-mono font-bold text-fg">16 kHz Clean PSTN</p>
                  </div>
                  <div>
                    <span className="text-fg-tertiary">Verification Threshold:</span>
                    <p className="font-mono font-bold text-emerald-400">Cosine ≥ 0.75</p>
                  </div>
                </div>
                <p className="border-t border-border/60 pt-2 text-[0.625rem] text-fg-tertiary">
                  E4 calculates cosine distance between incoming turn embeddings and enrolled target vector.
                </p>
              </div>
            ) : null}
          </div>

          {/* Attributed Contributing Factors Breakdown */}
          {evidence && evidence.top_factors.length > 0 ? (
            <div className="mt-4 border-t border-border/80 pt-3">
              <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
                Explainability Feature Attribution
              </span>
              <ul className="mt-2 space-y-1.5">
                {evidence.top_factors.map((factor) => (
                  <li
                    key={factor.factor}
                    className="flex items-center justify-between gap-3 rounded-md bg-surface-elevated/20 px-2.5 py-1.5 text-xs"
                  >
                    <span className="min-w-0 truncate text-fg-secondary">
                      {humanise(factor.factor)}
                    </span>
                    <span
                      className={cn(
                        'shrink-0 font-mono font-bold tnum',
                        factor.direction === 'INCREASES_RISK' ? 'text-band-high' : 'text-band-low',
                      )}
                    >
                      {factor.points >= 0 ? '+' : ''}
                      {factor.points.toFixed(3)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* Cryptographic SHA-256 Chain Notice */}
          {evidence ? (
            <p className="mt-3.5 border-t border-border/60 pt-2.5 text-[0.6875rem] text-fg-tertiary">
              {evidence.hash_chained
                ? 'Hash-chained cryptographic evidence record established.'
                : `Live analysis summary — not a hash-chained audit record (chain: ${evidence.chain_status.toLowerCase().replace(/_/g, ' ')}).`}
            </p>
          ) : null}

          {/* Cryptographic Evidence Dossier Export CTA */}
          <div className="mt-4 border-t border-border/80 pt-3.5">
            <button
              type="button"
              onClick={() => setShowDossier(true)}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-accent/40 bg-accent/10 px-4 py-2.5 text-xs font-bold text-accent transition-all hover:bg-accent/20 hover:border-accent hover:text-white shadow-sm"
            >
              <FileCheck className="h-4 w-4" />
              Export Cryptographic Evidence Dossier
            </button>
          </div>
        </>
      )}

      {/* Full-Screen Forensic Dossier Modal */}
      {showDossier ? (
        <ForensicDossierModal
          state={state}
          health={health}
          onClose={() => setShowDossier(false)}
        />
      ) : null}
    </Panel>
  );
};

