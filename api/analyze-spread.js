const axios = require('axios');

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