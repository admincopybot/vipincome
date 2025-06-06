"""
Authentic Debit Spread Storage System
Stores real-time spread detection results with unique IDs for Step 4 retrieval
"""
import psycopg2
import psycopg2.extras
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SpreadStorage:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.init_database()
    
    def init_database(self):
        """Initialize the spread storage table"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Create spreads table to store authentic spread data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS authentic_spreads (
                    spread_id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    strategy VARCHAR(20) NOT NULL,
                    long_contract VARCHAR(50) NOT NULL,
                    short_contract VARCHAR(50) NOT NULL,
                    long_strike DECIMAL(10,2) NOT NULL,
                    short_strike DECIMAL(10,2) NOT NULL,
                    expiration_date DATE NOT NULL,
                    dte INTEGER NOT NULL,
                    spread_cost DECIMAL(10,2) NOT NULL,
                    max_profit DECIMAL(10,2) NOT NULL,
                    roi DECIMAL(8,2) NOT NULL,
                    current_price DECIMAL(10,2) NOT NULL,
                    long_price DECIMAL(10,2) NOT NULL,
                    short_price DECIMAL(10,2) NOT NULL,
                    spread_width DECIMAL(10,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    api_source VARCHAR(50) DEFAULT 'TheTradeList',
                    INDEX(symbol, strategy, created_at)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Spread storage database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing spread storage: {e}")
    
    def store_spread(self, symbol: str, strategy: str, spread_data: dict) -> int:
        """
        Store authentic spread data and return unique spread_id
        
        Args:
            symbol: Stock symbol
            strategy: aggressive, balanced, conservative
            spread_data: Complete spread metrics from real-time detection
            
        Returns:
            spread_id: Unique identifier for this authentic spread
        """
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Extract spread details
            long_contract = spread_data.get('long_ticker', '')
            short_contract = spread_data.get('short_ticker', '')
            long_strike = float(spread_data.get('long_strike', 0))
            short_strike = float(spread_data.get('short_strike', 0))
            expiration_date = spread_data.get('expiration', '')
            dte = int(spread_data.get('dte', 0))
            spread_cost = float(spread_data.get('spread_cost', 0))
            max_profit = float(spread_data.get('max_profit', 0))
            roi = float(spread_data.get('roi', 0))
            current_price = float(spread_data.get('current_price', 0))
            long_price = float(spread_data.get('long_price', 0))
            short_price = float(spread_data.get('short_price', 0))
            spread_width = float(spread_data.get('spread_width', 0))
            
            # Insert spread data
            cursor.execute('''
                INSERT INTO authentic_spreads (
                    symbol, strategy, long_contract, short_contract,
                    long_strike, short_strike, expiration_date, dte,
                    spread_cost, max_profit, roi, current_price,
                    long_price, short_price, spread_width
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING spread_id
            ''', (
                symbol, strategy, long_contract, short_contract,
                long_strike, short_strike, expiration_date, dte,
                spread_cost, max_profit, roi, current_price,
                long_price, short_price, spread_width
            ))
            
            spread_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            
            logger.info(f"Stored authentic spread {spread_id}: {symbol} {strategy} ROI={roi:.1f}%")
            return spread_id
            
        except Exception as e:
            logger.error(f"Error storing spread: {e}")
            return None
    
    def get_spread(self, spread_id: int) -> dict:
        """
        Retrieve authentic spread data by ID
        
        Args:
            spread_id: Unique spread identifier
            
        Returns:
            Complete spread data for Step 4 analysis
        """
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT * FROM authentic_spreads 
                WHERE spread_id = %s
            ''', (spread_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Convert to regular dict
                spread_data = dict(result)
                logger.info(f"Retrieved authentic spread {spread_id}: {spread_data['symbol']} {spread_data['strategy']}")
                return spread_data
            else:
                logger.warning(f"Spread {spread_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving spread {spread_id}: {e}")
            return None
    
    def cleanup_old_spreads(self, hours: int = 24):
        """Remove spreads older than specified hours"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM authentic_spreads 
                WHERE created_at < NOW() - INTERVAL '%s hours'
            ''', (hours,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted} old spreads")
            
        except Exception as e:
            logger.error(f"Error cleaning up spreads: {e}")

# Global instance
spread_storage = SpreadStorage()