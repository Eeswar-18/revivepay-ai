// RevivePay AI — Utility functions

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// ── cn helper (clsx + tailwind-merge) ──────────────────────────────────────

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Monetary formatting ────────────────────────────────────────────────────

/** Convert paise (integer) to rupee display string: ₹1,500.00 */
export function formatPaise(paise: number): string {
  const rupees = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(rupees);
}

/** Short format: ₹1.5K, ₹2.3L, ₹1.2Cr */
export function formatPaiseShort(paise: number): string {
  const rupees = paise / 100;
  if (rupees >= 1_00_00_000) return `₹${(rupees / 1_00_00_000).toFixed(1)}Cr`;
  if (rupees >= 1_00_000) return `₹${(rupees / 1_00_000).toFixed(1)}L`;
  if (rupees >= 1_000) return `₹${(rupees / 1_000).toFixed(1)}K`;
  return `₹${rupees.toFixed(0)}`;
}

// ── Percentage formatting ──────────────────────────────────────────────────

export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/** Format basis points as percentage: 200 bps → 2.00% */
export function formatBps(bps: number): string {
  return `${(bps / 100).toFixed(2)}%`;
}

// ── Date/time formatting ───────────────────────────────────────────────────

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Intl.DateTimeFormat('en-IN', {
      dateStyle: 'medium',
    }).format(new Date(iso));
  } catch {
    return '—';
  }
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Intl.DateTimeFormat('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso));
  } catch {
    return '—';
  }
}

export function formatTimeAgo(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(iso);
  } catch {
    return '—';
  }
}

// ── UUID formatting ────────────────────────────────────────────────────────

export function truncateId(id: string, chars = 8): string {
  return id.slice(0, chars);
}

// ── Risk level computation ─────────────────────────────────────────────────

import type { CaseState, PolicyVerdict } from './types';

/** Derive a risk level from case state and amount */
export function computeRiskLevel(
  state: CaseState,
  amountMinor: number
): 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' {
  if (state === 'BLOCKED' || state === 'FAILED' || state === 'EXPIRED') return 'CRITICAL';
  if (state === 'ESCALATED' || state === 'EXECUTING') return 'HIGH';
  if (state === 'DETECTED' || state === 'FEATURISED' || state === 'PROPOSED') {
    if (amountMinor > 5_000_000) return 'HIGH'; // > ₹50,000
    if (amountMinor > 1_000_000) return 'MEDIUM'; // > ₹10,000
    return 'LOW';
  }
  if (state === 'RECOVERED' || state === 'CLOSED') return 'LOW';
  return 'MEDIUM';
}

/** Color classes for risk levels */
export function riskLevelColors(level: string): string {
  switch (level) {
    case 'LOW':
      return 'bg-success/15 text-success border-success/30';
    case 'MEDIUM':
      return 'bg-warning/15 text-warning border-warning/30';
    case 'HIGH':
      return 'bg-[#f97316]/15 text-[#f97316] border-[#f97316]/30';
    case 'CRITICAL':
      return 'bg-danger/15 text-danger border-danger/30';
    default:
      return 'bg-text-3/10 text-text-3 border-border';
  }
}

/** Color classes for case states */
export function caseStateColors(state: CaseState): string {
  switch (state) {
    case 'DETECTED':
      return 'bg-info/15 text-info border-info/30';
    case 'FEATURISED':
      return 'bg-[#8b5cf6]/15 text-[#8b5cf6] border-[#8b5cf6]/30';
    case 'PROPOSED':
      return 'bg-[#a78bfa]/15 text-[#a78bfa] border-[#a78bfa]/30';
    case 'APPROVED':
      return 'bg-success/15 text-success border-success/30';
    case 'BLOCKED':
      return 'bg-danger/15 text-danger border-danger/30';
    case 'ESCALATED':
      return 'bg-warning/15 text-warning border-warning/30';
    case 'SCHEDULED':
      return 'bg-accent/15 text-accent border-accent/30';
    case 'EXECUTING':
      return 'bg-accent/15 text-accent border-accent/30';
    case 'AWAITING_OUTCOME':
      return 'bg-[#8b5cf6]/15 text-[#8b5cf6] border-[#8b5cf6]/30';
    case 'RECOVERED':
      return 'bg-success/15 text-success border-success/30';
    case 'FAILED':
      return 'bg-danger/15 text-danger border-danger/30';
    case 'STOPPED':
      return 'bg-text-3/10 text-text-3 border-border';
    case 'EXPIRED':
      return 'bg-danger/15 text-danger border-danger/30';
    case 'CLOSED':
      return 'bg-text-3/10 text-text-3 border-border';
    default:
      return 'bg-text-3/10 text-text-3 border-border';
  }
}

/** Color classes for policy verdicts */
export function verdictColors(verdict: string): string {
  switch (verdict) {
    case 'APPROVE':
      return 'bg-success/15 text-success border-success/30';
    case 'MODIFY':
      return 'bg-warning/15 text-warning border-warning/30';
    case 'BLOCK':
      return 'bg-danger/15 text-danger border-danger/30';
    case 'ESCALATE':
      return 'bg-[#f97316]/15 text-[#f97316] border-[#f97316]/30';
    default:
      return 'bg-text-3/10 text-text-3 border-border';
  }
}

/** Format action type for display: RETRY_SAME_RAIL → Retry Same Rail */
export function formatActionType(action: string | null): string {
  if (!action) return '—';
  return action
    .split('_')
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ');
}

/** Format case type for display */
export function formatCaseType(type: string): string {
  return type
    .split('_')
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ');
}

/** Get icon name for action type */
export function actionIcon(action: string | null): string {
  if (!action) return 'circle-dashed';
  switch (action) {
    case 'STOP':
      return 'octagon';
    case 'RETRY_SAME_RAIL':
    case 'RETRY_ALTERNATE_RAIL':
      return 'refresh-cw';
    case 'EMAIL_NUDGE':
      return 'mail';
    case 'SMS_NUDGE':
      return 'message-square';
    case 'WHATSAPP_NUDGE':
      return 'message-circle';
    case 'REQUEST_NEW_INSTRUMENT':
      return 'credit-card';
    case 'AGENT_CALL':
      return 'phone';
    default:
      return 'circle-dashed';
  }
}
