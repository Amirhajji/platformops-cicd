// src/components/analytics/VolatilitySection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchVolatility } from '../../api/analytics.api';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { useState } from 'react';

export function VolatilitySection() {
  const [signal, setSignal] = useState('C1.api_qps');

  const { data: volatility = 0, isLoading, isError } = useQuery<number>({
    queryKey: ['volatility', signal],
    queryFn: () => fetchVolatility(signal, 10),
  });

  const chartData = [{ name: signal, volatility }];

  if (isError) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/20 p-8 text-center text-red-300">
        Failed to load volatility data. Check backend response.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 animate-pulse">
        <div className="h-8 w-48 bg-zinc-800 rounded mb-4" />
        <div className="h-80 bg-zinc-800 rounded" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Signal Volatility</h2>

      <select
        value={signal}
        onChange={(e) => setSignal(e.target.value)}
        className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 mb-6"
      >
        <option value="C1.api_qps">C1.api_qps</option>
        <option value="C6.error_rate">C6.error_rate</option>
      </select>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <XAxis dataKey="name" stroke="#71717a" />
          <YAxis stroke="#71717a" />
          <Tooltip />
          <Bar dataKey="volatility" fill="#10b981" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      <div className="text-center mt-4">
        <p className="text-2xl font-bold text-zinc-100">
          {volatility.toFixed(2)}
        </p>
        <p className="text-sm text-zinc-400">Volatility Score</p>
      </div>
    </div>
  );
}