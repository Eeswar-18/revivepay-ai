'use client';

import {
  AlertTriangle,
  TrendingUp,
  Shield,
  ArrowRight,
  FlaskConical,
  CircleDashed,
  Activity,
  Layers,
  ArrowUpRight,
} from 'lucide-react';
import { useCases, useDecisions, useVersion } from '@/lib/hooks';
import { MetricCard } from '@/components/ui/card';
import { Card } from '@/components/ui/card';
import { StateBadge, VerdictBadge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { MetricCardSkeleton } from '@/components/ui/loading-skeleton';
import { formatPaise, formatTimeAgo, truncateId, formatActionType, computeRiskLevel } from '@/lib/utils';
import Link from 'next/link';

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function getRiskDistribution(cases: { state: string; amount_at_risk_minor: number }[]) {
  const dist = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
  cases.forEach((c) => {
    const level = computeRiskLevel(c.state as never, c.amount_at_risk_minor);
    dist[level]++;
  });
  return dist;
}

export default function OverviewPage() {
  const cases = useCases({ limit: 100 });
  const decisions = useDecisions({ limit: 20 });
  const version = useVersion();

  const isLoading = cases.isLoading || decisions.isLoading;
  const isError = cases.isError || decisions.isError;

  const allCases = cases.data || [];
  const allDecisions = decisions.data || [];
  const totalCases = allCases.length;
  const failedPayments = allCases.filter((c) => c.case_type === 'FAILED_PAYMENT').length;
  const recoveredCases = allCases.filter((c) => c.state === 'RECOVERED').length;
  const highRiskCases = allCases.filter(
    (c) => c.state === 'BLOCKED' || c.state === 'FAILED' || c.state === 'ESCALATED' || c.state === 'EXPIRED'
  ).length;
  const recoveryRate = totalCases > 0 ? recoveredCases / totalCases : 0;
  const riskDist = getRiskDistribution(allCases);
  const totalRisk = riskDist.LOW + riskDist.MEDIUM + riskDist.HIGH + riskDist.CRITICAL || 1;

  if (isError) {
    return (
      <ErrorState
        message="Unable to connect to RevivePay API. Ensure the backend is running on localhost:8000."
        onRetry={() => { cases.refetch(); decisions.refetch(); }}
      />
    );
  }

  return (
    <div className="space-y-8 page-enter">
      {/* Header */}
      <div>
        <p className="text-sm text-text-3">{getGreeting()}</p>
        <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-text-1">
          Payment Risk Intelligence
        </h1>
        <p className="mt-1.5 text-sm text-text-3 max-w-lg leading-relaxed">
          Monitor payment failures, detect risk patterns, and understand recovery decisions in real time.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          <>
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
          </>
        ) : (
          <>
            <MetricCard label="Total Cases" value={totalCases} icon={Layers} accent />
            <MetricCard label="Failed Payments" value={failedPayments} icon={CircleDashed} />
            <MetricCard
              label="Recovery Rate"
              value={`${(recoveryRate * 100).toFixed(1)}%`}
              icon={TrendingUp}
              accent={recoveryRate > 0}
            />
            <MetricCard
              label="High Risk"
              value={highRiskCases}
              icon={Shield}
            />
          </>
        )}
      </div>

      {/* Risk Distribution Bar */}
      {!isLoading && totalCases > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-text-1">Risk Distribution</h3>
            <span className="text-xs text-text-3">{totalCases} cases</span>
          </div>
          <div className="flex h-2.5 overflow-hidden rounded-full bg-surface-2">
            {riskDist.LOW > 0 && (
              <div
                className="bg-success transition-all duration-1000 ease-out"
                style={{ width: `${(riskDist.LOW / totalRisk) * 100}%` }}
              />
            )}
            {riskDist.MEDIUM > 0 && (
              <div
                className="bg-warning transition-all duration-1000 ease-out"
                style={{ width: `${(riskDist.MEDIUM / totalRisk) * 100}%` }}
              />
            )}
            {riskDist.HIGH > 0 && (
              <div
                className="bg-[#f97316] transition-all duration-1000 ease-out"
                style={{ width: `${(riskDist.HIGH / totalRisk) * 100}%` }}
              />
            )}
            {riskDist.CRITICAL > 0 && (
              <div
                className="bg-danger transition-all duration-1000 ease-out"
                style={{ width: `${(riskDist.CRITICAL / totalRisk) * 100}%` }}
              />
            )}
          </div>
          <div className="flex items-center gap-6 mt-3.5">
            {[
              { label: 'Low', count: riskDist.LOW, color: 'bg-success' },
              { label: 'Medium', count: riskDist.MEDIUM, color: 'bg-warning' },
              { label: 'High', count: riskDist.HIGH, color: 'bg-[#f97316]' },
              { label: 'Critical', count: riskDist.CRITICAL, color: 'bg-danger' },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${item.color}`} />
                <span className="text-xs text-text-3">{item.label}</span>
                <span className="text-xs font-semibold tabular text-text-2">{item.count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Empty state */}
      {!isLoading && totalCases === 0 && (
        <Card className="py-0">
          <EmptyState
            icon={FlaskConical}
            title="No payment cases yet"
            description="Once transactions enter RevivePay, risk decisions and recovery recommendations will appear here."
            action={
              <Link
                href="/simulation"
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-accent-hover hover:shadow-lg hover:shadow-accent/20"
              >
                <FlaskConical className="h-4 w-4" />
                Run Simulation
              </Link>
            }
          />
        </Card>
      )}

      {/* Two-column: Recent Cases + Recent Decisions */}
      {totalCases > 0 && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          {/* Recent Cases */}
          <Card padding="none">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <div>
                <h2 className="text-sm font-semibold text-text-1">Recent Cases</h2>
                <p className="mt-0.5 text-xs text-text-3">Latest payment risk cases</p>
              </div>
              <Link
                href="/cases"
                className="flex items-center gap-1 text-xs font-medium text-accent transition-colors hover:text-accent-hover"
              >
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="divide-y divide-border/40">
              {allCases.slice(0, 8).map((c) => (
                <Link
                  key={c.id}
                  href={`/cases/${c.id}`}
                  className="flex items-center justify-between px-6 py-3.5 table-row-hover group"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-[11px] text-text-3">
                        {truncateId(c.id)}
                      </span>
                      <StateBadge state={c.state} />
                    </div>
                    <p className="mt-1 text-xs text-text-3 capitalize">{c.case_type.replace(/_/g, ' ').toLowerCase()}</p>
                  </div>
                  <div className="text-right flex items-center gap-2">
                    <div>
                      <p className="text-sm font-semibold tabular text-text-1">
                        {formatPaise(c.amount_at_risk_minor)}
                      </p>
                      <p className="mt-0.5 text-[11px] text-text-3">
                        {formatTimeAgo(c.detected_at)}
                      </p>
                    </div>
                    <ArrowUpRight className="h-3.5 w-3.5 text-text-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </Link>
              ))}
            </div>
          </Card>

          {/* Recent Decisions */}
          <Card padding="none">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <div>
                <h2 className="text-sm font-semibold text-text-1">Recent Decisions</h2>
                <p className="mt-0.5 text-xs text-text-3">AI-powered recovery decisions</p>
              </div>
              <Link
                href="/decisions"
                className="flex items-center gap-1 text-xs font-medium text-accent transition-colors hover:text-accent-hover"
              >
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="divide-y divide-border/40">
              {allDecisions.slice(0, 8).map((d) => (
                <div key={d.id} className="flex items-center justify-between px-6 py-3.5 table-row-hover">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-[11px] text-text-3">
                        {truncateId(d.id)}
                      </span>
                      {d.policy_verdict && <VerdictBadge verdict={d.policy_verdict} />}
                    </div>
                    <p className="mt-1 text-xs text-text-3">
                      {formatActionType(d.action_type)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-text-2">{d.llm_provider}</p>
                    <p className="mt-0.5 text-[11px] text-text-3">
                      {formatTimeAgo(d.created_at)}
                    </p>
                  </div>
                </div>
              ))}
              {allDecisions.length === 0 && (
                <div className="px-6 py-10 text-center">
                  <Activity className="mx-auto h-8 w-8 text-text-4" />
                  <p className="mt-2 text-sm text-text-3">No decisions recorded yet</p>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* System Info */}
      {version.data && (
        <div className="flex flex-wrap items-center justify-between gap-4 px-1">
          <div className="flex items-center gap-3 text-xs text-text-3">
            <span>
              v{version.data.version}
              {version.data.git_sha && (
                <span className="ml-1 font-mono text-text-4">({version.data.git_sha.slice(0, 7)})</span>
              )}
            </span>
            <span className="text-text-4">·</span>
            <span>LLM: {version.data.llm_provider}</span>
          </div>
          <span className="rounded-full bg-warning/6 border border-warning/12 px-3 py-1 text-[10px] font-semibold text-warning tracking-wider uppercase">
            Simulated Data
          </span>
        </div>
      )}
    </div>
  );
}
