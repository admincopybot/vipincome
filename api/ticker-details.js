import { Client } from 'pg';
import redis from '../../lib/redis'; // Import our new Redis utility

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
    const cacheKey = `ticker-details:${symbolUpper}`;

    // 1. Check Redis cache first
    try {
      const cachedResult = await redis.get(cacheKey);
      if (cachedResult) {
        console.log(`CACHE HIT for ${symbolUpper}`);
        return res.status(200).json({
          success: true,
          data: JSON.parse(cachedResult),
          source: 'cache'
        });
      }
    } catch (cacheError) {
        console.warn(`Redis GET error for ${cacheKey}:`, cacheError.message);
    }

    console.log(`CACHE MISS for ${symbolUpper}. Fetching from database.`);
    
    // 2. If not in cache, fetch from the database
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
        CASE WHEN trend1_pass = 'YES' THEN true ELSE false END as trend1_pass,
        CASE WHEN trend2_pass = 'YES' THEN true ELSE false END as trend2_pass,
        CASE WHEN snapback_pass = 'YES' THEN true ELSE false END as snapback_pass,
        CASE WHEN momentum_pass = 'YES' THEN true ELSE false END as momentum_pass,
        CASE WHEN stabilizing_pass = 'YES' THEN true ELSE false END as stabilizing_pass
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

    // 3. Save the result to Redis with a 24-hour expiration
    try {
        await redis.set(cacheKey, JSON.stringify(tickerData), { ex: 86400 }); // 24 hours
        console.log(`SAVED to cache: ${cacheKey}`);
    } catch (cacheError) {
        console.warn(`Redis SET error for ${cacheKey}:`, cacheError.message);
    }
    
    res.status(200).json({
      success: true,
      data: tickerData,
      source: 'database'
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