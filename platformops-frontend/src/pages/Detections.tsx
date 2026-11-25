// Alerts and incidents.
import { useMemo } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, type Alert, type IncidentDetail as Detail, type KqiSeries } from '../api'
import { PanelsChart } from '../components/PanelsChart'
import { Card, Empty, Loaded, PageTitle, StatusBadge } from '../components/States'
import {
  around,
  bucketText,
  formatDuration,
  formatScore,
  formatTime,
  plural,
  statusOf,
} from '../format'
import { useRun } from '../session'
import { useLoad } from '../useLoad'

function useComponentFilter() {
  const { components } = useRun()
  const [params, setParams] = useSearchParams()
  const wanted = params.get('component') ?? ''
  const component = components.some((c) => c.id === wanted) ? wanted : ''
  const select = (
    <div className="filters">
      <label>
        Component
        <select
          value={component}
          onChange={(event) =>
            setParams(event.target.value ? { component: event.target.value } : {}, {
              replace: true,
            })
          }
        >
          <option value="">All components</option>
          {components.map((c) => (
            <option key={c.id} value={c.id}>
              {c.id} {c.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
  return { component, select }
}

function ComponentLink({ id }: { id: string }) {
  const { componentName } = useRun()
  return (
    <Link to={`/components/${id}`}>
      <span className="nav-id">{id}</span> {componentName(id)}
    </Link>
  )
}

export function Alerts() {
  const { range } = useRun()
  const { component, select } = useComponentFilter()
  const load = useLoad((signal) => api.alerts(component, range, signal), [component, range])
  return (
    <>
      <PageTitle title="Alerts">
        <span className="note">A KPI has an alert while its health is below 50</span>
      </PageTitle>
      <Card>
        {select}
        <Loaded load={load}>
          {(alerts) =>
            alerts.length ? (
              <>
                <p className="note">{plural(alerts.length, 'alert')} in the range</p>
                <AlertTable alerts={alerts} />
              </>
            ) : (
              <Empty>No alert in this range.</Empty>
            )
          }
        </Loaded>
      </Card>
    </>
  )
}

function AlertTable({ alerts }: { alerts: Alert[] }) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th>Component</th>
            <th>KPI</th>
            <th>Start (UTC)</th>
            <th>End (UTC)</th>
            <th className="number">Duration</th>
            <th className="number">Min health</th>
            <th>Worst status</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id}>
              <td>
                <ComponentLink id={alert.component_id} />
              </td>
              <td>
                {alert.kpi_name} <code>{alert.kpi_id}</code>
              </td>
              <td>{formatTime(alert.start_ts)}</td>
              <td>{formatTime(alert.end_ts)}</td>
              <td className="number">{formatDuration(alert.duration_seconds)}</td>
              <td className="number">{formatScore(alert.min_health)}</td>
              <td>
                <StatusBadge status={statusOf(alert.min_health)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Incidents() {
  const { range } = useRun()
  const { component, select } = useComponentFilter()
  const load = useLoad((signal) => api.incidents(component, range, signal), [component, range])
  return (
    <>
      <PageTitle title="Incidents">
        <span className="note">Alerts of one component that overlap or follow each other</span>
      </PageTitle>
      <Card>
        {select}
        <Loaded load={load}>
          {(incidents) =>
            incidents.length ? (
              <>
                <p className="note">{plural(incidents.length, 'incident')} in the range</p>
                <div className="scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Incident</th>
                        <th>Component</th>
                        <th>Start (UTC)</th>
                        <th>End (UTC)</th>
                        <th className="number">Duration</th>
                        <th className="number">Alerts</th>
                        <th className="number">Min z</th>
                        <th>Worst status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {incidents.map((incident) => (
                        <tr key={incident.id}>
                          <td>
                            <Link to={`/incidents/${incident.id}`}>#{incident.id} details</Link>
                          </td>
                          <td>
                            <ComponentLink id={incident.component_id} />
                          </td>
                          <td>{formatTime(incident.start_ts)}</td>
                          <td>{formatTime(incident.end_ts)}</td>
                          <td className="number">{formatDuration(incident.duration_seconds)}</td>
                          <td className="number">{incident.alert_count}</td>
                          <td className="number">{formatScore(incident.min_z)}</td>
                          <td>
                            <StatusBadge status={statusOf(incident.min_z)} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <Empty>No incident in this range.</Empty>
            )
          }
        </Loaded>
      </Card>
    </>
  )
}

export function IncidentPage() {
  const { id = '' } = useParams()
  return <IncidentView key={id} id={id} />
}

function IncidentView({ id }: { id: string }) {
  const { run } = useRun()
  const load = useLoad(
    async (signal) => {
      const incident = await api.incident(id, signal)
      const { start_ts, end_ts } = incident
      const window = around(start_ts, end_ts, 60, run.start_utc, run.end_utc)
      const series = await api.kqiSeries(incident.component_id, window, signal)
      return { incident, series, window }
    },
    [id, run],
  )
  return (
    <>
      <PageTitle title={`Incident #${id}`}>
        <Link to="/incidents">All incidents</Link>
      </PageTitle>
      <Loaded load={load}>
        {({ incident, series, window }) => (
          <>
            <IncidentFacts incident={incident} window={window} />
            <IncidentChart incident={incident} series={series} />
            <Simulated incident={incident} />
            <Card title={`Alerts of this incident (${incident.alerts.length})`}>
              <AlertTable alerts={incident.alerts} />
            </Card>
          </>
        )}
      </Loaded>
    </>
  )
}

function IncidentFacts(props: { incident: Detail; window: { from: string; to: string } }) {
  const { incident, window } = props
  const { setRange } = useRun()
  return (
    <section className={`card global edge-${statusOf(incident.min_z)}`}>
      <div>
        <h2>
          <ComponentLink id={incident.component_id} />
        </h2>
        <div className="hero">
          <span className="hero-value">{formatScore(incident.min_z)}</span>
          <span className="note">lowest z</span>
          <StatusBadge status={statusOf(incident.min_z)} />
        </div>
      </div>
      <div className="fact">
        <span className="note">Detected (UTC)</span>
        <strong className="small">
          {formatTime(incident.start_ts)} → {formatTime(incident.end_ts)}
        </strong>
      </div>
      <div className="fact">
        <span className="note">Duration</span>
        <strong className="small">{formatDuration(incident.duration_seconds)}</strong>
      </div>
      <button type="button" className="button" onClick={() => setRange(window)}>
        Use as time range (± 1 h)
      </button>
    </section>
  )
}

function IncidentChart({ incident, series }: { incident: Detail; series: KqiSeries }) {
  const { run } = useRun()
  const panels = useMemo(
    () => [{ score: true, lines: [{ name: `z ${series.scope}`, values: series.z }] }],
    [series],
  )
  const areas = useMemo(() => {
    const list = [
      {
        from: incident.start_ts,
        to: incident.end_ts,
        label: 'detected',
        color: 'rgba(208, 59, 59, 0.12)',
      },
    ]
    const simulated = incident.simulated_incident
    return simulated
      ? [
          ...list,
          {
            from: simulated.start_ts,
            to: simulated.end_ts,
            label: 'simulated',
            color: 'rgba(0, 0, 0, 0)',
            dashed: true,
          },
        ]
      : list
  }, [incident])
  return (
    <Card
      title="Score z around the incident"
      note={bucketText(series.bucket_ticks, run.tick_seconds, 'minimum')}
    >
      <PanelsChart
        label="Score z of the component around the incident"
        ts={series.ts}
        panels={panels}
        height={200}
        areas={areas}
      />
    </Card>
  )
}

function Simulated({ incident }: { incident: Detail }) {
  const simulated = incident.simulated_incident
  if (!simulated) {
    return (
      <Card title="Simulated incident">
        <Empty>No simulated incident overlaps this one.</Empty>
      </Card>
    )
  }
  const minutes = (later: string, earlier: string) =>
    Math.round((Date.parse(later) - Date.parse(earlier)) / 60000)
  const start = minutes(incident.start_ts, simulated.start_ts)
  const end = minutes(incident.end_ts, simulated.end_ts)
  const shift = (value: number) =>
    value === 0 ? 'same minute' : value > 0 ? `${value} min later` : `${-value} min earlier`
  return (
    <Card title="Simulated incident" note="Ground truth, never used to detect">
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              <th>Start (UTC)</th>
              <th>End (UTC)</th>
              <th className="number">Duration</th>
              <th>Detected start</th>
              <th>Detected end</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{simulated.description}</td>
              <td>{formatTime(simulated.start_ts)}</td>
              <td>{formatTime(simulated.end_ts)}</td>
              <td className="number">{formatDuration(simulated.duration_seconds)}</td>
              <td>{shift(start)}</td>
              <td>{shift(end)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  )
}
