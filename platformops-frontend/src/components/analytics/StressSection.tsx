// src/components/analytics/StressSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchStressCurve, type StressPoint } from '../../api/analytics.api';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import { useState } from 'react';

export function StressSection() {
  const [component, setComponent] = useState('C1');

  const { data: stress = [], isLoading, isError } = useQuery<StressPoint[]>({
    queryKey: ['stress', component],
    queryFn: () => fetchStressCurve(component, 600, 20),
  });

  if (isError) return <div className="text-red-300">Failed to load stress data.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading stress data...</div>;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Stress Curve</h2>
      <select
        value={component}
        onChange={(e) => setComponent(e.target.value)}
        className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 mb-4"
      >
        <option value="C1">C1</option>
        <option value="C6">C6</option>
      </select>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={stress}>
          <XAxis dataKey="tick" stroke="#71717a" />
          <YAxis stroke="#71717a" />
          <Tooltip />
          <Line type="monotone" dataKey="stress_level" stroke="#ef4444" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}