import { useEffect } from 'react'
import type { ReactNode } from 'react'
import type { Status } from '../api'
import type { Load } from '../useLoad'

export function Loading({ text = 'Loading…' }: { text?: string }) {
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden="true" /> {text}
    </div>
  )
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="state">{children}</div>
}

/** Error, first loading, or the content (dimmed while it reloads). */
export function Loaded<T>(props: { load: Load<T>; children: (data: T) => ReactNode }) {
  const { load, children } = props
  if (load.error) return <ErrorBox message={load.error} onRetry={load.reload} />
  if (load.data === undefined) return <Loading />
  return (
    <div className={load.loading ? 'reloading' : undefined} aria-busy={load.loading}>
      {children(load.data)}
    </div>
  )
}

export function Card(props: {
  title?: string
  note?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${props.className ?? ''}`}>
      {props.title && (
        <header className="card-header">
          <h2>{props.title}</h2>
          {props.note && <span className="note">{props.note}</span>}
        </header>
      )}
      {props.children}
    </section>
  )
}

export function PageTitle({ title, children }: { title: string; children?: ReactNode }) {
  useEffect(() => {
    document.title = `${title} · PlatformOPS`
  }, [title])
  return (
    <div className="page-title">
      <h1>{title}</h1>
      {children}
    </div>
  )
}

// A shape per status, so that it never depends on the colour only.
const SHAPES: Record<Status, ReactNode> = {
  healthy: <circle cx="6" cy="6" r="5" />,
  degraded: <path d="M6 1 11.5 11H.5Z" />,
  critical: <rect x="1.2" y="1.2" width="9.6" height="9.6" rx="1" />,
}

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`badge badge-${status}`}>
      <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true">
        {SHAPES[status]}
      </svg>
      {status}
    </span>
  )
}
