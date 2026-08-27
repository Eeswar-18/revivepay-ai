'use client';

import { use } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useMerchant } from '@/lib/hooks';
import { Card, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ErrorState } from '@/components/ui/error-state';
import { PageSkeleton } from '@/components/ui/loading-skeleton';
import { formatPaise, formatBps, truncateId, formatDateTime } from '@/lib/utils';
import Link from 'next/link';

export default function MerchantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: merchant, isLoading, isError, refetch } = useMerchant(id);

  if (isError) return <ErrorState message="Failed to load merchant details." onRetry={() => refetch()} />;
  if (isLoading || !merchant) return <PageSkeleton />;

  return (
    <div className="space-y-6 page-enter">
      <Link href="/merchants" className="inline-flex items-center gap-1.5 text-sm text-text-3 hover:text-text-1 transition-colors">
        <ArrowLeft className="h-4 w-4" /> Merchants
      </Link>

      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-text-1">{merchant.name}</h1>
          <Badge variant={merchant.risk_appetite === 'aggressive' ? 'danger' : merchant.risk_appetite === 'balanced' ? 'warning' : 'success'}>
            {merchant.risk_appetite}
          </Badge>
        </div>
        <p className="mt-1.5 text-sm text-text-3">
          ID: <span className="font-mono text-text-3">{truncateId(merchant.id)}</span> · Currency: {merchant.currency} · Created: {formatDateTime(merchant.created_at)}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="Configuration" description="Merchant payment and retry settings" />
          <div className="mt-4 space-y-0">
            {[
              { label: 'Merchant ID', value: merchant.id, mono: true },
              { label: 'Name', value: merchant.name },
              { label: 'Currency', value: merchant.currency },
              { label: 'Risk Appetite', value: merchant.risk_appetite },
              { label: 'Max Retries', value: String(merchant.max_retries_default) },
              { label: 'Contact Budget/Week', value: `${merchant.contact_budget_per_week} contacts` },
            ].map(({ label, value, mono }, idx, arr) => (
              <div key={label} className={`flex items-center justify-between py-2.5 ${idx < arr.length - 1 ? 'border-b border-border/30' : ''}`}>
                <span className="text-xs text-text-3">{label}</span>
                <span className={`text-sm ${mono ? 'font-mono text-[11px] text-text-3' : 'text-text-2'}`}>{value}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="Financial Settings" description="MDR and autonomous action limits" />
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-surface-2/40 border border-border/30 px-4 py-3.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">MDR (basis points)</p>
              <p className="mt-1.5 metric-number text-text-1">{formatBps(merchant.mdr_bps)}</p>
            </div>
            <div className="rounded-xl bg-surface-2/40 border border-border/30 px-4 py-3.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">Autonomous Ceiling</p>
              <p className="mt-1.5 metric-number text-text-1">{formatPaise(merchant.autonomous_amount_ceiling_minor)}</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
