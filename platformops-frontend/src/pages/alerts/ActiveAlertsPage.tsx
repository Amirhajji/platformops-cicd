// src/pages/alerts/ActiveAlertsPage.tsx (updated)
import { useQuery } from '@tanstack/react-query';
import { fetchAlertEvents } from '../../api/alerts.api';
import { AlertEventsTable } from '../../components/alerts/AlertEventsTable';

type Props = { filter: { component: string; signal: string; severity: string; origin: string } };

export function ActiveAlertsPage({ filter }: Props) {
  const { data: activeAlerts, isLoading } = useQuery({
    queryKey: ['activeAlerts', filter],
    queryFn: () => fetchAlertEvents(filter.signal, 'OPEN', 100),
  });

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">Active Alerts ({activeAlerts?.length ?? 0})</h2>
      <AlertEventsTable alerts={activeAlerts ?? []} filter={filter} />
    </div>
  );
}

// Similar for AlertHistoryPage.tsx
export function AlertHistoryPage({ filter }: Props) {
  const { data: history, isLoading } = useQuery({
    queryKey: ['alertHistory', filter],
    queryFn: () => fetchAlertEvents(filter.signal, undefined, 200),
  });

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">Alert History ({history?.length ?? 0})</h2>
      <AlertEventsTable alerts={history ?? []} filter={filter} />
    </div>
  );
}