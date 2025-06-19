// Vercel serverless function for 30-day price chart data
// Follows existing patterns: Redis caching, TheTradeList API (NO JWT like other working endpoints)

import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

const TRADELIST_API_KEY = process.env.TRADELIST_API_KEY;

export default async function handler(req, res) {
  // Enable CORS (matching pattern from other working endpoints)
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  // Handle OPTIONS preflight request
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    console.log('=== CHART DATA API CALL START ===');
    console.log('Request body:', JSON.stringify(req.body, null, 2));
    console.log('Request headers:', JSON.stringify(req.headers, null, 2));
    
    const { ticker, startDate, endDate } = req.body;
    
    console.log(`Parsed parameters - Ticker: ${ticker}, StartDate: ${startDate}, EndDate: ${endDate}`);
    
    if (!ticker) {
      console.log('❌ ERROR: No ticker provided');
      return res.status(400).json({ error: 'Ticker symbol is required' });
    }

    // Check API key availability
    console.log(`API Key check - Available: ${!!TRADELIST_API_KEY}, Length: ${TRADELIST_API_KEY ? TRADELIST_API_KEY.length : 0}, First 8 chars: ${TRADELIST_API_KEY ? TRADELIST_API_KEY.substring(0, 8) : 'N/A'}...`);
    
    if (!TRADELIST_API_KEY) {
      console.log('❌ ERROR: TRADELIST_API_KEY not found in environment');
      return res.status(500).json({ error: 'API key not configured' });
    }

    // Check Redis cache first (5-minute TTL like other endpoints)
    const cacheKey = `chart_data:${ticker}:${startDate}:${endDate}`;
    console.log(`Cache key: ${cacheKey}`);
    
    const cachedData = await redis.get(cacheKey);
    
    if (cachedData) {
      console.log('✅ CACHE HIT - returning cached data');
      return res.status(200).json({
        success: true,
        data: cachedData,
        cached: true
      });
    }
    
    console.log('CACHE MISS - fetching from TheTradeList API');

    // Calculate 30 days ago if no startDate provided
    const endDateObj = endDate ? new Date(endDate) : new Date();
    const startDateObj = startDate ? new Date(startDate) : new Date(endDateObj.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    const formattedStartDate = startDateObj.toISOString().split('T')[0];
    const formattedEndDate = endDateObj.toISOString().split('T')[0];
    
    console.log(`Date range - Start: ${formattedStartDate}, End: ${formattedEndDate}`);

    // Build API URL with all parameters (matching working pattern)
    const apiParams = {
      ticker: ticker,
      range: '1/day',
      startdate: formattedStartDate,
      enddate: formattedEndDate,
      limit: 10, // Use same limit as working pattern
      next_url: '', // Add missing parameter from working pattern
      apiKey: TRADELIST_API_KEY
    };
    
    console.log('API parameters:', JSON.stringify(apiParams, null, 2));
    
    const apiUrl = `https://api.thetradelist.com/v1/data/range-data?${new URLSearchParams(apiParams)}`;
    console.log(`Full API URL: ${apiUrl.replace(TRADELIST_API_KEY, 'API_KEY_HIDDEN')}`);
    
    console.log('Making fetch request to TheTradeList...');
    const response = await fetch(apiUrl);
    
    console.log(`Response status: ${response.status}`);
    console.log(`Response status text: ${response.statusText}`);
    console.log(`Response headers:`, Object.fromEntries(response.headers.entries()));
    
    if (!response.ok) {
      const errorText = await response.text();
      console.log(`❌ TheTradeList API ERROR - Status: ${response.status}, Body: ${errorText}`);
      throw new Error(`TheTradeList API error: ${response.status} - ${errorText}`);
    }

    const responseText = await response.text();
    console.log(`Raw response body (first 500 chars): ${responseText.substring(0, 500)}`);
    
    let apiData;
    try {
      apiData = JSON.parse(responseText);
    } catch (parseError) {
      console.log(`❌ JSON Parse Error: ${parseError.message}`);
      console.log(`Full response body: ${responseText}`);
      throw new Error(`Invalid JSON response from TheTradeList API`);
    }
    
    console.log('Parsed API response:', JSON.stringify(apiData, null, 2));
    
    console.log(`API Data validation - Success: ${apiData.success}, Data exists: ${!!apiData.data}, Data length: ${apiData.data ? apiData.data.length : 0}`);
    
    if (!apiData.success || !apiData.data || apiData.data.length === 0) {
      console.log('❌ ERROR: No chart data available');
      console.log('Full API response structure:', Object.keys(apiData));
      return res.status(404).json({ 
        error: 'No chart data available for this symbol',
        ticker: ticker,
        apiResponse: apiData
      });
    }

    console.log(`✅ SUCCESS: Found ${apiData.data.length} data points`);
    console.log('Sample data point:', JSON.stringify(apiData.data[0], null, 2));

    // Transform data for Chart.js format
    console.log('Transforming data for Chart.js...');
    
    const chartData = {
      labels: apiData.data.map(item => {
        const date = new Date(item.t);
        return date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: 'numeric' });
      }),
      datasets: [{
        data: apiData.data.map(item => parseFloat(item.c)), // closing prices
        borderColor: 'rgb(147, 51, 234)', // purple color matching design
        backgroundColor: 'rgba(147, 51, 234, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.1
      }]
    };

    console.log(`Chart data created - Labels: ${chartData.labels.length}, Data points: ${chartData.datasets[0].data.length}`);
    console.log('Sample label:', chartData.labels[0]);
    console.log('Sample price:', chartData.datasets[0].data[0]);

    // Cache the result for 5 minutes (300 seconds)
    console.log(`Caching result with key: ${cacheKey}`);
    await redis.setex(cacheKey, 300, JSON.stringify(chartData));
    console.log('✅ Data cached successfully');

    console.log('=== CHART DATA API CALL SUCCESS ===');
    return res.status(200).json({
      success: true,
      data: chartData,
      cached: false
    });

  } catch (error) {
    console.log('=== CHART DATA API CALL ERROR ===');
    console.error('❌ Exception caught:', error.name);
    console.error('❌ Error message:', error.message);
    console.error('❌ Error stack:', error.stack);
    
    return res.status(500).json({ 
      error: 'Failed to fetch chart data',
      details: error.message,
      errorType: error.name
    });
  }
} 