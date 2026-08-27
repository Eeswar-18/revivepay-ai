'use client';

import { useState, useCallback } from 'react';
import { Sidebar } from './sidebar';
import { TopBar } from './topbar';
import { CommandPalette } from '@/components/ui/command-palette';
import { cn } from '@/lib/utils';

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleMobileClose = useCallback(() => setMobileOpen(false), []);

  return (
    <div className="min-h-screen bg-bg">
      <CommandPalette />
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        mobileOpen={mobileOpen}
        onMobileClose={handleMobileClose}
      />
      <div
        className={cn(
          'flex flex-col transition-all duration-300',
          sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-60'
        )}
      >
        <TopBar onMenuToggle={() => setMobileOpen(!mobileOpen)} />
        <main className="flex-1 p-4 sm:p-6 animate-fade-in">{children}</main>
      </div>
    </div>
  );
}
