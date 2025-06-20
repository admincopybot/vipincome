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

  try {
    const { symbol } = req.query;

    if (!symbol) {
      return res.status(400).json({
        success: false,
        error: 'Symbol is required'
      });
    }

    const symbolUpper = symbol.toUpperCase();

    // Connect to database
    const client = new Client({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
    });
    
    await client.connect();
    
    const query = `
      SELECT symbol, total_score, trading_volume_20_day, options_contracts_10_42_dte
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

    const ticker = result.rows[0];

    res.status(200).json({
      success: true,
      data: ticker
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