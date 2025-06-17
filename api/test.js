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

    // Try to connect to database
    const client = new Client({
      connectionString: dbUrl,
      ssl: nodeEnv === 'production' ? { rejectUnauthorized: false } : false
    });
    
    console.log('Attempting database connection...');
    await client.connect();
    console.log('Database connected successfully');
    
    // Test simple query
    const result = await client.query('SELECT NOW() as current_time');
    console.log('Query executed successfully');
    
    await client.end();
    console.log('Database connection closed');

    res.status(200).json({
      success: true,
      message: 'Database connection successful',
      current_time: result.rows[0].current_time,
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
      stack: error.stack
    });
  }
} 