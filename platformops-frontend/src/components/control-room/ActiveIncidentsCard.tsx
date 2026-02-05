export function ActiveIncidentsCard({ count }: { count: number }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="text-xs uppercase text-zinc-500">Active Incidents</div>
      <div className="mt-2 text-xl font-semibold">
        {count === 0 ? (
          <span className="text-emerald-400">None</span>
        ) : (
          <span className="text-red-400">{count}</span>
        )}
      </div>
    </div>
  );
}
