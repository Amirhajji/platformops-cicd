// src/components/alerts/AlertActions.tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { evaluateAlerts, resetAndEvaluate } from '../../api/alerts.api';

export function AlertActions() {
  const queryClient = useQueryClient();

  const evalMutation = useMutation({
    mutationFn: () => evaluateAlerts(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertSummary'] });
      queryClient.invalidateQueries({ queryKey: ['activeAlerts'] });
      queryClient.invalidateQueries({ queryKey: ['alertHistory'] });
    },
  });

  const resetEvalMutation = useMutation({
    mutationFn: () => resetAndEvaluate(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertSummary'] });
      queryClient.invalidateQueries({ queryKey: ['activeAlerts'] });
      queryClient.invalidateQueries({ queryKey: ['alertHistory'] });
    },
  });

  return (
    <div className="flex gap-3">
      <button
        onClick={() => evalMutation.mutate()}
        disabled={evalMutation.isPending}
        className="flex items-center gap-2 rounded-md bg-zinc-700 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-600 disabled:opacity-50 transition-colors"
      >
        {evalMutation.isPending ? 'Evaluating...' : 'Evaluate Now'}
      </button>
      <button
        onClick={() => resetEvalMutation.mutate()}
        disabled={resetEvalMutation.isPending}
        className="flex items-center gap-2 rounded-md bg-red-900/80 px-4 py-2 text-sm font-medium text-white hover:bg-red-900 disabled:opacity-50 transition-colors"
      >
        {resetEvalMutation.isPending ? 'Resetting...' : 'Reset & Re-evaluate'}
      </button>
    </div>
  );
}