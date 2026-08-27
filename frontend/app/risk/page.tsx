'use client';

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Treemap,
} from 'recharts';
import { Brain, Shield, AlertTriangle, TrendingDown } from 'lucide-react';
import { useCases, useDecisions } from '@/lib/hooks';
import { Card, CardHeader, MetricCard } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { MetricCardSkeleton } from '@/components/ui/loading-skeleton';
import { computeRiskLevel, formatCaseType } from '@/lib/utils';
import type { Case } from '@/lib/types';

const COLORS = {
  accent: '#5b73ff',
  success: '#34d399',
  warning: '#fbbf24',
  danger: '#f87171',
  orange: '#f97316',
  info: '#60a5fa',
  purple: '#a78bfa',
  text3: '#5a6580',
};

const RISK_COLORS: Record<string, string> = {
  LOW: COLORS.success,
  MEDIUM: COLORS.warning,
  HIGH: COLORS.orange,
  CRITICAL: COLORS.danger,
};

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-surface-1/95 backdrop-blur-md px-4 py-3 shadow-lg">
      <p className="text-xs font-semibold text-text-1 mb-1.5">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-text-3">{p.name}:</span>
          <span className="font-semibold tabular text-text-1">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

// Custom treemap content
function CustomTreemapContent(props: Record<string, unknown>): React.ReactElement {
  const x = Number(props.x || 0);
  const y = Number(props.y || 0);
  const width = Number(props.width || 0);
  const height = Number(props.height || 0);
  const name = String(props.name || '');
  const value = Number(props.value || 0);
  const fill = String(props.fill || '#5b73ff');
  if (width < 50 || height < 30) return <g />;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={6}
        fill={fill}
        fillOpacity={0.2}
        stroke={fill}
        strokeWidth={1}
        strokeOpacity={0.3}
      />
      {width > 60 && height > 40 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 6}
            textAnchor="middle"
            fill="#eaf0ff"
            fontSize={10}
            fontWeight={600}
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fill="#8e9bb8"
            fontSize={10}
            fontWeight={700}
            style={{ fontVariantNumeric: 'tabular-nums' }}
          >
            {value}
          </text>
        </>
      )}
    </g>
  );
}

export default function RiskPage() {
  const { data: cases, isLoading, isError, refetch } = useCases({ limit: 200 });
  const { data: decisions } = useDecisions({ limit: 200 });

  const allCases = cases || [];
  const allDecisions = decisions || [];

  // ── Memoized data ─────────────────────────────────────────────────────

  const riskData = useMemo(() => {
    const dist = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    allCases.forEach((c) => {
      const level = computeRiskLevel(c.state, c.amount_at_risk_minor);
      dist[level]++;
    });
    return Object.entries(dist).map(([level, count]) => ({
      level,
      count,
      fill: RISK_COLORS[level],
    }));
  }, [allCases]);

  const riskPieData = useMemo(() => {
    const dist = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    allCases.forEach((c) => {
      const level = computeRiskLevel(c.state, c.amount_at_risk_minor);
      dist[level]++;
    });
    return Object.entries(dist)
      .filter(([, v]) => v > 0)
      .map(([level, value]) => ({
        name: level,
        value,
        fill: RISK_COLORS[level],
      }));
  }, [allCases]);

  const caseTypeData = useMemo(() => {
    const dist: Record<string, number> = {};
    allCases.forEach((c) => { dist[c.case_type] = (dist[c.case_type] || 0) + 1; });
    const typeColors = [COLORS.accent, COLORS.purple, COLORS.warning, COLORS.info];
    return Object.entries(dist)
      .sort(([, a], [, b]) => b - a)
      .map(([type, count], i) => ({
        type: formatCaseType(type),
        fullName: type,
        count,
        fill: typeColors[i % typeColors.length],
      }));
  }, [allCases]);

  const verdictData = useMemo(() => {
    const dist = { APPROVE: 0, MODIFY: 0, BLOCK: 0, ESCALATE: 0 };
    allDecisions.forEach((d) => {
      if (d.policy_verdict && d.policy_verdict in dist) {
        dist[d.policy_verdict as keyof typeof dist]++;
      }
    });
    const verdictColors: Record<string, string> = {
      APPROVE: COLORS.success,
      MODIFY: COLORS.warning,
      BLOCK: COLORS.danger,
      ESCALATE: COLORS.orange,
    };
    return Object.entries(dist).map(([verdict, count]) => ({
      verdict,
      count,
      fill: verdictColors[verdict],
    }));
  }, [allDecisions]);

  const stateTreemapData = useMemo(() => {
    const dist: Record<string, number> = {};
    allCases.forEach((c) => { dist[c.state] = (dist[c.state] || 0) + 1; });
    const stateColors: Record<string, string> = {
      DETECTED: COLORS.info,
      FEATURISED: COLORS.purple,
      PROPOSED: COLORS.purple,
      APPROVED: COLORS.success,
      BLOCKED: COLORS.danger,
      ESCALATED: COLORS.warning,
      SCHEDULED: COLORS.accent,
      EXECUTING: COLORS.accent,
      AWAITING_OUTCOME: COLORS.purple,
      RECOVERED: COLORS.success,
      FAILED: COLORS.danger,
      CLOSED: COLORS.text3,
    };
    return Object.entries(dist)
      .sort(([, a], [, b]) => b - a)
      .map(([state, count]) => ({
        name: state,
        value: count,
        fill: stateColors[state] || COLORS.text3,
      }));
  }, [allCases]);

  // ── KPI values ────────────────────────────────────────────────────────

  const total = allCases.length;
  const criticalCount = allCases.filter((c) => computeRiskLevel(c.state, c.amount_at_risk_minor) === 'CRITICAL').length;
  const highRiskCount = allCases.filter((c) => computeRiskLevel(c.state, c.amount_at_risk_minor) === 'HIGH').length;
  const blockedCount = allDecisions.filter((d) => d.policy_verdict === 'BLOCK').length;
  const blockRate = allDecisions.length > 0 ? blockedCount / allDecisions.length : 0;

  // ── Error / Empty ─────────────────────────────────────────────────────

  if (isError) return <ErrorState message="Failed to load risk intelligence data." onRetry={() => refetch()} />;

  if (allCases.length === 0) {
    return (
      <div className="space-y-6 page-enter">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-1">Risk Intelligence</h1>
          <p className="mt-1 text-sm text-text-3">Analytics and insights from payment risk patterns.</p>
        </div>
        <Card>
          <EmptyState icon={Brain} title="No risk data yet" description="Risk intelligence will populate as cases are processed." />
        </Card>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 page-enter">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Risk Intelligence</h1>
        <p className="mt-1 text-sm text-text-3">Analytics and insights from payment risk patterns.</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          <>
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
          </>
        ) : (
          <>
            <MetricCard label="Total Cases" value={total} icon={Shield} accent />
            <MetricCard label="Critical Risk" value={criticalCount} icon={AlertTriangle} />
            <MetricCard label="High Risk" value={highRiskCount} icon={TrendingDown} />
            <MetricCard
              label="Block Rate"
              value={`${(blockRate * 100).toFixed(0)}%`}
              icon={Brain}
            />
          </>
        )}
      </div>

      {/* Charts Row 1: Risk Bar + Risk Donut */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Risk Distribution Bar */}
        <Card className="xl:col-span-2">
          <CardHeader title="Risk Distribution" description="Cases by severity level" />
          <div className="mt-5 h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" vertical={false} />
                <XAxis
                  dataKey="level"
                  tick={{ fill: '#5a6580', fontSize: 11 }}
                  axisLine={{ stroke: '#1a2030' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#5a6580', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(91,115,255,0.05)' }} />
                <Bar dataKey="count" name="Cases" radius={[6, 6, 0, 0]} maxBarSize={64}>
                  {riskData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Risk Donut */}
        <Card>
          <CardHeader title="Severity Mix" description="Proportion by risk level" />
          <div className="mt-5 flex flex-col items-center">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={riskPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                >
                  {riskPieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.9} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex items-center gap-4 mt-2">
              {riskPieData.map((item) => (
                <div key={item.name} className="flex items-center gap-1.5">
                  <div className="h-2 w-2 rounded-full" style={{ backgroundColor: item.fill }} />
                  <span className="text-[10px] font-medium text-text-3">{item.name}</span>
                  <span className="text-[10px] font-bold tabular text-text-2">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Charts Row 2: Case Types + Policy Verdicts */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Case Type Distribution */}
        <Card>
          <CardHeader title="Case Types" description="Distribution by event type" />
          <div className="mt-5 h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={caseTypeData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" vertical={false} />
                <XAxis
                  dataKey="type"
                  tick={{ fill: '#5a6580', fontSize: 10 }}
                  axisLine={{ stroke: '#1a2030' }}
                  tickLine={false}
                  angle={-15}
                  textAnchor="end"
                  height={50}
                />
                <YAxis
                  tick={{ fill: '#5a6580', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(91,115,255,0.05)' }} />
                <Bar dataKey="count" name="Cases" radius={[6, 6, 0, 0]} maxBarSize={52}>
                  {caseTypeData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Policy Verdicts */}
        <Card>
          <CardHeader title="Policy Verdicts" description="Decision outcomes from the policy kernel" />
          <div className="mt-5 h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={verdictData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" vertical={false} />
                <XAxis
                  dataKey="verdict"
                  tick={{ fill: '#5a6580', fontSize: 11 }}
                  axisLine={{ stroke: '#1a2030' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#5a6580', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(91,115,255,0.05)' }} />
                <Bar dataKey="count" name="Decisions" radius={[6, 6, 0, 0]} maxBarSize={52}>
                  {verdictData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* State Treemap */}
      <Card>
        <CardHeader title="Case State Treemap" description="Visual representation of case distribution across states" />
        <div className="mt-5 h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={stateTreemapData}
              dataKey="value"
              aspectRatio={4 / 3}
              content={CustomTreemapContent}
            />
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
