// src/api/alerts.api.ts (updated full file)
import { http } from "./http";

export type AlertRule = {
  id: number;
  signal_code: string;
  operator: string;
  threshold: number;
  min_duration_ticks: number;
  severity: string;
  enabled: boolean;
};

export type AlertEvent = {
  id: number;
  rule_id: number;
  component_code: string;
  signal_code: string;
  tick_start: number;
  tick_end?: number;
  peak_value: number;
  severity: string;
  status: string;
  origin: string;
};

export async function fetchAlertRules() {
  const { data } = await http.get<AlertRule[]>("/api/alerts/rules");
  return data;
}

export async function generateAllRules() {
  const { data } = await http.post("/api/alerts/rules/generate-all");
  return data;
}

export async function evaluateAlerts(lookbackTicks = 200, simulationMode = false) {
  const { data } = await http.post("/api/alerts/evaluate", { lookback_ticks: lookbackTicks, simulation_mode: simulationMode });
  return data;
}

export async function resetAndEvaluate(lookbackTicks = 200) {
  const { data } = await http.post("/api/alerts/reset-and-evaluate", { lookback_ticks: lookbackTicks });
  return data;
}

export async function fetchAlertEvents(signalCode?: string, status?: string, limit = 100) {
  const params = new URLSearchParams();
  if (signalCode) params.append("signal_code", signalCode);
  if (status) params.append("status", status);
  params.append("limit", limit.toString());
  const { data } = await http.get<AlertEvent[]>(`/api/alerts/events?${params}`);
  return data;
}

export async function fetchAlertSummary() {
  const { data } = await http.get<Record<string, number>>("/api/alerts/summary");
  return data;
}

export async function fetchAlertsStats(fromTick?: number, toTick?: number, limit = 10) {
  const params = new URLSearchParams();
  if (fromTick) params.append("from_tick", fromTick.toString());
  if (toTick) params.append("to_tick", toTick.toString());
  params.append("limit", limit.toString());
  const { data } = await http.get(`/api/analytics/alerts-stats?${params}`);
  return data;
}

// Bonus: Fetch spikes for alert patterns
export async function fetchAlertSpikes() {
  const { data } = await http.get("/api/analytics/patterns/spikes");
  return data;
}