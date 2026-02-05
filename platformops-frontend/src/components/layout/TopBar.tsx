import { useAuth } from "../../auth/auth.store";
import { useTimeWindow } from "../../context/TimeContext";

export function TopBar() {
  const { user, clearSession } = useAuth();
  const { window } = useTimeWindow();

  return (
    <header className="flex h-14 items-center justify-between border-b border-zinc-800 px-6">
      <div className="text-sm text-zinc-400">
        Ticks:{" "}
        <span className="text-zinc-200">
          {window.fromTick} → {window.toTick}
        </span>
      </div>

      <div className="flex items-center gap-4 text-sm">
        {/* placeholders – wired later */}
        <span className="rounded-md bg-emerald-950/40 px-2 py-1 text-emerald-400">
          HEALTH: OK
        </span>

        <span className="text-zinc-400">
          {user?.username} ({user?.roles?.join(", ")})
        </span>

        <button
          onClick={clearSession}
          className="text-zinc-400 hover:text-zinc-100"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
