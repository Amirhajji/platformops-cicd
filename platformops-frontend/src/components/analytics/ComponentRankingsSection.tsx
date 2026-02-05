// src/components/analytics/ComponentRankingsSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchComponentRankings } from '../../api/analytics.api';

export function ComponentRankingsSection() {
  const { data: rawData = [], isLoading, isError } = useQuery<any>({
    queryKey: ['componentRankings'],
    queryFn: () => fetchComponentRankings(10),
  });

  // Safe unwrap
  const rankings = Array.isArray(rawData) ? rawData : rawData?.rankings || rawData?.data || [];

  if (isError) {
    return <div className="rounded-xl border border-red-800 bg-red-950/20 p-8 text-center text-red-300">Failed to load rankings.</div>;
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 animate-pulse">
        <div className="h-8 w-48 bg-zinc-800 rounded mb-4" />
        <div className="h-64 bg-zinc-800 rounded" />
      </div>
    );
  }

  if (rankings.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-10 text-center text-zinc-500">
        No component rankings available.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Component Rankings</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-zinc-800">
          <thead className="bg-zinc-950">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Component</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Rank / Score</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {rankings.map((rank: any, i: number) => (
              <tr key={i} className="hover:bg-zinc-800/50 transition-colors">
                <td className="px-6 py-4 text-sm text-zinc-300">{rank.component || rank.component_code || 'N/A'}</td>
                <td className="px-6 py-4 text-sm text-zinc-300">{rank.rank || rank.score || rank.value || 'N/A'}</td>
                <td className="px-6 py-4 text-sm text-zinc-400">{rank.details || JSON.stringify(rank.extra || {})}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}