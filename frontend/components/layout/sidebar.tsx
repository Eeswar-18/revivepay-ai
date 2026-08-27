'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  AlertTriangle,
  Users,
  Building2,
  Brain,
  Cpu,
  FlaskConical,
  BarChart3,
  ScrollText,
  Settings,
  Zap,
  ChevronLeft,
  ChevronRight,
  Shield,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useVersion } from '@/lib/hooks';

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  group: 'main' | 'bottom';
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', href: '/', icon: LayoutDashboard, group: 'main' },
  { label: 'Cases', href: '/cases', icon: AlertTriangle, group: 'main' },
  { label: 'Transactions', href: '/transactions', icon: Zap, group: 'main' },
  { label: 'Customers', href: '/customers', icon: Users, group: 'main' },
  { label: 'Merchants', href: '/merchants', icon: Building2, group: 'main' },
  { label: 'Risk Intelligence', href: '/risk', icon: Brain, group: 'main' },
  { label: 'Decision Engine', href: '/decisions', icon: Cpu, group: 'main' },
  { label: 'Simulation', href: '/simulation', icon: FlaskConical, group: 'main' },
  { label: 'Analytics', href: '/analytics', icon: BarChart3, group: 'main' },
  { label: 'Audit Log', href: '/audit', icon: ScrollText, group: 'main' },
  { label: 'Settings', href: '/settings', icon: Settings, group: 'bottom' },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const pathname = usePathname();
  const version = useVersion();
  const mainItems = NAV_ITEMS.filter((i) => i.group === 'main');
  const bottomItems = NAV_ITEMS.filter((i) => i.group === 'bottom');

  useEffect(() => {
    onMobileClose();
  }, [pathname, onMobileClose]);

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-border px-4">
        <Link href="/" className="flex items-center gap-2.5 min-w-0 group">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-muted transition-all group-hover:shadow-lg group-hover:shadow-accent/20 group-hover:scale-105">
            <Shield className="h-4 w-4 text-white" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-text-1 whitespace-nowrap">
                RevivePay
              </span>
              <span className="text-[9px] font-medium uppercase tracking-widest text-text-4">
                AI Platform
              </span>
            </div>
          )}
        </Link>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <div className="space-y-0.5">
          {mainItems.map((item) => (
            <SidebarLink
              key={item.href}
              item={item}
              active={pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))}
              collapsed={collapsed}
            />
          ))}
        </div>
      </nav>

      {/* Bottom nav + env indicator */}
      <div className="border-t border-border px-2 py-3 space-y-0.5">
        {bottomItems.map((item) => (
          <SidebarLink
            key={item.href}
            item={item}
            active={pathname === item.href}
            collapsed={collapsed}
          />
        ))}
        {!collapsed && version.data && (
          <div className="mx-2 mt-3 rounded-xl bg-surface-2/60 border border-border/60 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-60 badge-critical-dot" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-3">Simulated Mode</span>
            </div>
            <p className="mt-1.5 text-[10px] text-text-4 font-mono">v{version.data.version}</p>
          </div>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="hidden lg:flex h-10 items-center justify-center border-t border-border text-text-3 transition-colors hover:bg-surface-2 hover:text-text-1"
      >
        {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>
    </>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden lg:flex fixed inset-y-0 left-0 z-40 flex-col border-r border-border bg-surface-0 transition-all duration-300',
          collapsed ? 'w-16' : 'w-60'
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" onClick={onMobileClose} />
          <aside className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-surface-0 animate-slide-in">
            <button
              onClick={onMobileClose}
              className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-lg text-text-3 hover:bg-surface-2 hover:text-text-1 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}

function SidebarLink({
  item,
  active,
  collapsed,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={cn(
        'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-all duration-150',
        active
          ? 'bg-accent/10 text-accent'
          : 'text-text-3 hover:bg-surface-2/70 hover:text-text-1',
        collapsed && 'justify-center px-2'
      )}
      title={collapsed ? item.label : undefined}
    >
      {active && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-accent" />
      )}
      <Icon
        className={cn(
          'h-[18px] w-[18px] shrink-0 transition-colors duration-150',
          active ? 'text-accent' : 'text-text-3 group-hover:text-text-1'
        )}
      />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
}
