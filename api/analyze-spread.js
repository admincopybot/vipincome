import { spawn } from 'child_process';
import path from 'path';

// Simple in-memory cache for 60 seconds
const cache = new Map();
const CACHE_TTL = 60 * 1000; // 60 seconds in milliseconds

function getCachedData(key) {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }
  // Remove expired entry
  if (cached) {
    cache.delete(key);
  }
  return null;
}

function setCachedData(key, data) {
  cache.set(key, {
    data: data,
    timestamp: Date.now()
  });
}

// A list of your 20 load-balanced Replit instances for spread analysis.
const SPREAD_ANALYZER_URLS = [
  'https://income-machine-spread-machine-1-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-2-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-3-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-4-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-5-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-6-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-7-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-8-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-9-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-10-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-11-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-12-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-13-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-14-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-15-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-16-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-17-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-18-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-19-daiadigitalco.replit.app',
  'https://income-machine-spread-machine-20-daiadigitalco.replit.app'
];

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
    
    const cacheKey = `spread-analysis:${ticker.toUpperCase()}`;

    // Check local cache first
    const cachedResult = getCachedData(cacheKey);
    if (cachedResult) {
      console.log(`CACHE HIT for spread analysis: ${cacheKey}`);
      res.setHeader('Content-Type', 'application/json');
      res.status(200).send(cachedResult);
      return;
    }

    console.log(`CACHE MISS for spread analysis: ${cacheKey}. Proxying to Replit.`);

    // Pick a random Replit instance
    const randomIndex = Math.floor(Math.random() * SPREAD_ANALYZER_URLS.length);
    const baseUrl = SPREAD_ANALYZER_URLS[randomIndex];
    const targetUrl = `${baseUrl}/api/analyze_debit_spread`;

    console.log(`Proxying to: ${targetUrl}`);
    console.log(`Request body: ${JSON.stringify({ ticker: ticker })}`);

    // Use AbortController for proper timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      console.log(`Aborting request due to timeout`);
      controller.abort();
    }, 25000); // 25 second timeout

    const proxyResponse = await fetch(targetUrl, {
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

    const responseBody = await proxyResponse.text();
    console.log(`Response body (first 300 chars): ${responseBody.substring(0, 300)}`);
    
    // STRICT VALIDATION: Reject any mock/demo data responses
    const mockDataIndicators = [
      'Simplified Spread Pricing',
      'Restored Working Version',
      'Demo',
      'Mock',
      'Test Data',
      'Fake',
      'Sample'
    ];
    
    let responseData;
    try {
      responseData = JSON.parse(responseBody);
    } catch (e) {
      console.error(`Invalid JSON response from Replit instance #${randomIndex + 1}`);
      throw new Error(`Invalid JSON response from analysis service`);
    }
    
    // Check if this looks like mock data
    const responseStr = JSON.stringify(responseData).toLowerCase();
    const isMockData = mockDataIndicators.some(indicator => 
      responseStr.includes(indicator.toLowerCase())
    );
    
    if (isMockData) {
      console.error(`🚨 MOCK DATA DETECTED from instance #${randomIndex + 1}! Response contains mock indicators.`);
      console.error(`Mock response preview: ${responseBody.substring(0, 500)}`);
      
      // Try a different instance if we detect mock data
      const retryIndex = (randomIndex + 1) % SPREAD_ANALYZER_URLS.length;
      const retryUrl = `${SPREAD_ANALYZER_URLS[retryIndex]}/api/analyze_debit_spread`;
      
      console.log(`Retrying with instance #${retryIndex + 1}: ${retryUrl}`);
      
      const retryController = new AbortController();
      const retryTimeoutId = setTimeout(() => {
        console.log(`Aborting retry request due to timeout`);
        retryController.abort();
      }, 20000); // Shorter timeout for retry
      
      try {
        const retryResponse = await fetch(retryUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ticker: ticker }),
          signal: retryController.signal
        });
        
        clearTimeout(retryTimeoutId);
        
        const retryBody = await retryResponse.text();
        console.log(`Retry response (first 300 chars): ${retryBody.substring(0, 300)}`);
        
        // Check retry response for mock data too
        const retryStr = retryBody.toLowerCase();
        const isRetryMockData = mockDataIndicators.some(indicator => 
          retryStr.includes(indicator.toLowerCase())
        );
        
        if (isRetryMockData) {
          console.error(`🚨 RETRY ALSO RETURNED MOCK DATA from instance #${retryIndex + 1}!`);
          throw new Error(`Analysis service is returning mock data instead of real results`);
        }
        
        // Retry was successful and real
        if (retryResponse.ok) {
          setCachedData(cacheKey, retryBody);
          console.log(`SAVED REAL DATA to cache: ${cacheKey}`);
        }
        
        res.setHeader('Content-Type', retryResponse.headers.get('Content-Type') || 'application/json');
        res.status(retryResponse.status).send(retryBody);
        return;
        
      } catch (retryError) {
        clearTimeout(retryTimeoutId);
        console.error(`Retry also failed: ${retryError.message}`);
        throw new Error(`Both primary and retry instances failed. Primary returned mock data, retry failed: ${retryError.message}`);
      }
    }
    
    // Original response was real data
    res.setHeader('Content-Type', proxyResponse.headers.get('Content-Type') || 'application/json');
    
    // Cache successful results
    if (proxyResponse.ok) {
      setCachedData(cacheKey, responseBody);
      console.log(`SAVED to cache: ${cacheKey}`);
    }
    
    res.status(proxyResponse.status).send(responseBody);

  } catch (error) {
    if (error.name === 'AbortError') {
      console.error(`Request timed out after 25 seconds`);
      res.status(504).json({ 
        success: false,
        error: 'Request timed out',
        details: 'The analysis service took too long to respond (>25 seconds)'
      });
    } else {
      console.error(`Error in spread analysis: ${error.name} - ${error.message}`);
      console.error(`Error stack: ${error.stack}`);
      
      // Check if the error message indicates mock data was detected
      if (error.message.includes('mock data') || error.message.includes('Mock data')) {
        res.status(422).json({ 
          success: false,
          error: 'MOCK DATA DETECTED',
          message: 'The analysis service returned test/demo data instead of real market data. This has been blocked to ensure data quality.',
          details: error.message,
          action_required: 'Please try again or contact support if this persists.'
        });
      } else {
        res.status(502).json({ 
          success: false,
          error: 'Service error',
          details: error.message 
        });
      }
    }
  }
}