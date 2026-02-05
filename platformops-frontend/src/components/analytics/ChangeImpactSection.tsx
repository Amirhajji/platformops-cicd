// src/components/analytics/ChangeImpactSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchChangeImpact, type ChangeImpact } from '../../api/analytics.api';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { useState } from 'react';

export function ChangeImpactSection() {
  const [signal, setSignal] = useState('C1.api_qps');

  const { data: changes = [], isLoading, isError } = useQuery<ChangeImpact[]>({
    queryKey: ['changeImpact', signal],
    queryFn: () => fetchChangeImpact(signal, 1000, 200),
  });

  if (isError) return <div className="text-red-300">Failed to load change impact.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading change impact...</div>;

  return (
    <div className="space-y-10">
      <h2 className="text-2xl font-semibold text-zinc-100 mb-6">Change Impact Analysis</h2>
      <select
        value={signal}
        onChange={(e) => setSignal(e.target.value)}
        className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 mb-4"
      >
        <option value="C1.api_qps">C1.api_qps</option>
        <option value="C1.processing_latency_ms">C1.processing_latency_ms</option>
      </select>
      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={changes}>
          <XAxis dataKey="change_tick" stroke="#71717a" />
          <YAxis stroke="#71717a" />
          <Tooltip />
          <Bar dataKey="impact_score" fill="#facc15" />
        </BarChart>
      </ResponsiveContainer>

      <div className="space-y-4">
        {changes.map((change, i) => (
          <div key={i} className="p-4 rounded-lg bg-zinc-950/50">
            <p>Change at tick {change.change_tick} (Impact: {change.impact_score.toFixed(2)})</p>
            <p>Affected: {change.affected_signals.join(', ')}</p>
          </div>
        ))}
      </div>
    </div>
  );
}