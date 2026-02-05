// src/components/analytics/ActiveHotspotsSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchActiveHotspots } from '../../api/analytics.api';

export function ActiveHotspotsSection() {
  const { data: rawData = [], isLoading, isError } = useQuery<any>({
    queryKey: ['activeHotspots'],
    queryFn: () => fetchActiveHotspots(15),
  });

  const hotspots = Array.isArray(rawData) ? rawData : rawData?.hotspots || rawData?.data || [];

  if (isError) return <div className="text-red-300">Failed to load hotspots.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading hotspots...</div>;

  if (hotspots.length === 0) {
    return <div className="text-zinc-500 text-center p-10">No active hotspots detected.</div>;
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Active Hotspots</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-zinc-800">
          <thead className="bg-zinc-950">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Hotspot</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Severity / Level</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {hotspots.map((hot: any, i: number) => (
              <tr key={i} className="hover:bg-zinc-800/50 transition-colors">
                <td className="px-6 py-4 text-sm text-zinc-300">{hot.hotspot || hot.component || 'N/A'}</td>
                <td className="px-6 py-4 text-sm text-zinc-300">{hot.level || hot.severity || hot.score || 'N/A'}</td>
                <td className="px-6 py-4 text-sm text-zinc-400">{hot.details || JSON.stringify(hot.extra || {})}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}