"""
Database models for ETF scoring system
Stores ticker data and 5 criteria scores
"""

import sqlite3
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ETFDatabase:
    def __init__(self, db_path='etf_scores.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create ETF scores table with all 5 criteria
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etf_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                current_price REAL,
                total_score INTEGER,
                
                -- Criteria 1: Trend1 (Price > 20-day EMA)
                trend1_pass BOOLEAN,
                trend1_current REAL,
                trend1_threshold REAL,
                
                -- Criteria 2: Trend2 (Price > 100-day EMA)  
                trend2_pass BOOLEAN,
                trend2_current REAL,
                trend2_threshold REAL,
                
                -- Criteria 3: Snapback (RSI < 50)
                snapback_pass BOOLEAN,
                snapback_rsi REAL,
                snapback_threshold REAL,
                
                -- Criteria 4: Momentum (Price > Previous Week Close)
                momentum_pass BOOLEAN,
                momentum_current REAL,
                momentum_threshold REAL,
                
                -- Criteria 5: Stabilizing (3-day ATR < 6-day ATR)
                stabilizing_pass BOOLEAN,
                stabilizing_current REAL,
                stabilizing_threshold REAL,
                
                calculation_time TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def upload_csv_data(self, csv_content):
        """Upload ETF data from CSV content to database"""
        try:
            # Parse CSV content
            if isinstance(csv_content, str):
                import io
                df = pd.read_csv(io.StringIO(csv_content))
            else:
                df = pd.read_csv(csv_content)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updated_count = 0
            
            for _, row in df.iterrows():
                # Convert YES/NO to boolean
                trend1_pass = row['Trend1_Pass'].upper() == 'YES'
                trend2_pass = row['Trend2_Pass'].upper() == 'YES'
                snapback_pass = row['Snapback_Pass'].upper() == 'YES'
                momentum_pass = row['Momentum_Pass'].upper() == 'YES'
                stabilizing_pass = row['Stabilizing_Pass'].upper() == 'YES'
                
                # Insert or replace record
                cursor.execute('''
                    INSERT OR REPLACE INTO etf_scores (
                        symbol, current_price, total_score,
                        trend1_pass, trend1_current, trend1_threshold,
                        trend2_pass, trend2_current, trend2_threshold,
                        snapback_pass, snapback_rsi, snapback_threshold,
                        momentum_pass, momentum_current, momentum_threshold,
                        stabilizing_pass, stabilizing_current, stabilizing_threshold,
                        calculation_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Symbol'],
                    float(row['Current_Price']),
                    int(row['Total_Score']),
                    trend1_pass,
                    float(row['Trend1_Current']),
                    float(row['Trend1_Threshold']),
                    trend2_pass,
                    float(row['Trend2_Current']),
                    float(row['Trend2_Threshold']),
                    snapback_pass,
                    float(row['Snapback_RSI']),
                    float(row['Snapback_Threshold']),
                    momentum_pass,
                    float(row['Momentum_Current']),
                    float(row['Momentum_Threshold']),
                    stabilizing_pass,
                    float(row['Stabilizing_Current']),
                    float(row['Stabilizing_Threshold']),
                    row['Calculation_Time']
                ))
                updated_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully uploaded {updated_count} ETF records to database")
            return {"success": True, "count": updated_count}
            
        except Exception as e:
            logger.error(f"Error uploading CSV data: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_all_etfs(self):
        """Get all ETF data from database in the format expected by the frontend"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, current_price, total_score,
                   trend1_pass, trend2_pass, snapback_pass, momentum_pass, stabilizing_pass
            FROM etf_scores
            ORDER BY total_score DESC, symbol ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to dictionary format expected by frontend
        etf_data = {}
        for row in rows:
            symbol = row[0]
            etf_data[symbol] = {
                'current_price': row[1],
                'total_score': row[2],
                'criteria': {
                    'trend1': row[3],
                    'trend2': row[4], 
                    'snapback': row[5],
                    'momentum': row[6],
                    'stabilizing': row[7]
                }
            }
        
        return etf_data
    
    def get_etf_count(self):
        """Get total count of ETFs in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM etf_scores')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_ticker_details(self, symbol):
        """Get detailed scoring data for a specific ticker for Step 2 analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, current_price, total_score,
                   trend1_pass, trend1_current, trend1_threshold,
                   trend2_pass, trend2_current, trend2_threshold,
                   snapback_pass, snapback_rsi, snapback_threshold,
                   momentum_pass, momentum_current, momentum_threshold,
                   stabilizing_pass, stabilizing_current, stabilizing_threshold,
                   calculation_time
            FROM etf_scores 
            WHERE UPPER(symbol) = UPPER(?)
        ''', (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Create a detailed ticker data object with descriptions
        ticker_data = type('TickerData', (), {})()
        
        ticker_data.symbol = row[0]
        ticker_data.current_price = row[1]
        ticker_data.total_score = row[2]
        
        # Trend 1 data
        ticker_data.trend1_pass = bool(row[3])
        ticker_data.trend1_current = row[4]
        ticker_data.trend1_threshold = row[5]
        ticker_data.trend1_description = f"Price (${row[4]:.2f}) is {'above' if row[3] else 'below'} the 20-day EMA (${row[5]:.2f})"
        
        # Trend 2 data
        ticker_data.trend2_pass = bool(row[6])
        ticker_data.trend2_current = row[7]
        ticker_data.trend2_threshold = row[8]
        ticker_data.trend2_description = f"Price (${row[7]:.2f}) is {'above' if row[6] else 'below'} the 100-day EMA (${row[8]:.2f})"
        
        # Snapback data
        ticker_data.snapback_pass = bool(row[9])
        ticker_data.snapback_current = row[10]
        ticker_data.snapback_threshold = row[11]
        ticker_data.snapback_description = f"RSI ({row[10]:.1f}) is {'below' if row[9] else 'above'} the threshold ({row[11]:.0f})"
        
        # Momentum data
        ticker_data.momentum_pass = bool(row[12])
        ticker_data.momentum_current = row[13]
        ticker_data.momentum_threshold = row[14]
        ticker_data.momentum_description = f"Current price (${row[13]:.2f}) is {'above' if row[12] else 'below'} last week's close (${row[14]:.2f})"
        
        # Stabilizing data
        ticker_data.stabilizing_pass = bool(row[15])
        ticker_data.stabilizing_current = row[16]
        ticker_data.stabilizing_threshold = row[17]
        ticker_data.stabilizing_description = f"3-day ATR ({row[16]:.2f}) is {'lower' if row[15] else 'higher'} than 6-day ATR ({row[17]:.2f})"
        
        ticker_data.calculation_time = row[18]
        
        return ticker_data