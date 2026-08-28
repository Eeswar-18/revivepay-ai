'use client';

import { useState, useMemo } from 'react';
import { Zap, Filter, X, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { useCases } from '@/lib/hooks';
import { DataTable } from '@/components/ui/data-table';
import { Card, MetricCard } from '@/components/ui/card';
import { StateBadge, RiskBadge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { TableSkeleton, MetricCardSkeleton } from '@/components/ui/loading-skeleton';
import {
  formatPaise,
  formatPaiseShort,
  formatTimeAgo,
  truncateId,
  computeRiskLevel,
  formatCaseType,
} from '@/lib/utils';
import type { Case, CaseState } from '@/lib/types';
import { useRouter } from 'next/navigation';

const CASE_STATES: CaseState[] = [
  'DETECTED',
  'FEATURISED',
  'PROPOSED',
  'APPROVED',
  'BLOCKED',
  'ESCALATED',
  'SCHEDULED',
  'EXECUTING',
  'AWAITING_OUTCOME',
  'RECOVERED',
  'FAILED',
  'STOPPED',
  'EXPIRED',
  'CLOSED',
];

export default function TransactionsPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const { data: cases, isLoading, isError, refetch } = useCases({ limit: 200 });

  const allCases = useMemo(() => cases || [], [cases]);

  // Summary metrics
  const totalAmount = useMemo(
    () => allCases.reduce((sum, c) => sum + c.amount_at_risk_minor, 0),
    [allCases]
  );
  const recoveredAmount = useMemo(
    () =>
      allCases
        .filter((c) => c.state === 'RECOVERED')
        .reduce((sum, c) => sum + c.amount_at_risk_minor, 0),
    [allCases]
  );
  const criticalCount = useMemo(
    () =>
      allCases.filter(
        (c) =>
          computeRiskLevel(c.state, c.amount_at_risk_minor) === 'CRITICAL'
      ).length,
    [allCases]
  );

  const transactions = useMemo(() => {
    const filtered = stateFilter
      ? allCases.filter((c) => c.state === stateFilter)
      : allCases;
    if (!search) return filtered;
    const q = search.toLowerCase();
    return filtered.filter(
      (c) =>
        c.id.toLowerCase().includes(q) ||
        c.case_type.toLowerCase().includes(q) ||
        c.state.toLowerCase().includes(q) ||
        c.merchant_id.toLowerCase().includes(q) ||
        c.customer_id.toLowerCase().includes(q)
    );
  }, [allCases, stateFilter, search]);

  const hasFilters = stateFilter || search;

  const columns = [
    {
      key: 'id',
      header: 'Transaction ID',
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
        <span className="font-semibold tabular text-text-1">
          {formatPaise(c.amount_at_risk_minor)}
        </span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk',
      render: (c: Case) => (
        <RiskBadge level={computeRiskLevel(c.state, c.amount_at_risk_minor)} />
      ),
    },
    {
      key: 'state',
      header: 'Status',
      hideOnMobile: true,
      render: (c: Case) => <StateBadge state={c.state} />,
    },
    {
      key: 'merchant_id',
      header: 'Merchant',
      hideOnMobile: true,
      render: (c: Case) => (
        <span className="font-mono text-xs text-text-3">
          {truncateId(c.merchant_id)}
        </span>
      ),
    },
    {
      key: 'customer_id',
      header: 'Customer',
      hideOnMobile: true,
      render: (c: Case) => (
        <span className="font-mono text-xs text-text-3">
          {truncateId(c.customer_id)}
        </span>
      ),
    },
    {
      key: 'detected_at',
      header: 'Time',
      render: (c: Case) => (
        <span className="text-xs text-text-3">{formatTimeAgo(c.detected_at)}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6 page-enter">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">
          Transactions
        </h1>
        <p className="mt-1 text-sm text-text-3">
          Payment transactions with amounts at risk and recovery tracking.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <>
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
          </>
        ) : (
          <>
            <MetricCard
              label="Total at Risk"
              value={formatPaiseShort(totalAmount)}
              icon={AlertTriangle}
              accent
            />
            <MetricCard
              label="Recovered"
              value={formatPaiseShort(recoveredAmount)}
              icon={TrendingUp}
              accent={recoveredAmount > 0}
            />
            <MetricCard
              label="Critical Risk"
              value={criticalCount}
              icon={TrendingDown}
            />
          </>
        )}
      </div>

      {/* Filters */}
      <Card padding="sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search by ID, type, merchant, customer..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search transactions"
              className="w-full rounded-lg border border-border bg-surface-2/50 px-3 py-2 pl-9 text-sm text-text-1 placeholder:text-text-4 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
            />
            <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-4" />
          </div>
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            aria-label="Filter by state"
            className="rounded-lg border border-border bg-surface-2/50 px-3 py-2 text-sm text-text-2 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
          >
            <option value="">All States</option>
            {CASE_STATES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          {hasFilters && (
            <button
              onClick={() => {
                setStateFilter('');
                setSearch('');
              }}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs text-text-3 transition-colors hover:bg-surface-2 hover:text-text-1"
            >
              <X className="h-3 w-3" /> Clear
            </button>
          )}
        </div>
      </Card>

      {/* Table */}
      <Card padding="none">
        {isError ? (
          <ErrorState
            message="Failed to load transactions."
            onRetry={() => refetch()}
          />
        ) : isLoading ? (
          <div className="p-6">
            <TableSkeleton rows={8} cols={8} />
          </div>
        ) : transactions.length === 0 ? (
          <EmptyState
            icon={Zap}
            title={hasFilters ? 'No matching transactions' : 'No transactions yet'}
            description={
              hasFilters
                ? 'Try adjusting your filters or search terms.'
                : 'Failed payment transactions will appear here.'
            }
          />
        ) : (
          <>
            <div className="border-b border-border px-5 py-2.5 text-xs text-text-3">
              {transactions.length} transaction
              {transactions.length !== 1 ? 's' : ''}
            </div>
            <DataTable
              columns={columns}
              data={transactions}
              keyExtractor={(c) => c.id}
              onRowClick={(c) => router.push(`/cases/${c.id}`)}
            />
          </>
        )}
      </Card>
    </div>
  );
}
