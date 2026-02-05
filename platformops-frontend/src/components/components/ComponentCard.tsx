// src/components/components/ComponentCard.tsx (updated)
import { Link } from "react-router-dom";
import { useQuery } from '@tanstack/react-query';
import { fetchComponentDetails } from '../../api/components.api'; // For health in card
import { HealthBadge } from "../control-room/HealthBadge";

type Props = {
  componentCode: string;
  signalCount: number;
};

export function ComponentCard({ componentCode, signalCount }: Props) {
  const { data } = useQuery({ queryKey: ['componentDetails', componentCode], queryFn: () => fetchComponentDetails(componentCode) });

  const health = data?.health_score ?? 0;
  const status: 'OK' | 'DEGRADED' | 'CRITICAL' = health > 70 ? 'OK' : health > 40 ? 'DEGRADED' : 'CRITICAL';

  return (
    <Link
      to={`/components/${componentCode}`}
      className="block rounded-xl border border-zinc-800 bg-zinc-900 p-4 hover:border-zinc-600 transition"
    >
      <div className="flex items-center justify-between">
        <div className="font-mono text-sm">{componentCode}</div>
        <HealthBadge status={status} />
      </div>
      <div className="mt-1 text-xs text-zinc-400">{signalCount} signals | Health: {health.toFixed(1)}%</div>
    </Link>
  );
}