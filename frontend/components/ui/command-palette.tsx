'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  LayoutDashboard,
  AlertTriangle,
  Zap,
  Users,
  Building2,
  Brain,
  Cpu,
  FlaskConical,
  BarChart3,
  ScrollText,
  Settings,
  ArrowRight,
  CornerDownLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  keywords: string[];
}

const COMMANDS: CommandItem[] = [
  { id: 'overview', label: 'Overview', description: 'Dashboard overview', href: '/', icon: LayoutDashboard, keywords: ['dashboard', 'home', 'overview'] },
  { id: 'cases', label: 'Cases', description: 'Payment risk cases', href: '/cases', icon: AlertTriangle, keywords: ['cases', 'risk', 'payment'] },
  { id: 'transactions', label: 'Transactions', description: 'Failed payment transactions', href: '/transactions', icon: Zap, keywords: ['transactions', 'payments', 'failed'] },
  { id: 'customers', label: 'Customers', description: 'Customer profiles', href: '/customers', icon: Users, keywords: ['customers', 'profiles', 'users'] },
  { id: 'merchants', label: 'Merchants', description: 'Merchant configurations', href: '/merchants', icon: Building2, keywords: ['merchants', 'business', 'configs'] },
  { id: 'risk', label: 'Risk Intelligence', description: 'Analytics and insights', href: '/risk', icon: Brain, keywords: ['risk', 'intelligence', 'analytics', 'insights'] },
  { id: 'decisions', label: 'Decision Engine', description: 'AI-powered decisions', href: '/decisions', icon: Cpu, keywords: ['decisions', 'AI', 'engine', 'policy'] },
  { id: 'simulation', label: 'Simulation', description: 'Run a test scenario', href: '/simulation', icon: FlaskConical, keywords: ['simulation', 'test', 'scenario', 'run'] },
  { id: 'analytics', label: 'Analytics', description: 'Performance metrics', href: '/analytics', icon: BarChart3, keywords: ['analytics', 'metrics', 'charts', 'graphs'] },
  { id: 'audit', label: 'Audit Log', description: 'System audit trail', href: '/audit', icon: ScrollText, keywords: ['audit', 'log', 'trail', 'history'] },
  { id: 'settings', label: 'Settings', description: 'System configuration', href: '/settings', icon: Settings, keywords: ['settings', 'config', 'system'] },
];

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // ── Keyboard shortcut ───────────────────────────────────────────────

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // ── Focus input when opened ─────────────────────────────────────────

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // ── Filter commands ─────────────────────────────────────────────────

  const filtered = query
    ? COMMANDS.filter((cmd) => {
        const q = query.toLowerCase();
        return (
          cmd.label.toLowerCase().includes(q) ||
          cmd.description?.toLowerCase().includes(q) ||
          cmd.keywords.some((k) => k.includes(q))
        );
      })
    : COMMANDS;

  // ── Navigate ────────────────────────────────────────────────────────

  const navigate = useCallback(
    (href: string) => {
      setIsOpen(false);
      router.push(href);
    },
    [router]
  );

  // ── Keyboard navigation in list ─────────────────────────────────────

  const handleListKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      navigate(filtered[selectedIndex].href);
    }
  };

  // ── Scroll selected into view ───────────────────────────────────────

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const item = list.children[selectedIndex] as HTMLElement;
    if (item) {
      item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex]);

  // ── Reset index when query changes ──────────────────────────────────

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={() => setIsOpen(false)}
      />

      {/* Palette */}
      <div className="relative w-full max-w-lg mx-4 rounded-2xl border border-border bg-surface-1 shadow-2xl animate-fade-in-scale overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 border-b border-border px-4 py-3.5">
          <Search className="h-4 w-4 shrink-0 text-text-4" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleListKeyDown}
            placeholder="Search pages, features..."
            className="flex-1 bg-transparent text-sm text-text-1 placeholder:text-text-4 outline-none"
          />
          <kbd className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-4">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[300px] overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-text-3">No results found for &ldquo;{query}&rdquo;</p>
            </div>
          ) : (
            filtered.map((cmd, idx) => {
              const Icon = cmd.icon;
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={cmd.id}
                  onClick={() => navigate(cmd.href)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={cn(
                    'flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors',
                    isSelected ? 'bg-accent/8 text-text-1' : 'text-text-2 hover:bg-surface-2/50'
                  )}
                >
                  <div
                    className={cn(
                      'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors',
                      isSelected ? 'bg-accent/15 text-accent' : 'bg-surface-2 text-text-3'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-text-1 truncate">{cmd.label}</p>
                    {cmd.description && (
                      <p className="text-[11px] text-text-3 truncate">{cmd.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {isSelected && (
                      <kbd className="flex items-center gap-0.5 rounded border border-border bg-surface-2 px-1.5 py-0.5 text-[10px] text-text-4">
                        <CornerDownLeft className="h-2.5 w-2.5" />
                      </kbd>
                    )}
                    <ArrowRight
                      className={cn(
                        'h-3.5 w-3.5 transition-opacity',
                        isSelected ? 'text-accent opacity-100' : 'text-text-4 opacity-0 group-hover:opacity-100'
                      )}
                    />
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Footer hint */}
        <div className="border-t border-border px-4 py-2.5 flex items-center gap-4 text-[10px] text-text-4">
          <span className="flex items-center gap-1">
            <kbd className="rounded border border-border bg-surface-2 px-1 py-0.5 font-mono text-[9px]">↑↓</kbd>
            navigate
          </span>
          <span className="flex items-center gap-1">
            <kbd className="rounded border border-border bg-surface-2 px-1 py-0.5 font-mono text-[9px]">↵</kbd>
            select
          </span>
          <span className="flex items-center gap-1">
            <kbd className="rounded border border-border bg-surface-2 px-1 py-0.5 font-mono text-[9px]">esc</kbd>
            close
          </span>
        </div>
      </div>
    </div>
  );
}
