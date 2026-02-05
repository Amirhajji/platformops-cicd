// src/pages/components/ComponentDetailsPage.tsx
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchComponentDetails, fetchAlertsByComponent, fetchComponentTimeAnalysis, fetchActiveAnomaly, fetchComponentRegimes, fetchComponentStress } from '../../api/components.api';
import { SignalGroupTable } from '../../components/components/SignalGroupTable';
import { TimeseriesChart } from '../../components/charts/TimeseriesChart';
import { AlertList } from '../../components/alerts/AlertList';
import { useState } from 'react';
import { RotateCcw } from 'lucide-react';

// Define SignalMeta here (mirrors TimeseriesChart)
interface SignalMeta {
  unit: string;
  description: string;
  polarity: string;
  threshold?: number;
}

export function ComponentDetailsPage() {
  const { code } = useParams<{ code: string }>();
  const [selectedSignals, setSelectedSignals] = useState<string[]>([]);
  const [transform, setTransform] = useState<'raw' | 'aggregate' | 'derivative' | 'normalized'>('raw');
  const [activeTab, setActiveTab] = useState('signals'); // Native tab state
  const queryClient = useQueryClient();

  const detailsQuery = useQuery({ queryKey: ['componentDetails', code], queryFn: () => fetchComponentDetails(code!) });
  const alertsQuery = useQuery({ queryKey: ['alertsByComponent', code], queryFn: () => fetchAlertsByComponent(code!) });
  const timeAnalysisQuery = useQuery({ queryKey: ['componentTimeAnalysis', code], queryFn: () => fetchComponentTimeAnalysis(code!) });
  const regimesQuery = useQuery({ queryKey: ['componentRegimes', code], queryFn: () => fetchComponentRegimes(code!) });
  const stressQuery = useQuery({ queryKey: ['componentStress', code], queryFn: () => fetchComponentStress(code!) });
  const anomalyQuery = useQuery({ queryKey: ['activeAnomaly'], queryFn: fetchActiveAnomaly });

  const data = detailsQuery.data;
  const anomalyWindow = anomalyQuery.data?.active 
    ? { from: anomalyQuery.data.anomalies?.[0]?.from_tick ?? 0, to: anomalyQuery.data.anomalies?.[0]?.to_tick ?? 0 } 
    : undefined;

  const metas: Record<string, SignalMeta> = (data?.signals ?? []).reduce(
    (acc, s) => ({ ...acc, [s.signal_code]: { unit: s.unit, description: s.description, polarity: s.polarity } }),
    {}
  );

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['componentDetails', code] });
    queryClient.invalidateQueries({ queryKey: ['alertsByComponent', code] });
    queryClient.invalidateQueries({ queryKey: ['componentTimeAnalysis', code] });
    queryClient.invalidateQueries({ queryKey: ['componentRegimes', code] });
    queryClient.invalidateQueries({ queryKey: ['componentStress', code] });
  };

  if (detailsQuery.isLoading) return <div className="text-zinc-400">Loading {code}...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">{code} Details</h1>
        <button onClick={refresh} className="flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-200">
          <RotateCcw size={16} /> Refresh
        </button>
      </div>
      <p className="text-sm text-zinc-400">
        Health: {(data?.health_score?.toFixed(1) ?? 'N/A')}% | Signals: {data?.signals?.length ?? 0}
      </p>

      {/* Native Tabs */}
      <div className="border-b border-zinc-800">
        <div className="flex space-x-1">
          {['signals', 'charts', 'alerts', 'timeline'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'border-b-2 border-zinc-200 text-zinc-100'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'signals' && (
        <SignalGroupTable 
          signals={data?.signals ?? []} 
          onSelectSignals={setSelectedSignals} 
        />
      )}

      {activeTab === 'charts' && (
        <>
          <div className="flex gap-2 mb-4">
            <select 
              className="rounded border border-zinc-800 bg-zinc-950 px-2 py-1 text-sm"
              value={transform}
              onChange={e => setTransform(e.target.value as 'raw' | 'aggregate' | 'derivative' | 'normalized')}
            >
              <option value="raw">Raw</option>
              <option value="aggregate">Aggregate (Avg)</option>
              <option value="derivative">Derivative</option>
              <option value="normalized">Normalized</option>
            </select>
          </div>
          {selectedSignals.length > 0 && (
            <TimeseriesChart 
              signalCodes={selectedSignals} 
              transform={transform} 
              anomalyWindow={anomalyWindow} 
              metas={metas}
            />
          )}
        </>
      )}

      {activeTab === 'alerts' && (
        <AlertList alerts={alertsQuery.data ?? []} componentCode={code!} />
      )}

      {activeTab === 'timeline' && (
        <>
          <TimeseriesChart 
            signalCodes={['health_score']} 
            transform="raw" 
            anomalyWindow={anomalyWindow} 
            data={timeAnalysisQuery.data?.series ?? []} 
            metas={{ health_score: { unit: '%', description: 'Component health', polarity: 'higher_is_better' } }}
          />
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="border border-zinc-800 rounded-lg p-4">
              <h3 className="text-sm font-medium mb-2">Regimes</h3>
              <ul className="text-xs space-y-2">
                {regimesQuery.data?.regimes?.map((r: any) => (
                  <li 
                    key={r.from_tick} 
                    className={`p-2 rounded ${r.regime === 'STABLE' ? 'bg-emerald-950/50' : r.regime === 'DEGRADED' ? 'bg-yellow-950/50' : 'bg-red-950/50'}`}
                  >
                    <span className="font-medium">{r.regime}</span> ({r.from_tick}–{r.to_tick})  
                    <br />Alerts: {r.alert_count} | Volatility: {r.avg_volatility?.toFixed(3)}
                  </li>
                )) ?? <li className="text-zinc-500">No regime data</li>}
              </ul>
            </div>
            <div className="border border-zinc-800 rounded-lg p-4">
              <h3 className="text-sm font-medium mb-2">Stress Curve</h3>
              <TimeseriesChart 
                signalCodes={['stress_score']} 
                transform="raw" 
                data={stressQuery.data?.series ?? []} 
                metas={{ stress_score: { unit: '', description: 'Stress level', polarity: 'higher_is_worse' } }}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}