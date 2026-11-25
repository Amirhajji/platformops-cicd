// Logged-in user, run settings and time range, shared by every page.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  api,
  ApiError,
  clearToken,
  getToken,
  setToken,
  setUnauthorizedHandler,
  type Component,
  type Range,
  type Run,
  type User,
} from './api'
import { ErrorBox, Loading } from './components/States'
import { useLoad } from './useLoad'

// --- authentication ---------------------------------------------------------

interface Auth {
  user: User | null
  /** The session ended because the API refused the token. */
  expired: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<Auth | null>(null)
const RANGE_KEY = 'platformops.range'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [expired, setExpired] = useState(false)
  const [restoring, setRestoring] = useState(getToken() !== null)
  const [error, setError] = useState<string>()
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearToken()
      setUser(null)
      setExpired(true)
    })
  }, [])

  // After a page refresh, the token of this tab is still in sessionStorage.
  useEffect(() => {
    if (getToken() === null) return
    const controller = new AbortController()
    setError(undefined)
    setRestoring(true)
    api.me(controller.signal).then(
      (me) => {
        setUser(me)
        setRestoring(false)
      },
      (failure: unknown) => {
        if (controller.signal.aborted) return
        setRestoring(false)
        if (!(failure instanceof ApiError && failure.status === 401)) {
          setError(failure instanceof Error ? failure.message : 'Unexpected error')
        }
      },
    )
    return () => controller.abort()
  }, [attempt])

  const login = useCallback(async (username: string, password: string) => {
    setToken((await api.login(username, password)).token)
    setUser(await api.me())
    setExpired(false)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    sessionStorage.removeItem(RANGE_KEY)
    setUser(null)
    setExpired(false)
  }, [])

  const value = useMemo(() => ({ user, expired, login, logout }), [user, expired, login, logout])
  if (error) {
    return (
      <main className="fullscreen">
        <ErrorBox message={error} onRetry={() => setAttempt((count) => count + 1)} />
      </main>
    )
  }
  if (restoring) {
    return (
      <main className="fullscreen">
        <Loading />
      </main>
    )
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth outside AuthProvider')
  return auth
}

// --- run and time range -----------------------------------------------------

interface RunState {
  run: Run
  components: Component[]
  componentName: (id: string) => string
  range: Range
  setRange: (range: Range) => void
}

const RunContext = createContext<RunState | null>(null)

const isInside = (range: Range, run: Run) =>
  run.start_utc <= range.from && range.from <= range.to && range.to <= run.end_utc

function savedRange(run: Run): Range {
  try {
    const saved = JSON.parse(sessionStorage.getItem(RANGE_KEY) ?? 'null') as Range | null
    if (saved && isInside(saved, run)) return { from: saved.from, to: saved.to }
  } catch {
    // not valid: use the whole run
  }
  return { from: run.start_utc, to: run.end_utc }
}

export function RunProvider({ children }: { children: ReactNode }) {
  const { data, error, reload } = useLoad(
    (signal) => Promise.all([api.run(signal), api.components(signal)]),
    [],
  )
  if (error) {
    return (
      <main className="fullscreen">
        <ErrorBox message={error} onRetry={reload} />
      </main>
    )
  }
  if (!data) {
    return (
      <main className="fullscreen">
        <Loading />
      </main>
    )
  }
  return (
    <LoadedRun run={data[0]} components={data[1]}>
      {children}
    </LoadedRun>
  )
}

function LoadedRun(props: { run: Run; components: Component[]; children: ReactNode }) {
  const { run, components, children } = props
  const [range, storeRange] = useState(() => savedRange(run))
  const value = useMemo<RunState>(
    () => ({
      run,
      components,
      componentName: (id) => components.find((c) => c.id === id)?.name ?? id,
      range,
      setRange: (next) => {
        sessionStorage.setItem(RANGE_KEY, JSON.stringify(next))
        storeRange(next)
      },
    }),
    [run, components, range],
  )
  return <RunContext.Provider value={value}>{children}</RunContext.Provider>
}

export function useRun(): RunState {
  const run = useContext(RunContext)
  if (!run) throw new Error('useRun outside RunProvider')
  return run
}
