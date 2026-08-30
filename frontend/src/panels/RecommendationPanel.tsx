import React from 'react';
import { ArrowRight, ShieldAlert } from 'lucide-react';

import { Badge } from '../components/Badge';
import { EmptyState } from '../components/PanelStates';
import { Panel } from '../components/Panel';
import { cn } from '../lib/cn';
import { humanise } from '../lib/format';
import { actionTokens } from '../lib/risk';
import { useSession } from '../state/useSession';

/**
 * Editorial Recommendation Panel (L5 Policy Engine).
 *
 * Verifications strings are sourced directly from the backend policy engine
 * (`recommended_verifications`), maintaining single source of truth.
 */
export const RecommendationPanel: React.FC = () => {
  const { state } = useSession();
  const decision = state.decision;

  if (!decision) {
    return (
      <Panel
        title="Recommended action"
        sectionNumber="02.B"
        tag="L5 Policy"
        subtitle="Automated Policy Directives"
      >
        <EmptyState
          message="No recommendation yet."
          hint="A policy recommendation accompanies each action-grade assessment."
        />
      </Panel>
    );
  }

  const action = actionTokens[decision.action];

  return (
    <Panel
      title="Recommended action"
      sectionNumber="02.B"
      tag="L5 Policy"
      subtitle="Automated Policy Directives"
    >
      {/* Primary Action Directives Strip */}
      <div className={cn('rounded-2xl border p-4 transition-all', action.border, action.surface)}>
        <div className="flex items-start gap-3.5">
          <div className={cn('mt-0.5 rounded-lg p-1.5 ring-1', action.border, action.surface)}>
            <ShieldAlert className={cn('h-5 w-5 shrink-0', action.text)} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className={cn('text-sm font-bold', action.text)}>{action.headline}</p>
            <div className="mt-1 flex items-center gap-2 font-mono text-micro uppercase tracking-wider text-fg-tertiary">
              <span className="font-semibold text-fg-secondary">{decision.action}</span>
              <span>·</span>
              <span>TRANSACTION TIER {decision.transaction_tier}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Required Out-Of-Band Verifications List */}
      {decision.recommended_verifications.length > 0 ? (
        <div className="mt-4 space-y-2">
          <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
            Mandated Verification Protocol
          </span>
          <ul className="space-y-2">
            {decision.recommended_verifications.map((item) => (
              <li
                key={item}
                className="flex items-start gap-2.5 rounded-xl border border-border/60 bg-surface-elevated/40 px-3 py-2 text-xs leading-relaxed text-fg-secondary"
              >
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-accent mt-0.5" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Attributed Reason Codes */}
      {decision.reason_codes.length > 0 ? (
        <div className="mt-4 border-t border-border/80 pt-3">
          <span className="font-mono text-micro uppercase tracking-wider text-fg-tertiary">
            Matched Rule Attribution Codes
          </span>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {decision.reason_codes.map((code) => (
              <Badge
                key={code}
                className="border-border bg-surface-elevated text-fg-secondary hover:text-fg"
                title={humanise(code)}
              >
                {code}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {/* Footer Rule Versioning */}
      <div className="mt-4 flex items-center justify-between border-t border-border/60 pt-2.5 font-mono text-micro text-fg-tertiary">
        <span>RULE: {decision.matched_policy}</span>
        <span>VERSION: {decision.policy_version}</span>
      </div>
    </Panel>
  );
};

