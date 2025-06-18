import { spawn } from 'child_process';
import path from 'path';

export default async function handler(req, res) {
  // Enhanced CORS handling for Vercel serverless
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
  res.setHeader('Access-Control-Max-Age', '86400'); // 24 hours
  
  // Handle OPTIONS preflight request
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    console.log('=== VERCEL INTEGRATED SPREAD ANALYSIS START ===');
    console.log('Request method:', req.method);
    console.log('Request headers:', req.headers);
    console.log('Raw request body:', req.body);
    
    // Parse request body
    let requestData;
    if (typeof req.body === 'string') {
      requestData = JSON.parse(req.body);
    } else {
      requestData = req.body || {};
    }

    const { ticker } = requestData;
    
    if (!ticker) {
      console.log('ERROR: No ticker provided');
      return res.status(400).json({
        error: 'Ticker symbol is required',
        received: requestData
      });
    }

    console.log(`Running integrated spread analysis for ticker: ${ticker}`);
    
    // Check for required environment variable
    if (!process.env.TRADELIST_API_KEY) {
      console.error('TRADELIST_API_KEY environment variable not set');
      return res.status(500).json({
        error: 'Analysis service not configured',
        message: 'Missing API configuration. Please contact support.',
        ticker: ticker
      });
    }
    
    // Run debit spread analysis directly in JavaScript
    const analyzer = new DebitSpreadAnalyzer(process.env.TRADELIST_API_KEY);
    const result = await analyzer.analyzeDebitSpread(ticker);
    
    console.log('Analysis result:', JSON.stringify(result, null, 2));
    
    if (result.success) {
      res.status(200).json(result);
    } else {
      res.status(400).json(result);
    }
    
  } catch (error) {
    console.error('=== INTEGRATED ANALYSIS ERROR ===');
    console.error('Error name:', error.name);
    console.error('Error message:', error.message);
    console.error('Error stack:', error.stack);
    
    if (error.message.includes('timeout')) {
      return res.status(408).json({
        error: 'Analysis timeout',
        message: 'The analysis is taking longer than expected. Please try again.',
        ticker: req.body?.ticker || 'unknown'
      });
    }
    
    return res.status(500).json({
      error: 'Analysis error',
      message: 'An error occurred during spread analysis.',
      details: error.message,
      ticker: req.body?.ticker || 'unknown'
    });
  }
}

/**
 * JavaScript implementation of the Debit Spread Analyzer
 * Replicates the functionality of your Python analyzer
 */
class DebitSpreadAnalyzer {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.strategyConfigs = {
      aggressive: { roi_min: 25, roi_max: 50, dte_min: 10, dte_max: 17 },
      balanced: { roi_min: 12, roi_max: 25, dte_min: 17, dte_max: 28 },
      conservative: { roi_min: 8, roi_max: 15, dte_min: 28, dte_max: 42 }
    };
  }

  async analyzeDebitSpread(ticker) {
    try {
      console.log(`Starting analysis for ${ticker}`);
      
      // Get current stock price
      const currentPrice = await this.getRealTimeStockPrice(ticker);
      if (!currentPrice) {
        return {
          success: false,
          error: 'Unable to fetch current stock price',
          ticker: ticker
        };
      }

      console.log(`Current price for ${ticker}: $${currentPrice}`);

      // Get options contracts
      const contracts = await this.getAllContracts(ticker);
      if (!contracts || contracts.length === 0) {
        return {
          success: false,
          error: 'No options contracts found',
          ticker: ticker
        };
      }

      console.log(`Found ${contracts.length} options contracts`);

      // Find best spreads for each strategy
      const strategies = await this.findBestSpreads(ticker, currentPrice, contracts);

      const response = {
        success: true,
        ticker: ticker,
        current_stock_price: currentPrice,
        strategies_found: Object.values(strategies).filter(s => s.found).length,
        strategies: strategies
      };

      return response;

    } catch (error) {
      console.error(`Analysis error for ${ticker}:`, error);
      return {
        success: false,
        error: `Analysis failed: ${error.message}`,
        ticker: ticker
      };
    }
  }

  async getRealTimeStockPrice(symbol) {
    try {
      // Use TheTradeList snapshot API (same as Python version)
      const url = 'https://api.thetradelist.com/v1/data/snapshot-locale';
      const params = new URLSearchParams({
        tickers: `${symbol},`,
        apiKey: this.apiKey
      });

      const response = await fetch(`${url}?${params}`, { timeout: 5000 });
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.status === 'OK' && data.tickers) {
          for (const tickerData of data.tickers) {
            if (tickerData.ticker === symbol && tickerData.fmv > 0) {
              return parseFloat(tickerData.fmv);
            }
          }
        }
      }

      // Fallback to scanner data
      const scannerUrl = 'https://api.thetradelist.com/v1/data/get_trader_scanner_data.php';
      const scannerParams = new URLSearchParams({
        apiKey: this.apiKey,
        returntype: 'json'
      });

      const scannerResponse = await fetch(`${scannerUrl}?${scannerParams}`, { timeout: 15000 });
      
      if (scannerResponse.ok) {
        const scannerData = await scannerResponse.json();
        
        for (const item of scannerData) {
          if (item.symbol === symbol && item.price > 0) {
            return parseFloat(item.price);
          }
        }
      }

      return null;
    } catch (error) {
      console.error(`Price fetch error for ${symbol}:`, error);
      return null;
    }
  }

  async getAllContracts(symbol) {
    try {
      const url = 'https://api.thetradelist.com/v1/data/options';
      const params = new URLSearchParams({
        symbol: symbol,
        apiKey: this.apiKey
      });

      const response = await fetch(`${url}?${params}`, { timeout: 15000 });
      
      if (!response.ok) {
        throw new Error(`Options API returned ${response.status}`);
      }

      const data = await response.json();
      
      if (data.status === 'OK' && data.contracts) {
        return data.contracts.filter(contract => 
          contract.type === 'call' && 
          contract.days_to_expiration >= 7 && 
          contract.days_to_expiration <= 45
        );
      }

      return [];
    } catch (error) {
      console.error(`Contracts fetch error for ${symbol}:`, error);
      return [];
    }
  }

  async findBestSpreads(symbol, currentPrice, contracts) {
    const strategies = {
      aggressive: { found: false },
      balanced: { found: false },
      conservative: { found: false }
    };

    for (const [strategyName, config] of Object.entries(this.strategyConfigs)) {
      console.log(`Analyzing ${strategyName} strategy for ${symbol}`);
      
      const filteredContracts = this.filterContractsByStrategy(contracts, config, currentPrice);
      
      if (filteredContracts.length < 2) {
        console.log(`Insufficient contracts for ${strategyName} strategy`);
        continue;
      }

      const bestSpread = await this.findBestSpreadForStrategy(filteredContracts, config);
      
      if (bestSpread) {
        strategies[strategyName] = {
          found: true,
          contracts: bestSpread.contracts,
          spread_details: bestSpread.spread_details,
          price_scenarios: this.generatePriceScenarios(bestSpread, currentPrice)
        };
        console.log(`Found ${strategyName} spread: ROI ${bestSpread.spread_details.roi_percent.toFixed(1)}%`);
      }
    }

    return strategies;
  }

  filterContractsByStrategy(contracts, config, currentPrice) {
    return contracts.filter(contract => {
      const dte = contract.days_to_expiration;
      const strike = parseFloat(contract.strike);
      
      return (
        dte >= config.dte_min &&
        dte <= config.dte_max &&
        strike >= currentPrice * 0.85 &&
        strike <= currentPrice * 1.15 &&
        contract.bid > 0.05 &&
        contract.ask > 0.05
      );
    });
  }

  async findBestSpreadForStrategy(contracts, config) {
    let bestSpread = null;
    let bestROI = 0;

    for (let i = 0; i < contracts.length; i++) {
      for (let j = i + 1; j < contracts.length; j++) {
        const longContract = contracts[i];
        const shortContract = contracts[j];

        // Ensure long strike < short strike
        if (parseFloat(longContract.strike) >= parseFloat(shortContract.strike)) {
          continue;
        }

        const spreadMetrics = this.calculateSpreadMetrics(longContract, shortContract);
        
        if (spreadMetrics && 
            spreadMetrics.roi_percent >= config.roi_min && 
            spreadMetrics.roi_percent <= config.roi_max &&
            spreadMetrics.roi_percent > bestROI) {
          
          bestROI = spreadMetrics.roi_percent;
          bestSpread = {
            contracts: {
              long_contract: longContract.contract_symbol,
              long_strike: parseFloat(longContract.strike),
              long_price: parseFloat(longContract.ask),
              short_contract: shortContract.contract_symbol,
              short_strike: parseFloat(shortContract.strike),
              short_price: parseFloat(shortContract.bid)
            },
            spread_details: spreadMetrics
          };
        }
      }
    }

    return bestSpread;
  }

  calculateSpreadMetrics(longContract, shortContract) {
    try {
      const longStrike = parseFloat(longContract.strike);
      const shortStrike = parseFloat(shortContract.strike);
      const longPrice = parseFloat(longContract.ask);
      const shortPrice = parseFloat(shortContract.bid);

      if (longStrike >= shortStrike || longPrice <= 0 || shortPrice <= 0) {
        return null;
      }

      const spreadCost = longPrice - shortPrice;
      const maxProfit = (shortStrike - longStrike) - spreadCost;
      const roiPercent = (maxProfit / spreadCost) * 100;

      if (spreadCost <= 0 || maxProfit <= 0 || roiPercent <= 0) {
        return null;
      }

      return {
        long_strike: longStrike,
        short_strike: shortStrike,
        spread_width: shortStrike - longStrike,
        spread_cost: spreadCost,
        max_profit: maxProfit,
        max_loss: spreadCost,
        roi_percent: roiPercent,
        breakeven_price: longStrike + spreadCost,
        days_to_expiration: longContract.days_to_expiration,
        expiration_date: longContract.expiration_date
      };
    } catch (error) {
      console.error('Spread calculation error:', error);
      return null;
    }
  }

  generatePriceScenarios(spread, currentPrice) {
    const scenarios = [];
    const { spread_details } = spread;
    
    // Generate 9 price scenarios from -20% to +20%
    for (let i = -20; i <= 20; i += 5) {
      const priceChange = i / 100;
      const scenarioPrice = currentPrice * (1 + priceChange);
      
      let profit = 0;
      if (scenarioPrice <= spread_details.long_strike) {
        profit = -spread_details.spread_cost;
      } else if (scenarioPrice >= spread_details.short_strike) {
        profit = spread_details.max_profit;
      } else {
        profit = (scenarioPrice - spread_details.long_strike) - spread_details.spread_cost;
      }

      scenarios.push({
        stock_price: scenarioPrice,
        price_change_percent: i,
        profit_loss: profit,
        profit_loss_percent: (profit / spread_details.spread_cost) * 100
      });
    }

    return scenarios;
  }
}