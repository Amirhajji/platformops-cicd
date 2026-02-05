// src/components/analytics/SystemStatsSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchSystemStats } from '../../api/analytics.api';

export function SystemStatsSection() {
  const { data: stats = {}, isLoading, isError } = useQuery<any>({
    queryKey: ['systemStats'],
    queryFn: fetchSystemStats,
  });

  if (isError) return <div className="text-red-300">Failed to load system stats.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading system stats...</div>;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">System Stats</h2>
      <pre className="bg-zinc-950 p-4 rounded text-sm overflow-auto">
        {JSON.stringify(stats, null, 2)}
      </pre>
    </div>
  );
}