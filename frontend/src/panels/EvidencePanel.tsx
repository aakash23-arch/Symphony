import React, { useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { FileText, UserCheck } from 'lucide-react';

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

/** Expert ids whose fused output is the acoustic synthetic-speech evidence. */
const ACOUSTIC = new Set(['E1', 'E2', 'E3']);

export const EvidencePanel: React.FC = () => {
  const { state, health } = useSession();
  const [showDossier, setShowDossier] = useState(false);
  const [showBiometricInfo, setShowBiometricInfo] = useState(false);
  const stale = isStale(state);
  const evidence = state.evidence;
  // Prefer the live thin belief for scalars; the full belief for structure.
  const live = state.beliefLive;
  const belief = state.belief;

  const pSpoof = live ? live.P_spoof : (belief?.P_spoof ?? null);
  const quality = live ? live.q_call : (belief?.q_call ?? evidence?.audio_quality ?? null);

  // Rows come from evidence when a session is running; otherwise from /health,
  // so the panel can still say which experts are even able to speak.
  const rows = evidence && evidence.experts.length > 0
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

  // Keep the tail: a long call would otherwise compress hundreds of points
  // into a few pixels and show nothing legible.
  const trajectory = (evidence?.belief_trajectory ?? belief?.trajectory ?? [])
    .slice(-120)
    .map((point) => ({
      t: point.t,
      // Null is passed through, not coerced. connectNulls={false} below then
      // breaks the line, which is the honest rendering of "no evidence here".
      p_spoof: point.p_spoof,
    }));

  return (
    <Panel
      title="Evidence"
      tag={evidence?.record_type ?? 'Live analysis'}
      stale={stale}
      staleLabel={stale ? `Last update ${formatClock(state.lastMessageAt)}` : undefined}
    >
      {state.evidenceStatus === 'loading' && !evidence ? (
        <LoadingState rows={4} />
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-4">
            <Metric
              label="Synthetic speech"
              value={pSpoof === null ? null : formatUnit(pSpoof)}
              nullLabel="no evidence"
            />
            <Metric
              label="Speaker consistency"
              value={
                speaker && speaker.p !== null ? formatUnit(1 - speaker.p) : null
              }
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

          <div className="mt-4">
            <MetricBar
              label="Acoustic evidence (E1–E3 mean)"
              value={
                acousticScores.length > 0
                  ? acousticScores.reduce((a, b) => a + b, 0) / acousticScores.length
                  : null
              }
              nullLabel="no acoustic expert produced a score"
              tone="bg-accent"
            />
          </div>

          {trajectory.length > 1 ? (
            <div className="mt-5">
              <p className="font-mono text-micro uppercase text-fg-tertiary">
                Belief trajectory
              </p>
              <div className="mt-2 h-24" aria-label="Synthetic speech belief over time">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trajectory} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
                    <CartesianGrid stroke="#232B3B" strokeDasharray="2 4" vertical={false} />
                    <XAxis
                      dataKey="t"
                      type="number"
                      domain={['dataMin', 'dataMax']}
                      tickFormatter={(value: number) => `${value.toFixed(1)}s`}
                      tick={{ fill: '#6B7280', fontSize: 10 }}
                      stroke="#232B3B"
                      tickLine={false}
                      minTickGap={24}
                    />
                    <YAxis
                      domain={[0, 1]}
                      ticks={[0, 0.5, 1]}
                      tick={{ fill: '#6B7280', fontSize: 10 }}
                      stroke="#232B3B"
                      tickLine={false}
                    />
                    {/* connectNulls MUST stay false: the default would draw a
                        straight line across windows where the experts produced
                        nothing, fabricating a trend out of absent evidence. */}
                    <Line
                      type="monotone"
                      dataKey="p_spoof"
                      stroke="#818CF8"
                      strokeWidth={1.5}
                      dot={false}
                      isAnimationActive={false}
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : null}

          <div className="mt-5 border-t border-border pt-3">
            <p className="font-mono text-micro uppercase text-fg-tertiary">Experts</p>
            <ul className="mt-2 space-y-1.5">
              {rows.map((row) => (
                <li
                  key={row.expert_id}
                  className="flex items-center justify-between gap-3 text-[0.8125rem]"
                >
                  <span className="min-w-0 truncate text-fg-secondary">
                    <span className="font-mono text-fg-tertiary">{row.expert_id}</span>{' '}
                    {expertNames[row.expert_id] ?? ''}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    {/* p is null unless status is OK, so the badge stands in for
                        the number rather than a 0.00 appearing beside it. */}
                    {row.p !== null ? (
                      <span className="font-mono tnum text-fg">{formatUnit(row.p)}</span>
                    ) : null}
                    <Badge className={cn('border-border', expertStatusTone(row.status))}>
                      {row.status}
                    </Badge>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {evidence ? (
            <p className="mt-3 border-t border-border pt-2.5 text-[0.6875rem] text-fg-tertiary">
              {evidence.hash_chained
                ? 'Hash-chained evidence record.'
                : `Live analysis summary — not a hash-chained audit record (chain: ${evidence.chain_status.toLowerCase().replace(/_/g, ' ')}).`}
            </p>
          ) : null}

          {/* Enrolled Biometric Reference Profile Inspector */}
          <div className="mt-3 border-t border-border pt-2.5">
            <button
              type="button"
              onClick={() => setShowBiometricInfo((prev) => !prev)}
              className="flex w-full items-center justify-between rounded-lg bg-surface-elevated/60 px-2.5 py-1.5 text-left text-xs text-fg-secondary transition-colors hover:bg-surface-hover hover:text-fg"
            >
              <span className="inline-flex items-center gap-1.5 font-mono text-[0.75rem]">
                <UserCheck className="h-3.5 w-3.5 text-accent" />
                Speaker Reference: <strong className="text-fg">Ananya Sharma (CFO)</strong>
              </span>
              <span className="font-mono text-[0.6875rem] text-accent">
                {showBiometricInfo ? 'Hide profile' : 'Inspect profile'}
              </span>
            </button>

            {showBiometricInfo ? (
              <div className="mt-2 rounded-lg border border-border bg-background/80 p-2.5 text-xs">
                <div className="grid grid-cols-2 gap-2 text-[0.6875rem]">
                  <div>
                    <span className="text-fg-tertiary">Voiceprint ID:</span>
                    <p className="font-mono font-medium text-fg">VP-CFO-8842</p>
                  </div>
                  <div>
                    <span className="text-fg-tertiary">Embedding Dim:</span>
                    <p className="font-mono font-medium text-fg">512-dim (WavLM-SV)</p>
                  </div>
                  <div>
                    <span className="text-fg-tertiary">Enrollment Sample:</span>
                    <p className="font-mono font-medium text-fg">16 kHz Clean PSTN</p>
                  </div>
                  <div>
                    <span className="text-fg-tertiary">Match Threshold:</span>
                    <p className="font-mono font-medium text-emerald-400">Cosine ≥ 0.75</p>
                  </div>
                </div>
                <p className="mt-2 border-t border-border/50 pt-1.5 text-[0.625rem] text-fg-tertiary">
                  E4 computes cosine distance between live turn embeddings and this reference vector.
                </p>
              </div>
            ) : null}
          </div>

          {evidence && evidence.top_factors.length > 0 ? (
            <div className="mt-3 border-t border-border pt-3">
              <p className="font-mono text-micro uppercase text-fg-tertiary">
                Contributing factors
              </p>
              <p className="mt-1 text-[0.6875rem] text-fg-tertiary/80">
                Features contributing to the score — attribution, not proof of anything.
              </p>
              <ul className="mt-2 space-y-1">
                {evidence.top_factors.map((factor) => (
                  <li
                    key={factor.factor}
                    className="flex items-baseline justify-between gap-3 text-[0.8125rem]"
                  >
                    <span className="min-w-0 truncate text-fg-secondary">
                      {humanise(factor.factor)}
                    </span>
                    <span
                      className={cn(
                        'shrink-0 font-mono tnum',
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

          {/* Export Evidence Dossier Button */}
          <div className="mt-4 border-t border-border pt-3">
            <button
              type="button"
              onClick={() => setShowDossier(true)}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-accent/40 bg-accent/10 px-3 py-2 text-xs font-semibold text-accent shadow-sm transition-colors hover:bg-accent/20 hover:text-white"
            >
              <FileText className="h-4 w-4" />
              Export Cryptographic Evidence Dossier
            </button>
          </div>
        </>
      )}

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
