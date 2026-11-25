// Client of the API (docs/API_V1.md).

export const API_BASE: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://192.168.21.133:8000'

export type Role = 'admin' | 'viewer'
export type Status = 'healthy' | 'degraded' | 'critical'

export interface User {
  id: number
  username: string
  role: Role
  created_at: string
}
export interface Run {
  spec_version: string
  seed: number
  start_utc: string
  end_utc: string
  tick_seconds: number
  ticks: number
}
export interface Scope {
  scope: string
  name: string
  z: number
  status: Status
  min_z: number
  alerts: number
  incidents: number
}
export interface Overview {
  from_ts: string
  to_ts: string
  scopes: Scope[]
}
export interface KqiSeries {
  scope: string
  bucket_ticks: number
  ts: string[]
  z: number[]
  status: Status[]
}
export interface Component {
  id: string
  name: string
  namespace: string
}
export interface Kpi {
  id: string
  name: string
  signal: string
  type: string
  value: number
  health: number
  good: number
  bad: number
  better: 'lower' | 'higher'
}
export interface ComponentDetail extends Component {
  at: string
  z: number
  status: Status
  kpis: Kpi[]
}
export interface KpiSeries {
  id: string
  name: string
  bucket_ticks: number
  ts: string[]
  value: number[]
  health: number[]
}
export interface Metric {
  id: number
  component_id: string
  column_name: string
  metric_id: string
  name: string
  unit: string
  resource: string
  level: string
  period_min: number
  range_min: number
  range_max: number | null
}
export interface MetricSeries {
  bucket_ticks: number
  ts: string[]
  series: { id: number; column_name: string; name: string; unit: string; values: number[] }[]
}
export interface Interval {
  id: number
  start_ts: string
  end_ts: string
  duration_seconds: number
}
export interface Alert extends Interval {
  kpi_id: string
  kpi_name: string
  component_id: string
  min_health: number
}
export interface Incident extends Interval {
  component_id: string
  alert_count: number
  min_z: number
}
export interface IncidentDetail extends Incident {
  alerts: Alert[]
  simulated_incident: (Interval & { description: string }) | null
}

// --- token ------------------------------------------------------------------

const TOKEN_KEY = 'platformops.token'

export const getToken = () => sessionStorage.getItem(TOKEN_KEY)
export const setToken = (token: string) => sessionStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => sessionStorage.removeItem(TOKEN_KEY)

let onUnauthorized: () => void = () => {}
/** Called when the API refuses the token. */
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

// --- requests ---------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

type Params = Record<string, string | number | null | undefined>

async function request<T>(
  method: string,
  path: string,
  { params, body, signal }: { params?: Params; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const url = new URL(API_BASE + path)
  for (const [name, value] of Object.entries(params ?? {})) {
    if (value !== null && value !== undefined && value !== '') {
      url.searchParams.set(name, String(value))
    }
  }
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers,
      signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new ApiError(0, `The API at ${API_BASE} cannot be reached.`)
  }
  if (response.ok) return (response.status === 204 ? undefined : await response.json()) as T

  const message = await response
    .json()
    .then((data) => data.error.message as string)
    .catch(() => `The API answered ${response.status}.`)
  if (response.status === 401 && path !== '/api/auth/login') {
    // A slow answer to an old token must not close a newer session.
    if (getToken() === token) onUnauthorized()
  }
  throw new ApiError(response.status, message)
}

const get = <T>(path: string, params?: Params, signal?: AbortSignal) =>
  request<T>('GET', path, { params, signal })

export interface Range {
  from: string
  to: string
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; role: Role }>('POST', '/api/auth/login', {
      body: { username, password },
    }),
  me: (signal?: AbortSignal) => get<User>('/api/auth/me', undefined, signal),
  run: (signal?: AbortSignal) => get<Run>('/api/run', undefined, signal),
  overview: (range: Range, signal?: AbortSignal) =>
    get<Overview>('/api/overview', { ...range }, signal),
  kqiSeries: (scope: string, range: Range, signal?: AbortSignal) =>
    get<KqiSeries>('/api/kqi/series', { scope, ...range }, signal),
  components: (signal?: AbortSignal) => get<Component[]>('/api/components', undefined, signal),
  component: (id: string, at: string, signal?: AbortSignal) =>
    get<ComponentDetail>(`/api/components/${encodeURIComponent(id)}`, { at }, signal),
  kpiSeries: (id: string, range: Range, signal?: AbortSignal) =>
    get<KpiSeries>(`/api/kpis/${encodeURIComponent(id)}/series`, { ...range }, signal),
  metrics: (component: string, q: string, signal?: AbortSignal) =>
    get<Metric[]>('/api/metrics', { component, q }, signal),
  metricSeries: (ids: number[], range: Range, signal?: AbortSignal) =>
    get<MetricSeries>('/api/metrics/series', { ids: ids.join(','), ...range }, signal),
  alerts: (component: string, range: Range, signal?: AbortSignal) =>
    get<Alert[]>('/api/alerts', { component, ...range }, signal),
  incidents: (component: string, range: Range, signal?: AbortSignal) =>
    get<Incident[]>('/api/incidents', { component, ...range }, signal),
  incident: (id: string, signal?: AbortSignal) =>
    get<IncidentDetail>(`/api/incidents/${encodeURIComponent(id)}`, undefined, signal),
  users: (signal?: AbortSignal) => get<User[]>('/api/users', undefined, signal),
  createUser: (username: string, password: string, role: Role) =>
    request<User>('POST', '/api/users', { body: { username, password, role } }),
  deleteUser: (id: number) => request<void>('DELETE', `/api/users/${id}`),
}
