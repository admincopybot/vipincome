"""
Backtest Service for Income Machine
This module provides functionality to backtest ETF technical scores for historical dates.
"""

import logging
import datetime
import json
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

from database import get_cached_price_data, save_price_data
from models import BacktestResult
from simplified_market_data import SimplifiedMarketDataService
from enhanced_polygon_client import EnhancedPolygonService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BacktestService:
    """Service for ETF backtesting to analyze historical ETF recommendations"""
    
    @staticmethod
    def calculate_historical_etf_score(symbol, date, use_cache=True):
        """
        Calculate ETF score for a given date in the past
        
        Args:
            symbol (str): ETF symbol
            date (datetime): Date to calculate score for
            use_cache (bool): Whether to use cached data
            
        Returns:
            tuple: (score, indicators_dict)
        """
        logger.info(f"Calculating historical score for {symbol} on {date.strftime('%Y-%m-%d')}")
        
        try:
            # Convert to datetime if string
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d')
            
            # Get data for 200 days before the target date to ensure enough history
            from_date = date - timedelta(days=200)
            to_date = date
            
            # Get historical data
            df = BacktestService._fetch_historical_data_for_date_range(symbol, from_date, to_date)
            
            if df is None or len(df) < 100:
                logger.error(f"Insufficient historical data for {symbol} on {date.strftime('%Y-%m-%d')}")
                return None, None
            
            # Filter data up to the target date
            df = df[df.index <= pd.Timestamp(date)]
            
            if df.empty:
                logger.error(f"No data available for {symbol} up to {date.strftime('%Y-%m-%d')}")
                return None, None
            
            # Get the closing price on the target date (or the last available date)
            current_price = df.iloc[-1]['close']
            
            # Calculate indicators
            score, indicators = BacktestService._calculate_indicators_for_date(df, current_price)
            
            return score, indicators
        
        except Exception as e:
            logger.error(f"Error calculating historical score for {symbol} on {date}: {str(e)}")
            return None, None
    
    @staticmethod
    def create_backtest(date_str, symbols=None, cache_result=True):
        """
        Create a backtest for a specific date with multiple ETFs
        
        Args:
            date_str (str): Date in YYYY-MM-DD format
            symbols (list): ETF symbols to backtest, or None for all tracked ETFs
            cache_result (bool): Whether to cache the result
            
        Returns:
            dict: Backtest results by symbol
        """
        logger.info(f"Creating backtest for {date_str}")
        
        try:
            # Convert string to datetime
            backtest_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # If no symbols provided, use default ETFs
            if not symbols:
                symbols = SimplifiedMarketDataService.default_etfs
            
            results = {}
            data_source = "unknown"
            
            # Calculate score for each symbol
            for symbol in symbols:
                try:
                    score, indicators = BacktestService.calculate_historical_etf_score(symbol, backtest_date)
                    
                    if score is not None:
                        results[symbol] = {
                            'score': score,
                            'indicators': indicators
                        }
                    else:
                        results[symbol] = {
                            'error': f"Failed to calculate score for {symbol} on {date_str}"
                        }
                except Exception as e:
                    logger.error(f"Error calculating backtest for {symbol}: {str(e)}")
                    results[symbol] = {
                        'error': str(e)
                    }
            
            # Add metadata
            results['_date'] = date_str
            results['_symbols'] = symbols
            results['_source'] = data_source
            
            # Cache result if requested
            if cache_result:
                try:
                    # Create backtest result model
                    backtest_result = BacktestResult(
                        date=date_str,
                        symbols=','.join(symbols),
                        results=json.dumps(results),
                        created_at=datetime.now()
                    )
                    backtest_result.save()
                    logger.info(f"Cached backtest result for {date_str}")
                except Exception as e:
                    logger.error(f"Failed to cache backtest result: {str(e)}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error creating backtest for {date_str}: {str(e)}")
            return {
                'error': f"Failed to create backtest: {str(e)}"
            }
    
    @staticmethod
    def get_cached_backtest(date_str):
        """
        Get a cached backtest result
        
        Args:
            date_str (str): Date in YYYY-MM-DD format
            
        Returns:
            dict or None: Cached backtest results or None if not found
        """
        logger.info(f"Getting cached backtest for {date_str}")
        
        try:
            # Query for backtest result
            backtest_result = BacktestResult.select().where(BacktestResult.date == date_str).order_by(
                BacktestResult.created_at.desc()
            ).first()
            
            if backtest_result:
                # Parse JSON results
                results = json.loads(backtest_result.results)
                logger.info(f"Found cached backtest for {date_str}")
                return results
            
            logger.info(f"No cached backtest found for {date_str}")
            return None
        
        except Exception as e:
            logger.error(f"Error getting cached backtest for {date_str}: {str(e)}")
            return None
    
    @staticmethod
    def _fetch_historical_data_for_date_range(symbol, from_date, to_date):
        """
        Fetch historical data for a date range
        
        Args:
            symbol (str): ETF symbol
            from_date (datetime): Start date
            to_date (datetime): End date
            
        Returns:
            DataFrame or None: Historical price data or None if error
        """
        try:
            logger.info(f"Fetching historical data for {symbol} from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
            
            # Try polygon.io first
            try:
                df = EnhancedPolygonService.get_historical_data(
                    symbol, 
                    timespan="day",
                    from_date=from_date.strftime('%Y-%m-%d'),
                    to_date=to_date.strftime('%Y-%m-%d'),
                    limit=5000
                )
                
                if df is not None and not df.empty:
                    # Convert polygon.io data format
                    df = pd.DataFrame({
                        'timestamp': df.index / 1000000000,  # Convert nanoseconds to seconds
                        'open': df['open'],
                        'high': df['high'],
                        'low': df['low'],
                        'close': df['close'],
                        'volume': df['volume']
                    })
                    
                    # Convert timestamp to datetime and set as index
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('timestamp', inplace=True)
                    
                    logger.info(f"Successfully fetched {len(df)} days of historical data for {symbol} from polygon.io")
                    return df
            except Exception as e:
                logger.warning(f"Failed to fetch data from polygon.io: {str(e)}")
            
            # Fall back to yfinance
            from_date_str = from_date.strftime('%Y-%m-%d')
            to_date_str = to_date.strftime('%Y-%m-%d')
            
            # Use yfinance to download data
            import yfinance as yf
            df = yf.download(symbol, start=from_date_str, end=to_date_str, progress=False)
            
            if df is not None and not df.empty:
                # Rename columns to match our format
                df = df.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                
                logger.info(f"Successfully fetched {len(df)} days of historical data for {symbol} from yfinance")
                return df
            
            logger.error(f"Failed to fetch historical data for {symbol}")
            return None
        
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    @staticmethod
    def _calculate_indicators_for_date(df, current_price):
        """
        Calculate the 5 technical indicators for a historical date
        
        Args:
            df (DataFrame): Historical price data
            current_price (float): Closing price for the date
            
        Returns:
            tuple: (score, indicators_dict)
        """
        try:
            # Calculate EMAs
            df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['ema_100'] = df['close'].ewm(span=100, adjust=False).mean()
            
            # Calculate RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Calculate ATR
            df['tr1'] = abs(df['high'] - df['low'])
            df['tr2'] = abs(df['high'] - df['close'].shift())
            df['tr3'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            df['atr_3'] = df['tr'].rolling(window=3).mean()
            df['atr_6'] = df['tr'].rolling(window=6).mean()
            
            # Get previous week's close
            # Assume df is sorted by date in ascending order
            last_week_close = df['close'].shift(5)  # Approximation, not perfect
            
            # Check indicators
            # 1. Trend 1: Price > 20 EMA
            trend1 = current_price > df['ema_20'].iloc[-1]
            
            # 2. Trend 2: Price > 100 EMA
            trend2 = current_price > df['ema_100'].iloc[-1]
            
            # 3. Snapback: RSI < 50
            snapback = df['rsi'].iloc[-1] < 50
            
            # 4. Momentum: Price > Previous Week's Close
            momentum = current_price > last_week_close.iloc[-1]
            
            # 5. Stabilizing: 3-Day ATR < 6-Day ATR
            stabilizing = df['atr_3'].iloc[-1] < df['atr_6'].iloc[-1]
            
            # Calculate score (1 point for each indicator)
            score = sum([trend1, trend2, snapback, momentum, stabilizing])
            
            # Build indicator details
            indicators = {
                'trend1': {
                    'pass': trend1,
                    'current': float(current_price),
                    'threshold': float(df['ema_20'].iloc[-1]),
                    'description': 'Price > 20-day EMA'
                },
                'trend2': {
                    'pass': trend2,
                    'current': float(current_price),
                    'threshold': float(df['ema_100'].iloc[-1]),
                    'description': 'Price > 100-day EMA'
                },
                'snapback': {
                    'pass': snapback,
                    'current': float(df['rsi'].iloc[-1]),
                    'threshold': 50.0,
                    'description': 'RSI < 50'
                },
                'momentum': {
                    'pass': momentum,
                    'current': float(current_price),
                    'threshold': float(last_week_close.iloc[-1]),
                    'description': 'Price > Previous Week\'s Close'
                },
                'stabilizing': {
                    'pass': stabilizing,
                    'current': float(df['atr_3'].iloc[-1]),
                    'threshold': float(df['atr_6'].iloc[-1]),
                    'description': '3-day ATR < 6-day ATR'
                }
            }
            
            return score, indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return 0, {}