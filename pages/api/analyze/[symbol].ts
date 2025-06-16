import type { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';
import { isAuthenticated } from '@/lib/auth';
import { getCachedData, setCachedData } from '@/lib/redis';

export interface SpreadDetails {
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
}

export interface SpreadContracts {
  long_contract: string;
  short_contract: string;
}

export interface PriceScenario {
  price_change_percent: string;
  future_stock_price: number;
  spread_value_at_expiration: number;
  profit_loss: number;
  roi_percent: number;
  outcome: 'profit' | 'loss';
}

export interface StrategyData {
  found: boolean;
  spread_details?: SpreadDetails;
  contracts?: SpreadContracts;
  price_scenarios?: PriceScenario[];
}

export interface SpreadAnalysisResponse {
  success: boolean;
  ticker: string;
  timestamp: string;
  strategies: {
    aggressive: StrategyData;
    balanced: StrategyData;
    conservative: StrategyData;
  };
}

const EXTERNAL_API_URL = 'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Validate JWT authentication
  const user = isAuthenticated(req);
  if (!user) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const { symbol } = req.query;
  
  if (!symbol || typeof symbol !== 'string') {
    return res.status(400).json({ error: 'Invalid symbol' });
  }

  const cacheKey = `spread_analysis:${symbol.toUpperCase()}`;
  
  try {
    // Check Redis cache first
    const cachedData = await getCachedData<SpreadAnalysisResponse>(cacheKey);
    if (cachedData) {
      return res.status(200).json(cachedData);
    }

    // Call external spread analysis API
    const response = await axios.post(EXTERNAL_API_URL, {
      ticker: symbol.toUpperCase()
    }, {
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (response.status === 200 && response.data.success) {
      const spreadData = response.data as SpreadAnalysisResponse;
      
      // Cache the result for 3 minutes
      await setCachedData(cacheKey, spreadData, 180);
      
      return res.status(200).json(spreadData);
    } else {
      return res.status(500).json({ 
        error: 'Failed to analyze spreads',
        details: response.data 
      });
    }
  } catch (error) {
    console.error('Spread analysis error:', error);
    
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return res.status(408).json({ error: 'Request timeout' });
      }
      if (error.response) {
        return res.status(error.response.status).json({ 
          error: 'External API error',
          details: error.response.data 
        });
      }
    }
    
    return res.status(500).json({ error: 'Internal server error' });
  }
}