// src/components/charts/TimeseriesChart.tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ReferenceArea, Brush, ReferenceLine } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { fetchMultiTimeseries, fetchAggregate, fetchDerivative, fetchNormalized, fetchComponentVolatility } from '../../api/components.api';
import { useTimeWindow } from '../../context/TimeContext';
import { PolarityIcon } from '../icons/PolarityIcon';

interface TimeseriesPoint {
  tick: number;
  value: number;
}

type TimeseriesData = Record<string, TimeseriesPoint[]>;

interface SignalMeta {
  unit: string;
  description: string;
  polarity: string;
  threshold?: number;
}

type Props = {
  signalCodes: string[];
  transform: 'raw' | 'aggregate' | 'derivative' | 'normalized';
  anomalyWindow?: { from: number; to: number };
  data?: TimeseriesPoint[];
  metas?: Record<string, SignalMeta>;
};

export function TimeseriesChart({ signalCodes, transform, anomalyWindow, data, metas = {} }: Props) {
  const { window } = useTimeWindow();

  const queryFn = async (): Promise<TimeseriesData> => {
    let res: TimeseriesData = {};
    try {
      if (transform === 'raw') {
        const rawRes = await fetchMultiTimeseries(signalCodes);
        res = rawRes?.signals ?? {};
      } else if (transform === 'aggregate') {
        const agg = await Promise.all(signalCodes.map(c => fetchAggregate(c).catch(() => [])));
        agg.forEach((series, i) => {
          res[signalCodes[i]] = series;
        });
      } else if (transform === 'derivative') {
        const der = await Promise.all(signalCodes.map(c => fetchDerivative(c).catch(() => [])));
        der.forEach((series, i) => {
          res[signalCodes[i]] = series;
        });
      } else {
        const norm = await Promise.all(signalCodes.map(c => fetchNormalized(c).catch(() => [])));
        norm.forEach((series, i) => {
          res[signalCodes[i]] = series;
        });
      }
    } catch (err) {
      console.error("Timeseries fetch failed:", err);
    }
    return res;
  };

  const { data: chartData = {}, isLoading, isError } = useQuery<TimeseriesData>({
    queryKey: ['timeseries', signalCodes, transform, window],
    queryFn,
  });

  if (isLoading) return <div className="text-zinc-400 animate-pulse">Loading chart...</div>;
  if (isError || Object.keys(chartData).length === 0) {
    return <div className="text-zinc-500 text-center py-10">No timeseries data available for selected signals</div>;
  }

  const usedData = data ? { 'health_score': data } : chartData;

  const mergedData: Array<Record<string, number | undefined>> = [];
  if (usedData) {
    const allTicks = new Set<number>();
    Object.values(usedData).forEach(series => {
      if (Array.isArray(series)) {
        series.forEach(p => allTicks.add(p.tick));
      }
    });

    Array.from(allTicks).sort((a, b) => a - b).forEach(tick => {
      const point: Record<string, number | undefined> = { tick };
      signalCodes.forEach(code => {
        const series = usedData[code];
        if (Array.isArray(series)) {
          const p = series.find(sp => sp.tick === tick);
          point[code] = p?.value;
        }
      });
      mergedData.push(point);
    });
  }

  const getTrend = (series: TimeseriesPoint[]): 'up' | 'down' | 'flat' => {
    if (series.length < 2) return 'flat';
    const slope = (series[series.length - 1].value - series[0].value) / (series.length - 1);
    return slope > 0 ? 'up' : slope < 0 ? 'down' : 'flat';
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload) return null;
    return (
      <div className="rounded bg-zinc-800 p-3 text-xs border border-zinc-600 shadow-lg">
        <p className="font-medium">Tick: {label}</p>
        {payload.map((p: any, i: number) => {
          const code = signalCodes[i];
          const meta = metas[code];
          return (
            <p key={code} className="mt-1">
              {code}: <span className="font-medium">{p.value?.toFixed(2) ?? 'N/A'}</span> {meta?.unit ?? ''}
              <br />
              <span className="text-zinc-400 text-xs">{meta?.description ?? ''}</span>
            </p>
          );
        })}
      </div>
    );
  };

  const handleExport = () => {
    const headers = ['tick', ...signalCodes];
    const rows = mergedData.map(row => [
      row.tick,
      ...signalCodes.map(code => row[code] ?? '')
    ]);
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${signalCodes.join('-')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-3">
          {signalCodes.map((code) => {
            const series = usedData[code] ?? [];
            const trend = getTrend(series);
            return (
              <div key={code} className="flex items-center gap-1 text-sm">
                <PolarityIcon polarity={metas[code]?.polarity ?? 'higher_is_worse'} trend={trend} />
                {code}
              </div>
            );
          })}
        </div>
        <button 
          onClick={handleExport}
          className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
        >
          Export CSV
        </button>
      </div>

      <LineChart width={800} height={400} data={mergedData.length > 0 ? mergedData : []}>
        <XAxis dataKey="tick" stroke="#71717a" />
        <YAxis stroke="#71717a" />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        {signalCodes.map((code) => {
          const polarity = metas[code]?.polarity ?? 'higher_is_worse';
          const color = polarity === 'higher_is_worse' ? '#ef4444' : '#10b981';
          return <Line key={code} type="monotone" dataKey={code} stroke={color} dot={false} connectNulls />;
        })}
        {signalCodes.map(code => {
          const threshold = metas[code]?.threshold;
          if (threshold !== undefined) {
            return <ReferenceLine key={`thresh-${code}`} y={threshold} stroke="#facc15" strokeDasharray="3 3" />;
          }
          return null;
        })}
        {anomalyWindow && (
          <ReferenceArea x1={anomalyWindow.from} x2={anomalyWindow.to} fill="#ef4444" fillOpacity={0.08} />
        )}
        <Brush dataKey="tick" height={30} stroke="#52525b" fill="#27272a" />
      </LineChart>

      <div className="grid grid-cols-3 gap-3">
        {signalCodes.map(code => (
          <VolatilityCard key={code} signalCode={code} />
        ))}
      </div>
    </div>
  );
}

function VolatilityCard({ signalCode }: { signalCode: string }) {
  const { data = 0, isLoading } = useQuery<number>({
    queryKey: ['volatility', signalCode],
    queryFn: () => fetchComponentVolatility(signalCode),
    placeholderData: 0,
  });

  return (
    <div className="rounded border border-zinc-800 p-3 text-xs bg-zinc-950/50">
      <div className="text-zinc-500">{signalCode} Volatility</div>
      <div className="font-medium mt-1">
        {isLoading ? '...' : data.toFixed(3)}
      </div>
    </div>
  );
}