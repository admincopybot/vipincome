#!/usr/bin/env python3
"""
Bulk ETF Technical Scoring Calculator
====================================

This application performs the exact 5-criteria technical scoring calculations
for 1000+ stock symbols using a database-first approach with incremental API updates.

CALCULATION CRITERIA (Each worth 1 point, total 0-5):
1. Trend 1: Current Price > 20-day EMA
2. Trend 2: Current Price > 100-day EMA  
3. Snapback: RSI < 50 (using 4-hour data)
4. Momentum: Current Price > Previous Week's Close (Friday)
5. Stabilizing: 3-day ATR < 6-day ATR

API Requirements:
- Polygon.io API key (POLYGON_API_KEY environment variable)
- Daily data: 2 years minimum for 100-day EMA
- 4-hour data: 28 days for RSI calculation

Database Schema:
- daily_prices: OHLCV daily data
- four_hour_prices: OHLCV 4-hour data  
- calculated_indicators: Pre-computed technical indicators
- etf_scores: Final scoring results
- symbol_metadata: Data tracking and quality control
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import time
import csv
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_calculator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TechnicalIndicators:
    """Data class for storing calculated technical indicators"""
    symbol: str
    current_price: float
    ema_20: float
    ema_100: float
    rsi_14: float
    weekly_close: float
    weekly_close_date: str
    atr_3: float
    atr_6: float
    calculation_date: datetime

@dataclass
class ScoringResult:
    """Data class for storing final scoring results"""
    symbol: str
    current_price: float
    total_score: int
    trend1_pass: bool
    trend1_current: float
    trend1_threshold: float
    trend1_description: str
    trend2_pass: bool
    trend2_current: float
    trend2_threshold: float
    trend2_description: str
    snapback_pass: bool
    snapback_current: float
    snapback_threshold: float
    snapback_description: str
    momentum_pass: bool
    momentum_current: float
    momentum_threshold: float
    momentum_description: str
    stabilizing_pass: bool
    stabilizing_current: float
    stabilizing_threshold: float
    stabilizing_description: str
    calculation_timestamp: datetime
    data_age_hours: int

class DatabaseManager:
    """Handles all database operations for the bulk calculator"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
            
    def create_tables(self):
        """Create all required database tables"""
        tables_sql = """
        -- Daily price data storage
        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            open_price DECIMAL(12,4) NOT NULL,
            high_price DECIMAL(12,4) NOT NULL,
            low_price DECIMAL(12,4) NOT NULL,
            close_price DECIMAL(12,4) NOT NULL,
            volume BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (symbol, date)
        );
        
        -- 4-hour price data storage
        CREATE TABLE IF NOT EXISTS four_hour_prices (
            symbol VARCHAR(10) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open_price DECIMAL(12,4) NOT NULL,
            high_price DECIMAL(12,4) NOT NULL,
            low_price DECIMAL(12,4) NOT NULL,
            close_price DECIMAL(12,4) NOT NULL,
            volume BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (symbol, timestamp)
        );
        
        -- Pre-calculated technical indicators
        CREATE TABLE IF NOT EXISTS calculated_indicators (
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            current_price DECIMAL(12,4),
            ema_20 DECIMAL(12,4),
            ema_100 DECIMAL(12,4),
            rsi_14 DECIMAL(6,2),
            weekly_close DECIMAL(12,4),
            weekly_close_date DATE,
            atr_3 DECIMAL(10,6),
            atr_6 DECIMAL(10,6),
            calculation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            needs_recalculation BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (symbol, date)
        );
        
        -- Final scoring results
        CREATE TABLE IF NOT EXISTS etf_scores (
            symbol VARCHAR(10) PRIMARY KEY,
            current_price DECIMAL(12,4),
            total_score INTEGER,
            trend1_pass BOOLEAN,
            trend1_current DECIMAL(12,4),
            trend1_threshold DECIMAL(12,4),
            trend1_description TEXT,
            trend2_pass BOOLEAN,
            trend2_current DECIMAL(12,4),
            trend2_threshold DECIMAL(12,4),
            trend2_description TEXT,
            snapback_pass BOOLEAN,
            snapback_current DECIMAL(6,2),
            snapback_threshold DECIMAL(6,2),
            snapback_description TEXT,
            momentum_pass BOOLEAN,
            momentum_current DECIMAL(12,4),
            momentum_threshold DECIMAL(12,4),
            momentum_description TEXT,
            stabilizing_pass BOOLEAN,
            stabilizing_current DECIMAL(10,6),
            stabilizing_threshold DECIMAL(10,6),
            stabilizing_description TEXT,
            calculation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_age_hours INTEGER
        );
        
        -- Symbol metadata and tracking
        CREATE TABLE IF NOT EXISTS symbol_metadata (
            symbol VARCHAR(10) PRIMARY KEY,
            sector VARCHAR(50),
            last_daily_update TIMESTAMP,
            last_4hour_update TIMESTAMP,
            last_calculation TIMESTAMP,
            data_quality_score INTEGER DEFAULT 100,
            min_date_available DATE,
            max_date_available DATE,
            total_daily_records INTEGER DEFAULT 0,
            total_4hour_records INTEGER DEFAULT 0,
            api_failures INTEGER DEFAULT 0,
            last_api_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices(symbol, date DESC);
        CREATE INDEX IF NOT EXISTS idx_four_hour_prices_symbol_time ON four_hour_prices(symbol, timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_calculated_indicators_symbol_date ON calculated_indicators(symbol, date DESC);
        CREATE INDEX IF NOT EXISTS idx_symbol_metadata_last_update ON symbol_metadata(last_calculation);
        """
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(tables_sql)
                self.conn.commit()
                logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

class PolygonApiClient:
    """Handles all Polygon.io API interactions with rate limiting and error handling"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()
        self.rate_limit_delay = 0.1  # 100ms between requests for free tier
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
        
    def _make_request(self, url: str, params: dict) -> dict:
        """Make HTTP request with error handling and retries"""
        self._rate_limit()
        
        params['apiKey'] = self.api_key
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    
        return None
        
    def fetch_daily_data(self, symbol: str, from_date: str, to_date: str) -> pd.DataFrame:
        """
        Fetch daily OHLCV data from Polygon API
        
        Args:
            symbol: Stock/ETF symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, timestamp
        """
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{from_date}/{to_date}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 5000
        }
        
        logger.info(f"Fetching daily data for {symbol}: {from_date} to {to_date}")
        data = self._make_request(url, params)
        
        if not data or 'results' not in data or not data['results']:
            logger.warning(f"No daily data found for {symbol}")
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(data['results'])
        df = df.rename(columns={
            'o': 'Open',
            'h': 'High', 
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume',
            't': 'timestamp'
        })
        
        # Convert timestamp and set as index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['date'] = df['timestamp'].dt.date
        df.set_index('timestamp', inplace=True)
        
        # Clean data
        df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'date']]
        df.dropna(inplace=True)
        
        logger.info(f"Retrieved {len(df)} daily records for {symbol}")
        return df
        
    def fetch_four_hour_data(self, symbol: str, from_date: str, to_date: str) -> pd.DataFrame:
        """
        Fetch 4-hour OHLCV data from Polygon API for RSI calculation
        
        Args:
            symbol: Stock/ETF symbol  
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, timestamp
        """
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/4/hour/{from_date}/{to_date}"
        params = {
            'adjusted': 'true',
            'sort': 'asc', 
            'limit': 5000
        }
        
        logger.info(f"Fetching 4-hour data for {symbol}: {from_date} to {to_date}")
        data = self._make_request(url, params)
        
        if not data or 'results' not in data or not data['results']:
            logger.warning(f"No 4-hour data found for {symbol}")
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(data['results'])
        df = df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low', 
            'c': 'Close',
            'v': 'Volume',
            't': 'timestamp'
        })
        
        # Convert timestamp and set as index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Clean data
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.dropna(inplace=True)
        
        logger.info(f"Retrieved {len(df)} 4-hour records for {symbol}")
        return df

class TechnicalCalculator:
    """Performs all technical indicator calculations using the exact logic from the original system"""
    
    @staticmethod
    def calculate_ema(series: pd.Series, window: int) -> pd.Series:
        """
        Calculate Exponential Moving Average
        Uses pandas ewm with adjust=False to match original implementation
        """
        return series.ewm(span=window, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, window: int = 14) -> float:
        """
        Calculate RSI using exact pipeline logic
        Uses ewm(alpha=1/length, adjust=False) for RMA
        """
        if len(df) < window + 1:
            logger.warning(f"Insufficient data for RSI calculation: {len(df)} < {window + 1}")
            return 50.0
        
        def rma(series, length):
            """RMA using exact logic from pipeline"""
            return series.ewm(alpha=1 / length, adjust=False).mean()

        def compute_rsi(close, length=14):
            """Compute RSI using exact PineScript logic from pipeline"""
            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = rma(gain, length)
            avg_loss = rma(loss, length)
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi = rsi.fillna(50)
            return rsi
        
        # Calculate RSI and return the latest value
        rsi_series = compute_rsi(df['Close'], window)
        return float(rsi_series.iloc[-1])
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, window: int) -> float:
        """
        Calculate Average True Range
        Matches original implementation exactly
        """
        if len(df) < window + 1:  # Need extra day for previous close
            logger.warning(f"Insufficient data for ATR calculation: {len(df)} < {window + 1}")
            return 0.0
            
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=window).mean()
        
        # Get most recent valid ATR value
        current_atr = atr.dropna().iloc[-1]
        return float(current_atr if not hasattr(current_atr, 'iloc') else current_atr.iloc[0])
    
    @staticmethod
    def get_latest_weekly_close(df: pd.DataFrame) -> Tuple[float, str]:
        """
        Get the latest completed weekly close price
        CRITICAL: Always uses Friday's closing price to match TradingView
        Returns both the price and the date used
        """
        # Ensure datetime index
        df.index = pd.to_datetime(df.index)
        
        # Filter for Friday data points only (weekday=4)
        friday_data = df[df.index.weekday == 4]
        
        if len(friday_data) > 0:
            # Get most recent Friday's close
            most_recent_friday_close = friday_data['Close'].iloc[-1]
            weekly_close = float(most_recent_friday_close if not hasattr(most_recent_friday_close, 'iloc') 
                              else most_recent_friday_close.iloc[0])
            
            # Get the date for tracking
            most_recent_friday_date = friday_data.index[-1].strftime('%Y-%m-%d')
            
            logger.info(f"Using Friday {most_recent_friday_date} close: ${weekly_close:.2f}")
            return weekly_close, most_recent_friday_date
        else:
            # Fallback if no Friday data available
            logger.warning("No Friday data found for weekly close calculation, using first available")
            fallback_close = float(df['Close'].iloc[0])
            fallback_date = df.index[0].strftime('%Y-%m-%d')
            return fallback_close, fallback_date

class BulkEtfCalculator:
    """Main application class that orchestrates the bulk calculation process"""
    
    def __init__(self, database_url: str, polygon_api_key: str):
        self.db = DatabaseManager(database_url)
        self.api = PolygonApiClient(polygon_api_key)
        self.calculator = TechnicalCalculator()
        
    def initialize(self):
        """Initialize the application and database"""
        logger.info("Initializing Bulk ETF Calculator")
        self.db.connect()
        self.db.create_tables()
        
    def shutdown(self):
        """Clean shutdown of the application"""
        logger.info("Shutting down Bulk ETF Calculator")
        self.db.disconnect()
        
    def load_symbol_list(self, symbols_file: str) -> List[str]:
        """Load symbol list from file (one symbol per line)"""
        try:
            with open(symbols_file, 'r') as f:
                symbols = [line.strip().upper() for line in f if line.strip()]
            logger.info(f"Loaded {len(symbols)} symbols from {symbols_file}")
            return symbols
        except Exception as e:
            logger.error(f"Failed to load symbols from {symbols_file}: {e}")
            return []
    
    def update_symbol_data(self, symbol: str, force_full_update: bool = False) -> bool:
        """
        Update data for a single symbol with incremental fetching
        
        Args:
            symbol: Stock/ETF symbol to update
            force_full_update: Whether to fetch all historical data regardless of what's in DB
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            logger.info(f"Updating data for {symbol}")
            
            # Calculate date ranges needed
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            if force_full_update:
                # Fetch full historical data
                daily_start = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')  # 2 years
                four_hour_start = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')  # 60 days for proper RSI
            else:
                # Get last update dates from metadata
                with self.db.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT last_daily_update, last_4hour_update, max_date_available
                        FROM symbol_metadata 
                        WHERE symbol = %s
                    """, (symbol,))
                    metadata = cursor.fetchone()
                
                if metadata and metadata['last_daily_update']:
                    # Incremental update - start from last update
                    daily_start = metadata['last_daily_update'].strftime('%Y-%m-%d')
                    four_hour_start = metadata['last_4hour_update'].strftime('%Y-%m-%d') if metadata['last_4hour_update'] else (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
                else:
                    # First time - fetch full historical data
                    daily_start = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
                    four_hour_start = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
            
            # Fetch daily data
            daily_df = self.api.fetch_daily_data(symbol, daily_start, end_date)
            if daily_df.empty:
                logger.warning(f"No daily data retrieved for {symbol}")
                return False
                
            # Fetch 4-hour data  
            four_hour_df = self.api.fetch_four_hour_data(symbol, four_hour_start, end_date)
            if four_hour_df.empty:
                logger.warning(f"No 4-hour data retrieved for {symbol}")
                return False
            
            # Store data in database
            self._store_daily_data(symbol, daily_df)
            self._store_four_hour_data(symbol, four_hour_df)
            
            # Update metadata
            self._update_symbol_metadata(symbol, daily_df, four_hour_df)
            
            logger.info(f"Successfully updated data for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update data for {symbol}: {e}")
            # Update error count in metadata
            self._increment_api_failures(symbol, str(e))
            return False
    
    def _store_daily_data(self, symbol: str, df: pd.DataFrame):
        """Store daily price data in database"""
        with self.db.conn.cursor() as cursor:
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO daily_prices (symbol, date, open_price, high_price, low_price, close_price, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume
                """, (symbol, row['date'], row['Open'], row['High'], row['Low'], row['Close'], row['Volume']))
            self.db.conn.commit()
    
    def _store_four_hour_data(self, symbol: str, df: pd.DataFrame):
        """Store 4-hour price data in database"""
        with self.db.conn.cursor() as cursor:
            for timestamp, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO four_hour_prices (symbol, timestamp, open_price, high_price, low_price, close_price, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timestamp) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume
                """, (symbol, timestamp, row['Open'], row['High'], row['Low'], row['Close'], row['Volume']))
            self.db.conn.commit()
    
    def _update_symbol_metadata(self, symbol: str, daily_df: pd.DataFrame, four_hour_df: pd.DataFrame):
        """Update symbol metadata with latest information"""
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO symbol_metadata (
                    symbol, last_daily_update, last_4hour_update, 
                    min_date_available, max_date_available,
                    total_daily_records, total_4hour_records, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    last_daily_update = EXCLUDED.last_daily_update,
                    last_4hour_update = EXCLUDED.last_4hour_update,
                    max_date_available = EXCLUDED.max_date_available,
                    total_daily_records = EXCLUDED.total_daily_records,
                    total_4hour_records = EXCLUDED.total_4hour_records,
                    updated_at = EXCLUDED.updated_at
            """, (
                symbol,
                datetime.now(),
                datetime.now(), 
                daily_df['date'].min(),
                daily_df['date'].max(),
                len(daily_df),
                len(four_hour_df),
                datetime.now()
            ))
            self.db.conn.commit()
    
    def _increment_api_failures(self, symbol: str, error_message: str):
        """Increment API failure count for a symbol"""
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO symbol_metadata (symbol, api_failures, last_api_error, updated_at)
                VALUES (%s, 1, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    api_failures = symbol_metadata.api_failures + 1,
                    last_api_error = EXCLUDED.last_api_error,
                    updated_at = EXCLUDED.updated_at
            """, (symbol, error_message, datetime.now()))
            self.db.conn.commit()
    
    def calculate_indicators(self, symbol: str) -> Optional[TechnicalIndicators]:
        """
        Calculate all technical indicators for a symbol using database data
        
        Returns:
            TechnicalIndicators object or None if calculation fails
        """
        try:
            logger.info(f"Calculating indicators for {symbol}")
            
            # Fetch daily data from database
            with self.db.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT date, open_price, high_price, low_price, close_price, volume
                    FROM daily_prices 
                    WHERE symbol = %s 
                    ORDER BY date DESC
                    LIMIT 730
                """, (symbol,))
                daily_records = cursor.fetchall()
            
            if len(daily_records) < 100:
                logger.warning(f"Insufficient daily data for {symbol}: {len(daily_records)} days")
                return None
                
            # Convert to DataFrame
            daily_df = pd.DataFrame(daily_records)
            daily_df.columns = ['date', 'Open', 'High', 'Low', 'Close', 'Volume']
            daily_df['date'] = pd.to_datetime(daily_df['date'])
            daily_df.set_index('date', inplace=True)
            daily_df.sort_index(inplace=True)  # Ensure chronological order
            
            # Fetch 4-hour data from database
            with self.db.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT timestamp, open_price, high_price, low_price, close_price, volume
                    FROM four_hour_prices
                    WHERE symbol = %s 
                    ORDER BY timestamp DESC
                    LIMIT 168  -- 28 days * 6 (4-hour periods per day)
                """, (symbol,))
                four_hour_records = cursor.fetchall()
            
            if len(four_hour_records) < 14:
                logger.warning(f"Insufficient 4-hour data for {symbol}: {len(four_hour_records)} periods")
                return None
                
            # Convert to DataFrame
            four_hour_df = pd.DataFrame(four_hour_records)
            four_hour_df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
            four_hour_df['timestamp'] = pd.to_datetime(four_hour_df['timestamp'])
            four_hour_df.set_index('timestamp', inplace=True)
            four_hour_df.sort_index(inplace=True)  # Ensure chronological order
            
            # Calculate indicators using exact original logic
            current_price = float(daily_df['Close'].iloc[-1])
            
            # EMA calculations
            ema_20 = self.calculator.calculate_ema(daily_df['Close'], 20).iloc[-1]
            ema_20 = float(ema_20 if not hasattr(ema_20, 'iloc') else ema_20.iloc[0])
            
            ema_100 = self.calculator.calculate_ema(daily_df['Close'], 100).iloc[-1]
            ema_100 = float(ema_100 if not hasattr(ema_100, 'iloc') else ema_100.iloc[0])
            
            # RSI calculation using 4-hour data
            rsi_14 = self.calculator.calculate_rsi(four_hour_df)
            
            # Weekly close calculation (Friday-based)
            weekly_close, weekly_close_date = self.calculator.get_latest_weekly_close(daily_df)
            
            # ATR calculations
            atr_3 = self.calculator.calculate_atr(daily_df, 3)
            atr_6 = self.calculator.calculate_atr(daily_df, 6)
            
            indicators = TechnicalIndicators(
                symbol=symbol,
                current_price=current_price,
                ema_20=ema_20,
                ema_100=ema_100,
                rsi_14=rsi_14,
                weekly_close=weekly_close,
                weekly_close_date=weekly_close_date,
                atr_3=atr_3,
                atr_6=atr_6,
                calculation_date=datetime.now()
            )
            
            # Store indicators in database
            self._store_indicators(indicators)
            
            logger.info(f"Successfully calculated indicators for {symbol}")
            return indicators
            
        except Exception as e:
            logger.error(f"Failed to calculate indicators for {symbol}: {e}")
            return None
    
    def _store_indicators(self, indicators: TechnicalIndicators):
        """Store calculated indicators in database"""
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO calculated_indicators (
                    symbol, date, current_price, ema_20, ema_100, rsi_14, 
                    weekly_close, weekly_close_date, atr_3, atr_6, calculation_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    current_price = EXCLUDED.current_price,
                    ema_20 = EXCLUDED.ema_20,
                    ema_100 = EXCLUDED.ema_100,
                    rsi_14 = EXCLUDED.rsi_14,
                    weekly_close = EXCLUDED.weekly_close,
                    weekly_close_date = EXCLUDED.weekly_close_date,
                    atr_3 = EXCLUDED.atr_3,
                    atr_6 = EXCLUDED.atr_6,
                    calculation_timestamp = EXCLUDED.calculation_timestamp
            """, (
                indicators.symbol,
                indicators.calculation_date.date(),
                indicators.current_price,
                indicators.ema_20,
                indicators.ema_100,
                indicators.rsi_14,
                indicators.weekly_close,
                indicators.weekly_close_date,
                indicators.atr_3,
                indicators.atr_6,
                indicators.calculation_date
            ))
            self.db.conn.commit()
    
    def calculate_score(self, indicators: TechnicalIndicators) -> ScoringResult:
        """
        Calculate the 5-criteria score using exact original logic
        
        Args:
            indicators: TechnicalIndicators object with all calculated values
            
        Returns:
            ScoringResult object with complete scoring breakdown
        """
        # Apply the 5 criteria exactly as in original implementation
        criteria1 = indicators.current_price > indicators.ema_20  # Price > 20 EMA
        criteria2 = indicators.current_price > indicators.ema_100  # Price > 100 EMA  
        criteria3 = indicators.rsi_14 < 50  # RSI < 50
        criteria4 = indicators.current_price > indicators.weekly_close  # Price > Last Week Close
        criteria5 = indicators.atr_3 < indicators.atr_6  # 3-day ATR < 6-day ATR
        
        # Calculate total score
        total_score = sum([criteria1, criteria2, criteria3, criteria4, criteria5])
        
        # Generate descriptions exactly as in original
        trend1_desc = f"Price (${indicators.current_price:.2f}) is {'above' if criteria1 else 'below'} the 20-day EMA (${indicators.ema_20:.2f})"
        trend2_desc = f"Price (${indicators.current_price:.2f}) is {'above' if criteria2 else 'below'} the 100-day EMA (${indicators.ema_100:.2f})"
        snapback_desc = f"RSI ({indicators.rsi_14:.1f}) is {'below' if criteria3 else 'above'} the threshold (50)"
        momentum_desc = f"Current price (${indicators.current_price:.2f}) is {'above' if criteria4 else 'below'} last week's close (${indicators.weekly_close:.2f})"
        stabilizing_desc = f"3-day ATR ({indicators.atr_3:.2f}) is {'lower' if criteria5 else 'higher'} than 6-day ATR ({indicators.atr_6:.2f})"
        
        # Calculate data age
        data_age_hours = int((datetime.now() - indicators.calculation_date).total_seconds() / 3600)
        
        return ScoringResult(
            symbol=indicators.symbol,
            current_price=indicators.current_price,
            total_score=total_score,
            trend1_pass=bool(criteria1),
            trend1_current=float(indicators.current_price),
            trend1_threshold=float(indicators.ema_20),
            trend1_description=trend1_desc,
            trend2_pass=bool(criteria2),
            trend2_current=float(indicators.current_price),
            trend2_threshold=float(indicators.ema_100),
            trend2_description=trend2_desc,
            snapback_pass=bool(criteria3),
            snapback_current=float(indicators.rsi_14),
            snapback_threshold=50.0,
            snapback_description=snapback_desc,
            momentum_pass=bool(criteria4),
            momentum_current=float(indicators.current_price),
            momentum_threshold=float(indicators.weekly_close),
            momentum_description=momentum_desc,
            stabilizing_pass=bool(criteria5),
            stabilizing_current=float(indicators.atr_3),
            stabilizing_threshold=float(indicators.atr_6),
            stabilizing_description=stabilizing_desc,
            calculation_timestamp=indicators.calculation_date,
            data_age_hours=data_age_hours
        )
    
    def store_score(self, score: ScoringResult):
        """Store final scoring result in database"""
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO etf_scores (
                    symbol, current_price, total_score,
                    trend1_pass, trend1_current, trend1_threshold, trend1_description,
                    trend2_pass, trend2_current, trend2_threshold, trend2_description,
                    snapback_pass, snapback_current, snapback_threshold, snapback_description,
                    momentum_pass, momentum_current, momentum_threshold, momentum_description,
                    stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
                    calculation_timestamp, data_age_hours
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    current_price = EXCLUDED.current_price,
                    total_score = EXCLUDED.total_score,
                    trend1_pass = EXCLUDED.trend1_pass,
                    trend1_current = EXCLUDED.trend1_current,
                    trend1_threshold = EXCLUDED.trend1_threshold,
                    trend1_description = EXCLUDED.trend1_description,
                    trend2_pass = EXCLUDED.trend2_pass,
                    trend2_current = EXCLUDED.trend2_current,
                    trend2_threshold = EXCLUDED.trend2_threshold,
                    trend2_description = EXCLUDED.trend2_description,
                    snapback_pass = EXCLUDED.snapback_pass,
                    snapback_current = EXCLUDED.snapback_current,
                    snapback_threshold = EXCLUDED.snapback_threshold,
                    snapback_description = EXCLUDED.snapback_description,
                    momentum_pass = EXCLUDED.momentum_pass,
                    momentum_current = EXCLUDED.momentum_current,
                    momentum_threshold = EXCLUDED.momentum_threshold,
                    momentum_description = EXCLUDED.momentum_description,
                    stabilizing_pass = EXCLUDED.stabilizing_pass,
                    stabilizing_current = EXCLUDED.stabilizing_current,
                    stabilizing_threshold = EXCLUDED.stabilizing_threshold,
                    stabilizing_description = EXCLUDED.stabilizing_description,
                    calculation_timestamp = EXCLUDED.calculation_timestamp,
                    data_age_hours = EXCLUDED.data_age_hours
            """, (
                score.symbol, score.current_price, score.total_score,
                score.trend1_pass, score.trend1_current, score.trend1_threshold, score.trend1_description,
                score.trend2_pass, score.trend2_current, score.trend2_threshold, score.trend2_description,
                score.snapback_pass, score.snapback_current, score.snapback_threshold, score.snapback_description,
                score.momentum_pass, score.momentum_current, score.momentum_threshold, score.momentum_description,
                score.stabilizing_pass, score.stabilizing_current, score.stabilizing_threshold, score.stabilizing_description,
                score.calculation_timestamp, score.data_age_hours
            ))
            self.db.conn.commit()
    
    def export_scores_to_csv(self, output_file: str) -> bool:
        """
        Export all calculated scores to CSV format for the display application
        
        Args:
            output_file: Path to output CSV file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            logger.info(f"Exporting scores to {output_file}")
            
            with self.db.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM etf_scores 
                    ORDER BY total_score DESC, symbol ASC
                """)
                scores = cursor.fetchall()
            
            if not scores:
                logger.warning("No scores found to export")
                return False
            
            # Write CSV file
            with open(output_file, 'w', newline='') as csvfile:
                fieldnames = [
                    'symbol', 'current_price', 'total_score',
                    'trend1_pass', 'trend1_current', 'trend1_threshold', 'trend1_description',
                    'trend2_pass', 'trend2_current', 'trend2_threshold', 'trend2_description', 
                    'snapback_pass', 'snapback_current', 'snapback_threshold', 'snapback_description',
                    'momentum_pass', 'momentum_current', 'momentum_threshold', 'momentum_description',
                    'stabilizing_pass', 'stabilizing_current', 'stabilizing_threshold', 'stabilizing_description',
                    'calculation_timestamp', 'data_age_hours'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for score in scores:
                    writer.writerow(score)
            
            logger.info(f"Successfully exported {len(scores)} scores to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export scores to CSV: {e}")
            return False
    
    def process_all_symbols(self, symbols_file: str, output_csv: str, force_update: bool = False):
        """
        Main processing function - updates data and calculates scores for all symbols
        
        Args:
            symbols_file: Path to file containing list of symbols
            output_csv: Path to output CSV file  
            force_update: Whether to force full data update for all symbols
        """
        logger.info("Starting bulk processing of all symbols")
        start_time = datetime.now()
        
        # Load symbols
        symbols = self.load_symbol_list(symbols_file)
        if not symbols:
            logger.error("No symbols loaded - aborting")
            return
        
        successful_updates = 0
        successful_calculations = 0
        
        # Process each symbol
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"Processing symbol {i}/{len(symbols)}: {symbol}")
            
            # Update data
            if self.update_symbol_data(symbol, force_update):
                successful_updates += 1
                
                # Calculate indicators and score
                indicators = self.calculate_indicators(symbol)
                if indicators:
                    score = self.calculate_score(indicators)
                    self.store_score(score)
                    successful_calculations += 1
                    
                    logger.info(f"✓ {symbol}: Score {score.total_score}/5")
                else:
                    logger.warning(f"✗ {symbol}: Failed to calculate indicators")
            else:
                logger.warning(f"✗ {symbol}: Failed to update data")
            
            # Progress update every 50 symbols
            if i % 50 == 0:
                elapsed = datetime.now() - start_time
                logger.info(f"Progress: {i}/{len(symbols)} symbols processed in {elapsed}")
        
        # Export results
        export_success = self.export_scores_to_csv(output_csv)
        
        # Final summary
        total_time = datetime.now() - start_time
        logger.info(f"""
        Bulk processing completed in {total_time}
        Total symbols: {len(symbols)}
        Successful data updates: {successful_updates}
        Successful calculations: {successful_calculations}
        CSV export: {'SUCCESS' if export_success else 'FAILED'}
        Output file: {output_csv if export_success else 'N/A'}
        """)

def main():
    """Main entry point for the bulk calculator application"""
    
    # Configuration from environment variables
    database_url = os.environ.get('DATABASE_URL')
    polygon_api_key = os.environ.get('POLYGON_API_KEY')
    
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    if not polygon_api_key:
        logger.error("POLYGON_API_KEY environment variable not set")
        sys.exit(1)
    
    # File paths
    symbols_file = os.environ.get('SYMBOLS_FILE', 'symbols.txt')
    output_csv = os.environ.get('OUTPUT_CSV', f'etf_scores_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    force_update = os.environ.get('FORCE_UPDATE', 'false').lower() == 'true'
    
    # Initialize and run application
    calculator = BulkEtfCalculator(database_url, polygon_api_key)
    
    try:
        calculator.initialize()
        calculator.process_all_symbols(symbols_file, output_csv, force_update)
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        calculator.shutdown()

if __name__ == "__main__":
    main()