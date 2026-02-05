// src/components/icons/PolarityIcon.tsx
import { ArrowUp, ArrowDown } from 'lucide-react';

type Props = { polarity: string; trend: 'up' | 'down' | 'flat' }; // Trend from slope

export function PolarityIcon({ polarity, trend }: Props) {
  const isBad = 
    (polarity === 'higher_is_worse' && trend === 'up') ||
    (polarity === 'lower_is_worse' && trend === 'down');
  const color = isBad ? 'text-red-400' : 'text-emerald-400';
  const Icon = trend === 'up' ? ArrowUp : trend === 'down' ? ArrowDown : null;

  return Icon ? <Icon size={16} className={color} /> : <span className="text-zinc-400">-</span>;
}