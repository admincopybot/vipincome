const axios = require('axios');

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
        error: 'Ticker is required'
      });
    }

    console.log(`Proxying spread analysis request for ticker: ${ticker}`);
    
    // Forward the request to your Replit endpoint
    const response = await axios.post(
      'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread',
      { ticker },
      {
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 45000 // 45 second timeout
      }
    );
    
    console.log(`Replit API response status: ${response.status}`);
    console.log(`Replit API response data:`, response.data);
    
    // Forward the response from Replit
    res.status(response.status).json(response.data);
    
  } catch (error) {
    console.error('Error calling Replit analysis endpoint:', error.message);
    
    if (error.response) {
      // Forward error response from Replit
      console.error('Replit error response:', error.response.data);
      res.status(error.response.status).json(error.response.data);
    } else if (error.code === 'ECONNABORTED') {
      res.status(408).json({
        success: false,
        error: 'Request timeout - analysis is taking longer than expected'
      });
    } else {
      res.status(500).json({
        success: false,
        error: 'Failed to analyze spreads',
        details: error.message
      });
    }
  }
}