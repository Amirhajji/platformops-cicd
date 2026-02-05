// src/api/incidents.api.ts (full file)
import type { AlertEvent } from "./alerts.api";
import { http } from "./http";

export type Incident = {
  id: number;
  title: string;
  description: string;
  status: string; // OPEN, ACKNOWLEDGED, RESOLVED
  severity: string; // INFO, WARNING, CRITICAL
  opened_at: string;
  resolved_at: string | null;
  resolution_note: string | null;
  collapse_risk: number | null;
  affected_components: string[];
  linked_alerts: AlertEvent[]; // from alerts.api
};

export type IncidentTimelineEvent = {
  tick: number;
  event: string;
  severity: string;
  signal: string;
};

export type IncidentComment = {
  id: number;
  incident_id: number;
  user_id: number;
  comment: string;
  created_at: string;
};

export async function fetchIncidents(status = "OPEN") {
  const { data } = await http.get<Incident[]>(`/api/incidents?status=${status}`);
  return data;
}

export async function fetchIncident(id: number) {
  const { data } = await http.get<Incident>(`/api/incidents/${id}`);
  return data;
}

export async function fetchIncidentTimeline(id: number) {
  const { data } = await http.get<{ timeline: IncidentTimelineEvent[] }>(`/api/incidents/${id}/timeline`);
  return data.timeline;
}

export async function acknowledgeIncident(id: number) {
  const { data } = await http.post<Incident>(`/api/incidents/${id}/acknowledge`);
  return data;
}

export async function resolveIncident(id: number, note: string) {
  const { data } = await http.post<Incident>(`/api/incidents/${id}/resolve`, { note });
  return data;
}

export async function groupAlertsIntoIncidents() {
  const { data } = await http.post<{ grouped_incidents: number }>("/api/incidents/group-alerts");
  return data.grouped_incidents;
}

export async function fetchIncidentComments(id: number) {
  const { data } = await http.get<IncidentComment[]>(`/api/incidents/${id}/comments`);
  return data;
}

export async function addIncidentComment(id: number, comment: string) {
  const { data } = await http.post<IncidentComment>(`/api/incidents/${id}/comments`, { comment });
  return data;
}