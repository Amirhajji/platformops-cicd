// src/components/analytics/SignalEnvelopeSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchSignalEnvelope } from '../../api/analytics.api';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { useState } from 'react';

export function SignalEnvelopeSection() {
  const [signal, setSignal] = useState('C1.api_qps');

  const { data: envelope = [], isLoading, isError } = useQuery<any[]>({
    queryKey: ['signalEnvelope', signal],
    queryFn: () => fetchSignalEnvelope(signal, 300, 10),
  });

  if (isError) return <div className="text-red-300">Failed to load envelope.</div>;
  if (isLoading) return <div className="text-zinc-400">Loading envelope...</div>;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-medium mb-4">Signal Envelope</h2>
      <select
        value={signal}
        onChange={(e) => setSignal(e.target.value)}
        className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 mb-4"
      >
        <option value="C1.api_qps">C1.api_qps</option>
        <option value="C1.processing_latency_ms">C1.processing_latency_ms</option>
      </select>
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={envelope}>
          <XAxis dataKey="tick" stroke="#71717a" />
          <YAxis stroke="#71717a" />
          <Tooltip />
          <Area type="monotone" dataKey="upper" fill="#10b981" fillOpacity={0.1} stroke="#10b981" />
          <Area type="monotone" dataKey="lower" fill="#ef4444" fillOpacity={0.1} stroke="#ef4444" />
          <Area type="monotone" dataKey="value" fill="#a855f7" fillOpacity={0.2} stroke="#a855f7" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}