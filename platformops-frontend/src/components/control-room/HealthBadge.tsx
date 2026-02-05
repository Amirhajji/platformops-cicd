// src/components/control-room/HealthBadge.tsx
import { Badge } from 'lucide-react'; // Assuming we add shadcn or similar; if not, use div with classes

type Props = { status: 'OK' | 'DEGRADED' | 'CRITICAL' };

export function HealthBadge({ status }: Props) {
  const color = 
    status === 'OK' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' :
    status === 'DEGRADED' ? 'bg-yellow-950 text-yellow-400 border-yellow-800' :
    'bg-red-950 text-red-400 border-red-800';

  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium border ${color}`}>
      {status}
    </span>
  );
}