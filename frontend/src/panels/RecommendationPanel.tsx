import React from 'react';
import { ShieldAlert } from 'lucide-react';

import { Badge } from '../components/Badge';
import { EmptyState } from '../components/PanelStates';
import { Panel } from '../components/Panel';
import { cn } from '../lib/cn';
import { humanise } from '../lib/format';
import { actionTokens } from '../lib/risk';
import { useSession } from '../state/useSession';

/**
 * What a human should do next, in words.
 *
 * The recommendation strings come from the backend's policy engine
 * (`recommended_verifications`), not from a lookup table here. A second
 * frontend-side mapping would be a second policy implementation, free to drift
 * from the one that actually made the decision.
 */
export const RecommendationPanel: React.FC = () => {
  const { state } = useSession();
  const decision = state.decision;

  if (!decision) {
    return (
      <Panel title="Recommended action" tag="L5 Policy">
        <EmptyState
          message="No recommendation yet."
          hint="A recommendation accompanies each action-grade assessment."
        />
      </Panel>
    );
  }

  const action = actionTokens[decision.action];

  return (
    <Panel title="Recommended action" tag="L5 Policy">
      <div className={cn('rounded-lg border px-4 py-3', action.border, action.surface)}>
        <div className="flex items-start gap-3">
          <ShieldAlert className={cn('mt-0.5 h-4 w-4 shrink-0', action.text)} aria-hidden />
          <div className="min-w-0">
            <p className={cn('text-sm font-semibold', action.text)}>{action.headline}</p>
            <p className="mt-1 font-mono text-micro uppercase text-fg-tertiary">
              {decision.action} · tier {decision.transaction_tier}
            </p>
          </div>
        </div>
      </div>

      {decision.recommended_verifications.length > 0 ? (
        <ul className="mt-3 space-y-1.5">
          {decision.recommended_verifications.map((item) => (
            <li key={item} className="flex gap-2 text-[0.8125rem] leading-snug text-fg-secondary">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-fg-tertiary" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
      ) : null}

      {decision.reason_codes.length > 0 ? (
        <div className="mt-4 border-t border-border pt-3">
          <p className="font-mono text-micro uppercase text-fg-tertiary">Reason codes</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {decision.reason_codes.map((code) => (
              <Badge key={code} className="border-border text-fg-secondary" title={humanise(code)}>
                {code}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      <p className="mt-4 border-t border-border pt-2.5 font-mono text-micro text-fg-tertiary">
        {decision.matched_policy} · policy {decision.policy_version}
      </p>
    </Panel>
  );
};
