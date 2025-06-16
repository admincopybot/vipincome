import React from 'react';
import { ETFData } from '@/lib/database';

interface TickerCardProps {
  ticker: ETFData;
  rank: number;
  onSelect: (symbol: string) => void;
}

const TickerCard: React.FC<TickerCardProps> = ({ ticker, rank, onSelect }) => {
  const criteriaIcons = [
    { name: 'Trend1', value: ticker.trend1_pass },
    { name: 'Trend2', value: ticker.trend2_pass },
    { name: 'Snapback', value: ticker.snapback_pass },
    { name: 'Momentum', value: ticker.momentum_pass },
    { name: 'Stabilizing', value: ticker.stabilizing_pass },
  ];

  const getRankBadgeColor = (rank: number) => {
    if (rank <= 3) return 'bg-gradient-to-r from-yellow-400 to-orange-400';
    return 'bg-gradient-to-r from-purple-600 to-purple-700';
  };

  const getContractsBadgeColor = (contracts: number) => {
    if (contracts === 0) return 'bg-gray-600';
    if (contracts >= 300) return 'bg-green-600';
    if (contracts >= 200) return 'bg-blue-600';
    if (contracts >= 100) return 'bg-yellow-600';
    return 'bg-red-600';
  };

  return (
    <div 
      className="bg-slate-800 border border-purple-500/30 rounded-xl p-6 hover:border-purple-400/60 transition-all duration-300 cursor-pointer hover:transform hover:scale-105"
      onClick={() => onSelect(ticker.symbol)}
    >
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1 rounded-full text-white font-bold text-sm ${getRankBadgeColor(rank)}`}>
            #{rank}
          </div>
          <h3 className="text-2xl font-bold text-white">{ticker.symbol}</h3>
          <div className="bg-purple-600 text-white px-2 py-1 rounded text-xs font-semibold">
            VIP
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-green-400">
            ${ticker.current_price.toFixed(2)}
          </div>
          <div className="text-gray-400 text-sm">
            Score: {ticker.score}/5
          </div>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-2 mb-4">
        {criteriaIcons.map((criteria, index) => (
          <div key={index} className="text-center">
            <div className={`w-8 h-8 rounded-full mx-auto mb-1 flex items-center justify-center ${
              criteria.value ? 'bg-green-500' : 'bg-gray-600'
            }`}>
              <span className="text-white text-xs font-bold">
                {criteria.value ? '✓' : '✗'}
              </span>
            </div>
            <div className="text-xs text-gray-400">{criteria.name}</div>
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center">
        <div className="text-gray-400 text-sm">
          Volume: {ticker.trading_volume.toLocaleString()}
        </div>
        <div className={`px-2 py-1 rounded text-xs font-semibold text-white ${getContractsBadgeColor(ticker.options_contracts_10_42_dte)}`}>
          {ticker.options_contracts_10_42_dte === 0 
            ? 'Processing...' 
            : `${ticker.options_contracts_10_42_dte} Contracts`
          }
        </div>
      </div>
    </div>
  );
};

export default TickerCard;