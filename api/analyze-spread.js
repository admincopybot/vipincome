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
    console.log('=== ANALYZE SPREAD PROXY START ===');
    console.log('Request method:', req.method);
    console.log('Request body:', req.body);
    console.log('Axios available:', typeof axios);
    
    const { ticker } = req.body;

    if (!ticker) {
      console.log('ERROR: No ticker provided');
      return res.status(400).json({
        success: false,
        error: 'Ticker is required'
      });
    }

    console.log(`Proxying spread analysis request for ticker: ${ticker}`);
    console.log('Making request to Replit API...');
    
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
    console.log(`Replit API response data:`, JSON.stringify(response.data, null, 2));
    
    // Forward the response from Replit
    res.status(response.status).json(response.data);
    
  } catch (error) {
    console.error('=== ERROR IN ANALYZE SPREAD PROXY ===');
    console.error('Error type:', error.constructor.name);
    console.error('Error message:', error.message);
    console.error('Error stack:', error.stack);
    
    if (error.response) {
      // Forward error response from Replit
      console.error('Replit error status:', error.response.status);
      console.error('Replit error data:', error.response.data);
      res.status(error.response.status).json(error.response.data);
    } else if (error.code === 'ECONNABORTED') {
      console.error('Request timeout occurred');
      res.status(408).json({
        success: false,
        error: 'Request timeout - analysis is taking longer than expected'
      });
    } else {
      console.error('Unknown error occurred');
      res.status(500).json({
        success: false,
        error: 'Failed to analyze spreads',
        details: error.message,
        errorType: error.constructor.name
      });
    }
  }
}