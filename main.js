// Pure Node.js Income Machine Application
// Eliminates all Python dependencies while maintaining identical functionality

const express = require('express');
const { Pool } = require('pg');
const jwt = require('jsonwebtoken');
const axios = require('axios');
const { Redis } = require('@upstash/redis');
const path = require('path');

const app = express();
const port = process.env.PORT || 5001;

// Middleware
app.use(express.json());
app.use(express.static('public'));

// Explicit favicon routes for custom domains
app.get('/favicon.ico', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'favicon.png'));
});

app.get('/favicon.png', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'favicon.png'));
});

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

// Redis connection for caching
const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

// JWT Public Key for OneClick Trading authentication
const PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtSt0xH5N6SOVXY4E2h1X
WE6edernQCmw2kfg6023C64hYR4PZH8XM2P9qoyAzq19UDJZbVj4hi/75GKHEFBC
zL+SrJLgc/6jZoMpOYtEhDgzEKKdfFtgpGD18Idc5IyvBLeW2d8gvfIJMuxRUnT6
K3spmisjdZtd+7bwMKPl6BGAsxZbhlkGjLI1gP/fHrdfU2uoL5okxbbzg1NH95xc
LSXX2JJ+q//t8vLGy+zMh8HPqFM9ojsxzT97AiR7uZZPBvR6c/rX5GDIFPvo5QVr
crCucCyTMeYqwyGl14zN0rArFi6eFXDn+JWTs3Qf04F8LQn7TiwxKV9KRgPHYFtG
qwIDAQAB
-----END PUBLIC KEY-----`;

// JWT validation middleware with Redis caching
const validateJWT = async (req, res, next) => {
  // Check for token in Authorization header or URL parameter
  let token = null;
  
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    token = authHeader.substring(7);
  } else if (req.query.token) {
    token = req.query.token;
  }
  
  if (!token) {
    return res.status(401).json({ error: 'Unauthorized - No token provided' });
  }
  
  // Create cache key from token hash to avoid storing full token
  const tokenHash = require('crypto').createHash('sha256').update(token).digest('hex').substring(0, 16);
  const cacheKey = `jwt_validation:${tokenHash}`;
  
  // Try Redis cache first (10 minutes TTL)
  try {
    const cachedUserStr = await redis.get(cacheKey);
    if (cachedUserStr) {
      const cachedUser = JSON.parse(cachedUserStr);
      req.user = cachedUser;
      console.log('JWT validation from cache for user:', cachedUser.sub);
      return next();
    }
  } catch (redisError) {
    // Continue with normal validation if cache fails
  }
  
  try {
    console.log('Attempting JWT validation with token length:', token.length);
    const decoded = jwt.verify(token, PUBLIC_KEY, { algorithms: ['RS256'] });
    req.user = decoded;
    console.log('JWT validation successful for user:', decoded.sub);
    
    // Cache the decoded user for 10 minutes
    try {
      await redis.setex(cacheKey, 600, JSON.stringify(decoded));
    } catch (redisError) {
      console.log('Failed to cache JWT validation:', redisError.message);
    }
    
    next();
  } catch (error) {
    console.log('JWT validation failed:', error.message);
    console.log('Token preview:', token.substring(0, 50) + '...');
    return res.status(401).json({ error: 'Invalid token', details: error.message });
  }
};

// API Routes
app.get('/api/tickers', validateJWT, async (req, res) => {
  try {
    const { search, limit } = req.query;
    
    // Use a single cache key for all scoreboard data
    const cacheKey = 'scoreboard_data';
    
    // Try to get data from Redis cache first (60 second TTL)
    try {
      const cachedDataStr = await redis.get(cacheKey);
      if (cachedDataStr) {
        const cachedData = JSON.parse(cachedDataStr);
        console.log(`Loaded ${cachedData.length} tickers from cache`);
        
        // Apply search and limit filters to cached data
        let filteredData = cachedData;
        
        if (search) {
          filteredData = cachedData.filter(ticker => 
            ticker.symbol.toUpperCase().includes(search.toUpperCase())
          );
        }
        
        if (limit) {
          filteredData = filteredData.slice(0, parseInt(limit, 10));
        }
        
        return res.json(filteredData);
      }
    } catch (redisError) {
      console.log('Redis cache miss or error, fetching from database');
    }
    
    let query = `
      SELECT 
        symbol, current_price, total_score as score,
        trend1_pass, trend1_current, trend1_threshold, trend1_description,
        trend2_pass, trend2_current, trend2_threshold, trend2_description,
        snapback_pass, snapback_current, snapback_threshold, snapback_description,
        momentum_pass, momentum_current, momentum_threshold, momentum_description,
        stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
        trading_volume_20_day as trading_volume, options_contracts_10_42_dte, 
        calculation_timestamp as last_updated
      FROM etf_scores
    `;
    
    let params = [];
    
    if (search) {
      query += ` WHERE symbol ILIKE $1`;
      params.push(`%${search.toUpperCase()}%`);
    }
    
    query += ` ORDER BY 
      total_score DESC, 
      options_contracts_10_42_dte DESC, 
      trading_volume_20_day DESC, 
      symbol ASC`;
    
    if (limit) {
      const limitIndex = params.length + 1;
      query += ` LIMIT $${limitIndex}`;
      params.push(parseInt(limit, 10));
    }
    
    const result = await pool.query(query, params);
    console.log(`Loaded ${result.rows.length} tickers from database`);
    
    // Convert PostgreSQL boolean strings to actual booleans
    const processedRows = result.rows.map(row => ({
      ...row,
      trend1_pass: row.trend1_pass === 't' || row.trend1_pass === true,
      trend2_pass: row.trend2_pass === 't' || row.trend2_pass === true,
      snapback_pass: row.snapback_pass === 't' || row.snapback_pass === true,
      momentum_pass: row.momentum_pass === 't' || row.momentum_pass === true,
      stabilizing_pass: row.stabilizing_pass === 't' || row.stabilizing_pass === true
    }));
    
    // Cache the processed data for 60 seconds (only cache full dataset)
    if (!search && !limit) {
      try {
        await redis.setex(cacheKey, 60, JSON.stringify(processedRows));
        console.log(`Cached scoreboard data for 60 seconds`);
      } catch (redisError) {
        console.log('Failed to cache data in Redis:', redisError.message);
      }
    }
    
    res.json(processedRows);
  } catch (error) {
    console.error('Database error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/api/ticker/:symbol', validateJWT, async (req, res) => {
  try {
    const { symbol } = req.params;
    const cacheKey = `ticker_details:${symbol.toUpperCase()}`;
    
    // Try Redis cache first (5 minutes TTL)
    try {
      const cachedDataStr = await redis.get(cacheKey);
      if (cachedDataStr) {
        const cachedData = JSON.parse(cachedDataStr);
        console.log(`Loaded ticker details for ${symbol} from cache`);
        return res.json(cachedData);
      }
    } catch (redisError) {
      console.log('Redis cache miss for ticker details, fetching from database');
    }
    
    const query = `
      SELECT 
        symbol, current_price, total_score as score,
        trend1_pass, trend1_current, trend1_threshold, trend1_description,
        trend2_pass, trend2_current, trend2_threshold, trend2_description,
        snapback_pass, snapback_current, snapback_threshold, snapback_description,
        momentum_pass, momentum_current, momentum_threshold, momentum_description,
        stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
        trading_volume_20_day as trading_volume, options_contracts_10_42_dte, 
        calculation_timestamp as last_updated
      FROM etf_scores 
      WHERE symbol = $1
    `;
    
    const result = await pool.query(query, [symbol.toUpperCase()]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Ticker not found' });
    }
    
    // Convert PostgreSQL boolean strings to actual booleans
    const ticker = {
      ...result.rows[0],
      trend1_pass: result.rows[0].trend1_pass === 't' || result.rows[0].trend1_pass === true,
      trend2_pass: result.rows[0].trend2_pass === 't' || result.rows[0].trend2_pass === true,
      snapback_pass: result.rows[0].snapback_pass === 't' || result.rows[0].snapback_pass === true,
      momentum_pass: result.rows[0].momentum_pass === 't' || result.rows[0].momentum_pass === true,
      stabilizing_pass: result.rows[0].stabilizing_pass === 't' || result.rows[0].stabilizing_pass === true
    };
    
    // Cache for 5 minutes
    try {
      await redis.setex(cacheKey, 300, JSON.stringify(ticker));
      console.log(`Cached ticker details for ${symbol} for 5 minutes`);
    } catch (redisError) {
      console.log('Failed to cache ticker details:', redisError.message);
    }
    
    console.log(`Loaded ticker details for ${symbol} from database`);
    res.json(ticker);
  } catch (error) {
    console.error('Database error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.post('/api/analyze/:symbol', validateJWT, async (req, res) => {
  try {
    const { symbol } = req.params;
    const cacheKey = `spread_analysis:${symbol.toUpperCase()}`;
    
    // Check Redis cache first (3-minute TTL)
    try {
      const cachedData = await redis.get(cacheKey);
      if (cachedData) {
        console.log(`Cache HIT for spread analysis: ${symbol}`);
        return res.json(JSON.parse(cachedData));
      }
    } catch (cacheError) {
      console.log('Cache miss or error:', cacheError.message);
    }
    
    console.log(`Fetching fresh spread analysis for ${symbol}...`);
    
    // Call external spread analysis API
    const response = await axios.post(
      'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread',
      { ticker: symbol.toUpperCase() },
      {
        timeout: 30000,
        headers: { 'Content-Type': 'application/json' }
      }
    );
    
    if (response.status === 200 && response.data.success) {
      // Cache for 3 minutes (180 seconds)
      try {
        await redis.setex(cacheKey, 180, JSON.stringify(response.data));
        console.log(`Cached spread analysis for ${symbol} (3 min TTL)`);
      } catch (cacheError) {
        console.log('Cache set error:', cacheError.message);
      }
      
      res.json(response.data);
    } else {
      res.status(500).json({ 
        error: 'Failed to analyze spreads',
        details: response.data 
      });
    }
  } catch (error) {
    console.error('Spread analysis error:', error.message);
    
    if (error.code === 'ECONNABORTED') {
      return res.status(408).json({ error: 'Request timeout' });
    }
    
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Removed progress polling system - now using simple time-based simulation

// Proxy endpoint for spread analysis to handle CORS
app.post('/api/analyze_debit_spread', async (req, res) => {
  console.log('=== STEP 3 API ENDPOINT CALLED ===');
  console.log('Request body:', req.body);
  console.log('Request timestamp:', new Date().toISOString());
  
  const { ticker } = req.body;
  if (!ticker) {
    console.log('ERROR: Missing ticker in request body');
    return res.status(400).json({ error: 'Ticker is required' });
  }
  
  const tickerUpper = ticker.toUpperCase();
  const cacheKey = `spread_analysis:${tickerUpper}`;
  
  // Try Redis cache first (3 minutes TTL)
  try {
    const cachedDataStr = await redis.get(cacheKey);
    if (cachedDataStr) {
      const cachedData = JSON.parse(cachedDataStr);
      console.log(`=== CACHE HIT: RETURNING CACHED SPREAD DATA FOR ${tickerUpper} ===`);
      return res.json(cachedData);
    }
  } catch (redisError) {
    console.log('Redis cache miss for spread analysis, proceeding with API calls');
  }
  
  console.log(`=== STARTING FAILOVER SEQUENCE FOR ${tickerUpper} ===`);
  
  // Primary and fallback endpoints
  const endpoints = [
    'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread',
    'https://income-machine-spread-check-try-2-real-daiadigitalco.replit.app/api/analyze_debit_spread',
    'https://income-machine-spread-check-try-3-real-daiadigitalco.replit.app/api/analyze_debit_spread'
  ];
  
  let lastError = null;
  
  // Try each endpoint in sequence
  for (let i = 0; i < endpoints.length; i++) {
    try {
      console.log(`=== ATTEMPTING ENDPOINT ${i + 1}/${endpoints.length} ===`);
      console.log(`URL: ${endpoints[i]}`);
      console.log(`Payload: {"ticker": "${ticker.toUpperCase()}"}`);
      console.log(`Timeout: 15 seconds`);
      
      const startTime = Date.now();
      
      const response = await axios.post(
        endpoints[i],
        { ticker: ticker.toUpperCase() },
        {
          timeout: 15000, // Reduced to 15 seconds for faster failover
          headers: { 'Content-Type': 'application/json' }
        }
      );
      
      const responseTime = Date.now() - startTime;
      console.log(`=== ENDPOINT ${i + 1} RESPONSE RECEIVED ===`);
      console.log(`Response time: ${responseTime}ms`);
      console.log(`Status: ${response.status}`);
      console.log(`Content-Type: ${response.headers['content-type']}`);
      console.log(`Response preview: ${JSON.stringify(response.data).substring(0, 200)}...`);
      
      if (response.status === 200) {
        // Check if response is HTML (endpoint starting up) instead of JSON
        if (typeof response.data === 'string' && response.data.includes('<html>')) {
          console.log(`=== ENDPOINT ${i + 1} FAILED: HTML STARTUP PAGE ===`);
          throw new Error('Endpoint returning HTML startup page');
        }
        
        // Check if response has proper spread data structure
        if (!response.data || !response.data.strategies) {
          console.log(`=== ENDPOINT ${i + 1} FAILED: INVALID JSON STRUCTURE ===`);
          throw new Error('Invalid JSON response structure');
        }
        
        console.log(`=== SUCCESS: ENDPOINT ${i + 1} PROVIDED VALID DATA ===`);
        console.log(`Strategies found: ${Object.keys(response.data.strategies || {}).length}`);
        
        // Cache the successful response for 3 minutes
        try {
          await redis.setex(cacheKey, 180, JSON.stringify(response.data));
          console.log(`=== CACHED SPREAD DATA FOR ${tickerUpper} (3 MIN TTL) ===`);
        } catch (redisError) {
          console.log('Failed to cache spread analysis:', redisError.message);
        }
        
        return res.json(response.data);
      } else {
        console.log(`=== ENDPOINT ${i + 1} FAILED: NON-200 STATUS ===`);
        throw new Error(`HTTP ${response.status}`);
      }
      
    } catch (error) {
      console.log(`=== ENDPOINT ${i + 1} FAILED ===`);
      console.log(`Error type: ${error.constructor.name}`);
      console.log(`Error code: ${error.code}`);
      console.log(`Error message: ${error.message}`);
      
      lastError = error;
      
      // Continue to next endpoint if available
      if (i < endpoints.length - 1) {
        console.log(`=== FAILING OVER TO ENDPOINT ${i + 2} ===`);
        continue;
      }
    }
  }
  
  // All endpoints failed
  console.log('=== ALL ENDPOINTS FAILED ===');
  console.log(`Final error: ${lastError.message}`);
  
  // Return appropriate error based on last failure
  if (lastError.code === 'ECONNABORTED' || lastError.message.includes('timeout')) {
    console.log('Returning timeout error');
    return res.status(408).json({ 
      error: 'All spread analysis services are currently overloaded. Please try again in a moment.',
      code: 'TIMEOUT'
    });
  }
  
  console.log('Returning general error');
  res.status(500).json({ 
    error: 'Spread analysis services are temporarily unavailable. Please try again.',
    details: lastError.message 
  });
});

// Serve the main application
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/ticker/:symbol', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'ticker.html'));
});

// Test endpoint to verify POST routing
app.post('/api/test', (req, res) => {
  console.log('POST /api/test called successfully');
  res.json({ success: true, message: 'POST routing works', body: req.body });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    service: 'Income Machine Node.js',
    timestamp: new Date().toISOString()
  });
});

// Redis cache testing endpoints
app.get('/api/cache/test', async (req, res) => {
  try {
    const testKey = 'cache_test';
    const testData = { message: 'Redis is working!', timestamp: new Date().toISOString() };
    
    // Set test data
    await redis.setex(testKey, 60, JSON.stringify(testData));
    
    // Get test data
    const retrieved = await redis.get(testKey);
    const parsed = JSON.parse(retrieved);
    
    res.json({
      success: true,
      message: 'Redis cache test successful',
      data: parsed
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Redis cache test failed',
      details: error.message
    });
  }
});

app.get('/api/cache/stats', async (req, res) => {
  try {
    const keys = await redis.keys('*');
    const cacheStats = {
      total_keys: keys.length,
      cache_keys: {
        scoreboard: keys.filter(k => k.includes('scoreboard')).length,
        jwt_validations: keys.filter(k => k.includes('jwt_validation')).length,
        ticker_details: keys.filter(k => k.includes('ticker_details')).length,
        spread_analysis: keys.filter(k => k.includes('spread_analysis')).length
      },
      all_keys: keys
    };
    
    res.json(cacheStats);
  } catch (error) {
    res.status(500).json({
      error: 'Failed to get cache stats',
      details: error.message
    });
  }
});

app.delete('/api/cache/clear', async (req, res) => {
  try {
    const keys = await redis.keys('*');
    if (keys.length > 0) {
      await redis.del(...keys);
    }
    
    res.json({
      success: true,
      message: `Cleared ${keys.length} cache entries`,
      cleared_keys: keys
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to clear cache',
      details: error.message
    });
  }
});

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`🚀 Income Machine Node.js server running on port ${port}`);
  console.log(`📊 Database: ${process.env.DATABASE_URL ? 'Connected' : 'Not configured'}`);
  console.log(`💾 Redis: ${process.env.UPSTASH_REDIS_REST_URL ? 'Connected' : 'Not configured'}`);
});

module.exports = app;