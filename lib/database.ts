import { Pool } from 'pg';

export interface ETFData {
  symbol: string;
  current_price: number;
  score: number;
  trend1_pass: boolean;
  trend2_pass: boolean;
  snapback_pass: boolean;
  momentum_pass: boolean;
  stabilizing_pass: boolean;
  trading_volume: number;
  options_contracts_10_42_dte: number;
  last_updated: string;
}

class Database {
  private pool: Pool;

  constructor() {
    this.pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
    });
  }

  async getAllETFs(): Promise<ETFData[]> {
    const query = `
      SELECT 
        symbol, 
        current_price, 
        score,
        trend1_pass,
        trend2_pass, 
        snapback_pass,
        momentum_pass,
        stabilizing_pass,
        trading_volume,
        options_contracts_10_42_dte,
        last_updated
      FROM etf_scores 
      ORDER BY score DESC, options_contracts_10_42_dte DESC, trading_volume DESC, symbol ASC
    `;
    
    const result = await this.pool.query(query);
    return result.rows;
  }

  async getETFBySymbol(symbol: string): Promise<ETFData | null> {
    const query = `
      SELECT 
        symbol, 
        current_price, 
        score,
        trend1_pass,
        trend2_pass, 
        snapback_pass,
        momentum_pass,
        stabilizing_pass,
        trading_volume,
        options_contracts_10_42_dte,
        last_updated
      FROM etf_scores 
      WHERE symbol = $1
    `;
    
    const result = await this.pool.query(query, [symbol.toUpperCase()]);
    return result.rows[0] || null;
  }

  async getTop3ETFs(): Promise<ETFData[]> {
    const query = `
      SELECT 
        symbol, 
        current_price, 
        score,
        trend1_pass,
        trend2_pass, 
        snapback_pass,
        momentum_pass,
        stabilizing_pass,
        trading_volume,
        options_contracts_10_42_dte,
        last_updated
      FROM etf_scores 
      WHERE options_contracts_10_42_dte != 1 AND options_contracts_10_42_dte != 99
      ORDER BY score DESC, options_contracts_10_42_dte DESC, trading_volume DESC, symbol ASC
      LIMIT 3
    `;
    
    const result = await this.pool.query(query);
    return result.rows;
  }

  async close() {
    await this.pool.end();
  }
}

export default new Database();