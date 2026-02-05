// src/components/analytics/RegimesSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchRegimes, type Regime } from '../../api/analytics.api';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { useState } from 'react';

export function RegimesSection() {
  const [component, setComponent] = useState('C1');

  const { data: regimes = [], isLoading, isError } = useQuery<Regime[]>({
    queryKey: ['regimes', component],
    queryFn: () => fetchRegimes(component, 1440, 60),
  });

  // Prepare data for chart (duration = end - start)
  const chartData = regimes.map(r => ({
    ...r,
    duration: r.end_tick - r.start_tick,
  }));

  if (isError) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/20 p-8 text-center text-red-300">
        Failed to load regimes data.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 animate-pulse">
        <div className="h-8 w-48 bg-zinc-800 rounded mb-4" />
        <div className="h-72 bg-zinc-800 rounded" />
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-10 text-center text-zinc-500">
        No regimes detected for this component.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Regime Detection</h2>

      {/* Component selector */}
      <select
        value={component}
        onChange={(e) => setComponent(e.target.value)}
        className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 mb-6"
      >
        <option value="C1">C1</option>
        <option value="C6">C6</option>
        {/* Add more components as needed */}
      </select>

      {/* Regime Duration Bar Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <XAxis dataKey="start_tick" stroke="#71717a" />
          <YAxis stroke="#71717a" label={{ value: 'Duration (ticks)', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
            labelStyle={{ color: '#e5e5e5' }}
          />
          <Bar dataKey="duration" fill="#a855f7" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      <p className="text-sm text-zinc-400 mt-4 text-center">
        Regime durations based on detected system states (stable, volatile, degraded, etc.).
      </p>
    </div>
  );
}