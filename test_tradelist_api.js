// Local test script to verify TheTradeList API endpoints
// Run with: node test_tradelist_api.js

const API_KEY = "5b4960fc-2cd5-4bda-bae1-e84c1"; // Your API key from the screenshot

async function testTheTradeListAPI() {
  console.log('=== TESTING TRADELIST API ENDPOINTS LOCALLY ===');
  console.log(`API Key: ${API_KEY.substring(0, 8)}...`);
  
  const symbol = 'MS';
  
  // Test 1: Stock Price API
  console.log('\n=== TEST 1: STOCK PRICE API ===');
  try {
    const priceUrl = 'https://api.thetradelist.com/v1/data/snapshot-locale';
    const priceParams = new URLSearchParams({
      tickers: `${symbol},`,
      apiKey: API_KEY
    });
    
    console.log(`Testing: ${priceUrl}?${priceParams}`);
    
    const priceResponse = await fetch(`${priceUrl}?${priceParams}`);
    console.log(`Status: ${priceResponse.status}`);
    
    if (priceResponse.ok) {
      const priceData = await priceResponse.json();
      console.log('✅ Price API SUCCESS');
      console.log('Response:', JSON.stringify(priceData, null, 2));
      
      // Check if we found the stock price
      if (priceData.status === 'OK' && priceData.tickers) {
        const msData = priceData.tickers.find(t => t.ticker === symbol);
        if (msData) {
          console.log(`✅ Found ${symbol} price: $${msData.fmv}`);
        } else {
          console.log(`❌ ${symbol} not found in price response`);
        }
      }
    } else {
      const errorText = await priceResponse.text();
      console.log('❌ Price API ERROR:', errorText);
    }
  } catch (error) {
    console.log('❌ Price API EXCEPTION:', error.message);
  }
  
  // Test 2: Options Contracts API - Try multiple endpoints
  console.log('\n=== TEST 2: OPTIONS CONTRACTS API ===');
  
  const optionsEndpoints = [
    'https://api.thetradelist.com/v1/data/options-contracts',
    'https://api.thetradelist.com/v1/data/options',
    'https://api.thetradelist.com/v1/data/options-chain'
  ];
  
  for (const endpoint of optionsEndpoints) {
    console.log(`\n--- Testing endpoint: ${endpoint} ---`);
    try {
      const optionsParams = new URLSearchParams({
        symbol: symbol,
        apiKey: API_KEY
      });
      
      console.log(`URL: ${endpoint}?${optionsParams}`);
      
      const optionsResponse = await fetch(`${endpoint}?${optionsParams}`, { 
        timeout: 15000,
        headers: {
          'User-Agent': 'Income-Machine-VIP/1.0'
        }
      });
      
      console.log(`Status: ${optionsResponse.status}`);
      console.log(`Headers:`, Object.fromEntries(optionsResponse.headers.entries()));
      
      if (optionsResponse.ok) {
        const optionsData = await optionsResponse.json();
        console.log('✅ Options API SUCCESS');
        console.log('Response keys:', Object.keys(optionsData));
        console.log('Full response:', JSON.stringify(optionsData, null, 2));
        
        // Check different possible response structures
        if (optionsData.contracts) {
          console.log(`✅ Found ${optionsData.contracts.length} contracts in 'contracts' array`);
          if (optionsData.contracts.length > 0) {
            console.log('Sample contract:', JSON.stringify(optionsData.contracts[0], null, 2));
          }
        } else if (optionsData.results) {
          console.log(`✅ Found ${optionsData.results.length} contracts in 'results' array`);
        } else if (optionsData.data) {
          console.log(`✅ Found data in 'data' field:`, typeof optionsData.data);
        } else {
          console.log('❓ Unknown response structure for options data');
        }
      } else {
        const errorText = await optionsResponse.text();
        console.log('❌ Options API ERROR:', errorText);
      }
    } catch (error) {
      console.log('❌ Options API EXCEPTION:', error.message);
    }
  }
  
  // Test 3: Scanner API (fallback)
  console.log('\n=== TEST 3: SCANNER API ===');
  try {
    const scannerUrl = 'https://api.thetradelist.com/v1/data/get_trader_scanner_data.php';
    const scannerParams = new URLSearchParams({
      apiKey: API_KEY,
      returntype: 'json'
    });
    
    console.log(`Testing: ${scannerUrl}?${scannerParams}`);
    
    const scannerResponse = await fetch(`${scannerUrl}?${scannerParams}`, { timeout: 15000 });
    console.log(`Status: ${scannerResponse.status}`);
    
    if (scannerResponse.ok) {
      const scannerData = await scannerResponse.json();
      console.log('✅ Scanner API SUCCESS');
      console.log(`Total items: ${scannerData.length}`);
      
      // Look for MS in scanner data
      const msData = scannerData.find(item => item.symbol === symbol);
      if (msData) {
        console.log(`✅ Found ${symbol} in scanner:`, JSON.stringify(msData, null, 2));
      } else {
        console.log(`❌ ${symbol} not found in scanner data`);
        console.log('Available symbols (first 10):', scannerData.slice(0, 10).map(s => s.symbol));
      }
    } else {
      const errorText = await scannerResponse.text();
      console.log('❌ Scanner API ERROR:', errorText);
    }
  } catch (error) {
    console.log('❌ Scanner API EXCEPTION:', error.message);
  }
  
  console.log('\n=== API TESTING COMPLETE ===');
}

// Run the test
testTheTradeListAPI().catch(console.error); 