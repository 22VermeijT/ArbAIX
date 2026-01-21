// Filter controls for opportunity list

import type { FilterState } from '../types';

interface FiltersProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
}

export function Filters({ filters, onChange }: FiltersProps) {
  const handleTypeChange = (type: FilterState['type']) => {
    onChange({ ...filters, type });
  };

  const handleRiskChange = (risk: FilterState['risk']) => {
    onChange({ ...filters, risk });
  };

  const handleMinProfitChange = (value: string) => {
    const minProfit = parseFloat(value) || 0;
    onChange({ ...filters, minProfit });
  };

  const handleSportChange = (sport: string) => {
    onChange({ ...filters, sport });
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">FILTERS</h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Type Filter */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Type</label>
          <select
            value={filters.type}
            onChange={(e) => handleTypeChange(e.target.value as FilterState['type'])}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Types</option>
            <option value="ARBITRAGE">Arbitrage</option>
            <option value="EV">+EV</option>
          </select>
        </div>

        {/* Risk Filter */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Risk</label>
          <select
            value={filters.risk}
            onChange={(e) => handleRiskChange(e.target.value as FilterState['risk'])}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Risks</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>
        </div>

        {/* Min Profit Filter */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Min Profit %</label>
          <input
            type="number"
            min="0"
            step="0.1"
            value={filters.minProfit || ''}
            onChange={(e) => handleMinProfitChange(e.target.value)}
            placeholder="0"
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Sport Filter */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Sport/Category</label>
          <input
            type="text"
            value={filters.sport}
            onChange={(e) => handleSportChange(e.target.value)}
            placeholder="All"
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>
    </div>
  );
}

export default Filters;
