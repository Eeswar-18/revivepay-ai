'use client';

import { usePathname } from 'next/navigation';
import { Search, Bell, Wifi, WifiOff, Menu } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useHealth } from '@/lib/hooks';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Overview',
  '/cases': 'Cases',
  '/transactions': 'Transactions',
  '/customers': 'Customers',
  '/merchants': 'Merchants',
  '/risk': 'Risk Intelligence',
  '/decisions': 'Decision Engine',
  '/simulation': 'Simulation',
  '/analytics': 'Analytics',
  '/audit': 'Audit Log',
  '/settings': 'Settings',
};

function getPageTitle(pathname: string): string {
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];
  if (pathname.startsWith('/cases/')) return 'Case Detail';
  if (pathname.startsWith('/customers/')) return 'Customer Detail';
  if (pathname.startsWith('/merchants/')) return 'Merchant Detail';
  return 'RevivePay AI';
}

interface TopBarProps {
  onMenuToggle?: () => void;
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const pathname = usePathname();
  const health = useHealth();
  const isOnline = health.data?.status === 'ok';
  const title = getPageTitle(pathname);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-bg/85 px-4 sm:px-6 backdrop-blur-xl">
      {/* Left: Mobile menu + Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          aria-label="Toggle navigation menu"
          className="flex lg:hidden h-8 w-8 items-center justify-center rounded-lg text-text-3 transition-colors hover:bg-surface-2 hover:text-text-1"
        >
          <Menu className="h-4 w-4" />
        </button>
        <div>
          <h1 className="text-[13px] font-semibold text-text-1">{title}</h1>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Search */}
        <button
          onClick={() => {
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }));
          }}
          aria-label="Open command palette (Ctrl+K)"
          className="hidden sm:flex h-8 items-center gap-2 rounded-lg border border-border bg-surface-1/50 px-3 text-xs text-text-3 transition-all duration-150 hover:border-border-strong hover:text-text-2 hover:bg-surface-1"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search</span>
          <kbd className="ml-1 rounded border border-border bg-surface-2/80 px-1.5 py-0.5 font-mono text-[10px] text-text-4">
            ⌘K
          </kbd>
        </button>

        {/* Notifications */}
        <button className="flex h-8 w-8 items-center justify-center rounded-lg border border-border text-text-3 transition-all duration-150 hover:border-border-strong hover:text-text-1 hover:bg-surface-1" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </button>

        {/* Environment badge */}
        <div
          className={cn(
            'flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-all',
            isOnline
              ? 'border-success/20 bg-success/8 text-success'
              : 'border-danger/20 bg-danger/8 text-danger'
          )}
        >
          {isOnline ? (
            <Wifi className="h-3 w-3" />
          ) : (
            <WifiOff className="h-3 w-3" />
          )}
          <span className="hidden sm:inline">
            {isOnline ? 'Simulated' : 'Offline'}
          </span>
        </div>
      </div>
    </header>
  );
}
