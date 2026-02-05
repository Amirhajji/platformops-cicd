// src/pages/anomalies/AnomaliesPage.tsx
import { useState } from 'react';
import { AnomalyActions } from '../../components/anomalies/AnomalyActions';
import { InjectionForm } from '../../components/anomalies/InjectionForm';
import { ActiveAnomalyCard } from '../../components/anomalies/ActiveAnomalyCard';
import { ImpactSummaryTable } from '../../components/anomalies/ImpactSummaryTable';
import { AnalysisNarrative } from '../../components/anomalies/AnalysisNarrative';
import { HealthRankingTable } from '../../components/anomalies/HealthRankingTable';
import { DeviationChart } from '../../components/anomalies/DeviationChart';


export function AnomaliesPage() {
  const [activeTab, setActiveTab] = useState('active');

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Anomalies Lab</h1>
        <AnomalyActions />
      </div>

      <p className="text-sm text-zinc-400">Inject, monitor, analyze anomalies in a controlled environment. Observe propagation, impacts, and system resilience.</p>

      {/* Tabs */}
      <div className="border-b border-zinc-800">
        <div className="flex space-x-1">
          {['injection', 'active', 'impact', 'analysis'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'border-b-2 border-zinc-200 text-zinc-100'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'injection' && <InjectionForm />}
      {activeTab === 'active' && <ActiveAnomalyCard />}
      {activeTab === 'impact' && <ImpactSummaryTable />}
      {activeTab === 'analysis' && (
        <div className="space-y-8">
          <AnalysisNarrative />
          <DeviationChart />
          <HealthRankingTable />
        </div>
      )}
    </div>
  );
}