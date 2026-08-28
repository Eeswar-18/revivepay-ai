'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, Filter, X, FlaskConical } from 'lucide-react';
import { useCases } from '@/lib/hooks';
import { DataTable } from '@/components/ui/data-table';
import { StateBadge, RiskBadge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { TableSkeleton } from '@/components/ui/loading-skeleton';
import { formatPaise, formatTimeAgo, truncateId, computeRiskLevel, formatCaseType } from '@/lib/utils';
import type { Case, CaseState, CaseType } from '@/lib/types';
import Link from 'next/link';

const CASE_STATES: CaseState[] = [
  'DETECTED', 'FEATURISED', 'PROPOSED', 'APPROVED', 'BLOCKED',
  'ESCALATED', 'SCHEDULED', 'EXECUTING', 'AWAITING_OUTCOME',
  'RECOVERED', 'FAILED', 'STOPPED', 'EXPIRED', 'CLOSED',
];

const CASE_TYPES: CaseType[] = [
  'FAILED_PAYMENT', 'ABANDONED_CHECKOUT', 'SUBSCRIPTION_DUNNING', 'INSTRUMENT_EXPIRY',
];

export default function CasesPage() {
  const router = useRouter();
  const [stateFilter, setStateFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [search, setSearch] = useState('');

  const { data: cases, isLoading, isError, refetch } = useCases({
    limit: 200,
    state: stateFilter || undefined,
    case_type: typeFilter || undefined,
  });

  const filteredCases = (cases || []).filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.id.toLowerCase().includes(q) ||
      c.case_type.toLowerCase().includes(q) ||
      c.state.toLowerCase().includes(q)
    );
  });

  const hasFilters = stateFilter || typeFilter || search;

  const columns = [
    {
      key: 'id',
      header: 'Case ID',
      primary: true,
      render: (c: Case) => (
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs text-accent">{truncateId(c.id)}</span>
          <StateBadge state={c.state} />
        </div>
      ),
    },
    {
      key: 'case_type',
      header: 'Type',
      render: (c: Case) => (
        <span className="text-xs text-text-2">{formatCaseType(c.case_type)}</span>
      ),
    },
    {
      key: 'amount_at_risk_minor',
      header: 'Amount',
      className: 'text-right',
      render: (c: Case) => (
        <span className="font-semibold tabular text-text-1">{formatPaise(c.amount_at_risk_minor)}</span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk',
      render: (c: Case) => <RiskBadge level={computeRiskLevel(c.state, c.amount_at_risk_minor)} />,
    },
    {
      key: 'state',
      header: 'Status',
      hideOnMobile: true,
      render: (c: Case) => <StateBadge state={c.state} />,
    },
    {
      key: 'detected_at',
      header: 'Detected',
      render: (c: Case) => (
        <span className="text-xs text-text-3">{formatTimeAgo(c.detected_at)}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6 page-enter">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Cases</h1>
        <p className="mt-1 text-sm text-text-3">
          Payment risk cases requiring investigation and recovery actions.
        </p>
      </div>

      {/* Filters */}
      <Card padding="sm">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search cases..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search cases"
              className="w-full rounded-lg border border-border bg-surface-2/50 px-3 py-2 pl-9 text-sm text-text-1 placeholder:text-text-4 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
            />
            <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-4" />
          </div>

          {/* State filter */}
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            aria-label="Filter by case state"
            className="rounded-lg border border-border bg-surface-2/50 px-3 py-2 text-sm text-text-2 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
          >
            <option value="">All States</option>
            {CASE_STATES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* Type filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            aria-label="Filter by case type"
            className="rounded-lg border border-border bg-surface-2/50 px-3 py-2 text-sm text-text-2 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
          >
            <option value="">All Types</option>
            {CASE_TYPES.map((t) => (
              <option key={t} value={t}>{formatCaseType(t)}</option>
            ))}
          </select>

          {hasFilters && (
            <button
              onClick={() => { setStateFilter(''); setTypeFilter(''); setSearch(''); }}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs text-text-3 transition-colors hover:bg-surface-2 hover:text-text-1"
            >
              <X className="h-3 w-3" />
              Clear
            </button>
          )}
        </div>
      </Card>

      {/* Content */}
      <Card padding="none">
        {isError ? (
          <ErrorState message="Failed to load cases. Is the backend running?" onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="p-6"><TableSkeleton rows={8} cols={6} /></div>
        ) : filteredCases.length === 0 ? (
          <EmptyState
            icon={AlertTriangle}
            title={hasFilters ? 'No matching cases' : 'No cases yet'}
            description={hasFilters ? 'Try adjusting your filters or search terms.' : 'Cases will appear here once payment events are processed.'}
            action={
              !hasFilters ? (
                <Link
                  href="/simulation"
                  className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
                >
                  <FlaskConical className="h-4 w-4" />
                  Run Simulation
                </Link>
              ) : undefined
            }
          />
        ) : (
          <>
            <div className="border-b border-border px-5 py-2.5 text-xs text-text-3">
              {filteredCases.length} case{filteredCases.length !== 1 ? 's' : ''}
            </div>
            <DataTable
              columns={columns}
              data={filteredCases}
              keyExtractor={(c) => c.id}
              onRowClick={(c) => router.push(`/cases/${c.id}`)}
            />
          </>
        )}
      </Card>
    </div>
  );
}
