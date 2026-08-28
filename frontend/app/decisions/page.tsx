'use client';

import { useState } from 'react';
import { Cpu, Filter, X } from 'lucide-react';
import { useDecisions } from '@/lib/hooks';
import { DataTable } from '@/components/ui/data-table';
import { Card } from '@/components/ui/card';
import { VerdictBadge, Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { TableSkeleton } from '@/components/ui/loading-skeleton';
import { truncateId, formatTimeAgo, formatActionType, formatPercent } from '@/lib/utils';
import type { Decision } from '@/lib/types';

const VERDICTS = ['APPROVE', 'MODIFY', 'BLOCK', 'ESCALATE'];

export default function DecisionsPage() {
  const [verdictFilter, setVerdictFilter] = useState('');
  const [search, setSearch] = useState('');

  const { data: decisions, isLoading, isError, refetch } = useDecisions({
    limit: 200,
    policy_verdict: verdictFilter || undefined,
  });

  const filtered = (decisions || []).filter((d) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      d.id.toLowerCase().includes(q) ||
      d.case_id.toLowerCase().includes(q) ||
      (d.action_type || '').toLowerCase().includes(q) ||
      (d.policy_verdict || '').toLowerCase().includes(q)
    );
  });

  const columns = [
    {
      key: 'id',
      header: 'Decision ID',
      primary: true,
      render: (d: Decision) => (
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs text-accent">{truncateId(d.id)}</span>
          {d.policy_verdict && <VerdictBadge verdict={d.policy_verdict} />}
        </div>
      ),
    },
    {
      key: 'case_id',
      header: 'Case',
      hideOnMobile: true,
      render: (d: Decision) => <span className="font-mono text-xs text-text-2">{truncateId(d.case_id)}</span>,
    },
    {
      key: 'seq',
      header: '#',
      className: 'text-center',
      hideOnMobile: true,
      render: (d: Decision) => <span className="text-xs text-text-3">{d.seq}</span>,
    },
    {
      key: 'action_type',
      header: 'Action',
      render: (d: Decision) => <span className="text-sm font-medium text-text-1">{formatActionType(d.action_type)}</span>,
    },
    {
      key: 'policy_verdict',
      header: 'Verdict',
      hideOnMobile: true,
      render: (d: Decision) => d.policy_verdict ? <VerdictBadge verdict={d.policy_verdict} /> : <span className="text-xs text-text-3">—</span>,
    },
    {
      key: 'status',
      header: 'Validation',
      hideOnMobile: true,
      render: (d: Decision) => (
        <Badge variant={d.status === 'valid' ? 'success' : d.status === 'invalid' ? 'danger' : 'default'}>
          {d.status || '—'}
        </Badge>
      ),
    },
    {
      key: 'llm_provider',
      header: 'LLM',
      hideOnMobile: true,
      render: (d: Decision) => <span className="text-xs text-text-3">{d.llm_provider}</span>,
    },
    {
      key: 'llm_confidence',
      header: 'Confidence',
      className: 'text-right',
      render: (d: Decision) => (
        <span className="tabular text-sm font-semibold text-text-1">
          {d.llm_confidence != null ? formatPercent(d.llm_confidence) : '—'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Time',
      render: (d: Decision) => <span className="text-xs text-text-3">{formatTimeAgo(d.created_at)}</span>,
    },
  ];

  return (
    <div className="space-y-6 page-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Decision Engine</h1>
        <p className="mt-1 text-sm text-text-3">AI-powered recovery decisions and policy evaluations.</p>
      </div>

      <Card padding="sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <input type="text" placeholder="Search decisions..." value={search} onChange={(e) => setSearch(e.target.value)}
              aria-label="Search decisions"
              className="w-full rounded-lg border border-border bg-surface-2/50 px-3 py-2 pl-9 text-sm text-text-1 placeholder:text-text-4 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors" />
            <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-4" />
          </div>
          <select value={verdictFilter} onChange={(e) => setVerdictFilter(e.target.value)}
            aria-label="Filter by verdict"
            className="rounded-lg border border-border bg-surface-2/50 px-3 py-2 text-sm text-text-2 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors">
            <option value="">All Verdicts</option>
            {VERDICTS.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          {(verdictFilter || search) && (
            <button onClick={() => { setVerdictFilter(''); setSearch(''); }}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs text-text-3 hover:bg-surface-2 hover:text-text-1 transition-colors">
              <X className="h-3 w-3" /> Clear
            </button>
          )}
        </div>
      </Card>

      <Card padding="none">
        {isError ? (
          <ErrorState message="Failed to load decisions." onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="p-6"><TableSkeleton rows={8} cols={9} /></div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={Cpu} title="No decisions yet" description="Decisions appear once the decision pipeline processes cases." />
        ) : (
          <>
            <div className="border-b border-border px-5 py-2.5 text-xs text-text-3">{filtered.length} decision{filtered.length !== 1 ? 's' : ''}</div>
            <DataTable columns={columns} data={filtered} keyExtractor={(d) => d.id} />
          </>
        )}
      </Card>
    </div>
  );
}
