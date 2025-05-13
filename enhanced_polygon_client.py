"""
Enhanced Polygon.io Client for Income Machine
This module provides an enhanced client for the Polygon.io API with specialized ETF analysis.
"""

import logging
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from polygon import RESTClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedPolygonService:
    """Enhanced service to fetch and analyze ETF data using Polygon.io API with TA library"""
    
    # Singleton client instance
    _client = None
    
    # Cache for API responses (symbol -> (data, timestamp))
    _cache = {}
    
    @classmethod
    def _get_client(cls):
        """Get or create the Polygon.io client instance"""
        if cls._client is None:
            api_key = os.environ.get('POLYGON_API_KEY')
            if not api_key:
                logger.error("Missing POLYGON_API_KEY environment variable")
                return None
            
            cls._client = RESTClient(api_key)
            logger.info("Initialized Polygon.io client")
        
        return cls._client
    
    @classmethod
    def get_etf_price(cls, symbol):
        """Get the latest price for an ETF"""
        try:
            client = cls._get_client()
            if not client:
                return None
            
            # Get previous day's close
            resp = client.get_previous_close(symbol)
            if resp and hasattr(resp, 'results') and resp.results:
                # Get the last result
                result = resp.results[-1]
                price = result.c  # Closing price
                
                logger.info(f"Got price for {symbol}: ${price}")
                return price
            
            logger.warning(f"No price data for {symbol}")
            return None
        
        except Exception as e:
            logger.error(f"Error getting ETF price for {symbol}: {str(e)}")
            return None
    
    @classmethod
    def get_historical_data(cls, symbol, timespan="day", multiplier=1, from_date=None, to_date=None, limit=200):
        """
        Get historical price data for technical analysis
        
        Parameters:
        - symbol: Ticker symbol
        - timespan: "minute", "hour", "day", "week", "month", "quarter", "year"
        - multiplier: Size of the timespan multiplier
        - from_date: Start date (datetime or string)
        - to_date: End date (datetime or string)
        - limit: Number of results (max 50000)
        
        Returns:
        - pandas DataFrame with OHLCV data
        """
        try:
            # Generate cache key
            cache_key = f"{symbol}_{timespan}_{multiplier}_{from_date}_{to_date}_{limit}"
            
            # Check cache
            if cache_key in cls._cache:
                data, timestamp = cls._cache[cache_key]
                # Use cache if less than 1 hour old
                if (time.time() - timestamp) < 3600:
                    logger.info(f"Using cached data for {symbol}")
                    return data
            
            # Get client
            client = cls._get_client()
            if not client:
                return None
            
            # Convert string dates to datetime if needed
            if isinstance(from_date, str):
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
            
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                # Set to end of day
                to_date = to_date.replace(hour=23, minute=59, second=59)
            
            # Convert datetime to ISO 8601 string for API
            from_date_str = from_date.isoformat() if from_date else None
            to_date_str = to_date.isoformat() if to_date else None
            
            # Fetch data from Polygon.io API
            logger.info(f"Fetching {timespan} data for {symbol} from {from_date_str} to {to_date_str}")
            
            # Get aggregates (bars) from API
            aggs = []
            
            # Use pagination if needed
            if limit > 5000:
                pages = (limit + 4999) // 5000  # Calculate number of pages
                for page in range(pages):
                    page_limit = min(5000, limit - page * 5000)
                    if page_limit <= 0:
                        break
                    
                    # Adjust from_date for each page
                    current_from_date = from_date_str
                    if page > 0 and aggs:
                        # Start from where the last page ended
                        last_timestamp = aggs[-1].timestamp
                        current_from_date = datetime.fromtimestamp(last_timestamp / 1000).isoformat()
                    
                    # Fetch data for this page
                    resp = client.get_aggs(
                        ticker=symbol,
                        multiplier=multiplier,
                        timespan=timespan,
                        from_=current_from_date,
                        to=to_date_str,
                        limit=page_limit
                    )
                    
                    if resp and hasattr(resp, 'results'):
                        aggs.extend(resp.results)
                    
                    # Break if we got fewer results than requested
                    if not resp or not hasattr(resp, 'results') or len(resp.results) < page_limit:
                        break
            else:
                # Fetch data in a single request
                resp = client.get_aggs(
                    ticker=symbol,
                    multiplier=multiplier,
                    timespan=timespan,
                    from_=from_date_str,
                    to=to_date_str,
                    limit=limit
                )
                
                if resp and hasattr(resp, 'results'):
                    aggs.extend(resp.results)
            
            # Create DataFrame from results
            if not aggs:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': agg.timestamp,
                'open': agg.open,
                'high': agg.high,
                'low': agg.low,
                'close': agg.close,
                'volume': agg.volume
            } for agg in aggs])
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            
            # Sort by timestamp
            df.sort_index(inplace=True)
            
            # Store in cache
            cls._cache[cache_key] = (df, time.time())
            
            logger.info(f"Retrieved {len(df)} {timespan} bars for {symbol}")
            return df
        
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None
    
    @classmethod
    def calculate_etf_score(cls, symbol):
        """
        Calculate a technical score (1-5) for an ETF based on specific indicators:
        1. Trend 1: Price > 20 EMA on Daily Timeframe
        2. Trend 2: Price > 100 EMA on Daily Timeframe
        3. Snapback: RSI < 50 on Daily Timeframe
        4. Momentum: Price > Previous Week's Closing Price
        5. Stabilizing: 3-Day ATR < 6-Day ATR
        
        Each indicator = 1 point, total score from 0-5
        """
        try:
            # Set default indicator values (all false)
            default_indicators = {
                'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > 20-day EMA'},
                'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > 100-day EMA'},
                'snapback': {'pass': False, 'current': 0, 'threshold': 50, 'description': 'RSI < 50'},
                'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > Previous Week\'s Close'},
                'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': '3-day ATR < 6-day ATR'}
            }
            
            # Get date range (about 1 year of data)
            to_date = datetime.now()
            from_date = to_date - timedelta(days=365)
            
            # Fetch daily historical data
            df = cls.get_historical_data(
                symbol=symbol,
                timespan="day",
                from_date=from_date,
                to_date=to_date,
                limit=365
            )
            
            if df is None or len(df) < 100:
                logger.warning(f"Insufficient historical data for {symbol}")
                return None
            
            # Get current price (latest close)
            current_price = df['close'].iloc[-1]
            
            # Calculate 20-day EMA
            df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
            
            # Calculate 100-day EMA
            df['ema_100'] = df['close'].ewm(span=100, adjust=False).mean()
            
            # Calculate RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Calculate ATR
            df['tr1'] = abs(df['high'] - df['low'])
            df['tr2'] = abs(df['high'] - df['close'].shift(1))
            df['tr3'] = abs(df['low'] - df['close'].shift(1))
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            df['atr_3'] = df['tr'].rolling(window=3).mean()
            df['atr_6'] = df['tr'].rolling(window=6).mean()
            
            # Find previous week's close (5 trading days ago)
            prev_week_close = df['close'].shift(5).iloc[-1]
            
            # Check indicators
            indicators = default_indicators.copy()
            score = 0
            
            # 1. Trend 1: Price > 20 EMA
            if current_price > df['ema_20'].iloc[-1]:
                indicators['trend1']['pass'] = True
                score += 1
            indicators['trend1']['current'] = float(current_price)
            indicators['trend1']['threshold'] = float(df['ema_20'].iloc[-1])
            
            # 2. Trend 2: Price > 100 EMA
            if current_price > df['ema_100'].iloc[-1]:
                indicators['trend2']['pass'] = True
                score += 1
            indicators['trend2']['current'] = float(current_price)
            indicators['trend2']['threshold'] = float(df['ema_100'].iloc[-1])
            
            # 3. Snapback: RSI < 50
            current_rsi = df['rsi'].iloc[-1]
            if current_rsi < 50:
                indicators['snapback']['pass'] = True
                score += 1
            indicators['snapback']['current'] = float(current_rsi)
            
            # 4. Momentum: Price > Previous Week's Close
            if current_price > prev_week_close:
                indicators['momentum']['pass'] = True
                score += 1
            indicators['momentum']['current'] = float(current_price)
            indicators['momentum']['threshold'] = float(prev_week_close)
            
            # 5. Stabilizing: 3-Day ATR < 6-Day ATR
            current_atr3 = df['atr_3'].iloc[-1]
            current_atr6 = df['atr_6'].iloc[-1]
            if current_atr3 < current_atr6:
                indicators['stabilizing']['pass'] = True
                score += 1
            indicators['stabilizing']['current'] = float(current_atr3)
            indicators['stabilizing']['threshold'] = float(current_atr6)
            
            logger.info(f"ETF {symbol} score: {score}/5 (price: ${current_price:.2f})")
            return score, current_price, indicators
        
        except Exception as e:
            logger.error(f"Error calculating score for {symbol}: {str(e)}")
            return None
    
    @classmethod
    def _default_indicators():
        """Return default indicator values in case of errors"""
        return {
            'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > 20-day EMA'},
            'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > 100-day EMA'},
            'snapback': {'pass': False, 'current': 0, 'threshold': 50, 'description': 'RSI < 50'},
            'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > Previous Week\'s Close'},
            'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': '3-day ATR < 6-day ATR'}
        }