const jwt = require('jsonwebtoken');

// OneClick Trading RS256 public key
const OCT_PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1NtjOd7kQqOjE3NDcyMj
EONZUSlmV4cCl6MrcIMjOwNfQ3NX0V5Nh8ZRnlUPnKojinSqAiXl1GrW9hPAufH
fRKRftSD79oi5x3XoFx0-acJlsu6OPUymMBof2mN121GW0bs_DFAZNS265c-3sfcK
piGvq9x0qsx3qNYL88qRC553d0JP4PYMeXq6Yr60sL5Sl0tz_r25UAp17pgv4VdG
w1yytgb8nAVjlvg4d1V2QykAdOMofruypllrimPvqH9WFph3czbQ-y4O9j73h4atz
DabF1PaTAT6vKif8STJM5ThwBNdhFW7GglC5zs0WnyX4W_7qlnZ3cHpTDKdRMmW
39Vm_XObq6tlkYdkXrZm4-dvPSdPgzfKjE5COvUg
-----END PUBLIC KEY-----`;

export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { token } = req.body;

    if (!token) {
      return res.status(400).json({
        success: false,
        error: 'Token is required'
      });
    }

    console.log(`Attempting JWT validation with token length: ${token.length}`);

    // Verify JWT token
    const decoded = jwt.verify(token, OCT_PUBLIC_KEY, { 
      algorithms: ['RS256'],
      issuer: 'oneclick-trading'
    });

    console.log(`JWT validation successful for user: ${decoded.sub}`);

    res.status(200).json({
      success: true,
      user: {
        id: decoded.sub,
        username: decoded.username || decoded.preferred_username || 'VIP User',
        tier: 'VIP'
      }
    });

  } catch (error) {
    console.error('JWT validation failed:', error.message);
    res.status(401).json({
      success: false,
      error: 'Invalid or expired token',
      details: error.message
    });
  }
}