import { useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth, useRun } from '../session'
import { ErrorBoundary } from './ErrorBoundary'
import { RangePicker } from './RangePicker'

export function Layout() {
  const { user, logout } = useAuth()
  const { run, components } = useRun()
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Main">
        <div className="brand">
          <img src="/favicon.svg" alt="" width="26" height="26" /> PlatformOPS
        </div>
        <NavLink to="/overview">Overview</NavLink>
        <div className="nav-group">Components</div>
        {components.map((component) => (
          <NavLink key={component.id} to={`/components/${component.id}`} className="nav-sub">
            <span className="nav-id">{component.id}</span> {component.name}
          </NavLink>
        ))}
        <div className="nav-group">Analysis</div>
        <NavLink to="/metrics">Metric explorer</NavLink>
        <NavLink to="/alerts">Alerts</NavLink>
        <NavLink to="/incidents">Incidents</NavLink>
        {user?.role === 'admin' && (
          <>
            <div className="nav-group">Administration</div>
            <NavLink to="/users">Users</NavLink>
          </>
        )}
      </nav>
      <div className="main">
        <header className="topbar">
          <div className="run-info">
            <strong>Simulated run</strong>
            <span className="note">
              spec v{run.spec_version} · seed {run.seed} · {run.start_utc.slice(0, 10)} to{' '}
              {run.end_utc.slice(0, 10)} · {run.ticks.toLocaleString('en')} ticks of{' '}
              {run.tick_seconds} s
            </span>
          </div>
          <RangePicker />
          <div className="user">
            <span>
              {user?.username} <span className="role">{user?.role}</span>
            </span>
            <button type="button" className="button" onClick={logout}>
              Log out
            </button>
          </div>
        </header>
        <main className="content">
          <ErrorBoundary key={pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
