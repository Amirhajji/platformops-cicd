import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api, type KqiSeries, type Scope } from '../api'
import { PanelsChart } from '../components/PanelsChart'
import { Card, Loaded, PageTitle, StatusBadge } from '../components/States'
import { bucketText, formatScore, formatTime } from '../format'
import { useRun } from '../session'
import { useLoad } from '../useLoad'

export function Overview() {
  const { range, components } = useRun()
  const overview = useLoad((signal) => api.overview(range, signal), [range])
  const series = useLoad(
    (signal) =>
      Promise.all(
        ['GLOBAL', ...components.map((c) => c.id)].map((scope) =>
          api.kqiSeries(scope, range, signal),
        ),
      ),
    [range, components],
  )
  return (
    <>
      <PageTitle title="Overview">
        <span className="note">Scores at {formatTime(range.to)} UTC, the end of the range</span>
      </PageTitle>
      <Loaded load={overview}>
        {({ scopes }) => {
          const total = scopes[0]
          return (
            <>
              <GlobalCard scope={total} />
              <div className="cards">
                {scopes.slice(1).map((scope) => (
                  <ScopeCard key={scope.scope} scope={scope} />
                ))}
              </div>
            </>
          )
        }}
      </Loaded>
      <Loaded load={series}>{(all) => <Timelines all={all} />}</Loaded>
    </>
  )
}

function GlobalCard({ scope }: { scope: Scope }) {
  return (
    <section className={`card global edge-${scope.status}`}>
      <div>
        <h2>Global score Z</h2>
        <div className="hero">
          <span className="hero-value">{formatScore(scope.z)}</span>
          <StatusBadge status={scope.status} />
        </div>
      </div>
      <Fact label="Lowest Z in the range" value={formatScore(scope.min_z)} />
      <Fact label="Alerts in the range" value={scope.alerts} to="/alerts" />
      <Fact label="Incidents in the range" value={scope.incidents} to="/incidents" />
    </section>
  )
}

function Fact({ label, value, to }: { label: string; value: string | number; to?: string }) {
  return (
    <div className="fact">
      <span className="note">{label}</span>
      <strong>{to ? <Link to={to}>{value}</Link> : value}</strong>
    </div>
  )
}

function ScopeCard({ scope }: { scope: Scope }) {
  return (
    <section className={`card scope edge-${scope.status}`}>
      <header>
        <h3>
          <Link to={`/components/${scope.scope}`}>
            <span className="nav-id">{scope.scope}</span> {scope.name}
          </Link>
        </h3>
        <StatusBadge status={scope.status} />
      </header>
      <div className="scope-z">{formatScore(scope.z)}</div>
      <dl>
        <div>
          <dt>Min z</dt>
          <dd>{formatScore(scope.min_z)}</dd>
        </div>
        <div>
          <dt>Alerts</dt>
          <dd>
            <Link to={`/alerts?component=${scope.scope}`}>{scope.alerts}</Link>
          </dd>
        </div>
        <div>
          <dt>Incidents</dt>
          <dd>
            <Link to={`/incidents?component=${scope.scope}`}>{scope.incidents}</Link>
          </dd>
        </div>
      </dl>
    </section>
  )
}

function Timelines({ all }: { all: KqiSeries[] }) {
  const { run, componentName } = useRun()
  const note = bucketText(all[0].bucket_ticks, run.tick_seconds, 'minimum')
  const global = useMemo(
    () => [{ score: true, lines: [{ name: 'Global Z', values: all[0].z }] }],
    [all],
  )
  const components = useMemo(
    () =>
      all.slice(1).map((series) => ({
        score: true,
        title: `${series.scope} ${componentName(series.scope)}`,
        lines: [{ name: series.scope, values: series.z }],
      })),
    [all, componentName],
  )
  return (
    <>
      <Card title="Global Z over time" note={note}>
        <PanelsChart label="Global Z over time" ts={all[0].ts} panels={global} height={180} />
      </Card>
      <Card title="Component scores over time" note={note}>
        <PanelsChart
          label="Score z of each component over time"
          ts={all[0].ts}
          panels={components}
          height={54}
        />
      </Card>
    </>
  )
}
