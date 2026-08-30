import React from 'react';
import { SignalPanel, SignalPanelProps } from './SignalPanel';

export interface EvidencePanelShellProps extends SignalPanelProps {
  hashChained?: boolean;
  chainStatus?: string;
  recordType?: string;
  onExportDossier?: () => void;
  exportLabel?: string;
}

/**
 * Specialized shell for L3 Neural and Biometric Evidence presentation.
 * Encapsulates cryptographic tamper-evident badges, telemetry timelines, and export actions.
 */
export const EvidencePanelShell: React.FC<EvidencePanelShellProps> = ({
  hashChained = false,
  chainStatus,
  recordType,
  onExportDossier,
  exportLabel = 'Export Cryptographic Evidence Dossier',
  children,
  ...panelProps
}) => {
  return (
    <SignalPanel
      {...panelProps}
      headerActions={
        <div className="flex items-center gap-2">
          {hashChained ? (
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-micro-label font-bold text-emerald-400 border border-emerald-500/30">
              SHA-256 VERIFIED
            </span>
          ) : null}
          {panelProps.headerActions}
        </div>
      }
    >
      <div className="space-y-4">
        {children}

        {/* Chain Disclaimer & Action Footer */}
        {(chainStatus || recordType || onExportDossier) && (
          <div className="mt-4 border-t border-border/70 pt-3.5 space-y-3">
            {chainStatus || recordType ? (
              <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-micro-label text-fg-tertiary">
                <span>RECORD // {recordType ?? 'LIVE_EVIDENCE_SUMMARY'}</span>
                <span>STATUS // {chainStatus ?? 'IN_SESSION'}</span>
              </div>
            ) : null}

            {onExportDossier ? (
              <button
                type="button"
                onClick={onExportDossier}
                className="w-full rounded-xl border border-accent/40 bg-accent/10 py-2.5 px-4 font-mono text-technical-label font-bold text-accent transition-all hover:bg-accent/20 hover:border-accent hover:text-white"
              >
                {exportLabel}
              </button>
            ) : null}
          </div>
        )}
      </div>
    </SignalPanel>
  );
};
