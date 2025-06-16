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

  try {
    const { search, top3 } = req.query;

    if (top3 === 'true') {
      const etfs = await database.getTop3ETFs();
      return res.status(200).json(etfs);
    }

    let etfs = await database.getAllETFs();

    // Apply search filter if provided
    if (search && typeof search === 'string') {
      const searchTerm = search.toLowerCase();
      etfs = etfs.filter(etf => 
        etf.symbol.toLowerCase().includes(searchTerm)
      );
    }

    // Filter out low contract tickers for better user experience
    etfs = etfs.filter(etf => 
      etf.options_contracts_10_42_dte === 0 || etf.options_contracts_10_42_dte >= 100
    );

    return res.status(200).json(etfs);
  } catch (error) {
    console.error('Database error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}