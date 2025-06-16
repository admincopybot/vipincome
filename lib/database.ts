import { Pool } from 'pg';

export interface ETFData {
  symbol: string;
  current_price: number;
  score: number;
  trend1_pass: boolean;
  trend1_current: number;
  trend1_threshold: number;
  trend1_description: string;
  trend2_pass: boolean;
  trend2_current: number;
  trend2_threshold: number;
  trend2_description: string;
  snapback_pass: boolean;
  snapback_current: number;
  snapback_threshold: number;
  snapback_description: string;
  momentum_pass: boolean;
  momentum_current: number;
  momentum_threshold: number;
  momentum_description: string;
  stabilizing_pass: boolean;
  stabilizing_current: number;
  stabilizing_threshold: number;
  stabilizing_description: string;
  trading_volume: number;
  options_contracts_10_42_dte: number;
  last_updated: string;
}

let pool: Pool | null = null;

export function getDatabase(): Pool {
  if (!pool) {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
    });
  }
  return pool;
}

export async function getAllETFs(): Promise<ETFData[]> {
  const db = getDatabase();
  
  const query = `
    SELECT 
      symbol, current_price, score,
      trend1_pass, trend1_current, trend1_threshold, trend1_description,
      trend2_pass, trend2_current, trend2_threshold, trend2_description,
      snapback_pass, snapback_current, snapback_threshold, snapback_description,
      momentum_pass, momentum_current, momentum_threshold, momentum_description,
      stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
      trading_volume, options_contracts_10_42_dte, last_updated
    FROM etf_scores 
    ORDER BY 
      score DESC,
      options_contracts_10_42_dte DESC,
      trading_volume DESC,
      symbol ASC
  `;
  
  const result = await db.query(query);
  return result.rows;
}

export async function getTickerBySymbol(symbol: string): Promise<ETFData | null> {
  const db = getDatabase();
  
  const query = `
    SELECT 
      symbol, current_price, score,
      trend1_pass, trend1_current, trend1_threshold, trend1_description,
      trend2_pass, trend2_current, trend2_threshold, trend2_description,
      snapback_pass, snapback_current, snapback_threshold, snapback_description,
      momentum_pass, momentum_current, momentum_threshold, momentum_description,
      stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
      trading_volume, options_contracts_10_42_dte, last_updated
    FROM etf_scores 
    WHERE symbol = $1
  `;
  
  const result = await db.query(query, [symbol.toUpperCase()]);
  return result.rows[0] || null;
}

export async function searchETFs(searchTerm: string = '', limit: number = 50): Promise<ETFData[]> {
  const db = getDatabase();
  
  const query = `
    SELECT 
      symbol, current_price, score,
      trend1_pass, trend1_current, trend1_threshold, trend1_description,
      trend2_pass, trend2_current, trend2_threshold, trend2_description,
      snapback_pass, snapback_current, snapback_threshold, snapback_description,
      momentum_pass, momentum_current, momentum_threshold, momentum_description,
      stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
      trading_volume, options_contracts_10_42_dte, last_updated
    FROM etf_scores 
    WHERE symbol ILIKE $1
    ORDER BY 
      score DESC,
      options_contracts_10_42_dte DESC,
      trading_volume DESC,
      symbol ASC
    LIMIT $2
  `;
  
  const result = await db.query(query, [`%${searchTerm.toUpperCase()}%`, limit]);
  return result.rows;
}