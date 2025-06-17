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
    // Get query parameters
    const { search = '', limit = '280' } = req.query;
    const limitNum = parseInt(limit);

    // Connect to database
    const client = new Client({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
    });
    
    await client.connect();
    
    const query = `
      SELECT symbol, total_score, trading_volume_20_day, options_contracts_10_42_dte
      FROM etf_scores 
      WHERE options_contracts_10_42_dte >= 100
      ORDER BY total_score DESC, options_contracts_10_42_dte DESC, trading_volume_20_day DESC, symbol ASC
    `;
    
    const result = await client.query(query);
    let tickers = result.rows;
    
    await client.end();
    
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
    console.error('API Error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch ticker data',
      details: error.message
    });
  }
}