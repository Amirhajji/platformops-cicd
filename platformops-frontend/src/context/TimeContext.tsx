// src/context/TimeContext.tsx
import { createContext, useContext, useState, useMemo } from "react";

export type TimeWindow = {
  fromTick: number;
  toTick: number;
};

type TimeContextValue = {
  window: TimeWindow;
  setWindow: (w: TimeWindow) => void;
};

const TimeContext = createContext<TimeContextValue | null>(null);

export function TimeProvider({ children }: { children: React.ReactNode }) {
  // default: last N ticks (placeholder, backend-driven later)
  const [window, setWindow] = useState<TimeWindow>({
    fromTick: 0,
    toTick: 500,
  });

  const value = useMemo(
    () => ({ window, setWindow }),
    [window]
  );

  return (
    <TimeContext.Provider value={value}>
      {children}
    </TimeContext.Provider>
  );
}

export function useTimeWindow() {
  const ctx = useContext(TimeContext);
  if (!ctx) {
    throw new Error("useTimeWindow must be used inside TimeProvider");
  }
  return ctx;
}
