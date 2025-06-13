"""
Database models for ETF scoring system - PostgreSQL version
Handles 292 tickers with trading volume tie-breaker for top rankings
Persistent data storage across deployments
"""

import os
import psycopg2
import pandas as pd
import logging
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class ETFDatabase:
    def __init__(self):
        self.connection_string = os.environ.get('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable not set")
        self.init_database()
    
    def _convert_bool(self, value):
        """Convert string boolean values from CSV to actual booleans"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 't', '1', 'yes')
        return bool(value)
    
    def get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(self.connection_string)
    
    def init_database(self):
        """Initialize PostgreSQL database matching exact CSV format"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etf_scores (
                symbol VARCHAR(10) PRIMARY KEY,
                current_price DECIMAL(10,2),
                total_score INTEGER,
                avg_volume_10d BIGINT,
                
                trend1_pass BOOLEAN,
                trend1_current DECIMAL(10,2),
                trend1_threshold DECIMAL(10,2),
                trend1_description TEXT,
                
                trend2_pass BOOLEAN,
                trend2_current DECIMAL(10,2),
                trend2_threshold DECIMAL(10,2),
                trend2_description TEXT,
                
                snapback_pass BOOLEAN,
                snapback_current DECIMAL(10,2),
                snapback_threshold DECIMAL(10,2),
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
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("PostgreSQL database initialized with CSV format and trading volume support")
    
    def upload_csv_data(self, csv_content):
        """Upload ETF data from CSV - SIMPLE: DELETE ALL THEN INSERT NEW"""
        try:
            import io
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Step 1: DELETE ALL RECORDS IMMEDIATELY
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM etf_scores')
            cursor.execute('DELETE FROM last_update') 
            conn.commit()
            logger.info(f"SIMPLE WIPE: Deleted all records, now inserting {len(df)} new records")
            
            updated_count = 0
            
            # Fill NaN values with defaults
            df = df.fillna({
                'avg_volume_10d': 0,  # Keep as 0 when missing from CSV
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
            
            # Handle empty string values and comma-separated numbers in avg_volume_10d column
            df['avg_volume_10d'] = df['avg_volume_10d'].replace('', 0)
            
            # Clean comma-separated numbers (e.g., "25,486,789" -> 25486789)
            def clean_volume(value):
                if pd.isna(value) or value == '':
                    return 0
                if isinstance(value, str):
                    # Remove commas and convert to int
                    return int(value.replace(',', ''))
                return int(value)
            
            df['avg_volume_10d'] = df['avg_volume_10d'].apply(clean_volume)
            
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
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            cursor.execute('DELETE FROM last_update')
            cursor.execute('INSERT INTO last_update (timestamp) VALUES (CURRENT_TIMESTAMP)')
            
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
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT timestamp FROM last_update ORDER BY timestamp DESC LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                # PostgreSQL returns datetime objects directly
                return result[0]
            else:
                # If no timestamp exists, return current time
                from datetime import datetime
                return datetime.now()
                
        except Exception as e:
            logger.error(f"Error getting last update time: {str(e)}")
            from datetime import datetime
            return datetime.now()
    
    def get_all_etfs(self):
        """Get all ETF data with TRADING VOLUME TIE-BREAKER for top rankings"""
        try:
            conn = self.get_connection()
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
            
        except Exception as e:
            logger.error(f"Error retrieving ETF data: {str(e)}")
            return {}
    
    def search_etfs(self, search_term='', limit=None):
        """Search ETFs by symbol with optional limit - optimized for VIP tier"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if search_term:
                # Search by symbol (case-insensitive)
                query = '''
                    SELECT symbol, current_price, total_score, avg_volume_10d,
                           trend1_pass, trend2_pass, snapback_pass, momentum_pass, stabilizing_pass
                    FROM etf_scores
                    WHERE UPPER(symbol) LIKE UPPER(%s)
                    ORDER BY total_score DESC, avg_volume_10d DESC, symbol ASC
                '''
                params = [f'%{search_term}%']
                
                if limit:
                    query += f' LIMIT {int(limit)}'
                    
                cursor.execute(query, params)
            else:
                # Return all ETFs with optional limit
                query = '''
                    SELECT symbol, current_price, total_score, avg_volume_10d,
                           trend1_pass, trend2_pass, snapback_pass, momentum_pass, stabilizing_pass
                    FROM etf_scores
                    ORDER BY total_score DESC, avg_volume_10d DESC, symbol ASC
                '''
                
                if limit:
                    query += f' LIMIT {int(limit)}'
                    
                cursor.execute(query)
            
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
            
        except Exception as e:
            logger.error(f"Error searching ETFs: {str(e)}")
            return {}
    
    def get_total_etf_count(self):
        """Get total count of ETFs in database - useful for VIP dashboard stats"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM etf_scores')
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting ETF count: {str(e)}")
            return 0
    
    def get_ticker_details(self, symbol):
        """Get detailed scoring data for Step 2 analysis with FIXED criteria parsing"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, current_price, total_score, avg_volume_10d,
                   trend1_pass, trend1_current, trend1_threshold, trend1_description,
                   trend2_pass, trend2_current, trend2_threshold, trend2_description,
                   snapback_pass, snapback_current, snapback_threshold, snapback_description,
                   momentum_pass, momentum_current, momentum_threshold, momentum_description,
                   stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
                   data_age_hours
            FROM etf_scores WHERE symbol = %s
        ''', (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        total_score = row[2]
        
        # USE ACTUAL CSV CRITERIA VALUES - correct column positions
        met_criteria = {
            'trend1': bool(row[4]),      # trend1_pass
            'trend2': bool(row[8]),      # trend2_pass  
            'snapback': bool(row[12]),   # snapback_pass
            'momentum': bool(row[16]),   # momentum_pass
            'stabilizing': bool(row[20]) # stabilizing_pass
        }
        
        return {
            'symbol': row[0],
            'current_price': row[1],
            'total_score': total_score,
            'avg_volume_10d': row[3],
            'trend1': {
                'pass': met_criteria['trend1'],
                'current': row[5] if row[5] else 0,
                'threshold': row[6] if row[6] else 0,
                'description': row[7] if row[7] else 'Price > 20-day EMA'
            },
            'trend2': {
                'pass': met_criteria['trend2'],
                'current': row[9] if row[9] else 0,
                'threshold': row[10] if row[10] else 0,
                'description': row[11] if row[11] else 'Price > 100-day EMA'
            },
            'snapback': {
                'pass': met_criteria['snapback'],
                'current': row[13] if row[13] else 0,
                'threshold': row[14] if row[14] else 50,
                'description': row[15] if row[15] else 'RSI < 50'
            },
            'momentum': {
                'pass': met_criteria['momentum'],
                'current': row[17] if row[17] else 0,
                'threshold': row[18] if row[18] else 0,
                'description': row[19] if row[19] else 'Price > Previous Week Close'
            },
            'stabilizing': {
                'pass': met_criteria['stabilizing'],
                'current': row[21] if row[21] else 0,
                'threshold': row[22] if row[22] else 0,
                'description': row[23] if row[23] else '3-day ATR < 6-day ATR'
            },
            'data_age_hours': row[24]
        }
    
    def get_etf_count(self):
        """Get total count of ETFs in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM etf_scores')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def update_ticker_criteria(self, symbol, criteria_data, new_score):
        """Update criteria for a specific ticker and recalculate score"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Map criteria to database fields
        criteria_mapping = {
            'criteria1': 'trend1_pass',
            'criteria2': 'trend2_pass', 
            'criteria3': 'snapback_pass',
            'criteria4': 'momentum_pass',
            'criteria5': 'stabilizing_pass'
        }
        
        # Build update query
        update_fields = []
        update_values = []
        
        for api_field, db_field in criteria_mapping.items():
            if api_field in criteria_data:
                update_fields.append(f"{db_field} = %s")
                update_values.append(criteria_data[api_field])
        
        # Add total score update
        update_fields.append("total_score = %s")
        update_values.append(new_score)
        
        # Add symbol for WHERE clause
        update_values.append(symbol)
        
        query = f"UPDATE etf_scores SET {', '.join(update_fields)} WHERE symbol = %s"
        
        cursor.execute(query, update_values)
        conn.commit()
        conn.close()