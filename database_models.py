"""
Database models for ETF scoring system - Updated for CSV format
Handles 292 tickers with trading volume tie-breaker for top rankings
"""

import sqlite3
import pandas as pd
import logging

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
        """Initialize database matching exact CSV format"""
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
                
                data_age_hours INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create table for tracking last update timestamp
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS last_update (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized with CSV format and trading volume support")
    
    def upload_csv_data(self, csv_content):
        """Upload ETF data from CSV - completely wipe and refresh"""
        try:
            import io
            df = pd.read_csv(io.StringIO(csv_content))
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # CRITICAL: Wipe all previous records
            logger.info("Clearing all previous ETF records...")
            cursor.execute('DELETE FROM etf_scores')
            conn.commit()
            logger.info("Previous records cleared successfully")
            
            updated_count = 0
            
            # Fill NaN values with defaults
            df = df.fillna({
                'avg_volume_10d': 0,
                'trend1_current': 0.0,
                'trend1_threshold': 0.0,
                'trend1_description': '',
                'trend2_current': 0.0,
                'trend2_threshold': 0.0,
                'trend2_description': '',
                'snapback_current': 0.0,
                'snapback_threshold': 0.0,
                'snapback_description': '',
                'momentum_current': 0.0,
                'momentum_threshold': 0.0,
                'momentum_description': '',
                'stabilizing_current': 0.0,
                'stabilizing_threshold': 0.0,
                'stabilizing_description': '',
                'data_age_hours': 0
            })
            
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO etf_scores (
                        symbol, current_price, total_score, avg_volume_10d,
                        trend1_pass, trend1_current, trend1_threshold, trend1_description,
                        trend2_pass, trend2_current, trend2_threshold, trend2_description,
                        snapback_pass, snapback_current, snapback_threshold, snapback_description,
                        momentum_pass, momentum_current, momentum_threshold, momentum_description,
                        stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
                        data_age_hours
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(row['symbol']),
                    float(row['current_price']),
                    int(row['total_score']),
                    int(row['avg_volume_10d']),
                    self._convert_bool(row['trend1_pass']),
                    float(row['trend1_current']),
                    float(row['trend1_threshold']),
                    str(row['trend1_description']),
                    self._convert_bool(row['trend2_pass']),
                    float(row['trend2_current']),
                    float(row['trend2_threshold']),
                    str(row['trend2_description']),
                    self._convert_bool(row['snapback_pass']),
                    float(row['snapback_current']),
                    float(row['snapback_threshold']),
                    str(row['snapback_description']),
                    self._convert_bool(row['momentum_pass']),
                    float(row['momentum_current']),
                    float(row['momentum_threshold']),
                    str(row['momentum_description']),
                    self._convert_bool(row['stabilizing_pass']),
                    float(row['stabilizing_current']),
                    float(row['stabilizing_threshold']),
                    str(row['stabilizing_description']),
                    int(row['data_age_hours'])
                ))
                updated_count += 1
            
            # Update last update timestamp
            from datetime import datetime
            current_time = datetime.now().isoformat()
            cursor.execute('DELETE FROM last_update')
            cursor.execute('INSERT INTO last_update (timestamp) VALUES (?)', (current_time,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully uploaded {updated_count} ETF records to database")
            return {"success": True, "count": updated_count}
            
        except Exception as e:
            logger.error(f"Error uploading CSV data: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_last_update_time(self):
        """Get the timestamp of the last CSV update"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT timestamp FROM last_update ORDER BY timestamp DESC LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            
            if result:
                from datetime import datetime
                return datetime.fromisoformat(result[0])
            else:
                # If no timestamp exists, return current time
                from datetime import datetime
                return datetime.now()
                
        except Exception as e:
            logger.error(f"Error getting last update time: {e}")
            from datetime import datetime
            return datetime.now()
    
    def get_all_etfs(self):
        """Get all ETF data with TRADING VOLUME TIE-BREAKER for top rankings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ORDER BY: total_score DESC, then avg_volume_10d DESC for tie-breaker
        cursor.execute('''
            SELECT symbol, current_price, total_score, avg_volume_10d,
                   trend1_pass, trend2_pass, snapback_pass, momentum_pass, stabilizing_pass
            FROM etf_scores
            ORDER BY total_score DESC, avg_volume_10d DESC, symbol ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to format expected by frontend
        etf_data = {}
        for row in rows:
            symbol = row[0]
            etf_data[symbol] = {
                'current_price': row[1],
                'total_score': row[2],
                'avg_volume_10d': row[3],
                'criteria': {
                    'trend1': row[4],
                    'trend2': row[5], 
                    'snapback': row[6],
                    'momentum': row[7],
                    'stabilizing': row[8]
                }
            }
        
        return etf_data
    
    def get_ticker_details(self, symbol):
        """Get detailed scoring data for Step 2 analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM etf_scores WHERE symbol = ?
        ''', (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'symbol': row[0],
            'current_price': row[1],
            'total_score': row[2],
            'avg_volume_10d': row[3],
            'trend1': {
                'pass': row[4],
                'current': row[5],
                'threshold': row[6],
                'description': row[7]
            },
            'trend2': {
                'pass': row[8],
                'current': row[9],
                'threshold': row[10],
                'description': row[11]
            },
            'snapback': {
                'pass': row[12],
                'current': row[13],
                'threshold': row[14],
                'description': row[15]
            },
            'momentum': {
                'pass': row[16],
                'current': row[17],
                'threshold': row[18],
                'description': row[19]
            },
            'stabilizing': {
                'pass': row[20],
                'current': row[21],
                'threshold': row[22],
                'description': row[23]
            },
            'data_age_hours': row[24]
        }
    
    def get_etf_count(self):
        """Get total count of ETFs in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM etf_scores')
        count = cursor.fetchone()[0]
        conn.close()
        return count