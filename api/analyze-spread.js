import { spawn } from 'child_process';
import path from 'path';
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

// Redundant spread analysis endpoints pool
const SPREAD_ANALYZER_ENDPOINTS = [
  'https://spreads-analysis-gipn.vercel.app/api/analyze_debit_spread',
  'https://spreads-analysis-4.vercel.app/api/analyze_debit_spread',
  'https://spreads-analysis-3.vercel.app/api/analyze_debit_spread',
  'https://spreads-analysis.vercel.app/api/analyze_debit_spread',
  'https://spreads-analysis-73sq.vercel.app/api/analyze_debit_spread'
];

// Shuffle array and return a copy for random endpoint selection
function shuffleEndpoints(endpoints) {
  const shuffled = [...endpoints];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

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

    // Redundant endpoint system with 3-try failover
    const shuffledEndpoints = shuffleEndpoints(SPREAD_ANALYZER_ENDPOINTS);
    const maxRetries = 3;
    let lastError = null;
    let proxyResponse = null;

    console.log(`Starting redundant spread analysis with ${maxRetries} endpoint attempts`);
    console.log(`Endpoint order: ${shuffledEndpoints.slice(0, maxRetries).join(' -> ')}`);
    console.log(`Request body: ${JSON.stringify({ ticker: ticker })}`);

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const currentEndpoint = shuffledEndpoints[attempt];
      console.log(`\n🔄 ATTEMPT ${attempt + 1}/${maxRetries}: ${currentEndpoint}`);

      try {
        // Use AbortController for proper timeout handling
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
          console.log(`⏰ Aborting request to ${currentEndpoint} due to timeout`);
          controller.abort();
        }, 30000); // 30 second timeout

        proxyResponse = await fetch(currentEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ticker: ticker }),
          signal: controller.signal
        });

        clearTimeout(timeoutId);
        
        console.log(`📊 Response from ${currentEndpoint}: ${proxyResponse.status}`);

        // Handle non-200 status codes as failures to try next endpoint
        if (!proxyResponse.ok) {
          const errorText = await proxyResponse.text();
          console.error(`❌ HTTP ${proxyResponse.status} error from ${currentEndpoint}: ${errorText}`);
          lastError = new Error(`HTTP ${proxyResponse.status} - ${currentEndpoint}`);
          continue; // Try next endpoint
        }

        // Success! Break out of retry loop
        console.log(`✅ SUCCESS: ${currentEndpoint} responded successfully`);
        break;

      } catch (error) {
        console.error(`❌ ERROR with ${currentEndpoint}: ${error.message}`);
        lastError = error;
        
        // Handle timeout errors - should retry next endpoint
        if (error.name === 'AbortError') {
          console.log(`⏰ TIMEOUT: ${currentEndpoint} timed out after 30s, trying next endpoint...`);
        }
        
        if (attempt === maxRetries - 1) {
          console.error(`💥 ALL ${maxRetries} ENDPOINTS FAILED`);
          throw new Error(`All analysis failed`);
        }
        
        console.log(`🔄 Trying next endpoint...`);
        continue; // Try next endpoint
      }
    }

    // Check if we have a successful response
    if (!proxyResponse || !proxyResponse.ok) {
      console.error(`💥 No successful response after ${maxRetries} attempts`);
      throw lastError || new Error('All endpoints failed');
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
    
    if (error.message === 'All analysis failed' || error.name === 'AbortError') {
      console.error(`All analysis methods failed`);
      res.status(504).json({ 
        success: false,
        error: 'All analysis failed',
        message: 'All analysis failed',
        user_message: 'All analysis failed. Please try again in a moment.',
        details: 'All analysis methods were attempted but none succeeded.',
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