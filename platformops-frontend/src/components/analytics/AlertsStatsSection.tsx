// src/components/analytics/AlertsStatsSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchAlertsStats } from '../../api/analytics.api';

export function AlertsStatsSection() {
  const { data: stats = [], isLoading, isError } = useQuery<any[]>({
    queryKey: ['alertsStats'],
    queryFn: () => fetchAlertsStats(1000, 2000, 10),
  });

  if (isError) return <div className="text-red-300">Failed to load alerts stats.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading alerts stats...</div>;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Alerts Stats</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-zinc-800">
          <thead className="bg-zinc-950">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Key</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {stats.map((stat: any, i: number) => (
              <tr key={i} className="hover:bg-zinc-800/50 transition-colors">
                <td className="px-6 py-4 text-sm text-zinc-300">{stat.key || 'N/A'}</td>
                <td className="px-6 py-4 text-sm text-zinc-300">{stat.value || 'N/A'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}