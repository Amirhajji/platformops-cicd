// src/components/control-room/AlertSummary.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchAlertSummary } from '../../api/controlRoom.api';

export function AlertSummary() {
  const { data } = useQuery({
    queryKey: ['alertSummary'],
    queryFn: fetchAlertSummary,
  });

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="text-xs uppercase text-zinc-500">Alert Summary</div>
      <div className="mt-2 grid grid-cols-3 gap-2">
        <div className="text-sm">Critical: <span className="text-red-400">{data?.critical ?? 0}</span></div>
        <div className="text-sm">Warning: <span className="text-yellow-400">{data?.warning ?? 0}</span></div>
        <div className="text-sm">Info: <span className="text-zinc-400">{data?.info ?? 0}</span></div>
      </div>
    </div>
  );
}