// Simulate the exact Vercel API call
async function testLocalEndpoint() {
  console.log('=== TESTING LOCAL ENDPOINT SIMULATION ===');
  
  // Simulate the request body
  const requestBody = {
    ticker: 'NFLX'
  };
  
  // Check environment variable (this is the most likely issue)
  console.log('Environment check:');
  console.log('TRADELIST_API_KEY exists:', !!process.env.TRADELIST_API_KEY);
  console.log('TRADELIST_API_KEY value:', process.env.TRADELIST_API_KEY || 'NOT SET');
  
  // Test the analyzer with the environment variable
  if (!process.env.TRADELIST_API_KEY) {
    console.log('\n❌ API KEY NOT SET - This is the problem!');
    console.log('Setting it manually for test...');
    process.env.TRADELIST_API_KEY = '5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5';
  }
  
  // Import and test the exact analyzer class from the API
  class DebitSpreadAnalyzer {
    constructor(apiKey) {
      this.apiKey = apiKey;
    }

    async getRealTimeStockPrice(symbol) {
      try {
        const url = 'https://api.thetradelist.com/v1/data/snapshot-locale';
        const params = new URLSearchParams({
          tickers: `${symbol},`,
          apiKey: this.apiKey
        });

        const response = await fetch(`${url}?${params}`, { timeout: 3000 });
        
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
        console.error(`Price fetch error for ${symbol}: ${error.message}`);
        return null;
      }
    }

    async getAllContracts(symbol) {
      try {
        console.log(`Getting contracts for ${symbol} with API key: ${this.apiKey ? 'SET' : 'NOT SET'}`);
        
        const url = 'https://api.thetradelist.com/v1/data/options-contracts';
        const params = new URLSearchParams({
          underlying_ticker: symbol,
          limit: 1000,
          apiKey: this.apiKey
        });

        console.log(`Request URL: ${url}?underlying_ticker=${symbol}&limit=1000&apiKey=${this.apiKey ? 'HIDDEN' : 'MISSING'}`);
        
        const response = await fetch(`${url}?${params}`, { timeout: 15000 });
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error(`Options API error: ${response.status} - ${errorText}`);
          return [];
        }

        const data = await response.json();
        console.log(`API Status: ${data.status}, Contracts: ${data.results?.length || 0}`);
        
        if (data.status !== 'OK' || !data.results || data.results.length === 0) {
          console.log(`No contracts available for ${symbol}`);
          return [];
        }

        return data.results;

      } catch (error) {
        console.error(`Contract fetch error for ${symbol}: ${error.message}`);
        return [];
      }
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

        return {
          success: true,
          ticker: ticker,
          current_stock_price: currentPrice,
          strategies_found: 0,
          contracts_found: contracts.length
        };

      } catch (error) {
        console.error(`Analysis error for ${ticker}:`, error);
        return {
          success: false,
          error: `Analysis failed: ${error.message}`,
          ticker: ticker
        };
      }
    }
  }
  
  // Test the exact logic from the API handler
  const { ticker } = requestBody;
  
  if (!ticker) {
    console.log('ERROR: No ticker provided');
    return;
  }

  console.log(`Running integrated spread analysis for ticker: ${ticker}`);
  
  // Check for required environment variable
  if (!process.env.TRADELIST_API_KEY) {
    console.error('TRADELIST_API_KEY environment variable not set');
    return {
      error: 'Analysis service not configured',
      message: 'Missing API configuration. Please contact support.',
      ticker: ticker
    };
  }
  
  // Run debit spread analysis directly in JavaScript
  const analyzer = new DebitSpreadAnalyzer(process.env.TRADELIST_API_KEY);
  const result = await analyzer.analyzeDebitSpread(ticker);
  
  console.log('Final Analysis result:', JSON.stringify(result, null, 2));
  
  return result;
}

testLocalEndpoint(); 