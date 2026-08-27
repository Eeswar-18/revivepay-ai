'use client';

import type { Decision } from '@/lib/types';
import { VerdictBadge } from '@/components/ui/badge';
import { formatActionType, formatPercent } from '@/lib/utils';

interface DecisionSummaryProps {
  decision: Decision;
}

export function DecisionSummary({ decision }: DecisionSummaryProps) {
  const d = decision as unknown as Record<string, unknown>;
  const verdict = (d.policy_verdict as string) || '—';
  const actionType = (d.action_type as string) || null;
  const provider = (d.llm_provider as string) || '—';
  const confidence = d.llm_confidence as number | null;
  const proposalJson = d.proposal_json as Record<string, unknown> | null;
  const appliedRules = d.applied_rules_json as Record<string, unknown> | null;

  return (
    <>
      {/* Decision summary grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-surface-2/50 border border-border/40 px-4 py-3.5">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-4">Verdict</p>
          <div className="mt-1.5"><VerdictBadge verdict={verdict} /></div>
        </div>
        <div className="rounded-xl bg-surface-2/50 border border-border/40 px-4 py-3.5">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-4">Action</p>
          <p className="mt-1.5 text-sm font-medium text-text-1">{formatActionType(actionType)}</p>
        </div>
        <div className="rounded-xl bg-surface-2/50 border border-border/40 px-4 py-3.5">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-4">LLM Provider</p>
          <p className="mt-1.5 text-sm font-medium text-text-1">{provider}</p>
        </div>
        <div className="rounded-xl bg-surface-2/50 border border-border/40 px-4 py-3.5">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-4">Confidence</p>
          <p className="mt-1.5 text-sm font-semibold tabular text-text-1">
            {confidence != null ? formatPercent(confidence) : '—'}
          </p>
        </div>
      </div>

      {/* Proposal */}
      {proposalJson && (
        <div className="rounded-xl bg-surface-2/40 border border-border/40 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-3">Proposal</p>
          <pre className="mt-2 overflow-x-auto font-mono text-[11px] text-text-3 leading-relaxed">
            {JSON.stringify(proposalJson, null, 2)}
          </pre>
        </div>
      )}

      {/* Applied rules */}
      {appliedRules && Object.keys(appliedRules).length > 0 && (
        <div className="rounded-xl bg-surface-2/40 border border-border/40 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-3">Applied Rules</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {Object.entries(appliedRules).map(([key, val]) => (
              <span
                key={key}
                className="rounded-full bg-accent/8 border border-accent/15 px-2.5 py-1 text-xs font-medium text-accent"
              >
                {key}: {String(val)}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
