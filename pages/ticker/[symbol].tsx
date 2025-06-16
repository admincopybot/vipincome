import React, { useState, useEffect } from 'react';
import { GetServerSideProps } from 'next';
import { useRouter } from 'next/router';
import axios from 'axios';
import { ETFData } from '@/lib/database';
import { SpreadAnalysisResponse } from '@/pages/api/analyze/[symbol]';

interface TickerPageProps {
  ticker: ETFData;
  isAuthenticated: boolean;
}

const TickerPage: React.FC<TickerPageProps> = ({ ticker, isAuthenticated }) => {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'step2' | 'step3' | 'step4'>('step2');
  const [spreadData, setSpreadData] = useState<SpreadAnalysisResponse | null>(null);
  const [loadingSpread, setLoadingSpread] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<'aggressive' | 'balanced' | 'conservative'>('aggressive');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/');
      return;
    }
  }, [isAuthenticated, router]);

  const loadSpreadData = async () => {
    if (spreadData) return; // Already loaded
    
    setLoadingSpread(true);
    try {
      const response = await axios.post(`/api/analyze/${ticker.symbol}`, {}, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
        }
      });
      
      if (response.status === 200) {
        setSpreadData(response.data);
      }
    } catch (error) {
      console.error('Failed to load spread data:', error);
    } finally {
      setLoadingSpread(false);
    }
  };

  const handleTabChange = (tab: 'step2' | 'step3' | 'step4') => {
    setActiveTab(tab);
    if (tab === 'step3' || tab === 'step4') {
      loadSpreadData();
    }
  };

  const renderCriteriaGrid = () => {
    const criteria = [
      { name: 'Trend1 (20-day EMA)', value: ticker.trend1_pass, description: '20-day exponential moving average trend' },
      { name: 'Trend2 (100-day EMA)', value: ticker.trend2_pass, description: '100-day exponential moving average trend' },
      { name: 'Snapback (RSI)', value: ticker.snapback_pass, description: 'Relative Strength Index momentum' },
      { name: 'Momentum (Weekly)', value: ticker.momentum_pass, description: 'Weekly momentum analysis' },
      { name: 'Stabilizing (ATR)', value: ticker.stabilizing_pass, description: 'Average True Range stability' },
    ];

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {criteria.map((criterion, index) => (
          <div key={index} className="bg-slate-700 rounded-lg p-4 border border-purple-500/20">
            <div className="flex items-center gap-3 mb-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                criterion.value ? 'bg-green-500' : 'bg-red-500'
              }`}>
                <span className="text-white text-xs font-bold">
                  {criterion.value ? '✓' : '✗'}
                </span>
              </div>
              <div className="font-semibold text-white">{criterion.name}</div>
            </div>
            <div className="text-gray-400 text-sm">{criterion.description}</div>
          </div>
        ))}
      </div>
    );
  };

  const renderStrategyCard = (strategy: 'aggressive' | 'balanced' | 'conservative') => {
    if (!spreadData || !spreadData.strategies[strategy]?.found) {
      return (
        <div className="bg-slate-700 rounded-lg p-6 border border-purple-500/20">
          <h3 className="text-xl font-bold text-white mb-4 capitalize">{strategy}</h3>
          <div className="text-gray-400">No {strategy} strategy available</div>
        </div>
      );
    }

    const strategyData = spreadData.strategies[strategy];
    const details = strategyData.spread_details!;
    const contracts = strategyData.contracts!;

    return (
      <div 
        className={`bg-slate-700 rounded-lg p-6 border cursor-pointer transition-all ${
          selectedStrategy === strategy 
            ? 'border-purple-400 bg-slate-600' 
            : 'border-purple-500/20 hover:border-purple-500/40'
        }`}
        onClick={() => setSelectedStrategy(strategy)}
      >
        <h3 className="text-xl font-bold text-white mb-4 capitalize">{strategy}</h3>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-400">DTE:</span>
            <span className="text-white font-semibold">{details.days_to_expiration} days</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">ROI:</span>
            <span className="text-green-400 font-semibold">{details.roi_percent.toFixed(1)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Max Profit:</span>
            <span className="text-white font-semibold">${details.max_profit.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Spread Cost:</span>
            <span className="text-white font-semibold">${details.spread_cost.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Strikes:</span>
            <span className="text-white font-semibold">${details.long_strike} / ${details.short_strike}</span>
          </div>
        </div>
      </div>
    );
  };

  const renderProfitMatrix = () => {
    if (!spreadData || !selectedStrategy || !spreadData.strategies[selectedStrategy]?.price_scenarios) {
      return <div className="text-gray-400">No profit scenarios available</div>;
    }

    const scenarios = spreadData.strategies[selectedStrategy].price_scenarios!;

    return (
      <div className="bg-slate-700 rounded-lg p-6 border border-purple-500/20">
        <h3 className="text-xl font-bold text-white mb-4">Profit Matrix at Expiration</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-purple-600 text-white">
                <th className="px-3 py-2 text-left">Price Change</th>
                <th className="px-3 py-2 text-left">Stock Price</th>
                <th className="px-3 py-2 text-left">Spread Value</th>
                <th className="px-3 py-2 text-left">Profit/Loss</th>
                <th className="px-3 py-2 text-left">ROI %</th>
                <th className="px-3 py-2 text-left">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((scenario, index) => (
                <tr key={index} className={`border-b border-slate-600 ${
                  scenario.outcome === 'profit' ? 'bg-green-900/20' : 'bg-red-900/20'
                }`}>
                  <td className="px-3 py-2 text-white">{scenario.price_change_percent}%</td>
                  <td className="px-3 py-2 text-white">${scenario.future_stock_price.toFixed(2)}</td>
                  <td className="px-3 py-2 text-white">${scenario.spread_value_at_expiration.toFixed(2)}</td>
                  <td className={`px-3 py-2 font-semibold ${
                    scenario.profit_loss >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    ${scenario.profit_loss.toFixed(2)}
                  </td>
                  <td className={`px-3 py-2 font-semibold ${
                    scenario.roi_percent >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {scenario.roi_percent.toFixed(1)}%
                  </td>
                  <td className={`px-3 py-2 font-semibold capitalize ${
                    scenario.outcome === 'profit' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {scenario.outcome}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 border-b border-purple-500/30 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/')}
                className="text-purple-400 hover:text-purple-300 transition-colors"
              >
                ← Back to Dashboard
              </button>
              <h1 className="text-3xl font-bold text-white">{ticker.symbol}</h1>
              <div className="bg-gradient-to-r from-yellow-400 to-orange-400 text-black px-3 py-1 rounded-full text-sm font-bold">
                VIP
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-green-400">
                ${ticker.current_price.toFixed(2)}
              </div>
              <div className="text-gray-400">
                Score: {ticker.score}/5
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-slate-800/30 border-b border-purple-500/20">
        <div className="container mx-auto px-6">
          <div className="flex gap-8">
            {[
              { id: 'step2', label: 'Step 2: Analysis' },
              { id: 'step3', label: 'Step 3: Strategies' },
              { id: 'step4', label: 'Step 4: Trade Details' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id as any)}
                className={`py-4 px-2 border-b-2 font-semibold transition-colors ${
                  activeTab === tab.id
                    ? 'border-purple-400 text-purple-400'
                    : 'border-transparent text-gray-400 hover:text-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-6 py-8">
        {activeTab === 'step2' && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Technical Analysis</h2>
              {renderCriteriaGrid()}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-slate-700 rounded-lg p-6 border border-purple-500/20">
                <h3 className="text-lg font-semibold text-white mb-2">Trading Volume</h3>
                <div className="text-2xl font-bold text-purple-400">
                  {ticker.trading_volume.toLocaleString()}
                </div>
              </div>
              
              <div className="bg-slate-700 rounded-lg p-6 border border-purple-500/20">
                <h3 className="text-lg font-semibold text-white mb-2">Options Contracts</h3>
                <div className="text-2xl font-bold text-purple-400">
                  {ticker.options_contracts_10_42_dte === 0 
                    ? 'Processing...' 
                    : ticker.options_contracts_10_42_dte.toLocaleString()
                  }
                </div>
              </div>
              
              <div className="bg-slate-700 rounded-lg p-6 border border-purple-500/20">
                <h3 className="text-lg font-semibold text-white mb-2">Last Updated</h3>
                <div className="text-lg text-purple-400">
                  {new Date(ticker.last_updated).toLocaleDateString()}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'step3' && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Income Strategies</h2>
              {loadingSpread ? (
                <div className="flex justify-center items-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                  <span className="ml-4 text-white">Analyzing spread opportunities...</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {renderStrategyCard('aggressive')}
                  {renderStrategyCard('balanced')}
                  {renderStrategyCard('conservative')}
                </div>
              )}
            </div>
            
            {spreadData && (
              <div>
                <h3 className="text-xl font-bold text-white mb-4">Selected Strategy: {selectedStrategy}</h3>
                {renderProfitMatrix()}
              </div>
            )}
          </div>
        )}

        {activeTab === 'step4' && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Trade Construction</h2>
              {loadingSpread ? (
                <div className="flex justify-center items-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                  <span className="ml-4 text-white">Loading trade details...</span>
                </div>
              ) : spreadData && spreadData.strategies[selectedStrategy]?.found ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <div className="bg-slate-700 rounded-lg p-6 border border-purple-500/20">
                    <h3 className="text-xl font-bold text-white mb-4">Trade Details</h3>
                    <div className="space-y-4">
                      {(() => {
                        const strategy = spreadData.strategies[selectedStrategy];
                        const details = strategy.spread_details!;
                        const contracts = strategy.contracts!;
                        
                        return (
                          <>
                            <div className="bg-green-900/30 border border-green-500/30 rounded-lg p-4">
                              <div className="font-semibold text-green-400 mb-2">BUY (Long Position)</div>
                              <div className="text-white">Buy the ${details.long_strike} {new Date(details.expiration_date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' })} Call</div>
                              <div className="text-gray-300 text-sm">Contract: {contracts.long_contract}</div>
                            </div>
                            
                            <div className="bg-red-900/30 border border-red-500/30 rounded-lg p-4">
                              <div className="font-semibold text-red-400 mb-2">SELL (Short Position)</div>
                              <div className="text-white">Sell the ${details.short_strike} {new Date(details.expiration_date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' })} Call</div>
                              <div className="text-gray-300 text-sm">Contract: {contracts.short_contract}</div>
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                  
                  <div className="bg-slate-700 rounded-lg p-6 border border-purple-500/20">
                    <h3 className="text-xl font-bold text-white mb-4">Risk/Reward Analysis</h3>
                    <div className="space-y-3">
                      {(() => {
                        const details = spreadData.strategies[selectedStrategy].spread_details!;
                        
                        return (
                          <>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Spread Width:</span>
                              <span className="text-white font-semibold">${details.spread_width.toFixed(0)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Spread Cost:</span>
                              <span className="text-white font-semibold">${details.spread_cost.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Max Profit:</span>
                              <span className="text-green-400 font-semibold">${details.max_profit.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Max Loss:</span>
                              <span className="text-red-400 font-semibold">${details.max_loss.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Breakeven:</span>
                              <span className="text-white font-semibold">${details.breakeven_price.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between border-t border-slate-600 pt-3">
                              <span className="text-gray-400">Target ROI:</span>
                              <span className="text-purple-400 font-bold text-lg">{details.roi_percent.toFixed(1)}%</span>
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-400">
                  No trade details available for selected strategy
                </div>
              )}
            </div>
            
            {spreadData && (
              <div>
                {renderProfitMatrix()}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export const getServerSideProps: GetServerSideProps = async (context) => {
  const { symbol } = context.params!;
  const { req } = context;
  const authHeader = req.headers.authorization;

  let isAuthenticated = false;
  let ticker = null;

  if (authHeader) {
    try {
      const response = await axios.get(`${process.env.NEXTAUTH_URL || 'http://localhost:3000'}/api/ticker/${symbol}`, {
        headers: {
          Authorization: authHeader
        }
      });
      
      if (response.status === 200) {
        isAuthenticated = true;
        ticker = response.data;
      }
    } catch (error) {
      console.error('Failed to fetch ticker:', error);
    }
  }

  if (!isAuthenticated || !ticker) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  return {
    props: {
      ticker,
      isAuthenticated
    }
  };
};

export default TickerPage;