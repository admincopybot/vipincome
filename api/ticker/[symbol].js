const fs = require('fs');
const path = require('path');

export default function handler(req, res) {
  // Enable CORS for cross-origin requests
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  try {
    // Extract ticker symbol from URL parameter
    const { symbol } = req.query;
    console.log('Serving ticker page for:', symbol);
    
    // Read and serve the ticker.html file
    const tickerPath = path.join(process.cwd(), 'public', 'ticker.html');
    const tickerHTML = fs.readFileSync(tickerPath, 'utf8');
    
    res.setHeader('Content-Type', 'text/html');
    res.status(200).send(tickerHTML);
  } catch (error) {
    console.error('Error serving ticker page:', error);
    res.status(500).send('Error loading ticker page');
  }
} 