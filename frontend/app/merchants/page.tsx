'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Building2, Filter, X } from 'lucide-react';
import { useMerchants } from '@/lib/hooks';
import { DataTable } from '@/components/ui/data-table';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { TableSkeleton } from '@/components/ui/loading-skeleton';
import { formatPaise, formatBps } from '@/lib/utils';
import type { Merchant } from '@/lib/types';

const RISK_APPETITES = ['conservative', 'balanced', 'aggressive'];

const APPETITE_COLORS: Record<string, string> = {
  conservative: 'bg-success/10 text-success border-success/20',
  balanced: 'bg-warning/10 text-warning border-warning/20',
  aggressive: 'bg-danger/10 text-danger border-danger/20',
};

export default function MerchantsPage() {
  const router = useRouter();
  const [appetiteFilter, setAppetiteFilter] = useState('');
  const [search, setSearch] = useState('');

  const { data: merchants, isLoading, isError, refetch } = useMerchants({
    limit: 200,
    risk_appetite: appetiteFilter || undefined,
  });

  const filtered = (merchants || []).filter((m) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return m.id.toLowerCase().includes(q) || m.name.toLowerCase().includes(q);
  });

  const columns = [
    {
      key: 'name',
      header: 'Merchant',
      primary: true,
      render: (m: Merchant) => (
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-medium text-text-1">{m.name}</span>
          <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold capitalize ${APPETITE_COLORS[m.risk_appetite] || ''}`}>
            {m.risk_appetite}
          </span>
        </div>
      ),
    },
    {
      key: 'currency',
      header: 'Currency',
      render: (m: Merchant) => <span className="text-xs text-text-2">{m.currency}</span>,
    },
    {
      key: 'risk_appetite',
      header: 'Risk Appetite',
      hideOnMobile: true,
      render: (m: Merchant) => (
        <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold capitalize ${APPETITE_COLORS[m.risk_appetite] || ''}`}>
          {m.risk_appetite}
        </span>
      ),
    },
    {
      key: 'mdr_bps',
      header: 'MDR',
      className: 'text-right',
      render: (m: Merchant) => <span className="tabular text-sm font-semibold text-text-1">{formatBps(m.mdr_bps)}</span>,
    },
    {
      key: 'autonomous_amount_ceiling_minor',
      header: 'Ceiling',
      className: 'text-right',
      hideOnMobile: true,
      render: (m: Merchant) => <span className="tabular text-sm text-text-1">{formatPaise(m.autonomous_amount_ceiling_minor)}</span>,
    },
    {
      key: 'contact_budget_per_week',
      header: 'Contact Budget',
      className: 'text-right',
      hideOnMobile: true,
      render: (m: Merchant) => <span className="tabular text-sm text-text-1">{m.contact_budget_per_week}/wk</span>,
    },
    {
      key: 'max_retries_default',
      header: 'Max Retries',
      className: 'text-right',
      hideOnMobile: true,
      render: (m: Merchant) => <span className="tabular text-sm text-text-1">{m.max_retries_default}</span>,
    },
  ];

  return (
    <div className="space-y-6 page-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Merchants</h1>
        <p className="mt-1 text-sm text-text-3">Merchant configurations and risk appetite settings.</p>
      </div>

      <Card padding="sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <input type="text" placeholder="Search merchants..." value={search} onChange={(e) => setSearch(e.target.value)}
              aria-label="Search merchants"
              className="w-full rounded-lg border border-border bg-surface-2/50 px-3 py-2 pl-9 text-sm text-text-1 placeholder:text-text-4 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors" />
            <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-4" />
          </div>
          <select value={appetiteFilter} onChange={(e) => setAppetiteFilter(e.target.value)}
            aria-label="Filter by risk appetite"
            className="rounded-lg border border-border bg-surface-2/50 px-3 py-2 text-sm text-text-2 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors">
            <option value="">All Appetites</option>
            {RISK_APPETITES.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          {(appetiteFilter || search) && (
            <button onClick={() => { setAppetiteFilter(''); setSearch(''); }}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs text-text-3 hover:bg-surface-2 hover:text-text-1 transition-colors">
              <X className="h-3 w-3" /> Clear
            </button>
          )}
        </div>
      </Card>

      <Card padding="none">
        {isError ? (
          <ErrorState message="Failed to load merchants." onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="p-6"><TableSkeleton rows={5} cols={7} /></div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={Building2} title="No merchants yet" description="Merchant profiles will appear once data is seeded." />
        ) : (
          <>
            <div className="border-b border-border px-5 py-2.5 text-xs text-text-3">{filtered.length} merchant{filtered.length !== 1 ? 's' : ''}</div>
            <DataTable columns={columns} data={filtered} keyExtractor={(m) => m.id} onRowClick={(m) => router.push(`/merchants/${m.id}`)} />
          </>
        )}
      </Card>
    </div>
  );
}
