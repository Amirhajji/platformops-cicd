import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Kpi, type KpiSeries, type Metric } from '../api'
import { MetricChart, MetricPicker, useSelectedMetrics } from '../components/Metrics'
import { PanelsChart } from '../components/PanelsChart'
import { Card, Loaded, PageTitle, StatusBadge } from '../components/States'
import { bucketText, formatNumber, formatScore, formatTime, statusOf } from '../format'
import { useRun } from '../session'
import { useLoad } from '../useLoad'

export function ComponentPage() {
  const { id = '' } = useParams()
  // A new key per component: nothing of the previous component stays visible.
  return <ComponentView key={id} id={id} />
}

function ComponentView({ id }: { id: string }) {
  const { range, componentName } = useRun()
  const detail = useLoad((signal) => api.component(id, range.to, signal), [id, range.to])
  const kpiIds = detail.data?.kpis.map((kpi) => kpi.id).join(',') ?? ''
  const series = useLoad(
    (signal) =>
      kpiIds
        ? Promise.all(kpiIds.split(',').map((kpi) => api.kpiSeries(kpi, range, signal)))
        : Promise.resolve<KpiSeries[]>([]),
    [kpiIds, range],
  )
  const metrics = useLoad((signal) => api.metrics(id, '', signal), [id])

  return (
    <>
      <PageTitle title={`${id} ${componentName(id) === id ? '' : componentName(id)}`.trim()}>
        <span className="note">At {formatTime(range.to)} UTC, the end of the range</span>
      </PageTitle>
      <Loaded load={detail}>
        {(component) => (
          <>
            <section className={`card global edge-${component.status}`}>
              <div>
                <h2>Score z</h2>
                <div className="hero">
                  <span className="hero-value">{formatScore(component.z)}</span>
                  <StatusBadge status={component.status} />
                </div>
              </div>
              <div className="fact">
                <span className="note">Namespace</span>
                <strong className="small">{component.namespace}</strong>
              </div>
              <div className="fact">
                <span className="note">In the range</span>
                <strong className="small">
                  <Link to={`/alerts?component=${id}`}>Alerts</Link>
                  {' · '}
                  <Link to={`/incidents?component=${id}`}>Incidents</Link>
                </strong>
              </div>
            </section>
            <Card title="KPIs" note="Health: 100 at G or better, 0 at B or worse">
              <KpiTable kpis={component.kpis} />
            </Card>
          </>
        )}
      </Loaded>
      {detail.data && (
        <Loaded load={series}>
          {(all) => (all.length ? <KpiHealth all={all} /> : null)}
        </Loaded>
      )}
      {detail.data && (
        <Loaded load={metrics}>{(list) => <ComponentMetrics id={id} metrics={list} />}</Loaded>
      )}
    </>
  )
}

function KpiTable({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th>KPI</th>
            <th>Signal</th>
            <th>Type</th>
            <th className="number">Value</th>
            <th className="number">G (good)</th>
            <th className="number">B (bad)</th>
            <th>Better</th>
            <th className="number">Health</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {kpis.map((kpi) => (
            <tr key={kpi.id}>
              <td>
                {kpi.name} <code>{kpi.id}</code>
              </td>
              <td>{kpi.signal}</td>
              <td>{kpi.type}</td>
              <td className="number">
                <strong>{formatNumber(kpi.value)}</strong>
              </td>
              <td className="number">{formatNumber(kpi.good)}</td>
              <td className="number">{formatNumber(kpi.bad)}</td>
              <td>{kpi.better === 'lower' ? '↓ lower' : '↑ higher'}</td>
              <td className="number">
                <strong>{formatScore(kpi.health)}</strong>
              </td>
              <td>
                <StatusBadge status={statusOf(kpi.health)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function KpiHealth({ all }: { all: KpiSeries[] }) {
  const { run } = useRun()
  const panels = useMemo(
    () =>
      all.map((series) => ({
        score: true,
        title: series.name,
        lines: [{ name: series.name, values: series.health }],
      })),
    [all],
  )
  return (
    <Card
      title="KPI health over time"
      note={bucketText(all[0].bucket_ticks, run.tick_seconds, 'minimum')}
    >
      <PanelsChart label="Health of each KPI over time" ts={all[0].ts} panels={panels} height={64} />
    </Card>
  )
}

function ComponentMetrics({ id, metrics }: { id: string; metrics: Metric[] }) {
  // At first: the first metric, on all its resources.
  const initial = useMemo(
    () =>
      metrics
        .filter((metric) => metric.metric_id === metrics[0].metric_id)
        .slice(0, 6)
        .map((metric) => metric.id),
    [metrics],
  )
  const { ids, toggle, clear } = useSelectedMetrics(initial)
  return (
    <>
      <MetricChart ids={ids} onRemove={toggle} onClear={clear} />
      <Card title="Metrics of this component">
        <MetricPicker component={id} ids={ids} onToggle={toggle} />
      </Card>
    </>
  )
}
