// Main application component

import { useState, useEffect, useCallback } from 'react';
import type { Opportunity, FilterState, WSMessage, Stats } from './types';
import { fetchOpportunities, fetchStats, fetchSources, triggerScan, wsManager, Source } from './api';
import { Disclaimer } from './components/Disclaimer';
import { Filters } from './components/Filters';
import { OpportunityTable } from './components/OpportunityTable';
import { OpportunityCard } from './components/OpportunityCard';
import { Sources } from './components/Sources';

function App() {
  // State
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    type: 'all',
    minProfit: 0,
    risk: 'all',
    sport: '',
  });

  // Fetch opportunities with current filters
  const refreshOpportunities = useCallback(async () => {
    try {
      const data = await fetchOpportunities(filters);
      setOpportunities(data.opportunities);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to fetch opportunities:', err);
    }
  }, [filters]);

  // Fetch stats
  const refreshStats = useCallback(async () => {
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, []);

  // Fetch sources
  const refreshSources = useCallback(async () => {
    try {
      const data = await fetchSources();
      setSources(data.sources);
    } catch (err) {
      console.error('Failed to fetch sources:', err);
    }
  }, []);

  // Manual scan trigger
  const handleManualScan = async () => {
    setLoading(true);
    try {
      await triggerScan();
      await Promise.all([refreshOpportunities(), refreshStats(), refreshSources()]);
    } catch (err) {
      console.error('Failed to trigger scan:', err);
    }
    setLoading(false);
  };

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([refreshOpportunities(), refreshStats(), refreshSources()]);
      setLoading(false);
    };
    init();
  }, [refreshOpportunities, refreshStats, refreshSources]);

  // WebSocket connection - only connect once on mount
  useEffect(() => {
    wsManager.onStatusChange(setConnected);

    wsManager.onMessage((data: unknown) => {
      const msg = data as WSMessage;

      if (msg.type === 'scan_result' || msg.type === 'initial_opportunities') {
        if (msg.opportunities) {
          setOpportunities(msg.opportunities);
          setLastUpdate(new Date());
        }
      }
    });

    wsManager.connect();

    return () => {
      wsManager.disconnect();
    };
  }, []); // Empty dependency - connect once

  // Refresh when filters change
  useEffect(() => {
    refreshOpportunities();
  }, [filters, refreshOpportunities]);

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white">
                Arbitrage Intelligence Platform
              </h1>
              <p className="text-sm text-gray-400">
                Cross-market odds analysis & advisory
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* Connection Status */}
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    connected ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className="text-sm text-gray-400">
                  {connected ? 'Live' : 'Disconnected'}
                </span>
              </div>

              {/* Last Update */}
              {lastUpdate && (
                <span className="text-sm text-gray-500">
                  Updated: {lastUpdate.toLocaleTimeString()}
                </span>
              )}

              {/* Manual Scan */}
              <button
                onClick={handleManualScan}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded text-sm font-medium transition-colors"
              >
                {loading ? 'Scanning...' : 'Scan Now'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Disclaimer */}
        <Disclaimer />

        {/* Stats Bar */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-sm text-gray-500">Scanner</p>
              <p className={`text-lg font-semibold ${stats.scanner_running ? 'text-green-400' : 'text-red-400'}`}>
                {stats.scanner_running ? 'Running' : 'Stopped'}
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-sm text-gray-500">Markets</p>
              <p className="text-lg font-semibold">{stats.total_markets}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-sm text-gray-500">Arbitrage</p>
              <p className="text-lg font-semibold text-green-400">{stats.arbitrage_count}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-sm text-gray-500">+EV</p>
              <p className="text-lg font-semibold text-blue-400">{stats.ev_count}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-sm text-gray-500">Avg Profit</p>
              <p className="text-lg font-semibold text-green-400">
                {stats.average_profit_pct.toFixed(2)}%
              </p>
            </div>
          </div>
        )}

        {/* Data Sources */}
        {sources.length > 0 && <Sources sources={sources} />}

        {/* Filters */}
        <Filters filters={filters} onChange={setFilters} />

        {/* Selected Opportunity Detail */}
        {selectedOpportunity && (
          <OpportunityCard
            opportunity={selectedOpportunity}
            onClose={() => setSelectedOpportunity(null)}
          />
        )}

        {/* Opportunities Table */}
        <div>
          <h2 className="text-lg font-semibold mb-4">
            Opportunities ({opportunities.length})
          </h2>
          <OpportunityTable
            opportunities={opportunities}
            onSelect={setSelectedOpportunity}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 border-t border-gray-700 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
          Advisory Only - No bets placed automatically - Gamble responsibly
        </div>
      </footer>
    </div>
  );
}

export default App;
