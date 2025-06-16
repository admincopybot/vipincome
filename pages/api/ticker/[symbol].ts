import type { NextApiRequest, NextApiResponse } from 'next';
import database from '@/lib/database';
import { isAuthenticated } from '@/lib/auth';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Check authentication
  if (!isAuthenticated(req.headers.authorization)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const { symbol } = req.query;

  if (!symbol || typeof symbol !== 'string') {
    return res.status(400).json({ error: 'Symbol parameter is required' });
  }

  try {
    const etf = await database.getETFBySymbol(symbol);
    
    if (!etf) {
      return res.status(404).json({ error: 'Ticker not found' });
    }

    return res.status(200).json(etf);
  } catch (error) {
    console.error('Database error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}