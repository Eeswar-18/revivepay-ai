'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, Filter, X } from 'lucide-react';
import { useCustomers } from '@/lib/hooks';
import { DataTable } from '@/components/ui/data-table';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { TableSkeleton } from '@/components/ui/loading-skeleton';
import { formatPercent, truncateId } from '@/lib/utils';
import type { Customer, CustomerSegment } from '@/lib/types';

const SEGMENTS: CustomerSegment[] = ['NEW', 'OCCASIONAL', 'LOYAL', 'HIGH_VALUE'];

const SEGMENT_COLORS: Record<string, string> = {
  NEW: 'bg-info/10 text-info border-info/20',
  OCCASIONAL: 'bg-warning/10 text-warning border-warning/20',
  LOYAL: 'bg-success/10 text-success border-success/20',
  HIGH_VALUE: 'bg-accent/10 text-accent border-accent/20',
};

export default function CustomersPage() {
  const router = useRouter();
  const [segmentFilter, setSegmentFilter] = useState<string>('');
  const [search, setSearch] = useState('');

  const { data: customers, isLoading, isError, refetch } = useCustomers({
    limit: 200,
    segment: segmentFilter || undefined,
  });

  const filtered = (customers || []).filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.id.toLowerCase().includes(q) ||
      c.region.toLowerCase().includes(q) ||
      c.preferred_method.toLowerCase().includes(q) ||
      c.segment.toLowerCase().includes(q)
    );
  });

  const columns = [
    {
      key: 'id',
      header: 'Customer ID',
      primary: true,
      render: (c: Customer) => (
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs text-accent">{truncateId(c.id)}</span>
          <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${SEGMENT_COLORS[c.segment] || ''}`}>
            {c.segment}
          </span>
        </div>
      ),
    },
    {
      key: 'segment',
      header: 'Segment',
      hideOnMobile: true,
      render: (c: Customer) => (
        <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${SEGMENT_COLORS[c.segment] || ''}`}>
          {c.segment}
        </span>
      ),
    },
    {
      key: 'region',
      header: 'Region',
      render: (c: Customer) => <span className="text-xs text-text-2">{c.region}</span>,
    },
    {
      key: 'lifetime_txn_count',
      header: 'Transactions',
      className: 'text-right',
      render: (c: Customer) => (
        <span className="tabular text-sm font-semibold text-text-1">{c.lifetime_txn_count}</span>
      ),
    },
    {
      key: 'lifetime_success_rate',
      header: 'Success Rate',
      className: 'text-right',
      render: (c: Customer) => (
        <span className="tabular text-sm text-text-1">{formatPercent(c.lifetime_success_rate)}</span>
      ),
    },
    {
      key: 'preferred_method',
      header: 'Preferred',
      hideOnMobile: true,
      render: (c: Customer) => (
        <span className="text-xs text-text-2 uppercase font-medium">{c.preferred_method}</span>
      ),
    },
    {
      key: 'do_not_contact',
      header: 'DNC',
      hideOnMobile: true,
      render: (c: Customer) =>
        c.do_not_contact ? (
          <span className="text-xs font-semibold text-danger">Yes</span>
        ) : (
          <span className="text-xs text-text-3">No</span>
        ),
    },
  ];

  return (
    <div className="space-y-6 page-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Customers</h1>
        <p className="mt-1 text-sm text-text-3">Customer profiles with payment behavior and recovery history.</p>
      </div>

      <Card padding="sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <input type="text" placeholder="Search customers..." value={search} onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface-2/50 px-3 py-2 pl-9 text-sm text-text-1 placeholder:text-text-4 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors" />
            <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-4" />
          </div>
          <select value={segmentFilter} onChange={(e) => setSegmentFilter(e.target.value)}
            className="rounded-lg border border-border bg-surface-2/50 px-3 py-2 text-sm text-text-2 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors">
            <option value="">All Segments</option>
            {SEGMENTS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {(segmentFilter || search) && (
            <button onClick={() => { setSegmentFilter(''); setSearch(''); }}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs text-text-3 transition-colors hover:bg-surface-2 hover:text-text-1">
              <X className="h-3 w-3" /> Clear
            </button>
          )}
        </div>
      </Card>

      <Card padding="none">
        {isError ? (
          <ErrorState message="Failed to load customers." onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="p-6"><TableSkeleton rows={8} cols={7} /></div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={Users} title="No customers yet" description="Customer profiles will appear once transactions are processed." />
        ) : (
          <>
            <div className="border-b border-border px-5 py-2.5 text-xs text-text-3">{filtered.length} customer{filtered.length !== 1 ? 's' : ''}</div>
            <DataTable columns={columns} data={filtered} keyExtractor={(c) => c.id} onRowClick={(c) => router.push(`/customers/${c.id}`)} />
          </>
        )}
      </Card>
    </div>
  );
}
