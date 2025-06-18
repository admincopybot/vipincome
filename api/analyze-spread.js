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
      console.log(`=== DETAILED PRICE FETCH FOR ${symbol} ===`);
      
      // Use TheTradeList snapshot API (same as Python version)
      const url = 'https://api.thetradelist.com/v1/data/snapshot-locale';
      const params = new URLSearchParams({
        tickers: `${symbol},`,
        apiKey: this.apiKey
      });

      console.log(`Making price API call to: ${url}?${params}`);
      const response = await fetch(`${url}?${params}`, { timeout: 5000 });
      
      console.log(`Price API response status: ${response.status}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`Price API response data:`, JSON.stringify(data, null, 2));
        
        if (data.status === 'OK' && data.tickers) {
          console.log(`Found ${data.tickers.length} tickers in response`);
          
          for (const tickerData of data.tickers) {
            console.log(`Ticker: ${tickerData.ticker}, FMV: ${tickerData.fmv}`);
            if (tickerData.ticker === symbol && tickerData.fmv > 0) {
              console.log(`SUCCESS: Found price for ${symbol}: $${tickerData.fmv}`);
              return parseFloat(tickerData.fmv);
            }
          }
        }
      } else {
        const errorText = await response.text();
        console.error(`Price API error: ${response.status} - ${errorText}`);
      }

      console.log(`Primary price API failed, trying scanner fallback...`);

      // Fallback to scanner data
      const scannerUrl = 'https://api.thetradelist.com/v1/data/get_trader_scanner_data.php';
      const scannerParams = new URLSearchParams({
        apiKey: this.apiKey,
        returntype: 'json'
      });

      console.log(`Making scanner API call to: ${scannerUrl}?${scannerParams}`);
      const scannerResponse = await fetch(`${scannerUrl}?${scannerParams}`, { timeout: 15000 });
      
      console.log(`Scanner API response status: ${scannerResponse.status}`);
      
      if (scannerResponse.ok) {
        const scannerData = await scannerResponse.json();
        console.log(`Scanner API returned ${scannerData.length} items`);
        
        for (const item of scannerData) {
          if (item.symbol === symbol && item.price > 0) {
            console.log(`SUCCESS: Found price via scanner for ${symbol}: $${item.price}`);
            return parseFloat(item.price);
          }
        }
        console.log(`No matching ticker found in scanner data for ${symbol}`);
      } else {
        const errorText = await scannerResponse.text();
        console.error(`Scanner API error: ${scannerResponse.status} - ${errorText}`);
      }

      console.log(`FAILED: No price found for ${symbol} via any method`);
      return null;
    } catch (error) {
      console.error(`=== PRICE FETCH ERROR FOR ${symbol} ===`);
      console.error(`Error type: ${error.constructor.name}`);
      console.error(`Error message: ${error.message}`);
      console.error(`Error stack: ${error.stack}`);
      return null;
    }
  }

  async getAllContracts(symbol) {
    try {
      console.log(`=== DETAILED OPTIONS CONTRACT FETCH FOR ${symbol} ===`);
      
      // Use correct TheTradeList API with proper parameters
      const url = 'https://api.thetradelist.com/v1/data/options-contracts';
      const params = new URLSearchParams({
        underlying_ticker: symbol,  // CORRECT: use underlying_ticker, not symbol
        limit: 1000,
        apiKey: this.apiKey
      });

      console.log(`Making options API call to: ${url}?${params}`);
      console.log(`API Key present: ${this.apiKey ? 'YES' : 'NO'}`);
      console.log(`API Key length: ${this.apiKey?.length || 0}`);

      const response = await fetch(`${url}?${params}`, { timeout: 15000 });
      
      console.log(`Options API response status: ${response.status}`);
      console.log(`Options API response headers:`, Object.fromEntries(response.headers.entries()));
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Options API error: ${response.status} - ${errorText}`);
        throw new Error(`Options API returned ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      
      console.log(`Raw API response for ${symbol}:`, JSON.stringify(data, null, 2));
      console.log(`API response status: ${data.status}`);
      console.log(`Results array exists: ${data.results ? 'YES' : 'NO'}`);  // CORRECT: check results, not contracts
      console.log(`Total contracts returned: ${data.results?.length || 0}`);
      
      if (data.status === 'OK' && data.results && data.results.length > 0) {
        console.log(`Sample contract structure:`, JSON.stringify(data.results[0], null, 2));
        
        // Calculate days to expiration and filter contracts
        const currentDate = new Date();
        const filteredContracts = [];
        
        for (const contract of data.results) {
          // Calculate days to expiration
          const expirationDate = new Date(contract.expiration_date);
          const daysToExpiration = Math.ceil((expirationDate - currentDate) / (1000 * 60 * 60 * 24));
          
          const isCall = contract.contract_type === 'call';  // CORRECT: use contract_type
          const validDTE = daysToExpiration >= 7 && daysToExpiration <= 45;
          
          console.log(`Contract ${contract.ticker}: type=${contract.contract_type}, DTE=${daysToExpiration}, isCall=${isCall}, validDTE=${validDTE}`);
          
          if (isCall && validDTE) {
            // Get bid/ask quotes for this contract
            const quotes = await this.getContractQuotes(contract.ticker);
            if (quotes && quotes.bid > 0.05 && quotes.ask > 0.05) {
              filteredContracts.push({
                contract_symbol: contract.ticker,
                type: contract.contract_type,
                strike: contract.strike_price,
                days_to_expiration: daysToExpiration,
                expiration_date: contract.expiration_date,
                bid: quotes.bid,
                ask: quotes.ask
              });
            }
          }
        }
        
        console.log(`Filtered contracts count: ${filteredContracts.length}`);
        
        if (filteredContracts.length > 0) {
          console.log(`Sample filtered contract:`, JSON.stringify(filteredContracts[0], null, 2));
        }
        
        return filteredContracts;
      } else {
        console.log(`No contracts found - API status: ${data.status}, results: ${data.results}`);
        
        // Check if it's an error response
        if (data.error) {
          console.error(`API error message: ${data.error}`);
        }
        
        // Check if it's a different response structure
        console.log(`Full response keys:`, Object.keys(data));
      }

      return [];
    } catch (error) {
      console.error(`=== CONTRACTS FETCH ERROR FOR ${symbol} ===`);
      console.error(`Error type: ${error.constructor.name}`);
      console.error(`Error message: ${error.message}`);
      console.error(`Error stack: ${error.stack}`);
      return [];
    }
  }

  async getContractQuotes(contractTicker) {
    try {
      console.log(`Fetching quotes for contract: ${contractTicker}`);
      
      const url = 'https://api.thetradelist.com/v1/data/last-quote';
      const params = new URLSearchParams({
        ticker: contractTicker,
        apiKey: this.apiKey
      });

      const response = await fetch(`${url}?${params}`, { timeout: 10000 });
      
      if (response.ok) {
        const data = await response.json();
        console.log(`Quote data for ${contractTicker}:`, JSON.stringify(data, null, 2));
        
        if (data.results && data.results.length > 0) {
          const quote = data.results[0];
          return {
            bid: parseFloat(quote.bid) || 0,
            ask: parseFloat(quote.ask) || 0
          };
        }
      } else {
        console.log(`Quote API error for ${contractTicker}: ${response.status}`);
      }
      
      return null;
    } catch (error) {
      console.error(`Quote fetch error for ${contractTicker}:`, error.message);
      return null;
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