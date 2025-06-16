const express = require('express');
const { Pool } = require('pg');
const jwt = require('jsonwebtoken');
const axios = require('axios');
const { Redis } = require('@upstash/redis');
const path = require('path');

const app = express();
const port = process.env.PORT || 5000;

// Middleware
app.use(express.json());
app.use(express.static('public'));
app.use(express.static('.next/static'));

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

// Redis connection
const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

// JWT Public Key
const PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f5wg5l2hKsTeNem/V41
fGnJm6gOdrj8ym3rFkEjWT2btf06kkstX0BdVqKyGJm7TQsLt3nLDj9dxKwNsU0f
Vp4H3VHZrQNxVOgB2wG6dRkj7w+7QbqMTBJfEVUhkE9g0fOhp9Xg4GdO8g7N1qPb
f8n0WzGLWVFT5XPTfp5PaO3F6Q8Z5g5v1p4A2O4F8DQ8+P6K+N9w6zKtW5f6qW8x
f+bT7I7KqGbTr2XM7A3t0vOj5VRe8VQ7kK7Af6z8hD2L9Rg6K5z8X7g0+hWJn5zE
YOJr7qFzO5zRoE8TI6L8c4aZ6Eq2G6yKo8Y5J7cxW1yV+Q+p9zKJ9nK7p1Q2ov5X
QIDAQAB
-----END PUBLIC KEY-----`;

// Middleware to validate JWT
const validateJWT = (req, res, next) => {
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  const token = authHeader.substring(7);
  
  try {
    const decoded = jwt.verify(token, PUBLIC_KEY, { algorithms: ['RS256'] });
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};

// API Routes
app.get('/api/tickers', validateJWT, async (req, res) => {
  try {
    const { search, limit } = req.query;
    
    let query = `
      SELECT 
        symbol, current_price, score,
        trend1_pass, trend1_current, trend1_threshold, trend1_description,
        trend2_pass, trend2_current, trend2_threshold, trend2_description,
        snapback_pass, snapback_current, snapback_threshold, snapback_description,
        momentum_pass, momentum_current, momentum_threshold, momentum_description,
        stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
        trading_volume, options_contracts_10_42_dte, last_updated
      FROM etf_scores
    `;
    
    let params = [];
    
    if (search) {
      query += ` WHERE symbol ILIKE $1`;
      params.push(`%${search.toUpperCase()}%`);
    }
    
    query += ` ORDER BY score DESC, options_contracts_10_42_dte DESC, trading_volume DESC, symbol ASC`;
    
    if (limit) {
      const limitIndex = params.length + 1;
      query += ` LIMIT $${limitIndex}`;
      params.push(parseInt(limit, 10));
    }
    
    const result = await pool.query(query, params);
    res.json(result.rows);
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
        symbol, current_price, score,
        trend1_pass, trend1_current, trend1_threshold, trend1_description,
        trend2_pass, trend2_current, trend2_threshold, trend2_description,
        snapback_pass, snapback_current, snapback_threshold, snapback_description,
        momentum_pass, momentum_current, momentum_threshold, momentum_description,
        stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
        trading_volume, options_contracts_10_42_dte, last_updated
      FROM etf_scores 
      WHERE symbol = $1
    `;
    
    const result = await pool.query(query, [symbol.toUpperCase()]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Ticker not found' });
    }
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error('Database error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.post('/api/analyze/:symbol', validateJWT, async (req, res) => {
  try {
    const { symbol } = req.params;
    const cacheKey = `spread_analysis:${symbol.toUpperCase()}`;
    
    // Check Redis cache first
    const cachedData = await redis.get(cacheKey);
    if (cachedData) {
      return res.json(JSON.parse(cachedData));
    }
    
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
      // Cache for 3 minutes
      await redis.setex(cacheKey, 180, JSON.stringify(response.data));
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
    
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Serve the main application
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/ticker/:symbol', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'ticker.html'));
});

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`🚀 Income Machine server running on port ${port}`);
});

module.exports = app;