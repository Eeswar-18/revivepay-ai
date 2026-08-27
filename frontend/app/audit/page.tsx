'use client';

import { ScrollText } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';

export default function AuditPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Audit Log</h1>
        <p className="mt-1 text-sm text-text-3">
          Append-only, hash-chained audit trail of all system decisions and actions.
        </p>
      </div>

      <Card>
        <EmptyState
          icon={ScrollText}
          title="Audit log not yet available"
          description="The audit log API endpoint has not been implemented yet. Once the backend exposes /api/audit, this page will display the full hash-chained audit trail with filtering and search."
        />
      </Card>
    </div>
  );
}
