// src/components/anomalies/InjectionForm.tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { http } from '../../api/http'; // your axios instance

export function InjectionForm() {
  const queryClient = useQueryClient();

  const [params, setParams] = useState({
    pipeline: 'stream_lane',
    anomaly_type: 'backlog_growth',
    from_tick: 100,
    to_tick: 200,
    strength: 1.0 as number | undefined,
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const searchParams = new URLSearchParams();
      searchParams.append('pipeline', params.pipeline);
      searchParams.append('anomaly_type', params.anomaly_type);
      searchParams.append('from_tick', params.from_tick.toString());
      searchParams.append('to_tick', params.to_tick.toString());
      if (params.strength !== undefined) {
        searchParams.append('strength', params.strength.toString());
      }

      const url = `/api/anomalies/inject?${searchParams.toString()}`;
      console.log('Sending POST to:', url);

      // Use http.post with URL + no second arg (no body)
      const response = await http.post(url);
      return response.data; // return the JSON body
    },
    onSuccess: (responseData) => {
      console.log('Success - response data:', responseData);
      queryClient.invalidateQueries({ queryKey: ['activeAnomaly'] });
      queryClient.invalidateQueries({ queryKey: ['anomalyImpact'] });
      queryClient.invalidateQueries({ queryKey: ['anomalyAnalysis'] });
    },
    onError: (error) => {
      console.error('Full error:', error);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-lg font-medium">Anomaly Injection Lab</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">Pipeline</label>
          <select
            className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            value={params.pipeline}
            onChange={(e) => setParams({ ...params, pipeline: e.target.value })}
          >
            <option value="stream_lane">Stream Lane</option>
            <option value="rail">Rail</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">Anomaly Type</label>
          <select
            className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            value={params.anomaly_type}
            onChange={(e) => setParams({ ...params, anomaly_type: e.target.value })}
          >
            <option value="cpu_saturation">CPU Saturation</option>
            <option value="error_spike">Error Spike</option>
            <option value="latency_regression">Latency Regression</option>
            <option value="event_storm">Event Storm</option>
            <option value="backlog_growth">Backlog Growth</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">From Tick</label>
          <input
            type="number"
            className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            value={params.from_tick}
            onChange={(e) => setParams({ ...params, from_tick: Number(e.target.value) })}
          />
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">To Tick</label>
          <input
            type="number"
            className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            value={params.to_tick}
            onChange={(e) => setParams({ ...params, to_tick: Number(e.target.value) })}
          />
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">Strength (1.0 = normal)</label>
          <input
            type="number"
            step="0.1"
            min="0.1"
            max="5.0"
            className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            value={params.strength ?? ''}
            onChange={(e) => setParams({ ...params, strength: e.target.value ? Number(e.target.value) : undefined })}
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-md bg-zinc-700 px-6 py-2.5 text-sm font-medium text-white hover:bg-zinc-600 disabled:opacity-50 transition-colors"
        >
          {mutation.isPending ? 'Injecting...' : 'Inject Anomaly'}
        </button>
      </div>

      {mutation.isPending && <div className="text-center text-zinc-400">Injecting...</div>}

      {mutation.isSuccess && mutation.data && (
        <div className="rounded-md bg-green-950/40 border border-green-800 p-4 text-sm text-green-300">
          Success! Injected anomaly affecting <strong>{mutation.data?.affected_points ?? 'unknown'}</strong> points.
        </div>
      )}

      {mutation.isError && (
        <div className="rounded-md bg-red-950/40 border border-red-800 p-4 text-sm text-red-300">
          Injection failed: {mutation.error?.message || 'Unknown error - check Network tab'}
        </div>
      )}
    </form>
  );
}