// src/components/anomalies/AnalysisNarrative.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchAnomalyAnalysis } from '../../api/anomalies.api';

export function AnalysisNarrative() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['anomalyAnalysis'],
    queryFn: fetchAnomalyAnalysis,
  });

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 animate-pulse space-y-6">
        <div className="h-8 w-64 bg-zinc-800 rounded" />
        <div className="space-y-4">
          <div className="h-6 w-48 bg-zinc-800 rounded" />
          <div className="h-24 bg-zinc-800 rounded" />
        </div>
      </div>
    );
  }

  if (isError || !data || !data.active) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center text-zinc-500">
        No active anomaly to analyze. Inject one first.
      </div>
    );
  }

  const { anomaly, system_state, observations } = data;
  const collapseRisk = system_state.global_health?.collapse_risk ?? null;
  const status = system_state.global_health?.status ?? 'UNKNOWN';

  return (
    <div className="space-y-10">
      {/* Anomaly Overview */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="text-2xl font-bold text-zinc-100 mb-4">{anomaly.title}</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
          <div>
            <p className="text-zinc-400 mb-1">Type</p>
            <p className="font-medium">{anomaly.type}</p>
          </div>
          <div>
            <p className="text-zinc-400 mb-1">Pipeline</p>
            <p className="font-medium">{anomaly.pipeline}</p>
          </div>
          <div>
            <p className="text-zinc-400 mb-1">Window</p>
            <p className="font-medium">
              {anomaly.window.from_tick} → {anomaly.window.to_tick} ({anomaly.window.duration_ticks} ticks)
            </p>
          </div>
        </div>
      </div>

      {/* System State */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h3 className="text-lg font-medium text-zinc-200 mb-4">System State During Anomaly</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-4 rounded-lg bg-zinc-950/50 text-center">
            <p className="text-sm text-zinc-400 mb-1">Collapse Risk</p>
            <p className="text-3xl font-bold text-amber-400">
              {collapseRisk !== null ? collapseRisk.toFixed(2) : 'N/A'}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-zinc-950/50 text-center">
            <p className="text-sm text-zinc-400 mb-1">Status</p>
            <p className={`text-2xl font-bold ${
              status === 'DEGRADED' ? 'text-yellow-400' :
              status === 'CRITICAL' ? 'text-red-400' :
              'text-emerald-400'
            }`}>
              {status}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-zinc-950/50 text-center">
            <p className="text-sm text-zinc-400 mb-1">Cascading</p>
            <p className="text-2xl font-bold text-zinc-100">
              {system_state.cascading_behavior ? 'Yes' : 'No'}
            </p>
          </div>
        </div>
      </div>

      {/* Key Observations */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h3 className="text-lg font-medium text-zinc-200 mb-4">Key Observations</h3>
        {observations.length === 0 ? (
          <p className="text-zinc-500 text-center py-4">No observations available</p>
        ) : (
          <ul className="space-y-4">
            {observations.map((obs, i) => (
              <li key={i} className="p-4 rounded-lg bg-zinc-950/50 border border-zinc-800">
                <span className="font-medium text-amber-400 uppercase text-xs tracking-wide block mb-1">
                  {obs.type.replace('_', ' ')}
                </span>
                <p className="text-zinc-300">{obs.message}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Expected Behavior */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h3 className="text-lg font-medium text-zinc-200 mb-4">Expected Behavior</h3>
        <ul className="space-y-3 text-sm text-zinc-300">
          {anomaly.expected_behavior.map((item, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="text-emerald-400 text-xl mt-0.5">→</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}