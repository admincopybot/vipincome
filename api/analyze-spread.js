import { spawn } from 'child_process';
import path from 'path';
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

// Single dedicated spread analysis endpoint
const SPREAD_ANALYZER_URL = 'https://spreads-analysis-73sq.vercel.app/api/analyze_debit_spread';

export default async function handler(req, res) {
  // Set CORS headers for Vercel
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
    let requestData;
    if (typeof req.body === 'string') {
        try {
            requestData = JSON.parse(req.body);
        } catch (e) {
            return res.status(400).json({ error: 'Invalid JSON in request body' });
        }
    } else {
        requestData = req.body || {};
    }

    const { ticker } = requestData;

    if (!ticker) {
      return res.status(400).json({ error: 'Ticker symbol is required' });
    }
    
    const cacheKey = `spread_analysis:${ticker.toUpperCase()}`;
    console.log(`Cache key: ${cacheKey}`);

    // Check Redis cache first (1-minute TTL)
    try {
      const cachedResult = await redis.get(cacheKey);
      if (cachedResult) {
        console.log(`✅ CACHE HIT for spread analysis: ${cacheKey}`);
        // Parse cached result and add cached flag
        let cachedData;
        try {
          cachedData = typeof cachedResult === 'string' ? JSON.parse(cachedResult) : cachedResult;
        } catch (e) {
          cachedData = cachedResult;
        }
        
        // Add cached flag to the data and send as-is (no extra wrapping)
        cachedData.cached = true;
        
        res.setHeader('Content-Type', 'application/json');
        res.status(200).json(cachedData);
        return;
      }
      console.log(`CACHE MISS for spread analysis: ${cacheKey}. Proxying to Replit.`);
    } catch (redisError) {
      console.log('Redis cache error, proceeding with API call:', redisError.message);
    }

    console.log(`Calling spread analysis API: ${SPREAD_ANALYZER_URL}`);
    console.log(`Request body: ${JSON.stringify({ ticker: ticker })}`);

    // Use AbortController for proper timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      console.log(`Aborting request due to timeout`);
      controller.abort();
    }, 30000); // 30 second timeout

    const proxyResponse = await fetch(SPREAD_ANALYZER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ticker: ticker }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);
    
    console.log(`Response status: ${proxyResponse.status}`);
    console.log(`Response headers: ${JSON.stringify(Object.fromEntries(proxyResponse.headers.entries()))}`);

    // Handle non-200 status codes
    if (!proxyResponse.ok) {
      console.error(`HTTP ${proxyResponse.status} error from spread analysis service`);
      throw new Error(`HTTP ${proxyResponse.status} - Analysis service error`);
    }

    const responseBody = await proxyResponse.text();
    console.log(`Response body (first 300 chars): ${responseBody.substring(0, 300)}`);
    
    // Validate JSON response
    let responseData;
    try {
      responseData = JSON.parse(responseBody);
    } catch (e) {
      console.error(`Invalid JSON response from analysis service`);
      throw new Error(`Invalid JSON response from analysis service`);
    }
    
    // Cache successful results for 1 minute (60 seconds)
    try {
      await redis.setex(cacheKey, 60, responseBody);
      console.log(`✅ SAVED spread analysis to cache: ${cacheKey} for 1 minute`);
    } catch (redisError) {
      console.log('Failed to cache spread analysis:', redisError.message);
    }
    
    res.setHeader('Content-Type', proxyResponse.headers.get('Content-Type') || 'application/json');
    res.status(proxyResponse.status).send(responseBody);

  } catch (error) {
    console.error(`Error in spread analysis: ${error.name} - ${error.message}`);
    console.error(`Error stack: ${error.stack}`);
    
    if (error.name === 'AbortError') {
      console.error(`Request timed out after 30 seconds`);
      res.status(504).json({ 
        success: false,
        error: 'Request timeout',
        message: 'Could not find any trades at this moment',
        user_message: 'Could not find any trades at this moment. The system is experiencing high load.',
        details: 'The analysis service took too long to respond. Please try again in a moment.',
        action_required: 'Please wait a moment and try again.'
      });
    } else if (error.message.includes('404') || error.message.includes('Not Found')) {
      res.status(404).json({ 
        success: false,
        error: 'Service not found',
        message: 'Could not find any trades at this moment',
        user_message: 'Could not find any trades at this moment. The analysis service may be temporarily unavailable.',
        details: error.message,
        action_required: 'Please try again in a few minutes.'
      });
    } else if (error.message.includes('timeout') || error.message.includes('Timeout')) {
      res.status(504).json({ 
        success: false,
        error: 'Request timeout',
        message: 'Could not find any trades at this moment',
        user_message: 'Could not find any trades at this moment. The system is experiencing high load.',
        details: error.message,
        action_required: 'Please wait a moment and try again.'
      });
    } else {
      res.status(502).json({ 
        success: false,
        error: 'Service error',
        message: 'Could not find any trades at this moment',
        user_message: 'Could not find any trades at this moment. There was an unexpected error with the analysis service.',
        details: error.message,
        action_required: 'Please try again or contact support if this persists.'
      });
    }
  }
}