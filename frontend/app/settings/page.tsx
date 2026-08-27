'use client';

import { Settings, ExternalLink } from 'lucide-react';
import { useVersion, useHealth } from '@/lib/hooks';
import { Card, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ErrorState } from '@/components/ui/error-state';
import { formatDateTime } from '@/lib/utils';

export default function SettingsPage() {
  const { data: version, isError: versionError, refetch: refetchVersion } = useVersion();
  const { data: health, isError: healthError, refetch: refetchHealth } = useHealth();

  if (versionError && healthError) {
    return <ErrorState message="Failed to load settings." onRetry={() => { refetchVersion(); refetchHealth(); }} />;
  }

  return (
    <div className="space-y-6 page-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Settings</h1>
        <p className="mt-1 text-sm text-text-3">System configuration and integration details.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* System Info */}
        <Card>
          <CardHeader title="System Information" description="Backend version and runtime details" />
          <div className="mt-4 space-y-0">
            {version && (
              <>
                {[
                  { label: 'Application', value: version.app_name },
                  { label: 'Version', value: version.version },
                  { label: 'Git SHA', value: version.git_sha || '—', mono: true },
                  { label: 'LLM Provider', value: version.llm_provider },
                  { label: 'Environment', value: version.environment },
                ].map(({ label, value, mono }, idx, arr) => (
                  <div key={label} className={`flex items-center justify-between py-2.5 ${idx < arr.length - 1 ? 'border-b border-border/30' : ''}`}>
                    <span className="text-xs text-text-3">{label}</span>
                    <span className={`text-sm ${mono ? 'font-mono text-[11px] text-text-3' : 'text-text-2'}`}>{value}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </Card>

        {/* Health */}
        <Card>
          <CardHeader title="Service Health" description="Backend connectivity and database status" />
          <div className="mt-4 space-y-0">
            {health && (
              <>
                <div className="flex items-center justify-between py-2.5 border-b border-border/30">
                  <span className="text-xs text-text-3">API Status</span>
                  <Badge variant={health.status === 'ok' ? 'success' : 'danger'}>{health.status}</Badge>
                </div>
                <div className="flex items-center justify-between py-2.5 border-b border-border/30">
                  <span className="text-xs text-text-3">Database</span>
                  <Badge variant={health.database === 'ok' ? 'success' : 'danger'}>{health.database}</Badge>
                </div>
                <div className="flex items-center justify-between py-2.5 border-b border-border/30">
                  <span className="text-xs text-text-3">Uptime</span>
                  <span className="text-sm tabular font-semibold text-text-1">{Math.round(health.uptime_seconds)}s</span>
                </div>
                <div className="flex items-center justify-between py-2.5">
                  <span className="text-xs text-text-3">Last Checked</span>
                  <span className="text-sm text-text-2">{formatDateTime(health.timestamp)}</span>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>

      {/* API Integration */}
      <Card>
        <CardHeader title="API Integration" description="Backend API endpoints and documentation" />
        <div className="mt-4 space-y-0">
          {[
            { label: 'API Base URL', value: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000' },
            { label: 'Health Check', value: '/api/health' },
            { label: 'OpenAPI Docs', value: '/api/docs', link: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/docs` },
            { label: 'ReDoc', value: '/api/redoc', link: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/redoc` },
          ].map(({ label, value, link }, idx, arr) => (
            <div key={label} className={`flex items-center justify-between py-2.5 ${idx < arr.length - 1 ? 'border-b border-border/30' : ''}`}>
              <span className="text-xs text-text-3">{label}</span>
              {link ? (
                <a href={link} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-sm text-accent hover:text-accent-hover transition-colors">
                  {value} <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                <span className="text-sm font-mono text-[11px] text-text-3">{value}</span>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Environment Notice */}
      <Card>
        <div className="flex items-start gap-3.5 rounded-xl bg-warning/5 border border-warning/10 px-5 py-4">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-warning/10">
            <Settings className="h-4.5 w-4.5 text-warning" />
          </div>
          <div>
            <p className="text-sm font-semibold text-text-1">Simulated Environment</p>
            <p className="mt-1 text-xs text-text-3 leading-relaxed">
              All payment effects in this system are simulated. No real money moves. The system runs
              with the mock LLM provider by default. To use a real LLM provider, configure the
              appropriate API key in your environment variables.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
