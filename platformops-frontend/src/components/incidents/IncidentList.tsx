// src/components/incidents/IncidentList.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchIncidents } from '../../api/incidents.api';
import { Link } from 'react-router-dom';

type Props = {
  status: string;
};

export function IncidentList({ status }: Props) {
  const { data: incidents = [], isLoading, isError } = useQuery({
    queryKey: ['incidents', status],
    queryFn: () => fetchIncidents(status),
  });

  if (isLoading) {
    return (
      <div className="text-center text-zinc-400 py-12 animate-pulse">
        Loading {status.toLowerCase()} incidents...
      </div>
    );
  }

  if (isError || !incidents) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-10 text-center text-zinc-500">
        Failed to load incidents. Try refreshing.
      </div>
    );
  }

  if (incidents.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-10 text-center text-zinc-500">
        No {status.toLowerCase()} incidents at the moment.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900 shadow-sm">
      <table className="min-w-full divide-y divide-zinc-800">
        <thead className="bg-zinc-950">
          <tr>
            <th className="px-6 py-4 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">ID</th>
            <th className="px-6 py-4 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Title</th>
            <th className="px-6 py-4 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Severity</th>
            <th className="px-6 py-4 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Status</th>
            <th className="px-6 py-4 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Linked Alerts</th>
            <th className="px-6 py-4 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Opened</th>
            <th className="px-6 py-4 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Risk</th>
            <th className="px-6 py-4 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {incidents.map((inc) => (
            <tr key={inc.id} className="hover:bg-zinc-800/50 transition-colors">
              <td className="whitespace-nowrap px-6 py-4 text-sm font-mono text-zinc-300">#{inc.id}</td>
              <td className="px-6 py-4 text-sm font-medium text-zinc-200">{inc.title}</td>
              <td className="whitespace-nowrap px-6 py-4">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    inc.severity === 'CRITICAL' ? 'bg-red-900/60 text-red-300 ring-1 ring-red-500/30' :
                    inc.severity === 'WARNING' ? 'bg-yellow-900/60 text-yellow-300 ring-1 ring-yellow-500/30' :
                    'bg-zinc-800 text-zinc-300'
                  }`}
                >
                  {inc.severity}
                </span>
              </td>
              <td className="whitespace-nowrap px-6 py-4">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    inc.status === 'OPEN' ? 'bg-red-900/60 text-red-300 ring-1 ring-red-500/30' :
                    inc.status === 'ACKNOWLEDGED' ? 'bg-yellow-900/60 text-yellow-300 ring-1 ring-yellow-500/30' :
                    'bg-emerald-900/60 text-emerald-300 ring-1 ring-emerald-500/30'
                  }`}
                >
                  {inc.status}
                </span>
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-center text-zinc-300">
                {inc.linked_alerts?.length ?? 0}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-zinc-300">
                {new Date(inc.opened_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-center text-zinc-300">
                {inc.collapse_risk ? inc.collapse_risk.toFixed(2) : '—'}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm">
                <Link
                  to={`/incidents/${inc.id}`}
                  className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  Details →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}