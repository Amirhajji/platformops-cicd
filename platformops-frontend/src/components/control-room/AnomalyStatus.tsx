// src/components/control-room/AnomalyStatus.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchActiveAnomaly, fetchAnomalyImpact, fetchAnomalyAnalysis } from '../../api/controlRoom.api';

export function AnomalyStatus() {
  const activeQuery = useQuery({ queryKey: ['activeAnomaly'], queryFn: fetchActiveAnomaly });
  const impactQuery = useQuery({ queryKey: ['anomalyImpact'], queryFn: fetchAnomalyImpact, enabled: !!activeQuery.data?.active });
  const analysisQuery = useQuery({ queryKey: ['anomalyAnalysis'], queryFn: fetchAnomalyAnalysis, enabled: !!activeQuery.data?.active });

  const active = activeQuery.data;

  if (!active?.active) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <div className="text-xs uppercase text-zinc-500">Anomaly Status</div>
        <div className="mt-2 text-sm text-emerald-400">No active anomaly</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-red-800 bg-red-950/40 p-4">
      <div className="text-xs uppercase text-red-300">Active Anomaly</div>
      <div className="mt-2 text-sm text-red-200">{active.anomalies[0]?.anomaly_type ?? 'Unknown'}</div>
      <div className="mt-4 text-xs">
        <div className="font-semibold">Impact:</div>
        {impactQuery.data && (
          <ul className="list-disc pl-4">
            <li>Alerts: {impactQuery.data.simulated_alerts_count} (Critical: {impactQuery.data.by_severity?.critical ?? 0})</li>
            <li>Impacted Components: {impactQuery.data.most_impacted_components.join(', ')}</li>
            <li>Health Shift: {impactQuery.data.global_health_during_anomaly.toFixed(1)}%</li>
          </ul>
        )}
      </div>
      <div className="mt-4 text-xs">
        <div className="font-semibold">Analysis:</div>
        {analysisQuery.data && (
          <div className="space-y-1">
            <p>What changed: {analysisQuery.data.what_changed}</p>
            <p>Propagation: {analysisQuery.data.where_propagated}</p>
            <p>Degraded: {analysisQuery.data.degraded_components.join(', ')}</p>
            {/* Add charts if needed, e.g., Recharts for deviation summaries */}
          </div>
        )}
      </div>
    </div>
  );
}