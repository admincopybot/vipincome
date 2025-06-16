import type { NextApiRequest, NextApiResponse } from 'next';
import { getTickerBySymbol } from '@/lib/database';
import { isAuthenticated } from '@/lib/auth';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Validate JWT authentication
  const user = isAuthenticated(req);
  if (!user) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const { symbol } = req.query;
  
  if (!symbol || typeof symbol !== 'string') {
    return res.status(400).json({ error: 'Invalid symbol' });
  }

  try {
    const ticker = await getTickerBySymbol(symbol);
    
    if (!ticker) {
      return res.status(404).json({ error: 'Ticker not found' });
    }

    return res.status(200).json(ticker);
  } catch (error) {
    console.error('Database error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}