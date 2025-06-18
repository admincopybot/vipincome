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

  let client;

  try {
    // Check environment variables
    const dbUrl = process.env.DATABASE_URL;
    const nodeEnv = process.env.NODE_ENV;
    
    console.log('DATABASE_URL exists:', !!dbUrl);
    console.log('NODE_ENV:', nodeEnv);
    
    if (!dbUrl) {
      return res.status(500).json({
        success: false,
        error: 'DATABASE_URL environment variable is not set',
        env_check: {
          DATABASE_URL: !!dbUrl,
          NODE_ENV: nodeEnv
        }
      });
    }

    // Try to connect to NeonDB
    client = new Client({
      connectionString: dbUrl,
      ssl: {
        rejectUnauthorized: false
      }
    });
    
    console.log('Attempting NeonDB connection...');
    await client.connect();
    console.log('NeonDB connected successfully');
    
    // Test simple query
    const timeResult = await client.query('SELECT NOW() as current_time');
    console.log('Time query executed successfully');
    
    // Check if etf_scores table exists
    const tableCheck = await client.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'etf_scores'
      );
    `);
    
    // Get table schema - show all columns
    let tableSchema = null;
    if (tableCheck.rows[0].exists) {
      const schemaResult = await client.query(`
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'etf_scores'
        ORDER BY ordinal_position;
      `);
      tableSchema = schemaResult.rows;
    }
    
    // If table exists, get sample data with ALL columns
    let sampleData = null;
    let rowCount = 0;
    
    if (tableCheck.rows[0].exists) {
      const countResult = await client.query('SELECT COUNT(*) FROM etf_scores');
      rowCount = parseInt(countResult.rows[0].count);
      
      if (rowCount > 0) {
        // Get first row with ALL columns to see what data is available
        const sampleResult = await client.query('SELECT * FROM etf_scores LIMIT 1');
        sampleData = sampleResult.rows[0];
      }
    }

    res.status(200).json({
      success: true,
      message: 'NeonDB connection successful',
      current_time: timeResult.rows[0].current_time,
      database_info: {
        etf_scores_table_exists: tableCheck.rows[0].exists,
        etf_scores_row_count: rowCount,
        table_schema: tableSchema,
        sample_row_data: sampleData
      },
      env_check: {
        DATABASE_URL: !!dbUrl,
        NODE_ENV: nodeEnv
      }
    });

  } catch (error) {
    console.error('Test API Error:', error);
    res.status(500).json({
      success: false,
      error: 'Database connection failed',
      details: error.message,
      code: error.code,
      stack: error.stack
    });
  } finally {
    if (client) {
      try {
        await client.end();
        console.log('NeonDB connection closed');
      } catch (closeError) {
        console.error('Error closing NeonDB connection:', closeError);
      }
    }
  }
} 