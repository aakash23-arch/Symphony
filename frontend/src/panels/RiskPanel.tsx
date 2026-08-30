import React from 'react';
import { AlertCircle, AlertTriangle } from 'lucide-react';

import { Badge } from '../components/Badge';
import { MetricBar } from '../components/Metric';
import { DisconnectedState, EmptyState, ErrorState } from '../components/PanelStates';
import { Panel } from '../components/Panel';
import { cn } from '../lib/cn';
import { formatClock, NONE } from '../lib/format';
import {
  actionTokens,
  bandLabel,
  bandTokens,
  formatScore,
  scoreDisclaimer,
} from '../lib/risk';
import { isStale } from '../state/sessionReducer';
import { useSession } from '../state/useSession';

/**
 * Editorial Risk Assessment Panel (L4 Composite).
 *
 * Enforces two critical non-negotiable rules:
 *  1. The score is displayed as an uncalibrated scalar (e.g. `0.78`), NEVER as a percentage (`78%`).
 *  2. When no assessment is produced, an em dash (`—`) is rendered rather than 0.00.
 */
export const RiskPanel: React.FC = () => {
  const { state } = useSession();
  const stale = isStale(state);

  if (!state.sessionId) {
    return (
      <Panel
        title="Risk assessment"
        sectionNumber="02"
        tag="L4 Composite"
        subtitle="Multi-Modal Threat Level"
      >
        <EmptyState
          message="No active session."
          hint="Risk is produced by the pipeline once audio is flowing."
        />
        <p className="mt-4 border-t border-border/60 pt-2.5 text-[0.6875rem] text-fg-tertiary">
          {scoreDisclaimer('UNCALIBRATED_RISK_SCORE')}
        </p>
      </Panel>
    );
  }

  if (state.riskStatus === 'error' && state.error) {
    return (
      <Panel
        title="Risk assessment"
        sectionNumber="02"
        tag="L4 Composite"
        subtitle="Multi-Modal Threat Level"
      >
        <ErrorState code={state.error.code} message={state.error.message} />
        <p className="mt-4 border-t border-border/60 pt-2.5 text-[0.6875rem] text-fg-tertiary">
          {scoreDisclaimer('UNCALIBRATED_RISK_SCORE')}
        </p>
      </Panel>
    );
  }

  // Awaiting state: explicitly renders em dash rather than 0.00
  if (!state.decision) {
    return (
      <Panel
        title="Risk assessment"
        sectionNumber="02"
        tag="L4 Composite"
        subtitle="Multi-Modal Threat Level"
      >
        <div className="border border-dashed border-border bg-surface p-6">
          <div className="flex items-baseline justify-between">
            <p
              className="font-mono tnum text-7xl font-light tracking-tight text-fg-tertiary"
              data-testid="risk-score"
            >
              {NONE}
            </p>
            <span className="border border-border bg-surface px-2.5 py-1 font-mono text-micro uppercase text-fg-primary">
              Awaiting Assessment
            </span>
          </div>
          <p className="mt-3 font-mono text-micro uppercase tracking-wider text-band-uncertain">
            Awaiting first action-grade assessment
          </p>
          <p className="mt-1.5 text-xs text-fg-secondary">
            {state.riskMessage ??
              'The pipeline is accumulating spectral frames to produce a calibrated action-grade assessment.'}
          </p>
          <p className="mt-3 font-mono text-micro text-fg-tertiary border-t border-border/40 pt-2">
            frames seen {state.framesSeen} · scored {state.framesScored}
          </p>
          <p className="mt-2 text-[0.6875rem] text-fg-tertiary">
            {scoreDisclaimer('UNCALIBRATED_RISK_SCORE')}
          </p>
        </div>
      </Panel>
    );
  }

  const decision = state.decision;
  const risk = decision.risk;
  const band = bandTokens[risk.risk_band];
  const action = actionTokens[decision.action];
  const critical = risk.risk_band === 'CRITICAL';

  return (
    <Panel
      title="Risk assessment"
      sectionNumber="02"
      tag="L4 Composite"
      subtitle="Multi-Modal Threat Level"
    >
      {stale ? (
        <div className="mb-4">
          <DisconnectedState
            at={formatClock(state.lastMessageAt)}
            attempt={state.reconnectAttempt}
          />
        </div>
      ) : null}

      {/* Primary Risk Decision Hero Card */}
      <div
        className={cn(
          'relative overflow-hidden border p-5 transition-all duration-200',
          band.border,
          band.surface,
          critical && 'animate-pulse-edge',
        )}
        data-testid="risk-card"
        data-band={risk.risk_band}
      >
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-micro uppercase tracking-widest text-fg-tertiary">
                {risk.score_label}
              </span>
              <span className="font-mono text-[0.625rem] text-fg-tertiary">SCALE 0.00–1.00</span>
            </div>
            <p
              className={cn('mt-1 font-mono tnum text-7xl font-bold tracking-tight leading-none', band.text)}
              data-testid="risk-score"
            >
              {formatScore(risk.risk_score)}
            </p>
          </div>

          <div className="text-right">
            <p
              className={cn('text-xl font-bold tracking-tight', band.text)}
              data-testid="risk-band"
            >
              {bandLabel(risk.risk_band)}
            </p>
            <p className="mt-1 max-w-[24ch] text-xs text-fg-secondary leading-snug">{band.meaning}</p>
          </div>
        </div>

        {/* Uncalibrated caveat notice */}
        <p className="mt-4 border-t border-white/10 pt-2.5 text-[0.6875rem] text-fg-tertiary">
          {scoreDisclaimer(risk.score_semantics)}
        </p>
      </div>

      {/* Metric Bars & Current Action */}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <MetricBar
          label="Risk Assessment Confidence"
          value={risk.risk_confidence}
          tone={risk.risk_confidence < 0.4 ? 'bg-band-medium' : 'bg-accent'}
        />
        <div>
          <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
            Mandated Security Action
          </span>
          <div className="mt-1.5">
            <Badge
              className={cn('px-2.5 py-1 text-xs font-bold', action.text, action.border, action.surface)}
              title={action.headline}
            >
              <span data-testid="risk-action">{decision.action}</span>
            </Badge>
          </div>
        </div>
      </div>

      {/* Fail-Safe & Degradation Disclosures */}
      {(decision.fail_safe_engaged || state.analysisDegraded || risk.context_degraded) && (
        <div className="mt-4 space-y-2 border border-border bg-surface p-3">
          {decision.fail_safe_engaged ? (
            <div className="flex items-center gap-2 text-xs font-medium text-band-medium">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>Fail-safe engaged: Incomplete acoustic evidence triggered default protection.</span>
            </div>
          ) : null}
          {risk.context_degraded ? (
            <div className="flex items-center gap-2 text-xs text-band-medium">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              <span>Context degraded: Ingested telemetry vector had incomplete fields.</span>
            </div>
          ) : null}
          {state.degradationReasons.length > 0 ? (
            <p className="font-mono text-[0.6875rem] text-fg-tertiary pl-5">
              Reasons: {state.degradationReasons.join(' · ')}
            </p>
          ) : null}
        </div>
      )}
    </Panel>
  );
};

