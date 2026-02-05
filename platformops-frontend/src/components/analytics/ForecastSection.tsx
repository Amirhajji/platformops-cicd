// src/components/analytics/ForecastSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchForecast, type ForecastPoint } from '../../api/analytics.api';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Area } from 'recharts';
import { useState } from 'react';

export function ForecastSection() {
  const [signal, setSignal] = useState('C1.api_qps');

  const { data: forecast = [], isLoading, isError } = useQuery<ForecastPoint[]>({
    queryKey: ['forecast', signal],
    queryFn: () => fetchForecast(signal, 30),
  });

  if (isError) return <div className="text-red-300">Failed to load forecast.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading forecast...</div>;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Signal Forecast</h2>
      <select
        value={signal}
        onChange={(e) => setSignal(e.target.value)}
        className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 mb-4"
      >
        <option value="C1.api_qps">C1.api_qps</option>
        <option value="C1.processing_latency_ms">C1.processing_latency_ms</option>
      </select>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={forecast}>
          <XAxis dataKey="tick" stroke="#71717a" />
          <YAxis stroke="#71717a" />
          <Tooltip />
          <Area type="monotone" dataKey="upper" fill="#10b981" fillOpacity={0.1} stroke="#10b981" />
          <Area type="monotone" dataKey="lower" fill="#ef4444" fillOpacity={0.1} stroke="#ef4444" />
          <Line type="monotone" dataKey="value" stroke="#a855f7" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}