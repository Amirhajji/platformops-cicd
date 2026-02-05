// src/pages/analytics/AnalyticsPage.tsx (main page with tabs)
import { useState } from 'react';
import { HealthSection } from '../../components/analytics/HealthSection';
import { VolatilitySection } from '../../components/analytics/VolatilitySection';
import { ForecastSection } from '../../components/analytics/ForecastSection';
import { RegimesSection } from '../../components/analytics/RegimesSection';
import { StressSection } from '../../components/analytics/StressSection';
import { ChangeImpactSection } from '../../components/analytics/ChangeImpactSection';
import { SystemStatsSection } from '../../components/analytics/SystemStatsSection';
import { AlertsStatsSection } from '../../components/analytics/AlertsStatsSection';
import { ComponentRankingsSection } from '../../components/analytics/ComponentRankingsSection';
import { SignalCoverageSection } from '../../components/analytics/SignalCoverageSection';
import { ActiveHotspotsSection } from '../../components/analytics/ActiveHotspotsSection';
import { ComponentTimeAnalysisSection } from '../../components/analytics/ComponentTimeAnalysisSection';
import { SignalEnvelopeSection } from '../../components/analytics/SignalEnvelopeSection';
import { useTimeWindow } from '../../context/TimeContext';

export function AnalyticsPage() {
  const { window } = useTimeWindow();
  const [activeTab, setActiveTab] = useState('health');

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-zinc-100">Analytics Console</h1>

      <p className="text-sm text-zinc-400 max-w-2xl">
        Advanced insights: health trends, volatility, forecasts, regimes, stress curves, change impact. Time window: {window.fromTick} → {window.toTick}.
      </p>

      {/* Tabs */}
      <div className="border-b border-zinc-800 overflow-x-auto">
        <div className="flex space-x-4 pb-2">
          {['health', 'volatility', 'forecast', 'regimes', 'stress', 'change-impact', 'system-stats', 'alerts-stats', 'component-rankings', 'signal-coverage', 'active-hotspots', 'time-analysis', 'signal-envelope'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab
                  ? 'border-b-2 border-zinc-200 text-zinc-100'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Sections */}
      {activeTab === 'health' && <HealthSection />}
      {activeTab === 'volatility' && <VolatilitySection />}
      {activeTab === 'forecast' && <ForecastSection />}
      {activeTab === 'regimes' && <RegimesSection />}
      {activeTab === 'stress' && <StressSection />}
      {activeTab === 'change-impact' && <ChangeImpactSection />}
      {activeTab === 'system-stats' && <SystemStatsSection />}
      {activeTab === 'alerts-stats' && <AlertsStatsSection />}
      {activeTab === 'component-rankings' && <ComponentRankingsSection />}
      {activeTab === 'signal-coverage' && <SignalCoverageSection />}
      {activeTab === 'active-hotspots' && <ActiveHotspotsSection />}
      {activeTab === 'time-analysis' && <ComponentTimeAnalysisSection />}
      {activeTab === 'signal-envelope' && <SignalEnvelopeSection />}
    </div>
  );
}