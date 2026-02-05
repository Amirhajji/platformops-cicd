import { http } from "./http";

export type ComponentOverview = {
  component_code: string;
  health_score: number;
  active_alerts: number;
  status: "OK" | "DEGRADED" | "CRITICAL";
};

export async function fetchSystemOverview() {
  const { data } = await http.get<ComponentOverview[]>(
    "/api/system/overview"
  );
  return data;
}
