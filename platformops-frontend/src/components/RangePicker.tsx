import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { Range, Run } from '../api'
import { formatTime, toIso } from '../format'
import { useRun } from '../session'

const DAY = 24 * 3600 * 1000

interface Preset extends Range {
  label: string
}

function presetsOf(run: Run): Preset[] {
  const start = Date.parse(run.start_utc)
  const end = Date.parse(run.end_utc)
  const tick = run.tick_seconds * 1000
  const presets: Preset[] = [{ label: 'Whole run', from: run.start_utc, to: run.end_utc }]
  for (let day = start, number = 1; day <= end; day += DAY, number += 1) {
    const date = new Date(day).toLocaleDateString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      timeZone: 'UTC',
    })
    presets.push({
      label: `Day ${number} · ${date}`,
      from: toIso(day),
      to: toIso(Math.min(day + DAY - tick, end)),
    })
  }
  presets.push({ label: 'Last 6 h of the run', from: toIso(end - 6 * 3600000 + tick), to: run.end_utc })
  return presets
}

export function RangePicker() {
  const { run, range, setRange } = useRun()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const presets = useMemo(() => presetsOf(run), [run])
  const current = presets.find((p) => p.from === range.from && p.to === range.to)

  useEffect(() => {
    if (!open) return
    const onPointer = (event: PointerEvent) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const choose = (next: Range) => {
    setRange({ from: next.from, to: next.to })
    setOpen(false)
  }

  return (
    <div className="range" ref={box}>
      <button
        type="button"
        className="button range-button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <strong>{current?.label ?? 'Custom'}</strong>
        <span className="note">
          {formatTime(range.from)} → {formatTime(range.to)} UTC
        </span>
      </button>
      {open && (
        <div className="range-menu" role="dialog" aria-label="Time range">
          <ul>
            {presets.map((preset) => (
              <li key={preset.label}>
                <button
                  type="button"
                  aria-pressed={preset === current}
                  onClick={() => choose(preset)}
                >
                  <span className="check">{preset === current ? '✓' : ''}</span>
                  {preset.label}
                </button>
              </li>
            ))}
          </ul>
          <CustomRange run={run} range={range} onApply={choose} />
        </div>
      )}
    </div>
  )
}

function CustomRange(props: { run: Run; range: Range; onApply: (range: Range) => void }) {
  const { run, range, onApply } = props
  const [from, setFrom] = useState(range.from.slice(0, 16))
  const [to, setTo] = useState(range.to.slice(0, 16))
  const [low, high] = [run.start_utc.slice(0, 16), run.end_utc.slice(0, 16)]

  const inside = [from, to].every((text) => text.length === 16 && low <= text && text <= high)
  const problem = !inside
    ? `Choose times between ${formatTime(low)} and ${formatTime(high)}.`
    : from > to
      ? 'The start must not be after the end.'
      : null

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!problem) onApply({ from: `${from}:00Z`, to: `${to}:00Z` })
  }
  return (
    <form className="range-custom" onSubmit={submit} noValidate>
      <strong>Custom (UTC)</strong>
      <label>
        From
        <input
          type="datetime-local"
          min={low}
          max={high}
          value={from}
          onChange={(event) => setFrom(event.target.value)}
        />
      </label>
      <label>
        To
        <input
          type="datetime-local"
          min={low}
          max={high}
          value={to}
          onChange={(event) => setTo(event.target.value)}
        />
      </label>
      {problem && (
        <p className="field-error" role="alert">
          {problem}
        </p>
      )}
      <button type="submit" className="button primary" disabled={problem !== null}>
        Apply
      </button>
    </form>
  )
}
