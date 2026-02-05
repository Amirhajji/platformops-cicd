// src/components/analytics/HealthSection.tsx
import { useQuery } from '@tanstack/react-query';
import { fetchGlobalHealth, fetchComponentHealth } from '../../api/analytics.api';
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer, Text } from 'recharts';

// Safe conversion: any → number (handles object, string, null, undefined, NaN)
function safeToNumber(val: any): number {
  if (typeof val === 'number') return val;
  if (typeof val === 'string') return parseFloat(val) || 0;
  if (val && typeof val === 'object') {
    return (
      val.health ||
      val.health_score ||
      val.score ||
      val.value ||
      val.global_health ||
      val.percent ||
      0
    );
  }
  return 0;
}

export function HealthSection() {
  const { data: rawGlobal, isLoading: globalLoading, isError: globalError } = useQuery<any>({
    queryKey: ['globalHealth'],
    queryFn: fetchGlobalHealth,
  });

  const components = ['C1', 'C6'];

  const componentQueries = components.map(code => useQuery<any>({
    queryKey: ['componentHealth', code],
    queryFn: () => fetchComponentHealth(code),
  }));

  const globalValue = safeToNumber(rawGlobal);
  const componentValues = componentQueries.map(q => safeToNumber(q.data));

  const isLoading = globalLoading || componentQueries.some(q => q.isLoading);
  const hasError = globalError || componentQueries.some(q => q.isError);

  if (hasError) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/20 p-8 text-center text-red-300">
        Failed to load health data. Check backend response.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-10 animate-pulse">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-8">
          <div className="h-8 w-48 bg-zinc-800 rounded mb-6 mx-auto" />
          <div className="h-72 bg-zinc-800 rounded" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-6 h-80" />
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-6 h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-12">
      {/* Global Health */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-8 shadow-sm">
        <h2 className="text-2xl font-semibold text-zinc-100 mb-8 text-center">Global System Health</h2>
        <div className="flex flex-col md:flex-row items-center justify-center gap-12">
          <ResponsiveContainer width={320} height={320} minWidth={0} minHeight={0}>
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="90%"
              barSize={30}
              data={[{ name: 'Global', value: globalValue }]}
              startAngle={90}
              endAngle={-270}
            >
              <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
              <RadialBar
                dataKey="value"
                background={{ fill: '#27272a' }}
                cornerRadius={10}
                fill={globalValue >= 90 ? '#10b981' : globalValue >= 70 ? '#f59e0b' : '#ef4444'}
              />
              <Text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-5xl font-bold fill-zinc-100"
              >
                {`${Math.round(globalValue)}%`}
              </Text>
            </RadialBarChart>
          </ResponsiveContainer>

          <div className="text-center md:text-left">
            <p className="text-4xl font-bold text-zinc-100 mb-2">{Math.round(globalValue)}%</p>
            <p className="text-base text-zinc-400 mb-2">Current global health score</p>
            <p className={`text-lg font-semibold ${
              globalValue >= 90 ? 'text-emerald-400' :
              globalValue >= 70 ? 'text-yellow-400' :
              'text-red-400'
            }`}>
              {globalValue >= 90 ? 'Excellent' : globalValue >= 70 ? 'Stable' : 'Critical'}
            </p>
          </div>
        </div>
      </div>

      {/* Component Health */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-8 shadow-sm">
        <h2 className="text-2xl font-semibold text-zinc-100 mb-8 text-center">Component Health Scores</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          {components.map((code, i) => {
            const health = componentValues[i];
            return (
              <div key={code} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-6">
                <h3 className="text-xl font-medium text-zinc-200 mb-6 text-center">{code}</h3>
                <div className="flex items-center justify-center gap-10">
                  <ResponsiveContainer width={220} height={220} minWidth={0} minHeight={0}>
                    <RadialBarChart
                      cx="50%"
                      cy="50%"
                      innerRadius="60%"
                      outerRadius="90%"
                      barSize={25}
                      data={[{ name: code, value: health }]}
                      startAngle={90}
                      endAngle={-270}
                    >
                      <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                      <RadialBar
                        dataKey="value"
                        background={{ fill: '#27272a' }}
                        cornerRadius={8}
                        fill={health >= 80 ? '#10b981' : health >= 50 ? '#f59e0b' : '#ef4444'}
                      />
                      <Text
                        x="50%"
                        y="50%"
                        textAnchor="middle"
                        dominantBaseline="middle"
                        className="text-4xl font-bold fill-zinc-100"
                      >
                        {`${Math.round(health)}%`}
                      </Text>
                    </RadialBarChart>
                  </ResponsiveContainer>

                  <div className="text-center">
                    <p className="text-3xl font-bold text-zinc-100 mb-2">{Math.round(health)}%</p>
                    <p className={`text-base font-semibold ${
                      health >= 80 ? 'text-emerald-400' :
                      health >= 50 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {health >= 80 ? 'Healthy' : health >= 50 ? 'Degraded' : 'Critical'}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}