// src/components/anomalies/HealthRankingTable.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchAnomalyAnalysis } from '../../api/anomalies.api';

export function HealthRankingTable() {
  const { data } = useQuery({
    queryKey: ['anomalyAnalysis'],
    queryFn: fetchAnomalyAnalysis,
  });

  if (!data?.health?.components_ranked) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">Health Ranking (Impacted Components)</h3>
      <table className="w-full text-sm rounded-xl border border-zinc-800 bg-zinc-900">
        <thead className="border-b border-zinc-800 text-zinc-400">
          <tr>
            <th className="px-4 py-3 text-left">Component</th>
            <th className="px-4 py-3 text-left">Open Alerts</th>
            <th className="px-4 py-3 text-left">Health Score</th>
          </tr>
        </thead>
        <tbody>
          {data.health.components_ranked.map((c, i) => (
            <tr key={i} className="border-b border-zinc-800 last:border-0">
              <td className="px-4 py-3">{c.component_label} ({c.component_code})</td>
              <td className="px-4 py-3">{c.open_alerts}</td>
              <td className="px-4 py-3">{c.health_score?.toFixed(1) ?? 'N/A'}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}