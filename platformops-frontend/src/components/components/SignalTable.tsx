import type { ComponentSignal } from "../../api/components.api";

// src/components/components/SignalTable.tsx
export function SignalTable({ signals }: { signals: ComponentSignal[] }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900">
      <table className="w-full text-sm">
        <thead className="border-b border-zinc-800 text-zinc-400">
          <tr>
            <th className="px-4 py-3 text-left">Signal</th>
            <th className="px-4 py-3 text-left">Type</th>
            <th className="px-4 py-3 text-left">Unit</th>
            <th className="px-4 py-3 text-left">Polarity</th>
            <th className="px-4 py-3 text-left">Description</th>
          </tr>
        </thead>

        <tbody>
          {signals.map((s) => (
            <tr
              key={s.signal_code}
              className="border-b border-zinc-800 last:border-0"
            >
              <td className="px-4 py-3 font-mono text-xs">
                {s.signal_code}
              </td>
              <td className="px-4 py-3">{s.type}</td>
              <td className="px-4 py-3">{s.unit}</td>
              <td className="px-4 py-3">{s.polarity}</td>
              <td className="px-4 py-3 text-zinc-400">
                {s.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
