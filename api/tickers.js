const { Client } = require('pg');
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  let client;
  
  try {
    // Get query parameters - REMOVED DEFAULT LIMIT TO SHOW ALL RECORDS
    const { search = '', limit = '0' } = req.query;
    const limitNum = parseInt(limit);

    // Create cache key based on search and limit parameters
    const cacheKey = `scoreboard_data:${search}:${limit}`;
    console.log(`Cache key: ${cacheKey}`);

    // Check Redis cache first (1-minute TTL)
    try {
      const cachedData = await redis.get(cacheKey);
      if (cachedData) {
        console.log('✅ CACHE HIT - returning cached scoreboard data');
        return res.status(200).json({
          success: true,
          data: cachedData,
          cached: true
        });
      }
      console.log('CACHE MISS - fetching from database');
    } catch (redisError) {
      console.log('Redis cache error, proceeding with database query:', redisError.message);
    }

    // Check if DATABASE_URL exists
    if (!process.env.DATABASE_URL) {
      console.error('DATABASE_URL environment variable is not set');
      return res.status(500).json({
        success: false,
        error: 'Database configuration missing'
      });
    }

    // Connect to NeonDB with proper SSL configuration
    client = new Client({
      connectionString: process.env.DATABASE_URL,
      ssl: {
        rejectUnauthorized: false
      }
    });
    
    console.log('Connecting to NeonDB...');
    await client.connect();
    console.log('Connected to NeonDB successfully');
    
    const query = `
      SELECT 
        symbol, 
        total_score, 
        options_contracts_10_42_dte,
        current_price,
        -- Use boolean fields directly (no conversion needed!)
        trend1_pass,
        trend2_pass,
        snapback_pass,
        momentum_pass,
        stabilizing_pass,
        -- Include timestamp fields from actual schema
        price_updated,
        criteria_updated,
        options_updated
      FROM etf_scores 
      ORDER BY total_score DESC, options_contracts_10_42_dte DESC, symbol ASC
    `;
    
    console.log('Executing query...');
    const result = await client.query(query);
    console.log(`Query executed successfully, found ${result.rows.length} rows`);
    
    let tickers = result.rows;
    
    // Filter by search if provided
    if (search) {
      const searchUpper = search.toUpperCase();
      tickers = tickers.filter(ticker => 
        ticker.symbol.toUpperCase().includes(searchUpper)
      );
    }

    // Apply limit ONLY if explicitly requested (limit > 0)
    // Default behavior: Show ALL records (no limit)
    if (limitNum > 0) {
      tickers = tickers.slice(0, limitNum);
    }
    // If limitNum is 0 or not specified, show ALL records without limit

    // Cache the result for 1 minute (60 seconds)
    try {
      await redis.setex(cacheKey, 60, JSON.stringify(tickers));
      console.log('✅ Data cached successfully for 1 minute');
    } catch (redisError) {
      console.log('Failed to cache scoreboard data:', redisError.message);
    }

    res.status(200).json({
      success: true,
      data: tickers,
      count: tickers.length,
      cached: false
    });

  } catch (error) {
    console.error('Tickers API Error:', error);
    console.error('Error details:', {
      message: error.message,
      code: error.code,
      stack: error.stack
    });
    
    res.status(500).json({
      success: false,
      error: 'Failed to fetch ticker data',
      details: error.message,
      code: error.code
    });
  } finally {
    // Always close the connection
    if (client) {
      try {
        await client.end();
        console.log('Database connection closed');
      } catch (closeError) {
        console.error('Error closing database connection:', closeError);
      }
    }
  }
}