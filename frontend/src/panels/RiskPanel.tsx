import React from 'react';

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
 * The decision panel.
 *
 * Two rules are enforced here rather than trusted to callers:
 *
 *  1. The score is written as `0.78`, never `78%`. `score_semantics` is
 *     UNCALIBRATED_RISK_SCORE - the number orders calls by concern, it does not
 *     estimate a probability of fraud, and a percent sign would assert a
 *     calibration nobody performed. `formatScore` is the only formatter used.
 *  2. When no assessment exists the score slot shows an em dash, never a
 *     numeral. A zero here would paint a reassuring LOW for a call the system
 *     has said nothing about.
 */
export const RiskPanel: React.FC = () => {
  const { state } = useSession();
  const stale = isStale(state);

  if (!state.sessionId) {
    return (
      <Panel title="Risk assessment" tag="L4 Composite">
        <EmptyState
          message="No active session."
          hint="Risk is produced by the pipeline once audio is flowing."
        />
      </Panel>
    );
  }

  if (state.riskStatus === 'error' && state.error) {
    return (
      <Panel title="Risk assessment" tag="L4 Composite">
        <ErrorState code={state.error.code} message={state.error.message} />
      </Panel>
    );
  }

  // No decision yet. Deliberately renders an em dash and the awaiting notice
  // rather than any number at all.
  if (!state.decision) {
    return (
      <Panel title="Risk assessment" tag="L4 Composite">
        <div className="rounded-lg border border-dashed border-band-uncertain/50 bg-band-uncertain/5 risk-hatch px-5 py-6">
          <p
            className="font-mono tnum text-7xl leading-none text-fg-tertiary"
            data-testid="risk-score"
          >
            {NONE}
          </p>
          <p className="mt-3 font-mono text-micro uppercase text-band-uncertain">
            Awaiting first action-grade assessment
          </p>
          <p className="mt-2 text-[0.8125rem] text-fg-secondary">
            {state.riskMessage ??
              'The pipeline has not yet produced an assessment for this call.'}
          </p>
          <p className="mt-3 font-mono text-micro text-fg-tertiary">
            frames seen {state.framesSeen} · scored {state.framesScored}
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
    <Panel title="Risk assessment" tag="L4 Composite">
      {stale ? (
        <div className="mb-4">
          <DisconnectedState
            at={formatClock(state.lastMessageAt)}
            attempt={state.reconnectAttempt}
          />
        </div>
      ) : null}

      <div
        className={cn(
          'rounded-lg border px-5 py-5 transition-colors duration-150',
          band.border,
          band.surface,
          critical && 'animate-pulse-edge',
        )}
        data-testid="risk-card"
        data-band={risk.risk_band}
      >
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p
              className={cn('font-mono tnum text-7xl leading-none', band.text)}
              data-testid="risk-score"
            >
              {formatScore(risk.risk_score)}
            </p>
            <p className="mt-2 text-xs text-fg-tertiary">
              {risk.score_label} · scale 0.00–1.00
            </p>
          </div>

          <div className="text-right">
            <p
              className={cn('text-lg font-semibold tracking-tight', band.text)}
              data-testid="risk-band"
            >
              {bandLabel(risk.risk_band)}
            </p>
            <p className="mt-1 max-w-[22ch] text-xs text-fg-secondary">{band.meaning}</p>
          </div>
        </div>

        {/* Permanent, not a tooltip: the calibration caveat qualifies the number
            above it and must travel with every reading of it. */}
        <p className="mt-4 border-t border-white/5 pt-3 text-xs text-fg-tertiary">
          {scoreDisclaimer(risk.score_semantics)}
        </p>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <MetricBar
          label="Confidence"
          value={risk.risk_confidence}
          tone={risk.risk_confidence < 0.4 ? 'bg-band-medium' : 'bg-accent'}
        />
        <div>
          <p className="font-mono text-micro uppercase text-fg-tertiary">Current action</p>
          <div className="mt-1.5">
            <Badge
              className={cn(action.text, action.border, action.surface)}
              title={action.headline}
            >
              <span data-testid="risk-action">{decision.action}</span>
            </Badge>
          </div>
        </div>
      </div>

      {/* Qualifiers that change how much the decision above can be relied on.
          These belong in the layout, not behind a hover. */}
      {(decision.fail_safe_engaged || state.analysisDegraded || risk.context_degraded) && (
        <div className="mt-4 space-y-1.5 border-t border-border pt-3">
          {decision.fail_safe_engaged ? (
            <p className="text-xs text-band-medium">
              Fail-safe path — this outcome came from incomplete evidence, not a confident
              assessment.
            </p>
          ) : null}
          {risk.context_degraded ? (
            <p className="text-xs text-band-medium">
              Call context was incomplete when this was assessed.
            </p>
          ) : null}
          {state.degradationReasons.length > 0 ? (
            <p className="font-mono text-micro text-fg-tertiary">
              {state.degradationReasons.join(' · ')}
            </p>
          ) : null}
        </div>
      )}
    </Panel>
  );
};
