import type { Status } from './api'

/** Status bands of docs/PLATFORM_V1.md, also used for the health of a KPI. */
export function statusOf(score: number): Status {
  return score >= 80 ? 'healthy' : score >= 50 ? 'degraded' : 'critical'
}

export const STATUS_COLOR: Record<Status, string> = {
  healthy: '#0ca30c',
  degraded: '#d18a00',
  critical: '#d03b3b',
}

/** Categorical colours, in this fixed order (safe for colour-blind readers). */
export const SERIES_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300']

const plain = new Intl.NumberFormat('en', { maximumSignificantDigits: 5 })
const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumSignificantDigits: 4 })

export function formatNumber(value: number): string {
  return Math.abs(value) >= 100000 ? compact.format(value) : plain.format(value)
}

export function formatValue(value: number, unit?: string): string {
  if (!unit || unit === 'N/A') return formatNumber(value)
  return `${formatNumber(value)} ${unit}`
}

export const formatScore = (score: number) => score.toFixed(1)

/** 2026-11-01T05:00:00Z -> 2026-11-01 05:00 (all times are UTC). */
export const formatTime = (iso: string) => iso.slice(0, 16).replace('T', ' ')

export const toIso = (milliseconds: number) =>
  new Date(milliseconds).toISOString().slice(0, 19) + 'Z'

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min`
  const rest = minutes % 60
  return rest ? `${Math.floor(minutes / 60)} h ${rest} min` : `${minutes / 60} h`
}

/** What one point of a chart stands for. */
export function bucketText(bucketTicks: number, tickSeconds: number, how: string): string {
  return bucketTicks === 1
    ? `exact values, one point every ${formatDuration(tickSeconds)}`
    : `one point = ${how} of ${formatDuration(bucketTicks * tickSeconds)}`
}

/** A range around an interval, inside the run. */
export function around(start: string, end: string, minutes: number, low: string, high: string) {
  const from = toIso(Date.parse(start) - minutes * 60000)
  const to = toIso(Date.parse(end) + minutes * 60000)
  return { from: from < low ? low : from, to: to > high ? high : to }
}

export const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`
