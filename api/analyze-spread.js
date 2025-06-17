const https = require('https');

// Spread analysis endpoints with failover
const SPREAD_ENDPOINTS = [
  'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread',
  'https://income-machine-spread-check-try-2-real-daiadigitalco.replit.app/api/analyze_debit_spread',
  'https://income-machine-spread-check-try-3-real-daiadigitalco.replit.app/api/analyze_debit_spread'
];

function makeRequest(url, data, timeout = 15000) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify(data);
    const urlObj = new URL(url);
    
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port || 443,
      path: urlObj.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      },
      timeout: timeout
    };

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => {
        body += chunk;
      });
      
      res.on('end', () => {
        try {
          const parsed = JSON.parse(body);
          resolve({ status: res.statusCode, data: parsed });
        } catch (error) {
          reject(new Error('Invalid JSON response'));
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });

    req.write(postData);
    req.end();
  });
}

export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { ticker } = req.body;

    if (!ticker) {
      return res.status(400).json({
        success: false,
        error: 'Ticker symbol is required'
      });
    }

    const tickerUpper = ticker.toUpperCase();
    console.log(`=== SPREAD ANALYSIS REQUEST FOR ${tickerUpper} ===`);

    let lastError = null;

    // Try each endpoint with failover
    for (let i = 0; i < SPREAD_ENDPOINTS.length; i++) {
      const endpoint = SPREAD_ENDPOINTS[i];
      console.log(`=== TRYING ENDPOINT ${i + 1}: ${endpoint} ===`);

      try {
        const response = await makeRequest(endpoint, { ticker: tickerUpper });
        
        if (response.status === 200) {
          // Validate response structure
          if (!response.data || !response.data.strategies) {
            console.log(`=== ENDPOINT ${i + 1} FAILED: INVALID JSON STRUCTURE ===`);
            throw new Error('Invalid JSON response structure');
          }
          
          console.log(`=== SUCCESS: ENDPOINT ${i + 1} PROVIDED VALID DATA ===`);
          console.log(`Strategies found: ${Object.keys(response.data.strategies || {}).length}`);
          
          return res.json(response.data);
        } else {
          console.log(`=== ENDPOINT ${i + 1} FAILED: NON-200 STATUS ===`);
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (error) {
        console.log(`=== ENDPOINT ${i + 1} ERROR: ${error.message} ===`);
        lastError = error;
        
        if (i === SPREAD_ENDPOINTS.length - 1) {
          break;
        }
        
        console.log(`=== FAILING OVER TO ENDPOINT ${i + 2} ===`);
      }
    }
    
    console.log('All endpoints failed, returning error');
    res.status(500).json({ 
      error: 'Spread analysis services are temporarily unavailable. Please try again.',
      details: lastError.message 
    });

  } catch (error) {
    console.error('Spread analysis error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      details: error.message
    });
  }
}