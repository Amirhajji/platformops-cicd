// src/components/alerts/AlertTimelineGraph.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchAlertEvents } from '../../api/alerts.api'; // remove fetchAlertsStats if not needed
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface AlertEvent {
  tick_start: number;
  tick_end?: number;
  severity: string;
}

interface TimelinePoint {
  tick: number;
  critical: number;
  warning: number;
  info: number;
}

type Props = {
  filter: { component: string; signal: string; severity: string; origin: string };
};

export function AlertTimelineGraph({ filter }: Props) {
  // Explicit query function with no params (React Query standard)
  const fetchEvents = async () => {
    return fetchAlertEvents(filter.signal || undefined, undefined, 500);
  };

  const { data: events = [] } = useQuery<AlertEvent[]>({
    queryKey: ['alertEventsForTimeline', filter],
    queryFn: fetchEvents,
  });

  // Group by tick for stacking
  const timelineData: TimelinePoint[] = [];
  if (events.length > 0) {
    const ticks = [...new Set(events.map((e) => e.tick_start))].sort((a, b) => a - b);

    ticks.forEach((tick) => {
      const atTick = events.filter(
        (e) => e.tick_start <= tick && (e.tick_end ?? tick) >= tick
      );
      timelineData.push({
        tick,
        critical: atTick.filter((e) => e.severity === 'critical').length,
        warning: atTick.filter((e) => e.severity === 'warning').length,
        info: atTick.filter((e) => e.severity === 'info').length,
      });
    });
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 shadow-sm">
      <h3 className="mb-4 text-lg font-medium text-zinc-200">Alert Activity Timeline</h3>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={timelineData}>
          <defs>
            <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorWarning" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#eab308" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#eab308" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorInfo" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6b7280" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#6b7280" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="tick" stroke="#4b5563" />
          <YAxis stroke="#4b5563" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#18181b',
              borderColor: '#27272a',
              color: '#e5e7eb',
              borderRadius: '8px',
            }}
          />
          <Area
            type="monotone"
            dataKey="critical"
            stackId="1"
            stroke="#ef4444"
            fill="url(#colorCritical)"
          />
          <Area
            type="monotone"
            dataKey="warning"
            stackId="1"
            stroke="#eab308"
            fill="url(#colorWarning)"
          />
          <Area
            type="monotone"
            dataKey="info"
            stackId="1"
            stroke="#6b7280"
            fill="url(#colorInfo)"
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="mt-4 text-xs text-zinc-400">
        {/* Safe fallback — replace with real stats keys after checking response */}
        Loading stats... (check devtools for /api/analytics/alerts-stats)
      </div>
    </div>
  );
}