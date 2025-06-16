import type { NextApiRequest, NextApiResponse } from 'next';
import { getAllETFs, searchETFs } from '@/lib/database';
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

  try {
    const { search, limit } = req.query;
    
    let tickers;
    if (search && typeof search === 'string') {
      const limitNum = limit && typeof limit === 'string' ? parseInt(limit, 10) : 50;
      tickers = await searchETFs(search, limitNum);
    } else {
      tickers = await getAllETFs();
    }

    return res.status(200).json(tickers);
  } catch (error) {
    console.error('Database error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}