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
    
    // DETAILED ENVIRONMENT LOGGING
    console.log('=== ENVIRONMENT CHECK ===');
    console.log('TRADELIST_API_KEY exists:', !!process.env.TRADELIST_API_KEY);
    console.log('TRADELIST_API_KEY length:', process.env.TRADELIST_API_KEY?.length || 0);
    console.log('TRADELIST_API_KEY first 10 chars:', process.env.TRADELIST_API_KEY?.substring(0, 10) || 'NOT SET');
    console.log('NODE_ENV:', process.env.NODE_ENV);
    console.log('VERCEL:', process.env.VERCEL);
    console.log('VERCEL_ENV:', process.env.VERCEL_ENV);
    
    // Check for required environment variable
    if (!process.env.TRADELIST_API_KEY) {
      console.error('TRADELIST_API_KEY environment variable not set');
      return res.status(500).json({
        error: 'Analysis service not configured',
        message: 'Missing API configuration. Please contact support.',
        ticker: ticker,
        debug: {
          env_vars_available: Object.keys(process.env).filter(k => k.includes('TRADE')),
          all_env_count: Object.keys(process.env).length
        }
      });
    }
    
    console.log('=== STARTING ANALYZER ===');
    
    // Run debit spread analysis directly in JavaScript
    const analyzer = new DebitSpreadAnalyzer(process.env.TRADELIST_API_KEY);
    const result = await analyzer.analyzeDebitSpread(ticker);
    
    console.log('=== FINAL ANALYSIS RESULT ===');
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
        ticker: req.body?.ticker || 'unknown',
        debug: {
          error_type: 'timeout',
          error_message: error.message
        }
      });
    }
    
    return res.status(500).json({
      error: 'Analysis error',
      message: 'An error occurred during spread analysis.',
      details: error.message,
      ticker: req.body?.ticker || 'unknown',
      debug: {
        error_name: error.name,
        error_stack: error.stack
      }
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
    
    console.log('DebitSpreadAnalyzer initialized with API key:', this.apiKey ? 'SET' : 'NOT SET');
  }

  async analyzeDebitSpread(ticker) {
    try {
      console.log(`=== STARTING ANALYSIS FOR ${ticker} ===`);
      
      // Get current stock price
      console.log('STEP 1: Getting current stock price...');
      const currentPrice = await this.getRealTimeStockPrice(ticker);
      if (!currentPrice) {
        console.log('❌ FAILED: Unable to fetch current stock price');
        return {
          success: false,
          error: 'Unable to fetch current stock price',
          ticker: ticker,
          debug: {
            step: 'price_fetch',
            api_key_set: !!this.apiKey
          }
        };
      }

      console.log(`✅ SUCCESS: Current price for ${ticker}: $${currentPrice}`);

      // Get options contracts
      console.log('STEP 2: Getting options contracts...');
      const contracts = await this.getAllContracts(ticker);
      if (!contracts || contracts.length === 0) {
        console.log('❌ FAILED: No options contracts found');
        return {
          success: false,
          error: 'No options contracts found',
          ticker: ticker,
          debug: {
            step: 'contracts_fetch',
            api_key_set: !!this.apiKey,
            current_price: currentPrice,
            contracts_received: contracts ? contracts.length : 'null'
          }
        };
      }

      console.log(`✅ SUCCESS: Found ${contracts.length} options contracts`);

      // Find best spreads for each strategy
      console.log('STEP 3: Finding best spreads...');
      const strategies = await this.findBestSpreads(ticker, currentPrice, contracts);

      const response = {
        success: true,
        ticker: ticker,
        current_stock_price: currentPrice,
        strategies_found: Object.values(strategies).filter(s => s.found).length,
        strategies: strategies,
        debug: {
          total_contracts: contracts.length,
          analysis_completed: true
        }
      };

      console.log(`✅ ANALYSIS COMPLETE: Found ${response.strategies_found} strategies`);
      return response;

    } catch (error) {
      console.error(`❌ ANALYSIS ERROR for ${ticker}:`, error);
      return {
        success: false,
        error: `Analysis failed: ${error.message}`,
        ticker: ticker,
        debug: {
          error_name: error.name,
          error_message: error.message,
          api_key_set: !!this.apiKey
        }
      };
    }
  }

  async getRealTimeStockPrice(symbol) {
    try {
      console.log(`Getting price for ${symbol}...`);
      
      // Fast price fetch with timeout
      const url = 'https://api.thetradelist.com/v1/data/snapshot-locale';
      const params = new URLSearchParams({
        tickers: `${symbol},`,
        apiKey: this.apiKey
      });

      console.log(`Price request URL: ${url}?tickers=${symbol}&apiKey=${this.apiKey ? 'HIDDEN' : 'MISSING'}`);
      
      const response = await fetch(`${url}?${params}`, { timeout: 3000 });
      
      console.log(`Price API response status: ${response.status}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`Price API response:`, JSON.stringify(data, null, 2));
        
        if (data.status === 'OK' && data.tickers) {
          for (const tickerData of data.tickers) {
            if (tickerData.ticker === symbol && tickerData.fmv > 0) {
              console.log(`✅ Found price: $${tickerData.fmv}`);
              return parseFloat(tickerData.fmv);
            }
          }
        }
        
        console.log(`❌ No valid price data found in response`);
      } else {
        const errorText = await response.text();
        console.log(`❌ Price API error: ${response.status} - ${errorText}`);
      }

      return null;
    } catch (error) {
      console.error(`❌ Price fetch error for ${symbol}: ${error.message}`);
      return null;
    }
  }

  async getAllContracts(symbol) {
    try {
      console.log(`=== FAST CONTRACT FETCH FOR ${symbol} ===`);
      
      const url = 'https://api.thetradelist.com/v1/data/options-contracts';
      const params = new URLSearchParams({
        underlying_ticker: symbol,
        limit: 1000,
        apiKey: this.apiKey
      });

      const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
      };

      console.log(`Making contracts API call with User-Agent header and a 25-second timeout...`);
      
      const response = await fetch(`${url}?${params}`, { headers: headers, timeout: 25000 });
      
      console.log(`Contracts API response status: ${response.status}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`❌ Options API error: ${response.status} - ${errorText}`);
        throw new Error(`Options API returned ${response.status}: ${errorText}`);
      }
      
      const responseBodyText = await response.text(); // Get raw text first
      let data;
      try {
        data = JSON.parse(responseBodyText);
      } catch (e) {
        console.error("❌ Failed to parse JSON response from options API.");
        console.error("Raw Response Text:", responseBodyText);
        throw new Error("Invalid JSON response from options API.");
      }

      console.log(`Contracts API response status: ${data.status}`);
      console.log(`Contracts found: ${data.results?.length || 0}`);
      
      if (data.status !== 'OK' || !data.results || data.results.length === 0) {
        console.log(`❌ No contracts available for ${symbol}`);
        console.log(`Full API response (parsed):`, JSON.stringify(data, null, 2));
        return [];
      }

      // PERFORMANCE OPTIMIZATION: Pre-filter contracts before fetching quotes
      const currentDate = new Date();
      const currentPrice = await this.getRealTimeStockPrice(symbol);
      
      if (!currentPrice) {
        console.log(`❌ Could not get current price for ${symbol}`);
        return [];
      }
      
      console.log(`Current ${symbol} price: $${currentPrice}`);

      // Smart pre-filtering to reduce API calls
      const preFilteredContracts = data.results.filter(contract => {
        const expirationDate = new Date(contract.expiration_date);
        const daysToExpiration = Math.ceil((expirationDate - currentDate) / (1000 * 60 * 60 * 24));
        const strike = parseFloat(contract.strike_price);
        
        return (
          contract.contract_type === 'call' &&
          daysToExpiration >= 7 && daysToExpiration <= 45 &&
          strike >= currentPrice * 0.80 && strike <= currentPrice * 1.20  // Reasonable strike range
        );
      });

      console.log(`Pre-filtered to ${preFilteredContracts.length} relevant contracts`);

      // BALANCED FAST PROCESSING: Speed + Reliability
      const validContracts = [];
      const maxContracts = Math.min(preFilteredContracts.length, 30); // Balanced: 30 contracts
      
      // Sort by how close strike is to current price (most likely to have good spreads)
      preFilteredContracts.sort((a, b) => {
        const aDiff = Math.abs(a.strike_price - currentPrice);
        const bDiff = Math.abs(b.strike_price - currentPrice);
        return aDiff - bDiff;
      });

      console.log(`BALANCED FAST: Processing top ${maxContracts} contracts...`);

      // SMART PROCESSING: Process in small fast batches with early termination
      const startTime = Date.now();
      const batchSize = 6;
      
      for (let i = 0; i < maxContracts && validContracts.length < 20; i += batchSize) {
        const batch = preFilteredContracts.slice(i, i + batchSize);
        
        console.log(`Processing batch ${Math.floor(i/batchSize) + 1}...`);
        
        const batchPromises = batch.map(contract => 
          Promise.race([
            this.processContract(contract, currentDate, currentPrice),
            new Promise(resolve => setTimeout(() => resolve(null), 2500)) // 2.5s per contract
          ])
        );
        
        const batchResults = await Promise.all(batchPromises);
        
        // Add valid results from this batch
        for (const result of batchResults) {
          if (result && result.bid > 0.05 && result.ask > 0.05) {
            validContracts.push(result);
          }
        }
        
        console.log(`Batch ${Math.floor(i/batchSize) + 1}: Found ${validContracts.length} valid contracts so far`);
        
        // Early termination if we have enough contracts
        if (validContracts.length >= 15) {
          console.log(`✅ Early termination: Found sufficient contracts (${validContracts.length})`);
          break;
        }
        
        // Stop if we're taking too long
        if (Date.now() - startTime > 12000) { // 12 second total limit
          console.log(`⏰ Time limit reached: ${Date.now() - startTime}ms`);
          break;
        }
      }
      
      const processingTime = Date.now() - startTime;
      console.log(`✅ Processing completed in ${processingTime}ms`);
     
      console.log(`✅ Final contracts with quotes: ${validContracts.length}`);
      return validContracts;

    } catch (error) {
      console.error(`❌ Contract fetch error for ${symbol}: ${error.message}`);
      console.error(`Error stack:`, error.stack);
      return [];
    }
  }

  async processContract(contract, currentDate, currentPrice) {
    try {
      const expirationDate = new Date(contract.expiration_date);
      const daysToExpiration = Math.ceil((expirationDate - currentDate) / (1000 * 60 * 60 * 24));
      
      // Get quotes with reasonable timeout
      const quotes = await Promise.race([
        this.getContractQuotes(contract.ticker),
        new Promise(resolve => setTimeout(() => resolve(null), 2000)) // 2 second timeout per contract
      ]);
     
     if (quotes && quotes.bid > 0.05 && quotes.ask > 0.05) {
       return {
         contract_symbol: contract.ticker,
         type: contract.contract_type,
         strike: contract.strike_price,
         days_to_expiration: daysToExpiration,
         expiration_date: contract.expiration_date,
         bid: quotes.bid,
         ask: quotes.ask
       };
     }
     
     return null;
   } catch (error) {
     console.log(`⚠️ Error processing ${contract.ticker}: ${error.message}`);
     return null;
   }
 }

 async getContractQuotes(contractTicker) {
   try {
     const url = 'https://api.thetradelist.com/v1/data/last-quote';
     const params = new URLSearchParams({
       ticker: contractTicker,
       apiKey: this.apiKey
     });

     const response = await fetch(`${url}?${params}`, { timeout: 3000 });
     
     if (response.ok) {
       const data = await response.json();
       
       if (data.results && data.results.length > 0) {
         const quote = data.results[0];
         return {
           bid: parseFloat(quote.bid) || 0,
           ask: parseFloat(quote.ask) || 0
         };
       }
     }
     
     return null;
   } catch (error) {
     return null; // Fail silently for speed
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