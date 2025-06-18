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
    console.log('=== VERCEL PROXY TO REPLIT START ===');
    console.log('Request method:', req.method);
    console.log('Request headers:', req.headers);
    console.log('Raw request body:', req.body);
    
    // Parse request body
    let requestData;
    if (typeof req.body === 'string') {
      requestData = JSON.parse(req.body);
    } else {
      requestData = req.body || {};
    }

    const { ticker } = requestData;
    
    if (!ticker) {
      console.log('ERROR: No ticker provided');
      return res.status(400).json({
        error: 'Ticker symbol is required',
        received: requestData
      });
    }

    console.log(`Proxying analysis request for ticker: ${ticker}`);
    
    // Use native fetch instead of axios
    const replitUrl = 'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread';
    
    console.log('Calling Replit API:', replitUrl);
    
    const response = await fetch(replitUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ticker }),
      signal: AbortSignal.timeout(25000) // 25 second timeout
    });
    
    console.log('Replit response status:', response.status);
    console.log('Replit response headers:', Object.fromEntries(response.headers.entries()));
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Replit API error:', response.status, errorText);
      return res.status(response.status).json({
        error: 'Analysis service error',
        status: response.status,
        message: errorText,
        ticker: ticker
      });
    }
    
    const responseData = await response.json();
    console.log('Replit response data:', JSON.stringify(responseData, null, 2));
    
    // Forward the response from Replit
    res.status(200).json(responseData);
    
  } catch (error) {
    console.error('=== PROXY ERROR ===');
    console.error('Error name:', error.name);
    console.error('Error message:', error.message);
    console.error('Error stack:', error.stack);
    
    if (error.name === 'AbortError' || error.name === 'TimeoutError') {
      return res.status(408).json({
        error: 'Request timeout',
        message: 'The analysis is taking longer than expected. Please try again.',
        ticker: req.body?.ticker || 'unknown'
      });
    }
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return res.status(502).json({
        error: 'Unable to connect to analysis service',
        message: 'Please try again in a few moments.',
        ticker: req.body?.ticker || 'unknown'
      });
    }
    
    return res.status(500).json({
      error: 'Proxy error',
      message: 'An error occurred while processing the request.',
      details: error.message,
      ticker: req.body?.ticker || 'unknown'
    });
  }
}