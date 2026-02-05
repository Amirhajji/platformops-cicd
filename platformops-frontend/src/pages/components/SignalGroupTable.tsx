// src/pages/components/SignalGroupTable.tsx
import { useState } from 'react';
import type { ComponentSignal } from '../../api/components.api';

export function SignalGroupTable({ signals, onSelectSignals }: { signals: ComponentSignal[]; onSelectSignals: (codes: string[]) => void }) {
  const groups = signals.reduce((acc: Record<string, ComponentSignal[]>, s) => {
    const fam = s.family ?? 'unknown';
    acc[fam] = [...(acc[fam] || []), s];
    return acc;
  }, {});

  const [selected, setSelected] = useState<string[]>([]);

  const toggleSelect = (code: string) => {
    const newSel = selected.includes(code) ? selected.filter(c => c !== code) : [...selected, code];
    setSelected(newSel);
    onSelectSignals(newSel);
  };

  return (
    <div className="space-y-4">
      {Object.entries(groups).map(([family, sigs]) => (
        <div key={family}>
          <h3 className="text-sm font-medium uppercase text-zinc-500">{family}</h3>
          <table className="w-full text-sm mt-2 rounded-xl border border-zinc-800 bg-zinc-900">
            <thead className="border-b border-zinc-800 text-zinc-400">
              <tr>
                <th className="px-4 py-2 text-left">Select</th>
                <th className="px-4 py-2 text-left">Signal</th>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Unit</th>
                <th className="px-4 py-2 text-left">Polarity</th>
                <th className="px-4 py-2 text-left">Description</th>
              </tr>
            </thead>
            <tbody>
              {sigs.map(s => (
                <tr key={s.signal_code} className="border-b border-zinc-800 last:border-0">
                  <td className="px-4 py-2">
                    <input type="checkbox" checked={selected.includes(s.signal_code)} onChange={() => toggleSelect(s.signal_code)} />
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">{s.signal_code}</td>
                  <td className="px-4 py-2">{s.type}</td>
                  <td className="px-4 py-2">{s.unit}</td>
                  <td className="px-4 py-2">{s.polarity}</td>
                  <td className="px-4 py-2 text-zinc-400">{s.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}