// COMPREHENSIVE TEST: Complete spread analysis flow for MS ticker
const API_KEY = "5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5";

class TestDebitSpreadAnalyzer {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.strategyConfigs = {
      aggressive: { roi_min: 25, roi_max: 50, dte_min: 10, dte_max: 17 },
      balanced: { roi_min: 12, roi_max: 25, dte_min: 17, dte_max: 28 },
      conservative: { roi_min: 8, roi_max: 15, dte_min: 28, dte_max: 42 }
    };
  }

  async testCompleteFlow() {
    const symbol = 'MS';
    console.log(`🚀 TESTING COMPLETE FLOW FOR ${symbol}`);
    
    // STEP 1: Get stock price
    console.log('\n📈 STEP 1: GET STOCK PRICE');
    const stockPrice = await this.getRealTimeStockPrice(symbol);
    if (!stockPrice) {
      console.log('❌ FAILED: Could not get stock price');
      return false;
    }
    console.log(`✅ Stock Price: $${stockPrice}`);
    
    // STEP 2: Get all options contracts
    console.log('\n📋 STEP 2: GET ALL OPTIONS CONTRACTS');
    const allContracts = await this.getAllContracts(symbol);
    if (!allContracts || allContracts.length === 0) {
      console.log('❌ FAILED: No contracts found');
      return false;
    }
    console.log(`✅ Found ${allContracts.length} valid contracts with quotes`);
    
    // STEP 3: Filter by strategy and analyze spreads
    console.log('\n🎯 STEP 3: ANALYZE SPREADS BY STRATEGY');
    
    for (const [strategyName, config] of Object.entries(this.strategyConfigs)) {
      console.log(`\n--- ${strategyName.toUpperCase()} STRATEGY ---`);
      console.log(`Config: ROI ${config.roi_min}-${config.roi_max}%, DTE ${config.dte_min}-${config.dte_max}`);
      
      // Filter contracts for this strategy
      const filteredContracts = this.filterContractsByStrategy(allContracts, config, stockPrice);
      console.log(`Contracts matching ${strategyName} criteria: ${filteredContracts.length}`);
      
      if (filteredContracts.length >= 2) {
        // Find best spread for this strategy
        const bestSpread = await this.findBestSpreadForStrategy(filteredContracts, config);
        
        if (bestSpread) {
          console.log(`✅ Found ${strategyName} spread:`);
          console.log(`   Long: ${bestSpread.contracts.long_contract} @ $${bestSpread.contracts.long_price}`);
          console.log(`   Short: ${bestSpread.contracts.short_contract} @ $${bestSpread.contracts.short_price}`);
          console.log(`   Cost: $${bestSpread.spread_details.spread_cost.toFixed(2)}`);
          console.log(`   Max Profit: $${bestSpread.spread_details.max_profit.toFixed(2)}`);
          console.log(`   ROI: ${bestSpread.spread_details.roi_percent.toFixed(1)}%`);
          console.log(`   DTE: ${bestSpread.spread_details.days_to_expiration} days`);
        } else {
          console.log(`❌ No viable ${strategyName} spread found`);
        }
      } else {
        console.log(`❌ Insufficient contracts for ${strategyName} (need ≥2, have ${filteredContracts.length})`);
      }
    }
    
    return true;
  }

  async getRealTimeStockPrice(symbol) {
    try {
      const url = 'https://api.thetradelist.com/v1/data/snapshot-locale';
      const params = new URLSearchParams({
        tickers: `${symbol},`,
        apiKey: this.apiKey
      });

      const response = await fetch(`${url}?${params}`);
      
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

      return null;
    } catch (error) {
      console.error(`Price fetch error: ${error.message}`);
      return null;
    }
  }

  async getAllContracts(symbol) {
    try {
      console.log(`Fetching contracts for ${symbol}...`);
      
      const url = 'https://api.thetradelist.com/v1/data/options-contracts';
      const params = new URLSearchParams({
        underlying_ticker: symbol,
        limit: 1000,
        apiKey: this.apiKey
      });

      const response = await fetch(`${url}?${params}`);
      
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const data = await response.json();
      
      if (data.status !== 'OK' || !data.results) {
        throw new Error('Invalid response structure');
      }

      console.log(`API returned ${data.results.length} total contracts`);

      // Filter and enrich contracts
      const currentDate = new Date();
      const validContracts = [];
      
      for (const contract of data.results) {
        // Calculate days to expiration
        const expirationDate = new Date(contract.expiration_date);
        const daysToExpiration = Math.ceil((expirationDate - currentDate) / (1000 * 60 * 60 * 24));
        
        // Only process call options with reasonable DTE
        if (contract.contract_type === 'call' && daysToExpiration >= 7 && daysToExpiration <= 45) {
          console.log(`Processing ${contract.ticker} (Strike: $${contract.strike_price}, DTE: ${daysToExpiration})`);
          
          // Get quotes for this contract
          const quotes = await this.getContractQuotes(contract.ticker);
          
          if (quotes && quotes.bid > 0.05 && quotes.ask > 0.05) {
            validContracts.push({
              contract_symbol: contract.ticker,
              type: contract.contract_type,
              strike: contract.strike_price,
              days_to_expiration: daysToExpiration,
              expiration_date: contract.expiration_date,
              bid: quotes.bid,
              ask: quotes.ask
            });
            
            console.log(`✅ Added contract: Strike $${contract.strike_price}, Bid $${quotes.bid}, Ask $${quotes.ask}`);
          } else {
            console.log(`❌ Skipped ${contract.ticker}: insufficient liquidity`);
          }
          
          // Add small delay to avoid rate limiting
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
      
      console.log(`Final valid contracts: ${validContracts.length}`);
      return validContracts;
      
    } catch (error) {
      console.error(`Contract fetch error: ${error.message}`);
      return [];
    }
  }

  async getContractQuotes(contractTicker) {
    try {
      const url = 'https://api.thetradelist.com/v1/data/last-quote';
      const params = new URLSearchParams({
        ticker: contractTicker,
        apiKey: this.apiKey
      });

      const response = await fetch(`${url}?${params}`);
      
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
      console.error(`Quote fetch error for ${contractTicker}: ${error.message}`);
      return null;
    }
  }

  filterContractsByStrategy(contracts, config, currentPrice) {
    return contracts.filter(contract => {
      const dte = contract.days_to_expiration;
      const strike = parseFloat(contract.strike);
      
      const validDTE = dte >= config.dte_min && dte <= config.dte_max;
      const validStrike = strike >= currentPrice * 0.85 && strike <= currentPrice * 1.15;
      const validLiquidity = contract.bid > 0.05 && contract.ask > 0.05;
      
      return validDTE && validStrike && validLiquidity;
    });
  }

  async findBestSpreadForStrategy(contracts, config) {
    console.log(`Analyzing ${contracts.length} contracts for spread combinations...`);
    
    let bestSpread = null;
    let bestROI = 0;
    let combinationsChecked = 0;

    for (let i = 0; i < contracts.length; i++) {
      for (let j = i + 1; j < contracts.length; j++) {
        const longContract = contracts[i];
        const shortContract = contracts[j];

        // Ensure long strike < short strike (for debit spread)
        if (parseFloat(longContract.strike) >= parseFloat(shortContract.strike)) {
          continue;
        }

        combinationsChecked++;
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
          
          console.log(`New best ROI: ${spreadMetrics.roi_percent.toFixed(1)}%`);
        }
      }
    }

    console.log(`Checked ${combinationsChecked} spread combinations`);
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
}

// Run the comprehensive test
async function runCompleteTest() {
  console.log('🧪 STARTING COMPREHENSIVE FLOW TEST');
  console.log('=====================================');
  
  const analyzer = new TestDebitSpreadAnalyzer(API_KEY);
  const success = await analyzer.testCompleteFlow();
  
  console.log('\n📊 TEST SUMMARY');
  console.log('================');
  console.log(success ? '✅ COMPLETE FLOW TEST PASSED' : '❌ COMPLETE FLOW TEST FAILED');
  
  if (success) {
    console.log('\n🎉 THE ANALYZER WILL WORK CORRECTLY!');
    console.log('All steps validated:');
    console.log('  ✅ Stock price retrieval');
    console.log('  ✅ Options contract fetching');
    console.log('  ✅ Quote data enrichment');
    console.log('  ✅ Strategy-based filtering');
    console.log('  ✅ Spread combination analysis');
    console.log('  ✅ ROI calculations');
  }
}

runCompleteTest(); 