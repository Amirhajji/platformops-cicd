// Metric selection (up to 6) and comparison chart, used by two pages.
import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type Metric, type MetricSeries } from '../api'
import { bucketText, formatValue, plural, SERIES_COLORS } from '../format'
import { useRun } from '../session'
import { useLoad } from '../useLoad'
import { PanelsChart, type Panel } from './PanelsChart'
import { Card, Empty, Loaded } from './States'

export const MAX_METRICS = 6

/** Selected metric ids, kept in the URL so that links and refreshes keep them. */
export function useSelectedMetrics(initial: number[] = []) {
  const [params, setParams] = useSearchParams()
  const text = params.get('ids')
  const ids = useMemo(() => {
    if (text === null) return initial
    const parsed = text.split(',').map(Number)
    return [...new Set(parsed)].filter((id) => Number.isInteger(id) && id > 0).slice(0, MAX_METRICS)
  }, [text, initial])

  const setIds = (next: number[]) =>
    setParams(
      (previous) => {
        previous.set('ids', next.join(','))
        return previous
      },
      { replace: true },
    )
  const toggle = (id: number) =>
    setIds(ids.includes(id) ? ids.filter((other) => other !== id) : [...ids, id])
  return { ids, toggle, clear: () => setIds([]) }
}

/** A colour belongs to a metric while it is selected, whatever its position. */
function useColors(ids: number[]): Map<number, string> {
  const slots = useRef(new Map<number, number>())
  return useMemo(() => {
    for (const id of [...slots.current.keys()]) {
      if (!ids.includes(id)) slots.current.delete(id)
    }
    for (const id of ids) {
      if (slots.current.has(id)) continue
      const used = new Set(slots.current.values())
      slots.current.set(id, SERIES_COLORS.findIndex((_, slot) => !used.has(slot)))
    }
    return new Map([...slots.current].map(([id, slot]) => [id, SERIES_COLORS[slot]]))
  }, [ids])
}

function useDebounced(value: string, milliseconds: number): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), milliseconds)
    return () => clearTimeout(timer)
  }, [value, milliseconds])
  return debounced
}

export function MetricPicker(props: {
  /** Fixed component, or undefined to offer a filter. */
  component?: string
  ids: number[]
  onToggle: (id: number) => void
}) {
  const { ids, onToggle } = props
  const { components } = useRun()
  const [filter, setFilter] = useState('')
  const [search, setSearch] = useState('')
  const component = props.component ?? filter
  const q = useDebounced(search.trim(), 250)
  const found = useLoad((signal) => api.metrics(component, q, signal), [component, q])
  const full = ids.length >= MAX_METRICS

  return (
    <div className="picker">
      <div className="filters">
        {props.component === undefined && (
          <label>
            Component
            <select value={filter} onChange={(event) => setFilter(event.target.value)}>
              <option value="">All components</option>
              {components.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} {c.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="grow">
          Search
          <input
            type="search"
            value={search}
            maxLength={100}
            placeholder="name, metric id or resource, for example: node1 cpu"
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
      </div>
      <Loaded load={found}>
        {(metrics) => (
          <>
            <p className="note">
              {plural(metrics.length, 'metric')} found, {ids.length} of {MAX_METRICS} selected
              {full && ' (remove one to select another)'}
            </p>
            {metrics.length === 0 ? (
              <Empty>No metric matches this search.</Empty>
            ) : (
              <ul className="metric-list">
                {metrics.map((metric) => (
                  <MetricRow
                    key={metric.id}
                    metric={metric}
                    selected={ids.includes(metric.id)}
                    disabled={full && !ids.includes(metric.id)}
                    onToggle={onToggle}
                  />
                ))}
              </ul>
            )}
          </>
        )}
      </Loaded>
    </div>
  )
}

function MetricRow(props: {
  metric: Metric
  selected: boolean
  disabled: boolean
  onToggle: (id: number) => void
}) {
  const { metric, selected, disabled, onToggle } = props
  return (
    <li>
      <label className={disabled ? 'disabled' : undefined}>
        <input
          type="checkbox"
          checked={selected}
          disabled={disabled}
          onChange={() => onToggle(metric.id)}
        />
        <span className="metric-name">
          {metric.name} <span className="note">{metric.resource}</span>
        </span>
        <code>{metric.column_name}</code>
        <span className="note unit">{metric.unit}</span>
      </label>
    </li>
  )
}

/** An axis that stops at 100 %, with regular steps down to the lowest value. */
function percentAxis(values: number[]) {
  if (Math.max(...values) > 100) return {}
  const low = Math.min(...values)
  const interval = [1, 2, 5, 10].find((step) => (100 - low) / step <= 5) ?? 25
  return { min: Math.floor(low / interval) * interval, max: 100, interval }
}

function panelsOf(data: MetricSeries, colors: Map<number, string>, normalized: boolean): Panel[] {
  const lines = data.series.map((series) => {
    const low = Math.min(...series.values)
    const high = Math.max(...series.values)
    return {
      name: series.column_name,
      unit: series.unit,
      color: colors.get(series.id),
      values: series.values,
      drawn: normalized
        ? series.values.map((value) => (high > low ? (100 * (value - low)) / (high - low) : 50))
        : undefined,
    }
  })
  if (normalized) {
    return [{ title: '% of the own range of each metric', lines, min: 0, max: 100, interval: 25 }]
  }
  // One panel per unit: two scales never share an axis.
  const units = [...new Set(lines.map((line) => line.unit))]
  return units.map((unit) => {
    const own = lines.filter((line) => line.unit === unit)
    return {
      title: unit === 'N/A' ? 'no unit' : unit,
      lines: own,
      ...(unit === '%' ? percentAxis(own.flatMap((line) => line.values)) : {}),
    }
  })
}

export function MetricChart(props: {
  ids: number[]
  onRemove: (id: number) => void
  onClear: () => void
}) {
  const { ids, onRemove, onClear } = props
  const { run, range } = useRun()
  const [normalized, setNormalized] = useState(false)
  const colors = useColors(ids)
  const key = ids.join(',')
  const load = useLoad(
    (signal) =>
      ids.length ? api.metricSeries(ids, range, signal) : Promise.resolve<MetricSeries | null>(null),
    [key, range],
  )
  // While a new selection loads, the previous chart only shows metrics still selected.
  const data = useMemo(
    () =>
      load.data && {
        ...load.data,
        series: load.data.series.filter((series) => colors.has(series.id)),
      },
    [load.data, colors],
  )
  const panels = useMemo(
    () => (data ? panelsOf(data, colors, normalized) : []),
    [data, colors, normalized],
  )
  const mixed = new Set(data?.series.map((series) => series.unit)).size > 1

  return (
    <Card
      title="Selected metrics"
      note={data && ids.length > 0 && bucketText(data.bucket_ticks, run.tick_seconds, 'average')}
    >
      {ids.length === 0 ? (
        <Empty>Select up to {MAX_METRICS} metrics to compare them.</Empty>
      ) : (
        <Loaded load={load}>
          {() =>
            data && data.series.length > 0 ? (
              <>
                <div className="chips">
                  {data.series.map((series) => (
                    <span className="chip" key={series.id}>
                      <span className="line-key" style={{ background: colors.get(series.id) }} />
                      <span>
                        {series.name} <code>{series.column_name}</code>
                      </span>
                      <strong>
                        {formatValue(series.values[series.values.length - 1], series.unit)}
                      </strong>
                      <button
                        type="button"
                        aria-label={`Remove ${series.column_name}`}
                        onClick={() => onRemove(series.id)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <button type="button" className="button" onClick={onClear}>
                    Clear
                  </button>
                  {mixed && (
                    <label className="toggle">
                      <input
                        type="checkbox"
                        checked={normalized}
                        onChange={(event) => setNormalized(event.target.checked)}
                      />
                      Normalized, on one axis
                    </label>
                  )}
                </div>
                <PanelsChart
                  label="Selected metrics over time"
                  ts={data.ts}
                  panels={panels}
                  height={panels.length > 1 ? 150 : 300}
                />
              </>
            ) : (
              <Empty>Loading the selection…</Empty>
            )
          }
        </Loaded>
      )}
    </Card>
  )
}
