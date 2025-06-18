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

    // 2. Randomly pick a base URL for load balancing
    const randomIndex = Math.floor(Math.random() * SPREAD_ANALYZER_URLS.length);
    const baseUrl = SPREAD_ANALYZER_URLS[randomIndex];
    const endpoint = '/api/analyze_debit_spread';
    const targetUrl = baseUrl + endpoint;

    console.log(`Proxying spread analysis for ${ticker} to random Replit instance: #${randomIndex + 1} - ${targetUrl}`);

    // 3. Make the proxied request to the chosen Replit server
    const proxyResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Vercel-Proxy/1.0',
      },
      body: JSON.stringify({ ticker: ticker }),
      timeout: 28000 // 28-second timeout to avoid Vercel gateway timeouts
    });

    console.log(`Replit response status: ${proxyResponse.status}`);
    console.log(`Replit response headers:`, Object.fromEntries(proxyResponse.headers.entries()));

    // 4. Pipe the response back and cache if successful
    const responseBody = await proxyResponse.text();
    console.log(`Replit response body preview: ${responseBody.substring(0, 200)}...`);
    
    res.setHeader('Content-Type', proxyResponse.headers.get('Content-Type') || 'application/json');
    
    // Cache successful results
    if (proxyResponse.ok) {
      setCachedData(cacheKey, responseBody);
      console.log(`SAVED to cache: ${cacheKey}`);
    }
    
    res.status(proxyResponse.status).send(responseBody);

  } catch (error) {
    console.error(`Error proxying to spread analyzer: ${error.name} - ${error.message}`);
    res.status(502).json({ 
        success: false,
        error: 'The analysis service failed to respond.',
        details: error.message 
    });
  }
}