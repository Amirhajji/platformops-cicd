// src/components/control-room/MiniLaneMap.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchSystemOverview } from '../../api/controlRoom.api';
import { HealthBadge } from './HealthBadge';

// Static chains from cloud docs (real-time lane: C1→C2→C3→C6→C8)
const lanes = [
  { name: 'Real-Time Lane', components: ['C1', 'C2', 'C3', 'C6', 'C8'] },
  { name: 'Hourly Batch Lane', components: ['C1', 'C4', 'C5', 'C6', 'C7'] },
  // Add others if needed
];

export function MiniLaneMap() {
  const { data } = useQuery({ queryKey: ['systemOverview'], queryFn: fetchSystemOverview });

  const getStatus = (code: string) => data?.find((c: any) => c.component_code === code)?.status ?? 'UNKNOWN';

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="text-xs uppercase text-zinc-500">System Lanes (Causality Map)</div>
      <div className="mt-4 space-y-4">
        {lanes.map(lane => (
          <div key={lane.name}>
            <div className="text-sm text-zinc-300">{lane.name}</div>
            <div className="flex items-center gap-2 mt-1">
              {lane.components.map((code, i) => (
                <>
                  <div key={code} className="flex items-center gap-1">
                    <span className="font-mono text-xs">{code}</span>
                    <HealthBadge status={getStatus(code)} />
                  </div>
                  {i < lane.components.length - 1 && <span className="text-zinc-500">→</span>}
                </>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}