export function QuickActions({
  onEvaluateAlerts,
  onEvaluateIncidents,
  onRollbackAnomaly,
}: {
  onEvaluateAlerts: () => void;
  onEvaluateIncidents: () => void;
  onRollbackAnomaly: () => void;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-2">
      <div className="text-xs uppercase text-zinc-500">Quick Actions</div>

      <button className="w-full rounded bg-zinc-800 py-2 text-sm" onClick={onEvaluateAlerts}>
        Evaluate Alerts
      </button>

      <button className="w-full rounded bg-zinc-800 py-2 text-sm" onClick={onEvaluateIncidents}>
        Evaluate Incidents
      </button>

      <button className="w-full rounded bg-red-800 py-2 text-sm" onClick={onRollbackAnomaly}>
        Rollback Anomaly
      </button>
    </div>
  );
}
