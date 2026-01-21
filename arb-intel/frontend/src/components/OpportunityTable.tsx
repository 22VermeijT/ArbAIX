// Table view of opportunities

import type { Opportunity } from '../types';

interface OpportunityTableProps {
  opportunities: Opportunity[];
  onSelect: (opportunity: Opportunity) => void;
}

export function OpportunityTable({ opportunities, onSelect }: OpportunityTableProps) {
  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'LOW': return 'text-green-400';
      case 'MEDIUM': return 'text-yellow-400';
      case 'HIGH': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ARBITRAGE': return 'bg-green-600/20 text-green-400';
      case 'EV': return 'bg-blue-600/20 text-blue-400';
      default: return 'bg-gray-600/20 text-gray-400';
    }
  };

  if (opportunities.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center">
        <p className="text-gray-400">No opportunities found</p>
        <p className="text-sm text-gray-500 mt-2">
          Adjust your filters or wait for the next scan cycle
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Profit</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Event</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Risk</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Venues</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Expires</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {opportunities.map((opp, idx) => (
              <tr
                key={`${opp.event_id}-${idx}`}
                onClick={() => onSelect(opp)}
                className="hover:bg-gray-700/50 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${getTypeColor(opp.type)}`}>
                    {opp.type.slice(0, 3)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-green-400 font-semibold">
                    +{opp.profit_pct.toFixed(2)}%
                  </span>
                  <span className="text-gray-500 text-sm ml-2">
                    (${opp.profit_usd.toFixed(2)})
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="max-w-xs truncate" title={opp.event_name}>
                    {opp.event_name}
                  </div>
                  <div className="text-xs text-gray-500">{opp.market_type}</div>
                </td>
                <td className="px-4 py-3">
                  <span className={getRiskColor(opp.risk)}>{opp.risk}</span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-400">
                  {[...new Set(opp.instructions.map(i => i.venue))].join(' / ')}
                </td>
                <td className="px-4 py-3 text-sm text-yellow-400">
                  ~{opp.expires_in_seconds}s
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default OpportunityTable;
