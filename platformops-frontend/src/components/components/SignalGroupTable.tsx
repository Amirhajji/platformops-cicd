// src/components/components/SignalGroupTable.tsx
import type { ComponentSignal } from '../../api/components.api';
import { useState } from 'react';
import { Search } from 'lucide-react';
import { PolarityIcon } from '../icons/PolarityIcon';

export function SignalGroupTable({
  signals,
  onSelectSignals,
}: {
  signals: ComponentSignal[];
  onSelectSignals: (codes: string[]) => void;
}) {
  const [search, setSearch] = useState('');
  const [openFamilies, setOpenFamilies] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<string[]>([]);

  const toggleFamily = (fam: string) => {
    const newSet = new Set(openFamilies);
    if (newSet.has(fam)) newSet.delete(fam);
    else newSet.add(fam);
    setOpenFamilies(newSet);
  };

  // Explicitly typed accumulator
  const groups = signals.reduce<Record<string, ComponentSignal[]>>((acc, s) => {
    const fam = s.family ?? 'unknown';
    if (!acc[fam]) acc[fam] = [];
    acc[fam].push(s);
    return acc;
  }, {});

  // Filter with explicit typing
  const filteredGroups: Record<string, ComponentSignal[]> = {};
  Object.entries(groups).forEach(([fam, sigs]) => {
    const filteredSigs = sigs.filter(
      (s) =>
        s.signal_code.toLowerCase().includes(search.toLowerCase()) ||
        s.description.toLowerCase().includes(search.toLowerCase())
    );
    if (filteredSigs.length > 0) {
      filteredGroups[fam] = filteredSigs;
    }
  });

  const toggleSelect = (code: string) => {
    const newSel = selected.includes(code)
      ? selected.filter((c) => c !== code)
      : [...selected, code];
    setSelected(newSel);
    onSelectSignals(newSel);
  };

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
        <input
          placeholder="Search signals..."
          className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-10 py-2 text-sm outline-none focus:border-zinc-600"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {Object.entries(filteredGroups).map(([family, sigs]) => (
        <div key={family} className="border border-zinc-800 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleFamily(family)}
            className="w-full flex justify-between items-center px-4 py-3 text-sm font-medium text-zinc-300 bg-zinc-900 hover:bg-zinc-800 transition"
          >
            <span>
              {family} <span className="text-zinc-500">({sigs.length})</span>
            </span>
            <span className="text-zinc-500">{openFamilies.has(family) ? '−' : '+'}</span>
          </button>

          {openFamilies.has(family) && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[600px]">
                <thead className="bg-zinc-950 border-b border-zinc-800 text-zinc-400">
                  <tr>
                    <th className="px-4 py-3 text-left w-10">Select</th>
                    <th className="px-4 py-3 text-left">Signal</th>
                    <th className="px-4 py-3 text-left">Type</th>
                    <th className="px-4 py-3 text-left">Unit</th>
                    <th className="px-4 py-3 text-left">Polarity</th>
                    <th className="px-4 py-3 text-left">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {sigs.map((s) => (
                    <tr
                      key={s.signal_code}
                      className="border-b border-zinc-800 last:border-0 hover:bg-zinc-800/50 transition"
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selected.includes(s.signal_code)}
                          onChange={() => toggleSelect(s.signal_code)}
                          className="rounded border-zinc-700 bg-zinc-950 text-emerald-500 focus:ring-emerald-500"
                        />
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">{s.signal_code}</td>
                      <td className="px-4 py-3 text-zinc-300">{s.type}</td>
                      <td className="px-4 py-3 text-zinc-300">{s.unit}</td>
                      <td className="px-4 py-3 flex items-center gap-1.5">
                        <span className="text-zinc-300">{s.polarity}</span>
                        <PolarityIcon polarity={s.polarity} trend="flat" />
                      </td>
                      <td className="px-4 py-3 text-zinc-400 max-w-md truncate" title={s.description}>
                        {s.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}