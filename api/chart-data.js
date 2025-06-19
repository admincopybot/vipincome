// Vercel serverless function for 30-day price chart data
// Follows existing patterns: JWT validation, Redis caching, TheTradeList API

import { Redis } from '@upstash/redis';
import jwt from 'jsonwebtoken';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

const TRADELIST_API_KEY = process.env.TRADELIST_API_KEY;
const PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyV9LlPMuRVPkK83jm3Zj
o0s0x1KdYhKb0jT8lJiJIkp3TdKqLJdDKYcCr1jhA0x0O5oGvW4eN1gJQ7FKZJTA
XhKSfqNfGJO4T5zJlJp5YgJG8nN8o0Fy8QxPpJI5qF3Q4K9ZeD0uV6FgVRz1C1k
A5P3f6YcJk0JOqQsOnF0F5YyVP5c6jmqJ6VqRz3YQ3V8O4YJoQF1a2YMaQ0N5E1
HxJ4h6yRdGJw5vXJwvN5aGgFWz1XS9o5pF0vN5VjN1Jw2CKS8wjJ5gXNPjJqy8v
6O9OJzM3W8K4QoFG3fKJL2q8U9vV4cO7E4uOFNlFG8YGwFNSJ3M4hJl6VQKyRrF
QIDAQAB
-----END PUBLIC KEY-----`;

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Extract and validate JWT token
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'No valid authorization token provided' });
    }

    const token = authHeader.substring(7);
    
    try {
      jwt.verify(token, PUBLIC_KEY, { algorithms: ['RS256'] });
    } catch (jwtError) {
      console.error('JWT validation failed:', jwtError.message);
      return res.status(401).json({ error: 'Invalid or expired token' });
    }

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