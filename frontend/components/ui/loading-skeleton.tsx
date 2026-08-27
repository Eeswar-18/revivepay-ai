'use client';

import { cn } from '@/lib/utils';

function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn('skeleton-shimmer rounded-lg', className)} />
  );
}

export function MetricCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-6 relative overflow-hidden">
      <Skeleton className="h-3 w-24 rounded" />
      <Skeleton className="mt-3 h-9 w-32 rounded" />
      <Skeleton className="mt-2.5 h-3 w-20 rounded" />
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-3">
      <div className="flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3.5 flex-1 rounded" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, row) => (
        <div key={row} className="flex gap-4">
          {Array.from({ length: cols }).map((_, col) => (
            <Skeleton key={col} className="h-3.5 flex-1 rounded" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-6">
      <Skeleton className="h-4 w-1/3 rounded" />
      <Skeleton className="mt-4 h-3 w-full rounded" />
      <Skeleton className="mt-2 h-3 w-2/3 rounded" />
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in">
      <Skeleton className="h-8 w-48 rounded" />
      <Skeleton className="h-4 w-96 rounded" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
      </div>
      <CardSkeleton />
    </div>
  );
}
