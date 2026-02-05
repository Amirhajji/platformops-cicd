// src/pages/auth/AuthLayout.tsx
import type { ReactNode } from "react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 grid grid-cols-1 lg:grid-cols-2">
      {/* Left branding / context */}
      <div className="hidden lg:flex flex-col justify-between border-r border-zinc-800 p-10">
        <div>
          <div className="text-2xl font-semibold tracking-tight">
            PlatformOPS
          </div>
          <div className="mt-2 text-sm text-zinc-400 max-w-md">
            Operational observability platform for cloud systems.
            <br />
            Alerts, incidents, anomalies, analytics — unified.
          </div>
        </div>

        <div className="text-xs text-zinc-500">
          © {new Date().getFullYear()} PlatformOPS — Internal Systems Console
        </div>
      </div>

      {/* Right auth panel */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
