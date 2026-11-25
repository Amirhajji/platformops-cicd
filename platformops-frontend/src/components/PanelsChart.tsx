// One or several line panels, stacked on the same time axis.
import { LineChart } from 'echarts/charts'
import {
  AxisPointerComponent,
  GridComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useMemo, useRef, useState } from 'react'
import { formatNumber, formatTime, formatValue, STATUS_COLOR, statusOf } from '../format'

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  AxisPointerComponent,
  TitleComponent,
  MarkLineComponent,
  MarkAreaComponent,
  VisualMapComponent,
  CanvasRenderer,
])

export interface Line {
  name: string
  color?: string
  unit?: string
  values: number[]
  /** Values drawn instead of `values` (normalized view); the tooltip keeps `values`. */
  drawn?: number[]
}

export interface Panel {
  title?: string
  lines: Line[]
  /** Score from 0 to 100, coloured by status. */
  score?: boolean
  min?: number
  max?: number
  interval?: number
}

export interface Area {
  from: string
  to: string
  label: string
  color: string
  dashed?: boolean
}

const INK = '#15202e'
const MUTED = '#5b6776'
const GRID = '#e6eaef'
const FONT = '"Segoe UI", system-ui, sans-serif'

const escapeHtml = (text: string) =>
  text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)

const titleHeightOf = (panels: Panel[]) => (panels.some((panel) => panel.title) ? 34 : 8)

interface TooltipItem {
  seriesIndex: number
  dataIndex: number
  color: string
}

function buildOption(ts: string[], panels: Panel[], height: number, areas: Area[]) {
  const times = ts.map((text) => Date.parse(text))
  const first = times[0]
  const last = times[times.length - 1]
  const titleHeight = titleHeightOf(panels)
  const all = panels.flatMap((panel, index) => panel.lines.map((line) => ({ panel, line, index })))
  const top = (index: number) => titleHeight + index * (height + titleHeight)

  return {
    animation: false,
    useUTC: true,
    textStyle: { fontFamily: FONT },
    title: panels.map((panel, index) => ({
      text: panel.title ?? '',
      left: 0,
      top: top(index) - 24,
      padding: 0,
      textStyle: { fontSize: 12, fontWeight: 600, color: MUTED, fontFamily: FONT },
    })),
    grid: panels.map((_, index) => ({ left: 58, right: 16, top: top(index), height })),
    xAxis: panels.map((_, index) => ({
      type: 'time',
      gridIndex: index,
      min: first === last ? first - 60000 : first,
      max: first === last ? last + 60000 : last,
      axisLine: { lineStyle: { color: '#c3cad3' } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: {
        show: index === panels.length - 1,
        color: MUTED,
        hideOverlap: true,
        formatter: { year: '{d} {MMM}', month: '{d} {MMM}', day: '{d} {MMM}' },
      },
    })),
    yAxis: panels.map((panel, index) => ({
      type: 'value',
      gridIndex: index,
      min: panel.score ? 0 : panel.min,
      max: panel.score ? 100 : panel.max,
      interval: panel.score ? 50 : panel.interval,
      scale: !panel.score && panel.min === undefined,
      splitNumber: 3,
      axisLabel: { color: MUTED, formatter: (value: number) => formatNumber(value) },
      splitLine: { lineStyle: { color: GRID } },
    })),
    axisPointer: { link: [{ xAxisIndex: 'all' }], lineStyle: { color: '#8c97a5' } },
    tooltip: {
      trigger: 'axis',
      confine: true,
      backgroundColor: '#fff',
      borderColor: '#cfd6de',
      textStyle: { color: INK, fontSize: 12, fontFamily: FONT },
      formatter: (items: TooltipItem[]) => {
        if (!items.length) return ''
        const sorted = [...items].sort((a, b) => a.seriesIndex - b.seriesIndex)
        const rows = sorted.map(({ seriesIndex, dataIndex }) => {
          const { panel, line } = all[seriesIndex]
          const value = line.values[dataIndex]
          const color = panel.score ? STATUS_COLOR[statusOf(value)] : line.color
          const suffix = panel.score ? ` ${statusOf(value)}` : ''
          return (
            `<tr><td><span style="display:inline-block;width:14px;height:3px;` +
            `background:${color};vertical-align:middle;border-radius:2px"></span></td>` +
            `<td style="color:${MUTED}">${escapeHtml(line.name)}</td>` +
            `<td style="text-align:right;font-weight:600">` +
            `${escapeHtml(formatValue(value, line.unit))}${suffix}</td></tr>`
          )
        })
        const time = formatTime(ts[sorted[0].dataIndex])
        return `<div style="margin-bottom:4px">${time} UTC</div><table class="tip">${rows.join('')}</table>`
      },
    },
    visualMap: all.flatMap(({ panel }, seriesIndex) =>
      panel.score
        ? [
            {
              show: false,
              seriesIndex,
              dimension: 1,
              pieces: [
                { gte: 80, color: STATUS_COLOR.healthy },
                { gte: 50, lt: 80, color: STATUS_COLOR.degraded },
                { lt: 50, color: STATUS_COLOR.critical },
              ],
            },
          ]
        : [],
    ),
    series: all.map(({ panel, line, index }) => ({
      type: 'line',
      name: line.name,
      xAxisIndex: index,
      yAxisIndex: index,
      data: (line.drawn ?? line.values).map((value, i) => [times[i], value]),
      color: line.color,
      showSymbol: times.length === 1,
      symbolSize: 8,
      lineStyle: { width: panel.score ? 2 : 1.5 },
      emphasis: { disabled: true },
      markLine: panel.score
        ? {
            silent: true,
            symbol: 'none',
            label: {
              show: height >= 150,
              position: 'insideEndTop',
              formatter: (item: { value: number }) => `${item.value}`,
              color: MUTED,
              fontSize: 11,
            },
            lineStyle: { color: '#aeb7c2', type: 'dashed', width: 1 },
            data: [{ yAxis: 80 }, { yAxis: 50 }],
          }
        : undefined,
      markArea: areas.length
        ? {
            silent: true,
            data: areas.map((area, i) => [
              {
                xAxis: Date.parse(area.from),
                itemStyle: {
                  color: area.color,
                  borderColor: area.dashed ? INK : undefined,
                  borderType: 'dashed',
                  borderWidth: area.dashed ? 1 : 0,
                },
                name: area.label,
                label: { color: INK, position: i % 2 ? 'insideBottom' : 'insideTop' },
              },
              { xAxis: Date.parse(area.to) },
            ]),
          }
        : undefined,
    })),
  }
}

export function PanelsChart(props: {
  label: string
  ts: string[]
  panels: Panel[]
  /** Height of one panel. */
  height: number
  areas?: Area[]
}) {
  const { label, ts, panels, height, areas } = props
  const element = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!element.current) return
    const instance = echarts.init(element.current)
    chart.current = instance
    const observer = new ResizeObserver(() => instance.resize())
    observer.observe(element.current)
    return () => {
      observer.disconnect()
      instance.dispose()
      chart.current = null
    }
  }, [])

  const option = useMemo(
    () => buildOption(ts, panels, height, areas ?? []),
    [ts, panels, height, areas],
  )
  const titleHeight = titleHeightOf(panels)
  const total = panels.length * (height + titleHeight) + 30

  useEffect(() => {
    chart.current?.resize()
    chart.current?.setOption(option, { notMerge: true })
  }, [option, total])

  return (
    <div>
      <div
        ref={element}
        className="chart"
        role="img"
        aria-label={label}
        style={{ height: total }}
      />
      <DataTable ts={ts} panels={panels} />
    </div>
  )
}

/** The same data as text, for reading exact values. */
function DataTable({ ts, panels }: { ts: string[]; panels: Panel[] }) {
  const [open, setOpen] = useState(false)
  const lines = panels.flatMap((panel) => panel.lines)
  return (
    <details className="data-table" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Data table</summary>
      {open && (
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th>Time (UTC)</th>
                {lines.map((line, i) => (
                  <th key={i} className="number">
                    {line.name}
                    {line.unit && line.unit !== 'N/A' ? ` (${line.unit})` : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ts.map((time, row) => (
                <tr key={time}>
                  <td>{formatTime(time)}</td>
                  {lines.map((line, i) => (
                    <td key={i} className="number">
                      {formatNumber(line.values[row])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  )
}
