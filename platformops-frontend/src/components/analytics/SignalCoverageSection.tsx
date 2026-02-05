// src/components/analytics/SignalCoverageSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchSignalCoverage } from '../../api/analytics.api';

export function SignalCoverageSection() {
  const { data: rawData = [], isLoading, isError } = useQuery<any>({
    queryKey: ['signalCoverage'],
    queryFn: () => fetchSignalCoverage(200, 20),
  });

  const coverage = Array.isArray(rawData) ? rawData : rawData?.coverage || rawData?.data || [];

  if (isError) return <div className="text-red-300">Failed to load coverage.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading coverage...</div>;

  if (coverage.length === 0) {
    return <div className="text-zinc-500 text-center p-10">No signal coverage data available.</div>;
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Signal Coverage</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-zinc-800">
          <thead className="bg-zinc-950">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Signal</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Coverage %</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {coverage.map((item: any, i: number) => (
              <tr key={i} className="hover:bg-zinc-800/50 transition-colors">
                <td className="px-6 py-4 text-sm text-zinc-300">{item.signal || item.signal_code || 'N/A'}</td>
                <td className="px-6 py-4 text-sm text-zinc-300">{item.coverage || item.percentage || 'N/A'}</td>
                <td className="px-6 py-4 text-sm text-zinc-400">{item.details || JSON.stringify(item.extra || {})}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}