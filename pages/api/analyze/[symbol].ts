import type { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';
import redis from '@/lib/redis';
import { isAuthenticated } from '@/lib/auth';

export interface SpreadStrategy {
  found: boolean;
  spread_details?: {
    long_strike: number;
    short_strike: number;
    spread_width: number;
    spread_cost: number;
    max_profit: number;
    max_loss: number;
    breakeven_price: number;
    roi_percent: number;
    days_to_expiration: number;
    expiration_date: string;
  };
  contracts?: {
    long_contract: string;
    short_contract: string;
    long_price: number;
    short_price: number;
  };
  price_scenarios?: Array<{
    price_change_percent: number;
    future_stock_price: number;
    spread_value_at_expiration: number;
    profit_loss: number;
    roi_percent: number;
    outcome: string;
  }>;
  strategy_info?: {
    strategy_name: string;
    description: string;
    risk_level: string;
  };
}

export interface SpreadAnalysisResponse {
  success: boolean;
  ticker: string;
  timestamp: string;
  current_stock_price: number;
  strategies_found: number;
  strategies: {
    aggressive: SpreadStrategy;
    balanced: SpreadStrategy;
    conservative: SpreadStrategy;
  };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Check authentication
  if (!isAuthenticated(req.headers.authorization)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const { symbol } = req.query;

  if (!symbol || typeof symbol !== 'string') {
    return res.status(400).json({ error: 'Symbol parameter is required' });
  }

  try {
    const cacheKey = `spread_analysis_${symbol.toUpperCase()}`;
    
    // Check Redis cache first (3-minute expiry)
    const cachedData = await redis.get(cacheKey);
    if (cachedData) {
      console.log(`Cache HIT: Using cached spread data for ${symbol}`);
      return res.status(200).json(cachedData);
    }

    // Call external spread analysis API
    console.log(`Cache MISS: Calling external API for ${symbol}`);
    const externalApiUrl = 'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread';
    
    const response = await axios.post(externalApiUrl, {
      ticker: symbol.toUpperCase()
    }, {
      timeout: 30000
    });

    if (response.status === 200) {
      const spreadData: SpreadAnalysisResponse = response.data;
      
      // Cache the successful response for 3 minutes
      await redis.set(cacheKey, spreadData, 180);
      console.log(`Cached spread data for ${symbol} (3-minute expiry)`);
      
      return res.status(200).json(spreadData);
    } else {
      console.error(`External API returned status ${response.status} for ${symbol}`);
      return res.status(502).json({ error: 'External API error' });
    }

  } catch (error) {
    console.error('Spread analysis error:', error);
    
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return res.status(504).json({ error: 'External API timeout' });
      }
      return res.status(502).json({ error: 'External API unavailable' });
    }
    
    return res.status(500).json({ error: 'Internal server error' });
  }
}