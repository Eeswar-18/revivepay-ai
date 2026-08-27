'use client';

import { use } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Search,
  Shield,
  Brain,
  Zap,
  FileText,
  Target,
  Gavel,
  Send,
} from 'lucide-react';
import { useCase, useDecisions, useFeatures } from '@/lib/hooks';
import { DecisionSummary } from '@/components/case/decision-summary';
import type { Decision } from '@/lib/types';
import { Card, CardHeader } from '@/components/ui/card';
import { StateBadge, RiskBadge, VerdictBadge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { PageSkeleton } from '@/components/ui/loading-skeleton';
import {
  formatPaise,
  formatDateTime,
  truncateId,
  computeRiskLevel,
  formatActionType,
  formatCaseType,
} from '@/lib/utils';
import Link from 'next/link';

const PIPELINE_STEPS = [
  { key: 'DETECTED', label: 'Detection', icon: Search, description: 'Payment event classified as revenue-at-risk' },
  { key: 'FEATURISED', label: 'Features', icon: FileText, description: 'Deterministic feature vector computed' },
  { key: 'PROPOSED', label: 'Risk Score', icon: Target, description: 'Calibrated P(recovery) estimated per candidate' },
  { key: 'APPROVED', label: 'Policy', icon: Gavel, description: 'Deterministic policy kernel applied' },
  { key: 'EXECUTING', label: 'Decision', icon: Brain, description: 'AI planner selected best intervention' },
  { key: 'RECOVERED', label: 'Action', icon: Send, description: 'Recovery action executed idempotently' },
] as const;

function getPipelineStep(state: string): number {
  const order = ['DETECTED', 'FEATURISED', 'PROPOSED', 'APPROVED', 'EXECUTING', 'RECOVERED'];
  const idx = order.indexOf(state);
  if (idx >= 0) return idx;
  if (state === 'BLOCKED' || state === 'FAILED' || state === 'EXPIRED') return 3;
  if (state === 'ESCALATED') return 3;
  if (state === 'SCHEDULED') return 4;
  if (state === 'AWAITING_OUTCOME') return 5;
  if (state === 'CLOSED') return 5;
  return 0;
}

export default function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: caseData, isLoading, isError, refetch } = useCase(id);
  const { data: decisionsData } = useDecisions({ case_id: id });
  const decisions: Decision[] = decisionsData ?? [];
  const { data: features } = useFeatures(id);

  if (isError) {
    return (
      <ErrorState
        message="Failed to load case details. Check the case ID and ensure the backend is running."
        onRetry={() => refetch()}
      />
    );
  }

  if (isLoading || !caseData) {
    return <PageSkeleton />;
  }

  const riskLevel = computeRiskLevel(caseData.state, caseData.amount_at_risk_minor);
  const pipelineStep = getPipelineStep(caseData.state);
  const caseDecisions = decisions;
  const latestDecision: Decision | undefined = caseDecisions.length > 0 ? caseDecisions[caseDecisions.length - 1] : undefined;

  return (
    <div className="space-y-6 page-enter">
      {/* Back link */}
      <Link
        href="/cases"
        className="inline-flex items-center gap-1.5 text-sm text-text-3 transition-colors hover:text-text-1"
      >
        <ArrowLeft className="h-4 w-4" />
        Cases
      </Link>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-text-1">
              Case #{truncateId(caseData.id)}
            </h1>
            <RiskBadge level={riskLevel} />
            <StateBadge state={caseData.state} />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-text-3">
            <span className="font-semibold tabular text-text-1 text-lg">
              {formatPaise(caseData.amount_at_risk_minor)}
            </span>
            <span className="text-text-4">·</span>
            <span>{formatCaseType(caseData.case_type)}</span>
            <span className="text-text-4">·</span>
            <span>{formatDateTime(caseData.detected_at)}</span>
          </div>
        </div>
      </div>

      {/* Decision Pipeline Visualization */}
      <Card>
        <CardHeader title="Decision Pipeline" description="Current stage in the recovery decision process" />
        <div className="mt-6 overflow-x-auto pb-2">
          <div className="flex items-start justify-between min-w-[500px]">
            {PIPELINE_STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isComplete = idx < pipelineStep;
              const isCurrent = idx === pipelineStep;
              const isBlocked = caseData.state === 'BLOCKED' || caseData.state === 'FAILED' || caseData.state === 'EXPIRED';
              const isFailedStep = isBlocked && isCurrent;

              return (
                <div key={step.key} className="flex flex-1 items-start last:flex-none">
                  <div className="flex flex-col items-center">
                    {/* Circle */}
                    <div
                      className={`flex h-11 w-11 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                        isComplete
                          ? 'border-success bg-success/10 text-success shadow-sm glow-success'
                          : isFailedStep
                          ? 'border-danger bg-danger/10 text-danger shadow-sm glow-danger'
                          : isCurrent
                          ? 'border-accent bg-accent/10 text-accent shadow-sm glow-accent'
                          : 'border-border bg-surface-2 text-text-4'
                      }`}
                    >
                      {isComplete ? (
                        <CheckCircle2 className="h-5 w-5" />
                      ) : isFailedStep ? (
                        <XCircle className="h-5 w-5" />
                      ) : (
                        <Icon className="h-5 w-5" />
                      )}
                    </div>
                    {/* Label */}
                    <span
                      className={`mt-2.5 text-[10px] font-semibold text-center max-w-[68px] leading-tight ${
                        isCurrent ? 'text-text-1' : isComplete ? 'text-success' : 'text-text-3'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {/* Connector line */}
                  {idx < PIPELINE_STEPS.length - 1 && (
                    <div className="flex-1 px-1 pt-[22px]">
                      <div
                        className={`h-[2px] w-full transition-colors duration-500 ${
                          isComplete ? 'bg-success/50' : 'bg-border/60'
                        }`}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          {/* Current step description */}
          <div className="mt-6 rounded-lg bg-accent/5 border border-accent/10 px-4 py-3 text-xs">
            <span className="font-semibold text-accent">Current:</span>{' '}
            <span className="text-text-2">{PIPELINE_STEPS[Math.min(pipelineStep, PIPELINE_STEPS.length - 1)].description}</span>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* AI Decision Panel */}
        {latestDecision && (
          <Card>
            <CardHeader title="AI Decision" description="Latest decision from the RevivePay pipeline" />
            <div className="mt-4 space-y-4">
              <DecisionSummary decision={latestDecision} />
            </div>
          </Card>
        )}

        {/* Case Details */}
        <Card>
          <CardHeader title="Case Details" description="Full case information" />
          <div className="mt-4 space-y-0">
            {[
              { label: 'Case ID', value: caseData.id, mono: true },
              { label: 'Transaction ID', value: caseData.transaction_id, mono: true },
              { label: 'Merchant ID', value: caseData.merchant_id, mono: true },
              { label: 'Customer ID', value: caseData.customer_id, mono: true },
              { label: 'Case Type', value: formatCaseType(caseData.case_type) },
              { label: 'Amount at Risk', value: formatPaise(caseData.amount_at_risk_minor), bold: true },
              { label: 'State', value: caseData.state },
              { label: 'Priority Score', value: caseData.priority_score?.toFixed(2) || '—' },
              {
                label: 'Expected Net Value',
                value: caseData.expected_net_value_minor != null
                  ? formatPaise(caseData.expected_net_value_minor)
                  : '—',
              },
              { label: 'Attempts Used', value: String(caseData.attempts_used) },
              { label: 'Recovery Deadline', value: formatDateTime(caseData.recovery_deadline_at) },
              { label: 'Recovered Amount', value: formatPaise(caseData.recovered_amount_minor) },
              { label: 'Closed At', value: formatDateTime(caseData.closed_at) },
              { label: 'Close Reason', value: caseData.close_reason || '—' },
            ].map(({ label, value, mono, bold }, idx, arr) => (
              <div key={label} className={`flex items-center justify-between py-2.5 ${idx < arr.length - 1 ? 'border-b border-border/30' : ''}`}>
                <span className="text-xs text-text-3">{label}</span>
                <span
                  className={`text-sm ${mono ? 'font-mono text-[11px] text-text-3' : ''} ${
                    bold ? 'font-semibold tabular text-text-1' : 'text-text-2'
                  }`}
                >
                  {value}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Feature Vector */}
      {features && Object.keys(features).length > 0 && (
        <Card>
          <CardHeader title="Feature Vector" description="Deterministic features extracted for this case" />
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {Object.entries(features)
              .filter(([, v]) => typeof v === 'number' || typeof v === 'boolean')
              .sort(([a], [b]) => a.localeCompare(b))
              .slice(0, 24)
              .map(([key, value]) => (
                <div key={key} className="rounded-lg bg-surface-2/40 border border-border/40 px-3 py-2.5 hover:border-border-strong transition-colors">
                  <p className="text-[10px] text-text-4 truncate font-mono">{key}</p>
                  <p className="mt-0.5 text-sm font-semibold tabular text-text-1">
                    {typeof value === 'boolean' ? (value ? '✓' : '✗') : typeof value === 'number' ? value.toFixed(4) : String(value)}
                  </p>
                </div>
              ))}
          </div>
        </Card>
      )}

      {/* Decision History */}
      {caseDecisions.length > 0 && (
        <Card>
          <CardHeader
            title="Decision History"
            description={`${caseDecisions.length} decision${caseDecisions.length !== 1 ? 's' : ''} for this case`}
          />
          <div className="mt-4 space-y-2">
            {caseDecisions.map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between rounded-lg border border-border bg-surface-2/30 px-4 py-3 card-interactive"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-md bg-surface-3 font-mono text-[10px] font-bold text-text-2">
                    {d.seq}
                  </span>
                  {d.policy_verdict && <VerdictBadge verdict={d.policy_verdict} />}
                  <span className="text-sm font-medium text-text-1">{formatActionType(d.action_type)}</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-text-3">
                  <span className="font-mono text-text-4">{d.llm_provider}</span>
                  <span>{formatDateTime(d.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
