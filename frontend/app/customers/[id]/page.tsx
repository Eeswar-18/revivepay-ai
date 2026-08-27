'use client';

import { use } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useCustomer, useCases } from '@/lib/hooks';
import { Card, CardHeader } from '@/components/ui/card';
import { Badge, StateBadge } from '@/components/ui/badge';
import { ErrorState } from '@/components/ui/error-state';
import { PageSkeleton } from '@/components/ui/loading-skeleton';
import { formatPercent, truncateId, formatPaise, formatDateTime, formatCaseType } from '@/lib/utils';
import Link from 'next/link';

const SEGMENT_COLORS: Record<string, string> = {
  NEW: 'bg-info/10 text-info border-info/20',
  OCCASIONAL: 'bg-warning/10 text-warning border-warning/20',
  LOYAL: 'bg-success/10 text-success border-success/20',
  HIGH_VALUE: 'bg-accent/10 text-accent border-accent/20',
};

export default function CustomerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: customer, isLoading, isError, refetch } = useCustomer(id);
  const { data: cases } = useCases({ customer_id: id, limit: 50 });

  if (isError) return <ErrorState message="Failed to load customer details." onRetry={() => refetch()} />;
  if (isLoading || !customer) return <PageSkeleton />;

  const customerCases = cases || [];

  return (
    <div className="space-y-6 page-enter">
      <Link href="/customers" className="inline-flex items-center gap-1.5 text-sm text-text-3 hover:text-text-1 transition-colors">
        <ArrowLeft className="h-4 w-4" /> Customers
      </Link>

      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-text-1">
            Customer #{truncateId(customer.id)}
          </h1>
          <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${SEGMENT_COLORS[customer.segment] || ''}`}>
            {customer.segment}
          </span>
          {customer.do_not_contact && (
            <Badge variant="danger">Do Not Contact</Badge>
          )}
        </div>
        <p className="mt-1.5 text-sm text-text-3">
          Region: {customer.region} · Preferred: {customer.preferred_method.toUpperCase()} ·
          Member since {formatDateTime(customer.created_at)}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Profile */}
        <Card>
          <CardHeader title="Profile" description="Customer information and payment preferences" />
          <div className="mt-4 space-y-0">
            {[
              { label: 'Customer ID', value: customer.id, mono: true },
              { label: 'Merchant ID', value: customer.merchant_id, mono: true },
              { label: 'Region', value: customer.region },
              { label: 'Segment', value: customer.segment },
              { label: 'Email (hashed)', value: customer.email_hash.slice(0, 16) + '…', mono: true },
              { label: 'Phone (hashed)', value: customer.phone_hash.slice(0, 16) + '…', mono: true },
              { label: 'Preferred Method', value: customer.preferred_method.toUpperCase() },
              { label: 'Mandate Active', value: customer.mandate_active ? 'Yes' : 'No' },
              { label: 'Unsubscribed', value: customer.unsubscribed_at ? formatDateTime(customer.unsubscribed_at) : 'No' },
            ].map(({ label, value, mono }, idx, arr) => (
              <div key={label} className={`flex items-center justify-between py-2.5 ${idx < arr.length - 1 ? 'border-b border-border/30' : ''}`}>
                <span className="text-xs text-text-3">{label}</span>
                <span className={`text-sm ${mono ? 'font-mono text-[11px] text-text-3' : 'text-text-2'}`}>{value}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Payment Behavior */}
        <Card>
          <CardHeader title="Payment Behavior" description="Historical transaction and recovery metrics" />
          <div className="mt-4 grid grid-cols-2 gap-3">
            {[
              { label: 'Lifetime Transactions', value: customer.lifetime_txn_count },
              { label: 'Success Rate', value: formatPercent(customer.lifetime_success_rate) },
              { label: 'Recovery Successes', value: customer.prior_recovery_successes },
              { label: 'Prior Declines', value: customer.prior_declines },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl bg-surface-2/40 border border-border/30 px-4 py-3.5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">{label}</p>
                <p className="mt-1.5 metric-number text-text-1">{value}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Cases */}
      <Card padding="none">
        <div className="border-b border-border px-6 py-4">
          <h2 className="text-sm font-semibold text-text-1">Cases ({customerCases.length})</h2>
        </div>
        {customerCases.length === 0 ? (
          <div className="px-6 py-10 text-center text-sm text-text-3">No cases for this customer</div>
        ) : (
          <div className="divide-y divide-border/40">
            {customerCases.map((c) => (
              <Link key={c.id} href={`/cases/${c.id}`} className="flex items-center justify-between px-6 py-3.5 table-row-hover group">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-accent">{truncateId(c.id)}</span>
                  <StateBadge state={c.state} />
                  <span className="text-xs text-text-3">{formatCaseType(c.case_type)}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm font-semibold tabular text-text-1">{formatPaise(c.amount_at_risk_minor)}</span>
                  <span className="ml-2 text-xs text-text-3">{formatDateTime(c.detected_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
