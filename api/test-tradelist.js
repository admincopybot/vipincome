export default async function handler(req, res) {
  // CORS handling
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  try {
    console.log('=== TRADELIST API DEBUG TEST ===');
    
    const apiKey = process.env.TRADELIST_API_KEY;
    
    if (!apiKey) {
      return res.status(500).json({
        error: 'TRADELIST_API_KEY not configured',
        env_vars: Object.keys(process.env).filter(key => key.includes('TRADE'))
      });
    }

    console.log(`API Key present: ${apiKey ? 'YES' : 'NO'}`);
    console.log(`API Key length: ${apiKey?.length || 0}`);
    console.log(`API Key starts with: ${apiKey?.substring(0, 5)}...`);

    const symbol = req.query.symbol || 'AAPL';
    const testResults = {};

    // Test 1: Basic API connectivity with snapshot
    console.log('=== TEST 1: SNAPSHOT API ===');
    try {
      const snapshotUrl = 'https://api.thetradelist.com/v1/data/snapshot-locale';
      const snapshotParams = new URLSearchParams({
        tickers: `${symbol},`,
        apiKey: apiKey
      });

      console.log(`Testing: ${snapshotUrl}?${snapshotParams}`);
      
      const snapshotResponse = await fetch(`${snapshotUrl}?${snapshotParams}`, { timeout: 10000 });
      
      testResults.snapshot = {
        status: snapshotResponse.status,
        ok: snapshotResponse.ok,
        headers: Object.fromEntries(snapshotResponse.headers.entries())
      };

      if (snapshotResponse.ok) {
        const snapshotData = await snapshotResponse.json();
        testResults.snapshot.data = snapshotData;
        console.log('Snapshot API SUCCESS:', JSON.stringify(snapshotData, null, 2));
      } else {
        const errorText = await snapshotResponse.text();
        testResults.snapshot.error = errorText;
        console.log('Snapshot API ERROR:', errorText);
      }
    } catch (error) {
      testResults.snapshot = {
        error: error.message,
        stack: error.stack
      };
      console.log('Snapshot API EXCEPTION:', error);
    }

    // Test 2: Options API
    console.log('=== TEST 2: OPTIONS API ===');
    try {
      const optionsUrl = 'https://api.thetradelist.com/v1/data/options';
      const optionsParams = new URLSearchParams({
        symbol: symbol,
        apiKey: apiKey
      });

      console.log(`Testing: ${optionsUrl}?${optionsParams}`);
      
      const optionsResponse = await fetch(`${optionsUrl}?${optionsParams}`, { timeout: 15000 });
      
      testResults.options = {
        status: optionsResponse.status,
        ok: optionsResponse.ok,
        headers: Object.fromEntries(optionsResponse.headers.entries())
      };

      if (optionsResponse.ok) {
        const optionsData = await optionsResponse.json();
        testResults.options.data = {
          status: optionsData.status,
          contractsCount: optionsData.contracts?.length || 0,
          firstContract: optionsData.contracts?.[0] || null,
          sampleContracts: optionsData.contracts?.slice(0, 3) || []
        };
        console.log('Options API SUCCESS - Contract count:', optionsData.contracts?.length || 0);
      } else {
        const errorText = await optionsResponse.text();
        testResults.options.error = errorText;
        console.log('Options API ERROR:', errorText);
      }
    } catch (error) {
      testResults.options = {
        error: error.message,
        stack: error.stack
      };
      console.log('Options API EXCEPTION:', error);
    }

    // Test 3: Scanner API
    console.log('=== TEST 3: SCANNER API ===');
    try {
      const scannerUrl = 'https://api.thetradelist.com/v1/data/get_trader_scanner_data.php';
      const scannerParams = new URLSearchParams({
        apiKey: apiKey,
        returntype: 'json'
      });

      console.log(`Testing: ${scannerUrl}?${scannerParams}`);
      
      const scannerResponse = await fetch(`${scannerUrl}?${scannerParams}`, { timeout: 15000 });
      
      testResults.scanner = {
        status: scannerResponse.status,
        ok: scannerResponse.ok,
        headers: Object.fromEntries(scannerResponse.headers.entries())
      };

      if (scannerResponse.ok) {
        const scannerData = await scannerResponse.json();
        const relevantData = scannerData.filter(item => item.symbol === symbol);
        testResults.scanner.data = {
          totalItems: scannerData.length,
          relevantItems: relevantData.length,
          sampleData: scannerData.slice(0, 3),
          relevantData: relevantData
        };
        console.log('Scanner API SUCCESS - Total items:', scannerData.length);
      } else {
        const errorText = await scannerResponse.text();
        testResults.scanner.error = errorText;
        console.log('Scanner API ERROR:', errorText);
      }
    } catch (error) {
      testResults.scanner = {
        error: error.message,
        stack: error.stack
      };
      console.log('Scanner API EXCEPTION:', error);
    }

    // Return comprehensive test results
    res.status(200).json({
      success: true,
      message: 'TheTradeList API debug test completed',
      symbol: symbol,
      apiKey: {
        present: !!apiKey,
        length: apiKey?.length || 0,
        preview: apiKey ? `${apiKey.substring(0, 5)}...` : 'N/A'
      },
      tests: testResults,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('=== DEBUG TEST ERROR ===');
    console.error('Error:', error);

    res.status(500).json({
      error: 'Debug test failed',
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
  }
} 