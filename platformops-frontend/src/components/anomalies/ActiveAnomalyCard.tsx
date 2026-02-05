// src/components/anomalies/ActiveAnomalyCard.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchActiveAnomaly } from '../../api/anomalies.api';

// Reuse the type from your anomalies.api.ts (or define here if not exported)
interface ActiveAnomalyResponse {
  active: boolean;
  anomalies?: {
    anomaly_type: string;
    pipeline: string;
    from_tick: number;
    to_tick: number;
  }[];
}

export function ActiveAnomalyCard() {
  const { data, isLoading } = useQuery<ActiveAnomalyResponse>({
    queryKey: ['activeAnomaly'],
    queryFn: fetchActiveAnomaly,
  });

  if (isLoading) {
    return <div className="text-zinc-400 animate-pulse">Loading active anomaly...</div>;
  }

  if (!data?.active || !data.anomalies?.length) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 text-center text-zinc-500">
        No active anomaly detected
      </div>
    );
  }

  // Safe: take first anomaly (assuming only one active at a time)
  const anomaly = data.anomalies[0];

  return (
    <div className="rounded-xl border border-red-800 bg-red-950/20 p-6 space-y-4 shadow-sm">
      <h2 className="text-lg font-medium text-red-400">Active Anomaly Detected</h2>
      <div className="grid grid-cols-2 gap-6 text-sm">
        <div>
          <p className="text-zinc-400 mb-1">Type</p>
          <p className="font-medium">{anomaly.anomaly_type}</p>
        </div>
        <div>
          <p className="text-zinc-400 mb-1">Pipeline</p>
          <p className="font-medium">{anomaly.pipeline}</p>
        </div>
        <div>
          <p className="text-zinc-400 mb-1">From Tick</p>
          <p className="font-medium">{anomaly.from_tick}</p>
        </div>
        <div>
          <p className="text-zinc-400 mb-1">To Tick</p>
          <p className="font-medium">{anomaly.to_tick ?? 'Ongoing'}</p>
        </div>
      </div>
    </div>
  );
}