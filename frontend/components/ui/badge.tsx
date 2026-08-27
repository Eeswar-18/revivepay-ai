'use client';

import { cn } from '@/lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'accent';
}

export function Badge({ children, className, variant = 'default' }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold leading-5 tracking-wide transition-all duration-150',
        {
          'bg-surface-3/60 text-text-2 border-border': variant === 'default',
          'bg-success/10 text-success border-success/20': variant === 'success',
          'bg-warning/10 text-warning border-warning/20': variant === 'warning',
          'bg-danger/10 text-danger border-danger/20': variant === 'danger',
          'bg-info/10 text-info border-info/20': variant === 'info',
          'bg-accent/10 text-accent border-accent/20': variant === 'accent',
        },
        className
      )}
    >
      {children}
    </span>
  );
}

/** Risk level badge with semantic coloring */
export function RiskBadge({ level }: { level: string }) {
  const config = {
    LOW: { variant: 'success' as const, className: '' },
    MEDIUM: { variant: 'warning' as const, className: '' },
    HIGH: { variant: 'danger' as const, className: '' },
    CRITICAL: { variant: 'danger' as const, className: 'glow-danger' },
  }[level] || { variant: 'default' as const, className: '' };

  return (
    <Badge variant={config.variant} className={config.className}>
      {level === 'CRITICAL' && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full rounded-full bg-danger opacity-75 badge-critical-dot" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-danger" />
        </span>
      )}
      {level}
    </Badge>
  );
}

/** Case state badge */
export function StateBadge({ state }: { state: string }) {
  const variant = {
    DETECTED: 'info' as const,
    FEATURISED: 'accent' as const,
    PROPOSED: 'accent' as const,
    APPROVED: 'success' as const,
    BLOCKED: 'danger' as const,
    ESCALATED: 'warning' as const,
    SCHEDULED: 'info' as const,
    EXECUTING: 'accent' as const,
    AWAITING_OUTCOME: 'accent' as const,
    RECOVERED: 'success' as const,
    FAILED: 'danger' as const,
    STOPPED: 'default' as const,
    EXPIRED: 'danger' as const,
    CLOSED: 'default' as const,
  }[state] || ('default' as const);

  return <Badge variant={variant}>{state}</Badge>;
}

/** Policy verdict badge */
export function VerdictBadge({ verdict }: { verdict: string }) {
  const variant = {
    APPROVE: 'success' as const,
    MODIFY: 'warning' as const,
    BLOCK: 'danger' as const,
    ESCALATE: 'warning' as const,
  }[verdict] || ('default' as const);

  return <Badge variant={variant}>{verdict}</Badge>;
}
