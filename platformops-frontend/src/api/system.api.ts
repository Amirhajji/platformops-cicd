// src/api/system.api.ts
import { http } from "./http";

export async function pingAlerts() {
  const res = await http.get<{ ok: boolean }>("/api/alerts/ping");
  return res.data;
}
