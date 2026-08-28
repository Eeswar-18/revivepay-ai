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
  AreaChart,
  Area,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import { BarChart3, TrendingUp, Shield, AlertTriangle, Activity } from 'lucide-react';
import { useCases, useDecisions } from '@/lib/hooks';
import { Card, CardHeader, MetricCard } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { MetricCardSkeleton } from '@/components/ui/loading-skeleton';
import { formatPaise, formatPaiseShort, computeRiskLevel, formatActionType } from '@/lib/utils';
import type { Case } from '@/lib/types';

// ── Chart Colors ──────────────────────────────────────────────────────────

const COLORS = {
  accent: '#5b73ff',
  accentLight: '#7088ff',
  success: '#34d399',
  warning: '#fbbf24',
  danger: '#f87171',
  info: '#60a5fa',
  purple: '#a78bfa',
  orange: '#f97316',
  surface3: '#1c2333',
  text3: '#5a6580',
  text2: '#8e9bb8',
};

const STATE_COLORS: Record<string, string> = {
  DETECTED: COLORS.info,
  FEATURISED: COLORS.purple,
  PROPOSED: '#a78bfa',
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

const RISK_COLORS: Record<string, string> = {
  LOW: COLORS.success,
  MEDIUM: COLORS.warning,
  HIGH: COLORS.orange,
  CRITICAL: COLORS.danger,
};

// ── Custom Tooltip ────────────────────────────────────────────────────────

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

// ── Radar Data ────────────────────────────────────────────────────────────

function getRadarData(cases: Case[]) {
  const riskDist = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
  cases.forEach((c) => {
    const level = computeRiskLevel(c.state, c.amount_at_risk_minor);
    riskDist[level]++;
  });
  return [
    { subject: 'Low Risk', value: riskDist.LOW, fullMark: cases.length },
    { subject: 'Medium', value: riskDist.MEDIUM, fullMark: cases.length },
    { subject: 'High', value: riskDist.HIGH, fullMark: cases.length },
    { subject: 'Critical', value: riskDist.CRITICAL, fullMark: cases.length },
  ];
}

// ── Main Component ────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const { data: cases, isLoading, isError, refetch } = useCases({ limit: 200 });
  const { data: decisions } = useDecisions({ limit: 200 });

  const allCases = useMemo(() => cases || [], [cases]);
  const allDecisions = useMemo(() => decisions || [], [decisions]);

  // ── Memoized chart data ───────────────────────────────────────────────

  const stateData = useMemo(() => {
    const dist: Record<string, number> = {};
    allCases.forEach((c) => { dist[c.state] = (dist[c.state] || 0) + 1; });
    return Object.entries(dist)
      .sort(([, a], [, b]) => b - a)
      .map(([state, count]) => ({
        state: state.length > 12 ? state.slice(0, 10) + '…' : state,
        fullName: state,
        count,
        fill: STATE_COLORS[state] || COLORS.text3,
      }));
  }, [allCases]);

  const amountByState = useMemo(() => {
    const amounts: Record<string, number> = {};
    allCases.forEach((c) => {
      amounts[c.state] = (amounts[c.state] || 0) + c.amount_at_risk_minor;
    });
    return Object.entries(amounts)
      .sort(([, a], [, b]) => b - a)
      .map(([state, amount]) => ({
        state: state.length > 12 ? state.slice(0, 10) + '…' : state,
        fullName: state,
        amount,
        amountShort: formatPaiseShort(amount),
        fill: STATE_COLORS[state] || COLORS.text3,
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

  const caseTypePieData = useMemo(() => {
    const dist: Record<string, number> = {};
    allCases.forEach((c) => { dist[c.case_type] = (dist[c.case_type] || 0) + 1; });
    const typeColors = [COLORS.accent, COLORS.purple, COLORS.warning, COLORS.info];
    return Object.entries(dist).map(([type, count], i) => ({
      name: type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()),
      value: count,
      fill: typeColors[i % typeColors.length],
    }));
  }, [allCases]);

  const verdictData = useMemo(() => {
    const dist: Record<string, number> = { APPROVE: 0, MODIFY: 0, BLOCK: 0, ESCALATE: 0 };
    allDecisions.forEach((d) => {
      if (d.policy_verdict && d.policy_verdict in dist) {
        dist[d.policy_verdict]++;
      }
    });
    const verdictColors: Record<string, string> = {
      APPROVE: COLORS.success,
      MODIFY: COLORS.warning,
      BLOCK: COLORS.danger,
      ESCALATE: COLORS.orange,
    };
    return Object.entries(dist)
      .filter(([, v]) => v > 0)
      .map(([verdict, count]) => ({
        verdict,
        count,
        fill: verdictColors[verdict],
      }));
  }, [allDecisions]);

  const actionDist = useMemo(() => {
    const dist: Record<string, number> = {};
    allDecisions.forEach((d) => {
      if (d.action_type) dist[d.action_type] = (dist[d.action_type] || 0) + 1;
    });
    const actionColors = [COLORS.accent, COLORS.success, COLORS.warning, COLORS.purple, COLORS.info, COLORS.danger, COLORS.orange];
    return Object.entries(dist)
      .sort(([, a], [, b]) => b - a)
      .map(([action, count], i) => ({
        action: formatActionType(action),
        count,
        fill: actionColors[i % actionColors.length],
      }));
  }, [allDecisions]);

  const cumulativeTimeline = useMemo(() => {
    const sorted = [...allCases]
      .filter((c) => c.detected_at)
      .sort((a, b) => new Date(a.detected_at!).getTime() - new Date(b.detected_at!).getTime());
    return sorted.reduce<{ time: string; cumulative: number; amount: number }[]>((acc, c) => {
      const prev = acc.length > 0 ? acc[acc.length - 1].cumulative : 0;
      acc.push({
        time: new Date(c.detected_at!).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
        cumulative: prev + c.amount_at_risk_minor,
        amount: c.amount_at_risk_minor,
      });
      return acc;
    }, []);
  }, [allCases]);

  // ── KPI values ────────────────────────────────────────────────────────

  const totalAmount = allCases.reduce((s, c) => s + c.amount_at_risk_minor, 0);
  const recovered = allCases.filter((c) => c.state === 'RECOVERED');
  const recoveredAmount = recovered.reduce((s, c) => s + c.amount_at_risk_minor, 0);
  const totalDecisions = allDecisions.length;
  const approvedDecisions = allDecisions.filter((d) => d.policy_verdict === 'APPROVE').length;
  const approvalRate = totalDecisions > 0 ? approvedDecisions / totalDecisions : 0;

  // ── Error / Empty ─────────────────────────────────────────────────────

  if (isError) return <ErrorState message="Failed to load analytics data." onRetry={() => refetch()} />;

  if (allCases.length === 0) {
    return (
      <div className="space-y-6 page-enter">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-1">Analytics</h1>
          <p className="mt-1 text-sm text-text-3">Performance metrics and trend analysis.</p>
        </div>
        <Card>
          <EmptyState
            icon={BarChart3}
            title="No analytics data"
            description="Analytics will populate as cases are processed through the pipeline."
          />
        </Card>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 page-enter">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Analytics</h1>
        <p className="mt-1 text-sm text-text-3">Performance metrics and trend analysis across all cases.</p>
      </div>

      {/* KPI Row */}
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
            <MetricCard label="Total Amount at Risk" value={formatPaise(totalAmount)} icon={AlertTriangle} accent />
            <MetricCard label="Recovered Amount" value={formatPaise(recoveredAmount)} icon={TrendingUp} accent={recoveredAmount > 0} />
            <MetricCard label="Approval Rate" value={`${(approvalRate * 100).toFixed(0)}%`} icon={Shield} accent={approvalRate > 0} />
            <MetricCard label="Total Decisions" value={totalDecisions} icon={Activity} />
          </>
        )}
      </div>

      {/* Charts Row 1: State Distribution Bar + Risk Pie */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* State Bar Chart */}
        <Card className="xl:col-span-2">
          <CardHeader title="Cases by State" description="Distribution of current case states" />
          <div className="mt-5 h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stateData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" vertical={false} />
                <XAxis
                  dataKey="state"
                  tick={{ fill: '#5a6580', fontSize: 10 }}
                  axisLine={{ stroke: '#1a2030' }}
                  tickLine={false}
                  angle={-35}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  tick={{ fill: '#5a6580', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(91,115,255,0.05)' }} />
                <Bar dataKey="count" name="Cases" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {stateData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Risk Distribution Pie */}
        <Card>
          <CardHeader title="Risk Distribution" description="Cases by severity" />
          <div className="mt-5 h-[300px] flex flex-col items-center justify-center">
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

      {/* Charts Row 2: Amount by State + Policy Verdicts */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Amount by State */}
        <Card>
          <CardHeader title="Amount at Risk by State" description="Total monetary exposure per state" />
          <div className="mt-5 h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={amountByState} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fill: '#5a6580', fontSize: 10 }}
                  axisLine={{ stroke: '#1a2030' }}
                  tickLine={false}
                  tickFormatter={(v: number) => formatPaiseShort(v)}
                />
                <YAxis
                  type="category"
                  dataKey="state"
                  tick={{ fill: '#5a6580', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={90}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="rounded-xl border border-border bg-surface-1/95 backdrop-blur-md px-4 py-3 shadow-lg">
                        <p className="text-xs font-semibold text-text-1 mb-1">{d.fullName}</p>
                        <p className="text-sm font-bold tabular text-accent">{formatPaise(d.amount)}</p>
                      </div>
                    );
                  }}
                  cursor={{ fill: 'rgba(91,115,255,0.05)' }}
                />
                <Bar dataKey="amount" name="Amount" radius={[0, 4, 4, 0]} maxBarSize={28}>
                  {amountByState.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.75} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Policy Verdicts */}
        <Card>
          <CardHeader title="Policy Verdicts" description="Decision outcomes from the policy kernel" />
          <div className="mt-5 h-[320px]">
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

      {/* Charts Row 3: Case Types Pie + Action Distribution + Radar */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Case Types */}
        <Card>
          <CardHeader title="Case Types" description="Distribution by event type" />
          <div className="mt-5 flex flex-col items-center">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={caseTypePieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                >
                  {caseTypePieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
              {caseTypePieData.map((item) => (
                <div key={item.name} className="flex items-center gap-1.5">
                  <div className="h-2 w-2 rounded-full" style={{ backgroundColor: item.fill }} />
                  <span className="text-[10px] font-medium text-text-3">{item.name}</span>
                  <span className="text-[10px] font-bold tabular text-text-2">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Action Distribution */}
        <Card>
          <CardHeader title="Actions Recommended" description="AI planner action distribution" />
          <div className="mt-5 h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={actionDist} margin={{ top: 5, right: 10, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" vertical={false} />
                <XAxis
                  dataKey="action"
                  tick={{ fill: '#5a6580', fontSize: 9 }}
                  axisLine={{ stroke: '#1a2030' }}
                  tickLine={false}
                  angle={-25}
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
                <Bar dataKey="count" name="Count" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {actionDist.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Risk Radar */}
        <Card>
          <CardHeader title="Risk Radar" description="Multi-dimensional risk overview" />
          <div className="mt-5 h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={getRadarData(allCases)}>
                <PolarGrid stroke="#1a2030" />
                <PolarAngleAxis
                  dataKey="subject"
                  tick={{ fill: '#5a6580', fontSize: 10 }}
                />
                <PolarRadiusAxis
                  tick={{ fill: '#384258', fontSize: 9 }}
                  axisLine={false}
                />
                <Radar
                  name="Cases"
                  dataKey="value"
                  stroke={COLORS.accent}
                  fill={COLORS.accent}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
                <Tooltip content={<CustomTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Amount Over Time - Area Chart */}
      <Card>
        <CardHeader
          title="Risk Exposure Timeline"
          description="Cumulative amount at risk across detected cases"
        />
        <div className="mt-5 h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={cumulativeTimeline}
              margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.accent} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={COLORS.accent} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fill: '#5a6580', fontSize: 10 }}
                axisLine={{ stroke: '#1a2030' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#5a6580', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => formatPaiseShort(v)}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div className="rounded-xl border border-border bg-surface-1/95 backdrop-blur-md px-4 py-3 shadow-lg">
                      <p className="text-xs font-semibold text-text-1 mb-1">{payload[0]?.payload?.time}</p>
                      <p className="text-xs text-text-3">Amount: <span className="font-bold text-accent tabular">{formatPaise(payload[0]?.payload?.amount || 0)}</span></p>
                      <p className="text-xs text-text-3">Cumulative: <span className="font-bold text-text-1 tabular">{formatPaise(payload[0]?.payload?.cumulative || 0)}</span></p>
                    </div>
                  );
                }}
                cursor={{ stroke: COLORS.accent, strokeDasharray: '4 4', strokeOpacity: 0.3 }}
              />
              <Area
                type="monotone"
                dataKey="cumulative"
                stroke={COLORS.accent}
                fill="url(#areaGrad)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: COLORS.accent, stroke: '#0c1018', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
