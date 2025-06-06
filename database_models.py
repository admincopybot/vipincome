"""
Database models for ETF scoring system - SQLite version
Handles 292 tickers with trading volume tie-breaker for top rankings
"""

import sqlite3
import pandas as pd
import logging
import csv
import io
from datetime import datetime

logger = logging.getLogger(__name__)

class ETFDatabase:
    def __init__(self, db_path='etf_scores.db'):
        self.db_path = db_path
        self.init_database()
    
    def _convert_bool(self, value):
        """Convert string boolean values from CSV to actual booleans"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 't', '1', 'yes')
        return bool(value)
    
    def init_database(self):
        """Initialize SQLite database matching exact CSV format"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etf_scores (
                symbol TEXT PRIMARY KEY,
                current_price REAL,
                total_score INTEGER,
                avg_volume_10d INTEGER,
                
                trend1_pass BOOLEAN,
                trend1_current REAL,
                trend1_threshold REAL,
                trend1_description TEXT,
                
                trend2_pass BOOLEAN,
                trend2_current REAL,
                trend2_threshold REAL,
                trend2_description TEXT,
                
                snapback_pass BOOLEAN,
                snapback_current REAL,
                snapback_threshold REAL,
                snapback_description TEXT,
                
                momentum_pass BOOLEAN,
                momentum_current REAL,
                momentum_threshold REAL,
                momentum_description TEXT,
                
                stabilizing_pass BOOLEAN,
                stabilizing_current REAL,
                stabilizing_threshold REAL,
                stabilizing_description TEXT,
                
                calculation_timestamp TEXT,
                data_age_hours INTEGER
            );
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database initialized with CSV format and trading volume support")
    
    def upload_csv_data(self, csv_content):
        """Upload CSV data to SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM etf_scores')
            
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            count = 0
            
            for row in csv_reader:
                # Handle empty values
                def clean_val(val):
                    return None if val == '' else val
                
                # Convert boolean strings
                def to_bool(val):
                    return True if val == 'true' else False if val == 'false' else None
                
                # Convert numeric values
                def to_float(val):
                    try:
                        return float(val) if val and val != '' else None
                    except:
                        return None
                
                def to_int(val):
                    try:
                        return int(val) if val and val != '' else None
                    except:
                        return None
                
                cursor.execute('''
                    INSERT INTO etf_scores (
                        symbol, current_price, total_score, avg_volume_10d,
                        trend1_pass, trend1_current, trend1_threshold, trend1_description,
                        trend2_pass, trend2_current, trend2_threshold, trend2_description,
                        snapback_pass, snapback_current, snapback_threshold, snapback_description,
                        momentum_pass, momentum_current, momentum_threshold, momentum_description,
                        stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
                        calculation_timestamp, data_age_hours
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['symbol'],
                    to_float(row['current_price']),
                    to_int(row['total_score']),
                    to_int(row['avg_volume_10d']),
                    to_bool(row['trend1_pass']),
                    to_float(row['trend1_current']),
                    to_float(row['trend1_threshold']),
                    clean_val(row['trend1_description']),
                    to_bool(row['trend2_pass']),
                    to_float(row['trend2_current']),
                    to_float(row['trend2_threshold']),
                    clean_val(row['trend2_description']),
                    to_bool(row['snapback_pass']),
                    to_float(row['snapback_current']),
                    to_float(row['snapback_threshold']),
                    clean_val(row['snapback_description']),
                    to_bool(row['momentum_pass']),
                    to_float(row['momentum_current']),
                    to_float(row['momentum_threshold']),
                    clean_val(row['momentum_description']),
                    to_bool(row['stabilizing_pass']),
                    to_float(row['stabilizing_current']),
                    to_float(row['stabilizing_threshold']),
                    clean_val(row['stabilizing_description']),
                    row['calculation_timestamp'],
                    to_int(row['data_age_hours'])
                ))
                count += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Uploaded {count} symbols to SQLite database")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading CSV data: {e}")
            return False
    
    def get_all_etfs(self):
        """Get all ETF data from SQLite database - SORTED by score DESC, volume DESC"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM etf_scores 
                ORDER BY total_score DESC, avg_volume_10d DESC
            ''')
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convert to dictionary format
            etf_data = {}
            for row in rows:
                etf_data[row['symbol']] = dict(row)
            
            return etf_data
            
        except Exception as e:
            logger.error(f"Error getting ETF data: {e}")
            return {}
    
    def get_etf_by_symbol(self, symbol):
        """Get specific ETF data by symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM etf_scores WHERE symbol = ?', (symbol,))
            row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting ETF data for {symbol}: {e}")
            return None
    
    def get_top_etfs(self, limit=10):
        """Get top ETFs by score and volume"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM etf_scores 
                ORDER BY total_score DESC, avg_volume_10d DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting top ETFs: {e}")
            return []
    
    def get_last_update_time(self):
        """Get the timestamp of the most recent data update"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT MAX(calculation_timestamp) as last_update FROM etf_scores')
            row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return row['last_update'] if row and row['last_update'] else "No data available"
            
        except Exception as e:
            logger.error(f"Error getting last update time: {e}")
            return "Error retrieving update time"
    
    def get_ticker_details(self, symbol):
        """Get detailed ticker information - alias for get_etf_by_symbol"""
        return self.get_etf_by_symbol(symbol)