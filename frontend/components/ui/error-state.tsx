'use client';

import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = 'Unable to connect',
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 text-center', className)}>
      <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-danger/10 border border-danger/20">
        <AlertTriangle className="h-7 w-7 text-danger" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-text-1">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-text-3 leading-relaxed">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-6 rounded-lg bg-surface-2 border border-border px-4 py-2 text-sm font-medium text-text-1 transition-colors hover:bg-surface-3 hover:border-border-strong"
        >
          Retry
        </button>
      )}
    </div>
  );
}
