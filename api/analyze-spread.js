import { spawn } from 'child_process';
import path from 'path';
import redis from '../../lib/redis';

// A list of your 20 load-balanced Replit instances for spread analysis.
const SPREAD_ANALYZER_URLS = [
  'https://income-machine-spread-machine-1-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-2-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-3-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-4-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-5-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-6-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-7-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-8-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-9-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-10-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-11-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-12-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-13-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-14-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-15-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-16-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-17-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-18-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-19-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-20-daiadigitalco.replit.app'
];

export default async function handler(req, res) {
  // Set CORS headers for Vercel
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  // Handle OPTIONS preflight request
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    let requestData;
    if (typeof req.body === 'string') {
        try {
            requestData = JSON.parse(req.body);
        } catch (e) {
            return res.status(400).json({ error: 'Invalid JSON in request body' });
        }
    } else {
        requestData = req.body || {};
    }

    const { ticker } = requestData;

    if (!ticker) {
      return res.status(400).json({ error: 'Ticker symbol is required' });
    }
    
    const cacheKey = `spread-analysis:${ticker.toUpperCase()}`;

    // 1. Check Redis for a cached result
    try {
      const cachedResult = await redis.get(cacheKey);
      if (cachedResult) {
        console.log(`CACHE HIT for spread analysis: ${cacheKey}`);
        // Re-pipe the headers and body from the cached response
        res.setHeader('Content-Type', 'application/json');
        res.status(200).send(cachedResult);
        return;
      }
    } catch (e) {
      console.warn(`Redis GET error for ${cacheKey}:`, e.message);
    }

    console.log(`CACHE MISS for spread analysis: ${cacheKey}. Proxying to Replit.`);

    // 2. Randomly pick a base URL for load balancing
    const randomIndex = Math.floor(Math.random() * SPREAD_ANALYZER_URLS.length);
    const baseUrl = SPREAD_ANALYZER_URLS[randomIndex];
    const endpoint = '/api/analyze_debit_spread';
    const targetUrl = baseUrl + endpoint;

    console.log(`Proxying spread analysis for ${ticker} to random Replit instance: #${randomIndex + 1} - ${targetUrl}`);

    // 3. Make the proxied request to the chosen Replit server
    const proxyResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Vercel-Proxy/1.0',
      },
      body: JSON.stringify({ ticker: ticker }),
      timeout: 28000 // 28-second timeout to avoid Vercel gateway timeouts
    });

    // 4. Pipe the response back and cache it on success
    const responseBody = await proxyResponse.text();
    res.setHeader('Content-Type', proxyResponse.headers.get('Content-Type') || 'application/json');
    
    // Cache the successful result for 1 minute
    if (proxyResponse.ok) {
        try {
            await redis.set(cacheKey, responseBody, { ex: 60 }); // 60-second expiration
            console.log(`SAVED to cache: ${cacheKey}`);
        } catch (e) {
            console.warn(`Redis SET error for ${cacheKey}:`, e.message);
        }
    }
    
    res.status(proxyResponse.status).send(responseBody);

  } catch (error) {
    console.error(`Error proxying to spread analyzer: ${error.name} - ${error.message}`);
    res.status(502).json({ 
        success: false,
        error: 'The analysis service failed to respond.',
        details: error.message 
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
      const contracts = await this.getAllContracts(ticker, currentPrice);
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

  async getAllContracts(symbol, currentPrice) {
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
      
      if (!currentPrice) {
        console.log(`❌ CRITICAL ERROR: currentPrice was not passed to getAllContracts for ${symbol}`);
        return [];
      }
      
      console.log(`Using pre-fetched price for filtering: $${currentPrice}`);

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

      // Reverting to single-quote fetching which is the correct API, now with networking fixes.
      const validContracts = [];
      const maxContracts = Math.min(preFilteredContracts.length, 30); // Process a reasonable number
      
      preFilteredContracts.sort((a, b) => {
        const aDiff = Math.abs(a.strike_price - currentPrice);
        const bDiff = Math.abs(b.strike_price - currentPrice);
        return aDiff - bDiff;
      });

      console.log(`Fetching quotes for the top ${maxContracts} contracts...`);

      const startTime = Date.now();
      const batchSize = 5; // Smaller batches for this more intense operation
      
      for (let i = 0; i < maxContracts; i += batchSize) {
        const batch = preFilteredContracts.slice(i, i + batchSize);
        
        console.log(`Processing batch ${Math.floor(i/batchSize) + 1}...`);
        
        const batchPromises = batch.map(contract => 
          this.processContract(contract, currentDate)
        );
        
        const batchResults = await Promise.all(batchPromises);
        
        for (const result of batchResults) {
          if (result && result.bid > 0.05 && result.ask > 0.05) {
            validContracts.push(result);
          }
        }
        
        console.log(`Batch ${Math.floor(i/batchSize) + 1}: Found ${validContracts.length} valid contracts so far.`);
        
        if (Date.now() - startTime > 20000) { // More patient 20 second total limit
          console.log(`⏰ Time limit reached: ${Date.now() - startTime}ms`);
          break;
        }
      }
      
      const processingTime = Date.now() - startTime;
      console.log(`✅ Quote processing completed in ${processingTime}ms`);
     
      console.log(`✅ Final contracts with quotes: ${validContracts.length}`);
      return validContracts;

    } catch (error) {
      console.error(`❌ Contract fetch error for ${symbol}: ${error.message}`);
      console.error(`Error stack:`, error.stack);
      return [];
    }
  }

  async processContract(contract, currentDate) {
    try {
      const expirationDate = new Date(contract.expiration_date);
      const daysToExpiration = Math.ceil((expirationDate - currentDate) / (1000 * 60 * 60 * 24));
      
      const quotes = await this.getContractQuotes(contract.ticker);
     
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

     const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
     };

     const response = await fetch(`${url}?${params}`, { headers: headers, timeout: 4000 }); // 4s timeout per quote
     
     if (response.ok) {
       const data = await response.json();
       
       if (data.results && data.results.length > 0) {
         const quote = data.results[0];
         return {
           bid: parseFloat(quote.bid) || 0,
           ask: parseFloat(quote.ask) || 0
         };
      }
     } else {
       // Don't log here, too noisy. The lack of results is the signal.
     }
     
     return null;
   } catch (error) {
     // Also silent for speed.
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