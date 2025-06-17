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

// JWT validation middleware
const validateJWT = (req, res, next) => {
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
  
  try {
    console.log('Attempting JWT validation with token length:', token.length);
    const decoded = jwt.verify(token, PUBLIC_KEY, { algorithms: ['RS256'] });
    req.user = decoded;
    console.log('JWT validation successful for user:', decoded.sub);
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
    
    // Create cache key based on search and limit parameters
    const cacheKey = `scoreboard:${search || 'all'}:${limit || 'unlimited'}`;
    
    // Try to get data from Redis cache first (60 second TTL)
    try {
      const cachedData = await redis.get(cacheKey);
      if (cachedData) {
        console.log(`Loaded ${cachedData.length} tickers from cache`);
        return res.json(cachedData);
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
      (CASE WHEN trend1_pass THEN 1 ELSE 0 END + 
       CASE WHEN trend2_pass THEN 1 ELSE 0 END + 
       CASE WHEN snapback_pass THEN 1 ELSE 0 END + 
       CASE WHEN momentum_pass THEN 1 ELSE 0 END + 
       CASE WHEN stabilizing_pass THEN 1 ELSE 0 END) DESC, 
      options_contracts_10_42_dte DESC, 
      trading_volume DESC, 
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
    
    // Cache the processed data for 60 seconds
    try {
      await redis.setex(cacheKey, 60, JSON.stringify(processedRows));
      console.log(`Cached scoreboard data for 60 seconds`);
    } catch (redisError) {
      console.log('Failed to cache data in Redis:', redisError.message);
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
    
    console.log(`Loaded ticker details for ${symbol}`);
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

// Load balancing configuration for spread analysis APIs
const SPREAD_APIS = [
  'https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app',
  'https://income-machine-spread-check-2-daiadigitalco.replit.app',
  'https://income-machine-vip-spread-check-1-daiadigitalco.replit.app'
];

// Check API status and select best endpoint
async function selectBestSpreadAPI() {
  console.log('🔍 LOAD BALANCER: Checking status of all spread analysis APIs...');
  
  const statusPromises = SPREAD_APIS.map(async (apiUrl, index) => {
    try {
      console.log(`   📡 Checking API ${index + 1}: ${apiUrl}/api/status`);
      const statusResponse = await axios.get(`${apiUrl}/api/status`, { timeout: 5000 });
      const status = statusResponse.data.status || 0;
      console.log(`   ✅ API ${index + 1} response: ${status} concurrent requests`);
      return { apiUrl, status, available: true, index: index + 1 };
    } catch (error) {
      console.log(`   ❌ API ${index + 1} failed: ${error.message}`);
      return { apiUrl, status: 999, available: false, index: index + 1 }; // High status for unavailable APIs
    }
  });
  
  // Wait for all status checks to complete
  const apiStatuses = await Promise.all(statusPromises);
  
  console.log('📊 LOAD BALANCER: Status check results:');
  apiStatuses.forEach(api => {
    const statusText = api.available ? `${api.status} requests` : 'UNAVAILABLE';
    console.log(`   API ${api.index}: ${statusText}`);
  });
  
  // Sort by status (lowest first), prioritizing available APIs
  apiStatuses.sort((a, b) => {
    if (a.available && !b.available) return -1;
    if (!a.available && b.available) return 1;
    return a.status - b.status;
  });
  
  const selectedAPI = apiStatuses[0];
  console.log(`🎯 LOAD BALANCER: Selected API ${selectedAPI.index} with ${selectedAPI.status} concurrent requests`);
  console.log(`   Using endpoint: ${selectedAPI.apiUrl}`);
  
  return selectedAPI.apiUrl;
}

// Proxy endpoint for spread analysis to handle CORS
app.post('/api/analyze_debit_spread', async (req, res) => {
  console.log('POST /api/analyze_debit_spread called');
  console.log('Request body:', req.body);
  
  try {
    const { ticker } = req.body;
    if (!ticker) {
      console.log('Missing ticker in request body');
      return res.status(400).json({ error: 'Ticker is required' });
    }
    
    const cacheKey = `spread_analysis:${ticker.toUpperCase()}`;
    
    // Check Redis cache first (3-minute TTL)
    try {
      const cachedData = await redis.get(cacheKey);
      if (cachedData) {
        console.log(`Cache HIT for spread analysis: ${ticker}`);
        return res.json(JSON.parse(cachedData));
      }
    } catch (cacheError) {
      console.log('Cache miss or error:', cacheError.message);
    }
    
    console.log(`Fetching fresh spread analysis for ${ticker}...`);
    
    // Select the best available API endpoint based on current load
    const selectedAPI = await selectBestSpreadAPI();
    console.log(`Using API endpoint: ${selectedAPI}`);
    
    // Call external spread analysis API
    const response = await axios.post(
      `${selectedAPI}/api/analyze_debit_spread`,
      { ticker: ticker.toUpperCase() },
      {
        timeout: 30000,
        headers: { 'Content-Type': 'application/json' }
      }
    );
    
    if (response.status === 200 && response.data.success) {
      // Cache for 3 minutes (180 seconds)
      try {
        await redis.setex(cacheKey, 180, JSON.stringify(response.data));
        console.log(`Cached spread analysis for ${ticker} (3 min TTL)`);
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
    console.error('Spread analysis error:', error);
    
    if (error.code === 'ECONNABORTED') {
      return res.status(408).json({ error: 'Request timeout' });
    }
    
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
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

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`🚀 Income Machine Node.js server running on port ${port}`);
  console.log(`📊 Database: ${process.env.DATABASE_URL ? 'Connected' : 'Not configured'}`);
  console.log(`💾 Redis: ${process.env.UPSTASH_REDIS_REST_URL ? 'Connected' : 'Not configured'}`);
});

module.exports = app;