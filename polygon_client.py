import os
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests

logger = logging.getLogger(__name__)

class PolygonDataService:
    """Service to fetch ETF price and historical data from Polygon.io"""
    
    @staticmethod
    def get_etf_price(symbol):
        """Get the latest price for an ETF"""
        try:
            # Using REST API directly for simplicity
            api_key = os.environ.get("POLYGON_API_KEY")
            if not api_key:
                logger.error("No Polygon API key found in environment variables")
                return None
            
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apiKey={api_key}"
            response = requests.get(url)
            
            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"Error getting price for {symbol}: {error_msg}")
                return None
            
            data = response.json()
            if data['results']:
                # Return the closing price from previous day
                return data['results'][0]['c']
            else:
                logger.warning(f"No price data found for {symbol}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {str(e)}")
            return None
    
    @staticmethod
    def get_historical_data(symbol, timespan="day", multiplier=1, from_date=None, to_date=None, limit=100):
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
            api_key = os.environ.get("POLYGON_API_KEY")
            if not api_key:
                logger.error("No Polygon API key found in environment variables")
                return None
            
            # Default to 6 months of data if no dates specified
            if not from_date:
                from_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
            elif isinstance(from_date, datetime):
                from_date = from_date.strftime('%Y-%m-%d')
                
            if not to_date:
                to_date = datetime.now().strftime('%Y-%m-%d')
            elif isinstance(to_date, datetime):
                to_date = to_date.strftime('%Y-%m-%d')
            
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}?limit={limit}&apiKey={api_key}"
            response = requests.get(url)
            
            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"Error getting historical data for {symbol}: {error_msg}")
                return None
            
            data = response.json()
            if not data.get('results'):
                logger.error(f"No daily data available for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data['results'])
            
            # Rename columns to match yfinance format
            df = df.rename(columns={
                'o': 'Open',
                'h': 'High',
                'l': 'Low',
                'c': 'Close',
                'v': 'Volume',
                't': 'Timestamp'
            })
            
            # Convert timestamp to datetime
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
            df.set_index('Timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None
    
    @staticmethod
    def calculate_etf_score(symbol):
        """
        Calculate a technical score (1-5) for an ETF based on specific indicators:
        1. Trend 1: Price > 20 EMA on Daily Timeframe
        2. Trend 2: Price > 100 EMA on Daily Timeframe
        3. Snapback: RSI < 50 on Daily Timeframe (4-hour not available in Basic plan)
        4. Momentum: Price > Previous Week's Closing Price
        5. Stabilizing: 3-Day ATR < 6-Day ATR
        
        Each indicator = 1 point, total score from 0-5
        """
        try:
            # Get current price
            current_price = PolygonDataService.get_etf_price(symbol)
            if not current_price:
                logger.error(f"Unable to get current price for {symbol}")
                return PolygonDataService._default_indicators()
            
            # Get historical data (6 months)
            hist_data = PolygonDataService.get_historical_data(symbol, timespan="day", limit=180)
            if hist_data is None or len(hist_data) < 100:
                logger.error(f"Not enough historical data for {symbol}")
                return PolygonDataService._default_indicators()
            
            score = 0
            indicators = {}
            
            # 1. Trend 1: Price > 20 EMA on Daily Timeframe
            ema_20 = hist_data['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
            trend1_pass = current_price > ema_20
            if trend1_pass:
                score += 1
            
            trend1_desc = f"Price (${current_price:.2f}) is {'above' if trend1_pass else 'below'} the 20-day EMA (${ema_20:.2f})"
            indicators['trend1'] = {
                'pass': trend1_pass,
                'current': float(current_price),
                'threshold': float(ema_20),
                'description': trend1_desc
            }
            
            # 2. Trend 2: Price > 100 EMA on Daily Timeframe
            ema_100 = hist_data['Close'].ewm(span=100, adjust=False).mean().iloc[-1]
            trend2_pass = current_price > ema_100
            if trend2_pass:
                score += 1
            
            trend2_desc = f"Price (${current_price:.2f}) is {'above' if trend2_pass else 'below'} the 100-day EMA (${ema_100:.2f})"
            indicators['trend2'] = {
                'pass': trend2_pass,
                'current': float(current_price),
                'threshold': float(ema_100),
                'description': trend2_desc
            }
            
            # 3. Snapback: RSI < 50 on Daily Timeframe
            delta = hist_data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            # Handle division by zero
            rs = gain / loss.replace(0, 0.001)
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            snapback_pass = current_rsi < 50
            if snapback_pass:
                score += 1
            
            snapback_desc = f"RSI ({current_rsi:.1f}) is {'below' if snapback_pass else 'above'} the threshold (50)"
            indicators['snapback'] = {
                'pass': snapback_pass,
                'current': float(current_rsi),
                'threshold': 50.0,
                'description': snapback_desc
            }
            
            # 4. Momentum: Above Previous Week's Closing Price
            # Find exactly 7 calendar days ago or the closest trading day before that
            today = hist_data.index[-1]
            seven_days_ago = today - pd.Timedelta(days=7)
            
            # Find the closest trading day on or before 7 days ago
            closest_date = hist_data.index[hist_data.index <= seven_days_ago]
            
            if len(closest_date) > 0:
                prev_week_idx = closest_date[-1]  # Get the last date that's <= 7 days ago
                prev_week_close = hist_data.loc[prev_week_idx, 'Close']
            else:
                # Fallback if we don't have data from 7 days ago (use 5 trading days as approximation)
                prev_week_close = hist_data['Close'].iloc[-6] if len(hist_data) > 5 else hist_data['Close'].iloc[0]
            
            momentum_pass = current_price > prev_week_close
            if momentum_pass:
                score += 1
            
            momentum_desc = f"Current price (${current_price:.2f}) is {'above' if momentum_pass else 'below'} last week's close (${prev_week_close:.2f})"
            indicators['momentum'] = {
                'pass': momentum_pass,
                'current': float(current_price),
                'threshold': float(prev_week_close),
                'description': momentum_desc
            }
            
            # 5. Stabilizing: 3 Day ATR < 6 Day ATR
            high_low = hist_data['High'] - hist_data['Low']
            high_close = abs(hist_data['High'] - hist_data['Close'].shift())
            low_close = abs(hist_data['Low'] - hist_data['Close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            
            atr_3 = true_range.rolling(3).mean().iloc[-1]
            atr_6 = true_range.rolling(6).mean().iloc[-1]
            
            stabilizing_pass = atr_3 < atr_6
            if stabilizing_pass:
                score += 1
            
            stabilizing_desc = f"3-day ATR ({atr_3:.2f}) is {'lower' if stabilizing_pass else 'higher'} than 6-day ATR ({atr_6:.2f})"
            indicators['stabilizing'] = {
                'pass': stabilizing_pass,
                'current': float(atr_3),
                'threshold': float(atr_6),
                'description': stabilizing_desc
            }
            
            logger.info(f"Calculated score: {score}/5 using Polygon data")
            return score, indicators
            
        except Exception as e:
            logger.error(f"Error calculating ETF score: {str(e)}")
            return PolygonDataService._default_indicators()
    
    @staticmethod
    def _default_indicators():
        """Return default indicator values in case of errors"""
        return 3, {
            'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Error retrieving data'},
            'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Error retrieving data'},
            'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Error retrieving data'},
            'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Error retrieving data'},
            'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Error retrieving data'}
        }