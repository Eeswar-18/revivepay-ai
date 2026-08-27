'use client';

import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 text-center', className)}>
      {Icon && (
        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-surface-2 border border-border">
          <Icon className="h-7 w-7 text-text-3" />
        </div>
      )}
      <h3 className="mt-4 text-base font-semibold text-text-1">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-text-3 leading-relaxed">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
