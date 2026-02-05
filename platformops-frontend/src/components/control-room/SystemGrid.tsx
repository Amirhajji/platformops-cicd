// src/components/control-room/SystemGrid.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchSystemOverview } from '../../api/controlRoom.api';
import { HealthBadge } from './HealthBadge';
import { Link } from 'react-router-dom';

export function SystemGrid() {
  const { data, isLoading } = useQuery({
    queryKey: ['systemOverview'],
    queryFn: fetchSystemOverview,
  });

  if (isLoading) return <div className="text-zinc-400">Loading system...</div>;
  if (!data) return <div className="text-red-400">No system data</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {data.map((comp: any) => (
        <Link
          key={comp.component_code}
          to={`/components/${comp.component_code}`}
          className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 hover:border-zinc-600 transition"
        >
          <div className="flex items-center justify-between">
            <div className="font-mono text-sm text-zinc-200">{comp.component_code}</div>
            <HealthBadge status={comp.status} />
          </div>
          <div className="mt-2 text-xs text-zinc-400">
            Health: {comp.health_score.toFixed(1)}% | Active Alerts: {comp.active_alerts}
          </div>
        </Link>
      ))}
    </div>
  );
}