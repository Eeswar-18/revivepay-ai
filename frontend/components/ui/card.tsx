'use client';

import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
  accent?: boolean;
}

export function Card({ children, className, padding = 'md', hover = false, accent = false }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border bg-surface-1 relative overflow-hidden',
        accent ? 'border-accent/15' : 'border-border',
        hover && 'card-interactive cursor-default',
        {
          'p-0': padding === 'none',
          'p-4': padding === 'sm',
          'p-6': padding === 'md',
          'p-8': padding === 'lg',
        },
        className
      )}
    >
      {children}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: number; label: string; positive?: boolean };
  className?: string;
  accent?: boolean;
}

export function MetricCard({ label, value, icon: Icon, trend, className, accent }: MetricCardProps) {
  return (
    <Card className={cn('card-interactive group relative', className)} hover>
      {/* Accent top line */}
      {accent && (
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-accent/60 via-accent to-accent/60" />
      )}
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-medium uppercase tracking-wider text-text-3">{label}</p>
          <p className="mt-2.5 metric-number text-text-1">{value}</p>
          {trend && (
            <p className={cn('mt-1.5 text-xs font-medium', trend.positive ? 'text-success' : 'text-danger')}>
              {trend.positive ? '↑' : '↓'} {Math.abs(trend.value)}% {trend.label}
            </p>
          )}
        </div>
        {Icon && (
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all duration-200',
              accent
                ? 'bg-accent/10 text-accent group-hover:bg-accent/20 group-hover:shadow-lg group-hover:shadow-accent/10'
                : 'bg-surface-2 text-text-3 group-hover:bg-surface-3 group-hover:text-text-2'
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </Card>
  );
}

interface CardHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function CardHeader({ title, description, action }: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h3 className="text-sm font-semibold text-text-1">{title}</h3>
        {description && <p className="mt-1 text-xs text-text-3">{description}</p>}
      </div>
      {action}
    </div>
  );
}
