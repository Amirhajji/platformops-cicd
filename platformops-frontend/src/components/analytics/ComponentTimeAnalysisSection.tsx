// src/components/analytics/ComponentTimeAnalysisSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchComponentTimeAnalysis } from '../../api/analytics.api';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import { useState } from 'react';

export function ComponentTimeAnalysisSection() {
  const [component, setComponent] = useState('C1');

  const { data: rawData = {}, isLoading, isError } = useQuery<any>({
    queryKey: ['timeAnalysis', component],
    queryFn: () => fetchComponentTimeAnalysis(component, 500),
  });

  // Unwrap to array of {name, value}
  const chartData = Array.isArray(rawData) 
    ? rawData 
    : Object.entries(rawData).map(([key, value]) => ({ name: key, value: Number(value) || 0 }));

  if (isError) return <div className="text-red-300">Failed to load time analysis.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading time analysis...</div>;

  if (chartData.length === 0) {
    return <div className="text-zinc-500 text-center p-10">No time analysis data available.</div>;
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Component Time Analysis</h2>
      <select
        value={component}
        onChange={(e) => setComponent(e.target.value)}
        className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 mb-4"
      >
        <option value="C1">C1</option>
        <option value="C6">C6</option>
      </select>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <XAxis dataKey="name" stroke="#71717a" />
          <YAxis stroke="#71717a" />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#a855f7" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}