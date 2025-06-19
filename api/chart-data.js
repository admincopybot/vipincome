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
    const { ticker, startDate, endDate } = req.body;
    
    if (!ticker) {
      return res.status(400).json({ error: 'Ticker symbol is required' });
    }

    // Check Redis cache first (5-minute TTL like other endpoints)
    const cacheKey = `chart_data:${ticker}:${startDate}:${endDate}`;
    const cachedData = await redis.get(cacheKey);
    
    if (cachedData) {
      return res.status(200).json({
        success: true,
        data: cachedData,
        cached: true
      });
    }

    // Calculate 30 days ago if no startDate provided
    const endDateObj = endDate ? new Date(endDate) : new Date();
    const startDateObj = startDate ? new Date(startDate) : new Date(endDateObj.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    const formattedStartDate = startDateObj.toISOString().split('T')[0];
    const formattedEndDate = endDateObj.toISOString().split('T')[0];

    // Call TheTradeList range-data API
    const apiUrl = `https://api.thetradelist.com/v1/data/range-data?ticker=${ticker}&range=1/day&startdate=${formattedStartDate}&enddate=${formattedEndDate}&limit=50&apiKey=${TRADELIST_API_KEY}`;
    
    const response = await fetch(apiUrl);
    
    if (!response.ok) {
      throw new Error(`TheTradeList API error: ${response.status}`);
    }

    const apiData = await response.json();
    
    if (!apiData.success || !apiData.data || apiData.data.length === 0) {
      return res.status(404).json({ 
        error: 'No chart data available for this symbol',
        ticker: ticker
      });
    }

    // Transform data for Chart.js format
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

    // Cache the result for 5 minutes (300 seconds)
    await redis.setex(cacheKey, 300, JSON.stringify(chartData));

    return res.status(200).json({
      success: true,
      data: chartData,
      cached: false
    });

  } catch (error) {
    console.error('Chart data error:', error);
    return res.status(500).json({ 
      error: 'Failed to fetch chart data',
      details: error.message 
    });
  }
} 