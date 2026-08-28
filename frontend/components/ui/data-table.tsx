'use client';

import { cn } from '@/lib/utils';

interface Column<T> {
  key: string;
  header: string;
  className?: string;
  render?: (item: T) => React.ReactNode;
  /** If true, this column is shown as the primary title in mobile card view */
  primary?: boolean;
  /** If true, this column is hidden on mobile */
  hideOnMobile?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  keyExtractor: (item: T) => string;
}

export function DataTable<T>({
  columns,
  data,
  onRowClick,
  emptyMessage = 'No data available',
  keyExtractor,
}: DataTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-text-3">{emptyMessage}</p>
      </div>
    );
  }

  // Find primary column for mobile title
  const primaryCol = columns.find((c) => c.primary) || columns[0];
  const secondaryCols = columns.filter(
    (c) => c.key !== primaryCol.key && !c.hideOnMobile
  );

  return (
    <>
      {/* Desktop table view */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full" role="table">
          <thead>
            <tr className="border-b border-border">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-3',
                    col.className
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, idx) => (
              <tr
                key={keyExtractor(item)}
                onClick={() => onRowClick?.(item)}
                className={cn(
                  'border-b border-border/30 transition-colors duration-100',
                  onRowClick && 'cursor-pointer table-row-hover',
                  idx === data.length - 1 && 'border-b-0'
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className={cn('px-5 py-3.5 text-sm', col.className)}>
                    {col.render
                      ? col.render(item)
                      : String((item as Record<string, unknown>)[col.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile card view */}
      <div className="md:hidden divide-y divide-border/30" role="list" aria-label="Data rows">
        {data.map((item) => (
          <div
            key={keyExtractor(item)}
            onClick={() => onRowClick?.(item)}
            role="listitem"
            className={cn(
              'px-5 py-4 space-y-2',
              onRowClick && 'cursor-pointer active:bg-surface-2/50 transition-colors'
            )}
          >
            {/* Primary info */}
            <div className="flex items-center justify-between">
              <div className="min-w-0 flex-1">
                {primaryCol.render
                  ? primaryCol.render(item)
                  : String((item as Record<string, unknown>)[primaryCol.key] ?? '—')}
              </div>
              {/* Show first non-primary, non-hidden column as right-aligned badge */}
              {secondaryCols[0] && (
                <div className="ml-3 shrink-0">
                  {secondaryCols[0].render
                    ? secondaryCols[0].render(item)
                    : String((item as Record<string, unknown>)[secondaryCols[0].key] ?? '—')}
                </div>
              )}
            </div>
            {/* Secondary info row */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              {secondaryCols.slice(1).map((col) => (
                <div key={col.key} className="flex items-center gap-1.5">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-text-4">
                    {col.header}:
                  </span>
                  <span className="text-xs text-text-2">
                    {col.render
                      ? col.render(item)
                      : String((item as Record<string, unknown>)[col.key] ?? '—')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
