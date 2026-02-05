// src/api/analytics.api.ts
import { http } from "./http";

// Helper: safely get number from any response
function getNumber(data: any): number {
  if (typeof data === 'number') return data;
  if (data && typeof data.volatility === 'number') return data.volatility;
  if (data && typeof data.health === 'number') return data.health;
  if (data && typeof data.health_score === 'number') return data.health_score;
  if (data && typeof data.score === 'number') return data.score;
  if (data && typeof data.value === 'number') return data.value;
  if (typeof data === 'string') return parseFloat(data) || 0;
  return 0;
}

// Global Health
export async function fetchGlobalHealth() {
  const { data } = await http.get<any>("/api/analytics/global-health");
  return getNumber(data);
}

// Component Health
export async function fetchComponentHealth(code: string) {
  const { data } = await http.get<any>(`/api/analytics/component-health/${code}`);
  return getNumber(data);
}

// Volatility – FIXED: always extract the real volatility number
export async function fetchVolatility(signalCode: string, window = 10) {
  const { data } = await http.get<any>("/api/analytics/volatility", {
    params: { signal_code: signalCode, window },
  });
  return getNumber(data); // now returns 0.42, not the object
}

// Forecast
export type ForecastPoint = {
  tick: number;
  value: number;
  upper: number;
  lower: number;
};

export async function fetchForecast(signalCode: string, horizonTicks = 30) {
  const { data } = await http.get<any>("/api/analytics/forecast/signal", {
    params: { signal_code: signalCode, horizon_ticks: horizonTicks },
  });
  return Array.isArray(data) ? data : data?.forecast || data?.data || [];
}

// Regimes
export type Regime = {
  start_tick: number;
  end_tick: number;
  type: string;
};

export async function fetchRegimes(component: string, window = 1440, bucketSize = 60) {
  const { data } = await http.get<any>(`/api/analytics/component-regimes/${component}`, {
    params: { window, bucket_size: bucketSize },
  });
  return Array.isArray(data) ? data : data?.regimes || data?.data || [];
}

// Stress Curve
export type StressPoint = {
  tick: number;
  stress_level: number;
};

export async function fetchStressCurve(component: string, window = 600, bucket = 20) {
  const { data } = await http.get<any>(`/api/analytics/component-stress/${component}`, {
    params: { window, bucket },
  });
  return Array.isArray(data) ? data : data?.stress || data?.data || [];
}

// Change Impact
export type ChangeImpact = {
  change_tick: number;
  impact_score: number;
  affected_signals: string[];
};

export async function fetchChangeImpact(signalCode?: string, pivotTick = 1000, window = 200) {
  const params = signalCode ? { signal_code: signalCode, pivot_tick: pivotTick, window } : { pivot_tick: pivotTick, window };
  const { data } = await http.get<any>("/api/analytics/signal-change-impact", { params });
  return Array.isArray(data) ? data : data?.impacts || data?.data || [];
}

// Other endpoints (keep as-is or add similar unwrap if needed)
export async function fetchSystemStats() {
  const { data } = await http.get<any>("/api/analytics/system-stats");
  return data ?? {};
}

export async function fetchAlertsStats(fromTick = 1000, toTick = 2000, limit = 10) {
  const { data } = await http.get<any>("/api/analytics/alerts-stats", { params: { from_tick: fromTick, to_tick: toTick, limit } });
  return Array.isArray(data) ? data : data?.stats || data?.data || [];
}

export async function fetchComponentRankings(limit = 10) {
  const { data } = await http.get<any>("/api/analytics/component-rankings", { params: { limit } });
  return Array.isArray(data) ? data : data?.rankings || data?.data || [];
}

export async function fetchSignalCoverage(windowTicks = 200, limit = 20) {
  const { data } = await http.get<any>("/api/analytics/signal-coverage", { params: { window_ticks: windowTicks, limit } });
  return Array.isArray(data) ? data : data?.coverage || data?.data || [];
}

export async function fetchActiveHotspots(limit = 15) {
  const { data } = await http.get<any>("/api/analytics/active-hotspots", { params: { limit } });
  return Array.isArray(data) ? data : data?.hotspots || data?.data || [];
}

export async function fetchComponentTimeAnalysis(component: string, maxTicks = 500) {
  const { data } = await http.get<any>(`/api/analytics/component-time-analysis/${component}`, { params: { max_ticks: maxTicks } });
  return data ?? {};
}

export async function fetchSignalEnvelope(signalCode: string, window = 300, bucket = 10) {
  const { data } = await http.get<any>("/api/analytics/signal-envelope", { params: { signal_code: signalCode, window, bucket } });
  return Array.isArray(data) ? data : data?.envelope || data?.data || [];
}