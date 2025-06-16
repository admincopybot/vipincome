"""
Enhanced ETF Scoring System for Income Machine
This module provides an improved implementation of the 5-factor technical scoring system
for ETFs, with reliable calculations that match TradingView's results.
"""

import os
import requests
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

def fetch_daily_data(symbol, period='2y'):
    """
    Fetch daily price data for the given symbol using Polygon API.
    
    Args:
        symbol (str): The ETF symbol (e.g., 'XLP', 'SPY')
        period (str): The time period to fetch (default: '2y' for 2 years)
        
    Returns:
        pandas.DataFrame: DataFrame with OHLCV data at daily timeframe
    """
    try:
        api_key = os.environ.get("TRADELIST_API_KEY")
        if not api_key:
            logger.error("No TheTradeList API key found in environment variables")
            return pd.DataFrame()
        
        # Calculate from_date based on period
        if period == '2y':
            days = 730
        elif period == '1y':
            days = 365
        elif period == '6mo':
            days = 180
        elif period == '3mo':
            days = 90
        else:
            days = 730  # Default to 2 years
        
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Use TheTradeList range-data endpoint for historical data
        url = f"https://api.thetradelist.com/v1/data/range-data"
        params = {
            'ticker': symbol,
            'range': '1/day',
            'startdate': from_date,
            'enddate': to_date,
            'limit': 5000,
            'next_url': '',
            'apiKey': api_key
        }
        
        logger.info(f"Fetching daily data for {symbol} from {from_date} to {to_date}")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Error fetching daily data for {symbol}: {response.text}")
            return pd.DataFrame()
        
        data = response.json()
        
        if 'results' not in data or not data['results']:
            logger.warning(f"No daily data found for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(data['results'])
        
        # Rename columns to match yfinance format
        df = df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume',
            't': 'timestamp'
        })
        
        # Convert timestamp to datetime and set as index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Remove any extra columns to match yfinance output
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Handle missing data
        df.dropna(inplace=True)
        
        # Validate that we have enough data
        if len(df) < 100:  # Minimum required for 100-day EMA
            logger.warning(f"Warning: Insufficient data for {symbol}, only {len(df)} days available")
        
        return df
    except Exception as e:
        logger.error(f"Error fetching daily data for {symbol}: {str(e)}")
        return pd.DataFrame()

def fetch_hourly_data(symbol, period='7d'):
    """
    Fetch hourly price data for the given symbol using Polygon API.
    
    Args:
        symbol (str): The ETF symbol (e.g., 'XLP', 'SPY')
        period (str): The time period to fetch (default: '7d' for 7 days)
        
    Returns:
        pandas.DataFrame: DataFrame with OHLCV data at hourly timeframe
    """
    try:
        api_key = os.environ.get("POLYGON_API_KEY")
        if not api_key:
            logger.error("No Polygon API key found in environment variables")
            return pd.DataFrame()
        
        # Calculate from_date based on period
        if period == '7d':
            days = 7
        elif period == '5d':
            days = 5
        elif period == '3d':
            days = 3
        elif period == '1d':
            days = 1
        else:
            days = 7  # Default to 7 days
        
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Use the v2/aggs/ticker/{stocksTicker}/range endpoint for historical data
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/hour/{from_date}/{to_date}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 5000,
            'apiKey': api_key
        }
        
        logger.info(f"Fetching hourly data for {symbol} from {from_date} to {to_date}")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Error fetching hourly data for {symbol}: {response.text}")
            return pd.DataFrame()
        
        data = response.json()
        
        if 'results' not in data or not data['results']:
            logger.warning(f"No hourly data found for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(data['results'])
        
        # Rename columns to match yfinance format
        df = df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume',
            't': 'timestamp'
        })
        
        # Convert timestamp to datetime and set as index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Remove any extra columns to match yfinance output
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Handle missing data
        df.dropna(inplace=True)
        
        return df
    except Exception as e:
        logger.error(f"Error fetching hourly data for {symbol}: {str(e)}")
        return pd.DataFrame()

def fetch_four_hour_data(symbol, period='28d'):
    """
    Fetch 4-hour price data for the given symbol using Polygon API.
    Used for RSI calculation to match TradingView's 4-hour RSI.
    
    Args:
        symbol (str): The ETF symbol (e.g., 'XLP', 'SPY')
        period (str): The time period to fetch (default: '28d' for 28 days)
        
    Returns:
        pandas.DataFrame: DataFrame with OHLCV data at 4-hour timeframe
    """
    try:
        api_key = os.environ.get("POLYGON_API_KEY")
        if not api_key:
            logger.error("No Polygon API key found in environment variables")
            return pd.DataFrame()
        
        # Calculate from_date based on period
        if period == '28d':
            days = 28
        elif period == '14d':
            days = 14
        elif period == '7d':
            days = 7
        else:
            days = 28  # Default to 28 days (4 weeks)
        
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Request 4-hour bars - use multiplier=4 with timespan="hour"
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/4/hour/{from_date}/{to_date}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 5000,
            'apiKey': api_key
        }
        
        logger.info(f"Fetching 4-hour data for {symbol} from {from_date} to {to_date}")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Error fetching 4-hour data for {symbol}: {response.text}")
            return pd.DataFrame()
        
        data = response.json()
        
        if 'results' not in data or not data['results']:
            logger.warning(f"No 4-hour data found for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(data['results'])
        
        # Rename columns to match yfinance format
        df = df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume',
            't': 'timestamp'
        })
        
        # Convert timestamp to datetime and set as index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Remove any extra columns to match yfinance output
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Handle missing data
        df.dropna(inplace=True)
        
        logger.info(f"[POLYGON API] Successfully fetched 4-hour data for {symbol}: {len(df)} bars")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching 4-hour data for {symbol}: {str(e)}")
        return pd.DataFrame()

def get_latest_weekly_close(df):
    """
    Get the latest completed weekly close price.
    ALWAYS uses Friday's closing price for weekly candles to match TradingView.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        
    Returns:
        float: The closing price from the most recent completed Friday
    """
    # Ensure we have a datetime index
    df.index = pd.to_datetime(df.index)
    
    # Get the day of the week for the latest data point (0=Monday, 4=Friday, 6=Sunday)
    current_day = df.index[-1].weekday()
    today_date = df.index[-1].date()
    
    # CRITICAL FIX: Find the most recent Friday data point directly
    # This ensures we get the previous Friday's close, not today's close
    
    # First, filter for only Friday data points (weekday=4)
    friday_data = df[df.index.weekday == 4]
    
    if len(friday_data) > 0:
        # Get the most recent Friday's close
        most_recent_friday_close = friday_data['Close'].iloc[-1]
        weekly_close = float(most_recent_friday_close if not hasattr(most_recent_friday_close, 'iloc') 
                          else most_recent_friday_close.iloc[0])
        
        # Log the date we're using for the weekly close
        most_recent_friday_date = friday_data.index[-1].strftime('%Y-%m-%d')
        logger.info(f"Using {most_recent_friday_date} as the most recent Friday close: ${weekly_close:.2f}")
        
        return weekly_close
    else:
        # Fallback if no Friday data available
        logger.warning(f"No Friday data found for weekly close calculation, using oldest available data")
        return float(df['Close'].iloc[0])

def calculate_ema(series, window):
    """
    Calculate the Exponential Moving Average for a price series.
    
    Args:
        series (pandas.Series): Price series (typically closing prices)
        window (int): EMA period (e.g., 20 for 20-day EMA)
        
    Returns:
        pandas.Series: The EMA values
    """
    return series.ewm(span=window, adjust=False).mean()

def calculate_rsi(df_hourly, window=14):
    """
    Calculate the Relative Strength Index.
    
    Args:
        df_hourly (pandas.DataFrame): DataFrame with hourly price data
        window (int): RSI period (default: 14)
        
    Returns:
        float: The current RSI value
    """
    delta = df_hourly['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    
    # Handle division by zero
    avg_loss = avg_loss.replace(0, 0.00001)  
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Get the most recent valid RSI value
    current_rsi = rsi.dropna().iloc[-1]
    return float(current_rsi if not hasattr(current_rsi, 'iloc') else current_rsi.iloc[0])

def calculate_atr(df, window):
    """
    Calculate the Average True Range.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        window (int): ATR period (e.g., 3 for 3-day ATR)
        
    Returns:
        float: The current ATR value
    """
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    
    # Get the most recent valid ATR value
    current_atr = atr.dropna().iloc[-1]
    return float(current_atr if not hasattr(current_atr, 'iloc') else current_atr.iloc[0])

def get_current_price(symbol):
    """
    Get the current price for a symbol using Polygon API's previous close endpoint.
    
    Args:
        symbol (str): The ETF symbol
        
    Returns:
        float: The current price, or None if not available
    """
    try:
        api_key = os.environ.get("POLYGON_API_KEY")
        if not api_key:
            logger.error("No Polygon API key found in environment variables")
            return None
        
        # Use the previous close endpoint which is available on free tier
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        params = {
            'apiKey': api_key
        }
        
        logger.info(f"Fetching current price for {symbol}")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Error fetching current price for {symbol}: {response.text}")
            return None
        
        data = response.json()
        
        if 'results' in data and data['results']:
            # Return the closing price from previous day
            return data['results'][0]['c']
        else:
            logger.warning(f"No current price data found for {symbol}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting current price for {symbol}: {str(e)}")
        return None

def score_etf(symbol):
    """
    Calculate the 5-factor technical score for an ETF using Polygon API.
    
    Args:
        symbol (str): The ETF symbol
        
    Returns:
        dict: A dictionary with score and detailed metrics
    """
    try:
        logger.info(f"[POLYGON API] Starting technical analysis for {symbol}")
        
        # Fetch data from Polygon API
        df_daily = fetch_daily_data(symbol)
        df_four_hour = fetch_four_hour_data(symbol)  # Using 4-hour data for RSI to match TradingView
        
        # Log data retrieval results
        if not df_daily.empty:
            logger.info(f"[POLYGON API] Successfully fetched daily data for {symbol}: {len(df_daily)} days")
        else:
            logger.error(f"[POLYGON API] Failed to fetch daily data for {symbol}")
            
        if not df_four_hour.empty:
            logger.info(f"[POLYGON API] Successfully fetched 4-hour data for {symbol}: {len(df_four_hour)} bars")
        else:
            logger.error(f"[POLYGON API] Failed to fetch 4-hour data for {symbol}")
        
        if df_daily.empty or df_four_hour.empty:
            logger.error(f"[POLYGON API] Insufficient data for {symbol} score calculation")
            return {
                "Symbol": symbol,
                "Score": 0,
                "Error": "Insufficient data from Polygon API",
                "Price": 0,
                "RSI": 0
            }
        
        # Get current price from Polygon API
        polygon_price = get_current_price(symbol)
        
        # Extract current price from historical data as fallback
        historical_price = float(df_daily['Close'].iloc[-1] if not hasattr(df_daily['Close'].iloc[-1], 'iloc') 
                              else df_daily['Close'].iloc[-1].iloc[0])
        
        # Use Polygon price if available, otherwise use historical price
        current_price = polygon_price if polygon_price is not None else historical_price
        
        logger.info(f"[POLYGON API] Current price for {symbol}: ${current_price:.2f}")
        
        # Calculate technical indicators using Polygon data
        logger.info(f"[POLYGON API] Calculating technical indicators for {symbol}")
        
        ema20 = calculate_ema(df_daily['Close'], 20).iloc[-1]
        ema20 = float(ema20 if not hasattr(ema20, 'iloc') else ema20.iloc[0])
        logger.info(f"[POLYGON API] 20-day EMA for {symbol}: ${ema20:.2f}")
        
        ema100 = calculate_ema(df_daily['Close'], 100).iloc[-1]
        ema100 = float(ema100 if not hasattr(ema100, 'iloc') else ema100.iloc[0])
        logger.info(f"[POLYGON API] 100-day EMA for {symbol}: ${ema100:.2f}")
        
        rsi_value = calculate_rsi(df_four_hour)  # Using 4-hour data for RSI to match TradingView
        logger.info(f"[POLYGON API] 4-hour RSI value for {symbol}: {rsi_value:.2f}")
        
        weekly_close = get_latest_weekly_close(df_daily)
        logger.info(f"[POLYGON API] Weekly close for {symbol}: ${weekly_close:.2f}")
        
        atr3 = calculate_atr(df_daily, 3)
        atr6 = calculate_atr(df_daily, 6)
        logger.info(f"[POLYGON API] ATR values for {symbol}: 3-day = {atr3:.4f}, 6-day = {atr6:.4f}")
        
        # Evaluate the 5 criteria
        criteria1 = current_price > ema20  # Price > 20 EMA
        criteria2 = current_price > ema100  # Price > 100 EMA
        criteria3 = rsi_value < 50  # RSI < 50
        criteria4 = current_price > weekly_close  # Price > Last Week Close
        criteria5 = atr3 < atr6  # 3-day ATR < 6-day ATR
        
        # Calculate total score
        total_score = sum([criteria1, criteria2, criteria3, criteria4, criteria5])
        
        # Prepare detailed results with descriptions
        trend1_desc = f"Price (${current_price:.2f}) is {'above' if criteria1 else 'below'} the 20-day EMA (${ema20:.2f})"
        trend2_desc = f"Price (${current_price:.2f}) is {'above' if criteria2 else 'below'} the 100-day EMA (${ema100:.2f})"
        snapback_desc = f"RSI ({rsi_value:.1f}) is {'below' if criteria3 else 'above'} the threshold (50)"
        momentum_desc = f"Current price (${current_price:.2f}) is {'above' if criteria4 else 'below'} last week's close (${weekly_close:.2f})"
        stabilizing_desc = f"3-day ATR ({atr3:.2f}) is {'lower' if criteria5 else 'higher'} than 6-day ATR ({atr6:.2f})"
        
        # Log criteria results
        logger.info(f"[POLYGON API] Criteria 1 (Price > 20 EMA): {'PASS' if criteria1 else 'FAIL'}")
        logger.info(f"[POLYGON API] Criteria 2 (Price > 100 EMA): {'PASS' if criteria2 else 'FAIL'}")
        logger.info(f"[POLYGON API] Criteria 3 (RSI < 50): {'PASS' if criteria3 else 'FAIL'}")
        logger.info(f"[POLYGON API] Criteria 4 (Price > Weekly Close): {'PASS' if criteria4 else 'FAIL'}")
        logger.info(f"[POLYGON API] Criteria 5 (3-day ATR < 6-day ATR): {'PASS' if criteria5 else 'FAIL'}")
        logger.info(f"[POLYGON API] Final score for {symbol}: {total_score}/5")
        
        # Construct indicator details in the format used by the existing app
        indicators = {
            'trend1': {
                'pass': bool(criteria1),
                'current': float(current_price),
                'threshold': float(ema20),
                'description': trend1_desc
            },
            'trend2': {
                'pass': bool(criteria2),
                'current': float(current_price),
                'threshold': float(ema100),
                'description': trend2_desc
            },
            'snapback': {
                'pass': bool(criteria3),
                'current': float(rsi_value),
                'threshold': 50.0,
                'description': snapback_desc
            },
            'momentum': {
                'pass': bool(criteria4),
                'current': float(current_price),
                'threshold': float(weekly_close),
                'description': momentum_desc
            },
            'stabilizing': {
                'pass': bool(criteria5),
                'current': float(atr3),
                'threshold': float(atr6),
                'description': stabilizing_desc
            }
        }
        
        return total_score, current_price, indicators
        
    except Exception as e:
        logger.error(f"Error scoring {symbol}: {str(e)}")
        return 0, 0.0, {}

class EnhancedEtfScoringService:
    """Enhanced service to analyze and score ETFs using reliable technical indicators."""
    
    def __init__(self, cache_duration=3600):  # Default 1-hour cache
        """
        Initialize the ETF scoring service with caching.
        
        Args:
            cache_duration (int): Cache duration in seconds
        """
        self.cache = {}  # Symbol -> (score_data, timestamp)
        self.cache_duration = cache_duration
    
    def get_etf_score(self, symbol, force_refresh=False, price_override=None):
        """
        Get the ETF score, using cached value if available and recent.
        
        Args:
            symbol (str): The ETF symbol
            force_refresh (bool): Whether to force a data refresh
            price_override (float): Optional override for current price (e.g., from a real-time API)
            
        Returns:
            tuple: (score, current_price, indicators_dict)
        """
        now = datetime.now()
        cache_key = f"etf_score_{symbol}"
        
        # Check if we have a cached value that's still valid
        if (not force_refresh and 
            cache_key in self.cache and 
            (now - self.cache[cache_key][1]).total_seconds() < self.cache_duration):
            
            # If we have a price override, update just the current price while maintaining the same score
            if price_override is not None:
                score_data, indicators = self.cache[cache_key][0][0], self.cache[cache_key][0][2]
                logger.info(f"Using cached technical score for {symbol} with updated real-time price")
                return (score_data, price_override, indicators)
            
            # Otherwise return the fully cached result
            return self.cache[cache_key][0]
        
        # Calculate new score
        score_result = score_etf(symbol)
        
        # Update cache
        self.cache[cache_key] = (score_result, now)
        
        return score_result
    
    def analyze_etfs(self, symbols, force_refresh=False):
        """
        Analyze multiple ETFs and return their scores.
        
        Args:
            symbols (list): List of ETF symbols
            force_refresh (bool): Whether to force a data refresh
            
        Returns:
            dict: Dictionary with ETF symbols as keys and score data as values
        """
        results = {}
        
        for symbol in symbols:
            score, price, indicators = self.get_etf_score(symbol, force_refresh)
            results[symbol] = {
                "score": score,
                "price": price,
                "indicators": indicators
            }
        
        return results
    
    def clear_cache(self):
        """Clear the entire cache."""
        self.cache = {}

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = EnhancedEtfScoringService()
    etfs = ["XLK", "XLF", "XLV", "XLY", "XLC"]
    
    results = service.analyze_etfs(etfs)
    for symbol, data in results.items():
        print(f"{symbol}: Score {data['score']}/5, Price: ${data['price']:.2f}")
        for name, indicator in data['indicators'].items():
            status = "✓" if indicator['pass'] else "✗"
            print(f"  {status} {indicator['description']}")
        print()