const { Client } = require('pg');

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
    // Get query parameters
    const { search = '', limit = '280' } = req.query;
    const limitNum = parseInt(limit);

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
      SELECT symbol, total_score, trading_volume_20_day, options_contracts_10_42_dte
      FROM etf_scores 
      WHERE options_contracts_10_42_dte >= 100
      ORDER BY total_score DESC, options_contracts_10_42_dte DESC, trading_volume_20_day DESC, symbol ASC
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

    // Apply limit
    if (limitNum > 0) {
      tickers = tickers.slice(0, limitNum);
    }

    res.status(200).json({
      success: true,
      data: tickers,
      count: tickers.length
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