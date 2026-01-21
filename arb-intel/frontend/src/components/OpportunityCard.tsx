// Detailed opportunity card with bet instructions

import type { Opportunity } from '../types';

interface OpportunityCardProps {
  opportunity: Opportunity;
  onClose: () => void;
}

export function OpportunityCard({ opportunity, onClose }: OpportunityCardProps) {
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
      case 'ARBITRAGE': return 'bg-green-600';
      case 'EV': return 'bg-blue-600';
      default: return 'bg-gray-600';
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-900 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`px-2 py-1 rounded text-xs font-semibold ${getTypeColor(opportunity.type)}`}>
            {opportunity.type}
          </span>
          <span className="text-lg font-bold text-green-400">
            +{opportunity.profit_pct.toFixed(2)}%
          </span>
          <span className="text-gray-400">
            (${opportunity.profit_usd.toFixed(2)})
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 text-xl"
        >
          X
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Event Info */}
        <div>
          <h3 className="text-lg font-semibold">{opportunity.event_name}</h3>
          <p className="text-sm text-gray-400">
            {opportunity.market_type} | Risk: <span className={getRiskColor(opportunity.risk)}>{opportunity.risk}</span>
          </p>
        </div>

        {/* Instructions */}
        <div className="bg-gray-900 rounded p-4">
          <h4 className="text-sm font-semibold text-gray-400 mb-3">BET INSTRUCTIONS</h4>
          <div className="space-y-3">
            {opportunity.instructions.map((inst, idx) => (
              <div key={idx} className="flex items-start gap-3">
                <span className="bg-blue-600 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm flex-shrink-0">
                  {inst.step}
                </span>
                <div className="flex-1">
                  <p className="font-medium">
                    Bet <span className="text-green-400">${inst.stake_usd.toFixed(2)}</span> on{' '}
                    <span className="text-blue-300">{inst.outcome}</span>
                  </p>
                  <p className="text-sm text-gray-400">
                    at {inst.venue.charAt(0).toUpperCase() + inst.venue.slice(1)} ({inst.odds_american})
                  </p>
                  <p className="text-xs text-gray-500">
                    Potential payout: ${inst.potential_payout.toFixed(2)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="bg-gray-900 rounded p-3">
            <p className="text-gray-500">Total Stake</p>
            <p className="text-lg font-semibold">${opportunity.total_stake.toFixed(2)}</p>
          </div>
          <div className="bg-gray-900 rounded p-3">
            <p className="text-gray-500">Expected Profit</p>
            <p className="text-lg font-semibold text-green-400">${opportunity.profit_usd.toFixed(2)}</p>
          </div>
          <div className="bg-gray-900 rounded p-3">
            <p className="text-gray-500">Fees</p>
            <p className="text-lg font-semibold">${opportunity.fees_usd.toFixed(2)}</p>
          </div>
          <div className="bg-gray-900 rounded p-3">
            <p className="text-gray-500">Expires In</p>
            <p className="text-lg font-semibold text-yellow-400">~{opportunity.expires_in_seconds}s</p>
          </div>
        </div>

        {/* Raw Text */}
        <details className="text-sm">
          <summary className="cursor-pointer text-gray-500 hover:text-gray-300">
            View formatted instructions
          </summary>
          <pre className="mt-2 bg-gray-900 rounded p-4 text-xs overflow-x-auto whitespace-pre-wrap">
            {opportunity.formatted_text}
          </pre>
        </details>
      </div>
    </div>
  );
}

export default OpportunityCard;
