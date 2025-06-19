import { Client } from 'pg';
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

  try {
    const { symbol } = req.query;

    if (!symbol) {
      return res.status(400).json({
        success: false,
        error: 'Symbol is required'
      });
    }

    const symbolUpper = symbol.toUpperCase();
    const cacheKey = `ticker_details:${symbolUpper}`;
    console.log(`Cache key: ${cacheKey}`);

    // Check Redis cache first (1-minute TTL)
    try {
      const cachedResult = await redis.get(cacheKey);
      if (cachedResult) {
        console.log(`✅ CACHE HIT for ${symbolUpper}`);
        return res.status(200).json({
          success: true,
          data: cachedResult,
          cached: true
        });
      }
      console.log(`CACHE MISS for ${symbolUpper}. Fetching from database.`);
    } catch (redisError) {
      console.log('Redis cache error, proceeding with database query:', redisError.message);
    }
    
    // Fetch from the database
    const client = new Client({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
    });
    
    await client.connect();
    
    const query = `
      SELECT 
        symbol, 
        total_score, 
        trading_volume_20_day, 
        options_contracts_10_42_dte,
        current_price,
        -- Use boolean fields directly (no conversion needed!)
        trend1_pass,
        trend2_pass,
        snapback_pass,
        momentum_pass,
        stabilizing_pass,
        calculation_timestamp,
        data_age_hours
      FROM etf_scores 
      WHERE UPPER(symbol) = $1
    `;
    
    const result = await client.query(query, [symbolUpper]);
    
    await client.end();
    
    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Ticker not found'
      });
    }

    const tickerData = result.rows[0];

    // Cache the result for 1 minute (60 seconds)
    try {
      await redis.setex(cacheKey, 60, JSON.stringify(tickerData));
      console.log(`✅ Data cached successfully for ${symbolUpper} for 1 minute`);
    } catch (redisError) {
      console.log('Failed to cache ticker details:', redisError.message);
    }
    
    res.status(200).json({
      success: true,
      data: tickerData,
      cached: false
    });

  } catch (error) {
    console.error('Ticker details API error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch ticker details',
      details: error.message
    });
  }
} 