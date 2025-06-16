import React, { useState, useEffect } from 'react';
import { GetServerSideProps } from 'next';
import { useRouter } from 'next/router';
import TickerCard from '@/components/TickerCard';
import { ETFData } from '@/lib/database';
import axios from 'axios';

interface DashboardProps {
  initialTickers: ETFData[];
  isAuthenticated: boolean;
}

const Dashboard: React.FC<DashboardProps> = ({ initialTickers, isAuthenticated }) => {
  const router = useRouter();
  const [tickers, setTickers] = useState<ETFData[]>(initialTickers);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredTickers, setFilteredTickers] = useState<ETFData[]>(initialTickers);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      // Redirect to access screen or show login prompt
      return;
    }
  }, [isAuthenticated]);

  useEffect(() => {
    // Filter tickers based on search term
    if (searchTerm.trim() === '') {
      setFilteredTickers(tickers);
    } else {
      const filtered = tickers.filter(ticker =>
        ticker.symbol.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredTickers(filtered);
    }
  }, [searchTerm, tickers]);

  const handleTickerSelect = (symbol: string) => {
    router.push(`/ticker/${symbol}`);
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="bg-slate-800 border border-purple-500/30 rounded-xl p-8 max-w-md">
          <div className="text-center">
            <div className="bg-gradient-to-r from-purple-600 to-purple-700 text-white px-4 py-2 rounded-full inline-block mb-4">
              VIP ACCESS REQUIRED
            </div>
            <h1 className="text-2xl font-bold text-white mb-4">Income Machine</h1>
            <p className="text-gray-300 mb-6">
              VIP access required. Please authenticate through OneClick Trading to access the Income Machine.
            </p>
            <a
              href="https://oneclick.trading"
              className="bg-gradient-to-r from-purple-600 to-purple-700 text-white px-6 py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-purple-800 transition-all"
            >
              Access OneClick Trading
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 border-b border-purple-500/30 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <h1 className="text-3xl font-bold text-white">Income Machine</h1>
              <div className="bg-gradient-to-r from-yellow-400 to-orange-400 text-black px-3 py-1 rounded-full text-sm font-bold">
                VIP
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search tickers..."
                  value={searchTerm}
                  onChange={handleSearch}
                  className="bg-slate-700 border border-purple-500/30 rounded-lg px-4 py-2 text-white placeholder-gray-400 focus:outline-none focus:border-purple-400 w-64"
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Top Trade Opportunities</h2>
          <p className="text-gray-300">
            {filteredTickers.length} tickers available • All tickers accessible with VIP access
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredTickers.map((ticker, index) => (
              <TickerCard
                key={ticker.symbol}
                ticker={ticker}
                rank={index + 1}
                onSelect={handleTickerSelect}
              />
            ))}
          </div>
        )}

        {filteredTickers.length === 0 && searchTerm && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg">
              No tickers found matching "{searchTerm}"
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-slate-800/30 border-t border-purple-500/30 mt-12">
        <div className="container mx-auto px-6 py-6">
          <div className="text-center text-gray-400 text-sm">
            Income Machine VIP • Real-time ETF analysis and options strategy generation
          </div>
        </div>
      </div>
    </div>
  );
};

export const getServerSideProps: GetServerSideProps = async (context) => {
  const { req } = context;
  const authHeader = req.headers.authorization;

  // Check JWT authentication
  let isAuthenticated = false;
  let tickers: ETFData[] = [];

  if (authHeader) {
    try {
      const response = await axios.get(`${process.env.NEXTAUTH_URL || 'http://localhost:3000'}/api/tickers`, {
        headers: {
          Authorization: authHeader
        }
      });
      
      if (response.status === 200) {
        isAuthenticated = true;
        tickers = response.data;
      }
    } catch (error) {
      console.error('Authentication failed:', error);
    }
  }

  return {
    props: {
      initialTickers: tickers,
      isAuthenticated
    }
  };
};

export default Dashboard;