const axios = require('axios');

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
    console.log('=== VERCEL SERVERLESS SPREAD ANALYSIS START ===');
    console.log('Request method:', req.method);
    console.log('Raw request body type:', typeof req.body);
    console.log('Raw request body:', req.body);
    
    // Parse request body manually (Vercel serverless requirement)
    let requestData;
    if (typeof req.body === 'string') {
      try {
        requestData = JSON.parse(req.body);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        return res.status(400).json({ 
          error: 'Invalid JSON in request body',
          details: parseError.message 
        });
      }
    } else if (req.body && typeof req.body === 'object') {
      requestData = req.body;
    } else {
      console.error('No request body found');
      return res.status(400).json({ error: 'Request body is required' });
    }

    console.log('Parsed request data:', requestData);
    
    const { ticker } = requestData;
    
    if (!ticker) {
      console.log('ERROR: No ticker provided in request data');
      return res.status(400).json({
        error: 'Ticker symbol is required',
        received: requestData
      });
    }

    console.log(`Starting spread analysis for ticker: ${ticker}`);
    
    // External API call with proper timeout handling
    const externalApiUrl = 'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread';
    
    console.log('Making request to external API:', externalApiUrl);
    
    const response = await axios.post(externalApiUrl, 
      { ticker }, 
      {
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 30000, // 30 second timeout (within Vercel's limits)
        validateStatus: function (status) {
          return status < 500; // Don't throw for 4xx errors
        }
      }
    );
    
    console.log(`External API response status: ${response.status}`);
    console.log('External API response data:', JSON.stringify(response.data, null, 2));
    
    if (response.status >= 400) {
      console.error(`External API error: ${response.status}`);
      return res.status(response.status).json({
        error: 'External analysis service error',
        status: response.status,
        message: response.data?.message || 'Analysis service unavailable',
        ticker: ticker
      });
    }
    
    // Validate response structure
    const spreadData = response.data;
    if (!spreadData || typeof spreadData !== 'object') {
      console.error('Invalid response structure from external API');
      return res.status(502).json({
        error: 'Invalid response from analysis service',
        ticker: ticker
      });
    }
    
    console.log(`Successfully analyzed spread for ${ticker}`);
    
    // Return the spread analysis data
    res.status(200).json(spreadData);
    
  } catch (error) {
    console.error('=== VERCEL SERVERLESS ERROR ===');
    console.error('Error type:', error.constructor.name);
    console.error('Error message:', error.message);
    console.error('Error code:', error.code);
    
    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      console.error('Request timeout occurred');
      return res.status(408).json({
        error: 'Analysis timeout',
        message: 'The analysis is taking longer than expected. Please try again.',
        ticker: req.body?.ticker || 'unknown'
      });
    }
    
    if (error.response) {
      console.error('External API error response:', error.response.status, error.response.data);
      return res.status(error.response.status).json({
        error: 'External analysis service error',
        message: error.response.data?.message || 'Analysis service unavailable',
        ticker: req.body?.ticker || 'unknown'
      });
    }
    
    // Generic server error
    console.error('Unknown error occurred:', error.stack);
    return res.status(500).json({
      error: 'Unable to analyze spread at this time',
      message: 'Please try again in a few moments',
      ticker: req.body?.ticker || 'unknown',
      errorType: error.constructor.name
    });
  }
}