'use client';

import { useMemo } from 'react';
import { ScrollText, ArrowRight, Clock } from 'lucide-react';
import { useDecisions, useCases } from '@/lib/hooks';
import { Card } from '@/components/ui/card';
import { VerdictBadge, Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { TableSkeleton } from '@/components/ui/loading-skeleton';
import {
  truncateId,
  formatDateTime,
  formatTimeAgo,
  formatActionType,
} from '@/lib/utils';

import Link from 'next/link';

interface AuditEntry {
  id: string;
  timestamp: string | null;
  type: 'decision' | 'case_created' | 'case_updated';
  title: string;
  subtitle: string;
  verdict: string | null;
  actionType: string | null;
  caseId: string;
  meta: string;
}

export default function AuditPage() {
  const {
    data: decisions,
    isLoading: decisionsLoading,
    isError: decisionsError,
    refetch: refetchDecisions,
  } = useDecisions({ limit: 200 });
  const {
    data: cases,
    isLoading: casesLoading,
  } = useCases({ limit: 200 });

  const isLoading = decisionsLoading || casesLoading;

  const allDecisions = useMemo(() => decisions || [], [decisions]);
  const allCases = useMemo(() => cases || [], [cases]);

  // Build audit trail from decisions and cases
  const auditEntries = useMemo(() => {
    const entries: AuditEntry[] = [];

    // Add case creation events
    allCases.forEach((c) => {
      entries.push({
        id: `case-${c.id}`,
        timestamp: c.detected_at,
        type: 'case_created',
        title: `Case detected: ${c.case_type.replace(/_/g, ' ').toLowerCase()}`,
        subtitle: `Amount at risk: created case`,
        verdict: null,
        actionType: null,
        caseId: c.id,
        meta: c.state,
      });
    });

    // Add decision events
    allDecisions.forEach((d) => {
      entries.push({
        id: d.id,
        timestamp: d.created_at,
        type: 'decision',
        title: `Decision: ${formatActionType(d.action_type)}`,
        subtitle: `${d.llm_provider} — ${d.llm_model}`,
        verdict: d.policy_verdict,
        actionType: d.action_type,
        caseId: d.case_id,
        meta: d.status || 'recorded',
      });
    });

    // Sort by timestamp descending (most recent first)
    return entries.sort((a, b) => {
      if (!a.timestamp) return 1;
      if (!b.timestamp) return -1;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
  }, [allCases, allDecisions]);

  if (decisionsError) {
    return (
      <div className="space-y-6 page-enter">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-1">Audit Log</h1>
          <p className="mt-1 text-sm text-text-3">
            Append-only audit trail of all system decisions and actions.
          </p>
        </div>
        <ErrorState
          message="Failed to load audit data."
          onRetry={() => refetchDecisions()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 page-enter">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Audit Log</h1>
        <p className="mt-1 text-sm text-text-3">
          Chronological audit trail of all payment events and AI decisions.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-[11px] font-medium uppercase tracking-wider text-text-3">
            Total Events
          </p>
          <p className="mt-2 metric-number text-text-1">{auditEntries.length}</p>
        </Card>
        <Card>
          <p className="text-[11px] font-medium uppercase tracking-wider text-text-3">
            Decisions
          </p>
          <p className="mt-2 metric-number text-text-1">{allDecisions.length}</p>
        </Card>
        <Card>
          <p className="text-[11px] font-medium uppercase tracking-wider text-text-3">
            Cases Detected
          </p>
          <p className="mt-2 metric-number text-text-1">{allCases.length}</p>
        </Card>
      </div>

      {/* Timeline */}
      <Card padding="none">
        {isLoading ? (
          <div className="p-6">
            <TableSkeleton rows={10} cols={4} />
          </div>
        ) : auditEntries.length === 0 ? (
          <EmptyState
            icon={ScrollText}
            title="No audit entries yet"
            description="The audit trail will populate as cases are detected and decisions are made."
          />
        ) : (
          <div className="divide-y divide-border/30">
            {/* Table header */}
            <div className="grid grid-cols-12 gap-4 px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-text-3 border-b border-border">
              <div className="col-span-1 hidden sm:block" />
              <div className="col-span-5 sm:col-span-4">Event</div>
              <div className="col-span-3 hidden sm:block">Details</div>
              <div className="col-span-2 sm:col-span-2 text-center">Status</div>
              <div className="col-span-4 sm:col-span-2 text-right">Time</div>
            </div>

            {/* Timeline entries */}
            {auditEntries.map((entry) => (
              <div
                key={entry.id}
                className="grid grid-cols-12 gap-4 px-6 py-4 table-row-hover group items-center"
              >
                {/* Timeline dot */}
                <div className="col-span-1 hidden sm:flex items-center justify-center">
                  <div
                    className={`h-2.5 w-2.5 rounded-full ${
                      entry.type === 'decision'
                        ? entry.verdict === 'APPROVE'
                          ? 'bg-success'
                          : entry.verdict === 'BLOCK'
                            ? 'bg-danger'
                            : entry.verdict === 'ESCALATE'
                              ? 'bg-warning'
                              : 'bg-accent'
                        : 'bg-info'
                    }`}
                  />
                </div>

                {/* Event */}
                <div className="col-span-7 sm:col-span-4 min-w-0">
                  <p className="text-sm font-medium text-text-1 truncate">
                    {entry.title}
                  </p>
                  <p className="text-xs text-text-3 truncate mt-0.5">
                    {entry.subtitle}
                  </p>
                </div>

                {/* Details */}
                <div className="col-span-3 hidden sm:block">
                  <div className="flex items-center gap-1.5">
                    <Link
                      href={`/cases/${entry.caseId}`}
                      className="font-mono text-[11px] text-accent hover:text-accent-hover transition-colors"
                    >
                      {truncateId(entry.caseId)}
                    </Link>
                    <ArrowRight className="h-2.5 w-2.5 text-text-4" />
                    <span className="text-[11px] text-text-3 capitalize">
                      {entry.meta.replace(/_/g, ' ').toLowerCase()}
                    </span>
                  </div>
                </div>

                {/* Status badge */}
                <div className="col-span-2 sm:col-span-2 flex justify-center">
                  {entry.verdict ? (
                    <VerdictBadge verdict={entry.verdict} />
                  ) : (
                    <Badge variant="info">
                      {entry.type === 'case_created' ? 'New' : entry.meta}
                    </Badge>
                  )}
                </div>

                {/* Time */}
                <div className="col-span-5 sm:col-span-2 text-right">
                  <div className="flex items-center justify-end gap-1.5">
                    <Clock className="h-3 w-3 text-text-4 hidden sm:block" />
                    <span className="text-xs text-text-3">
                      {formatTimeAgo(entry.timestamp)}
                    </span>
                  </div>
                  <p className="text-[10px] text-text-4 mt-0.5 hidden sm:block">
                    {formatDateTime(entry.timestamp)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
