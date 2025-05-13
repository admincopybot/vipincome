import os
import logging
import json
from datetime import datetime, timedelta
import pandas as pd
from polygon import RESTClient
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from models import db, HistoricalPrice, BacktestResult
from database import get_cached_price_data, save_price_data

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
        try:
            # Get historical data up to the specified date
            from_date = date - timedelta(days=180)  # Need 6 months for 100 EMA
            
            # Get data from cache or API
            if use_cache:
                df = get_cached_price_data(symbol, from_date=from_date)
                
                if df is None or len(df) < 100:
                    # Cache miss or insufficient data, fetch from API
                    df = BacktestService._fetch_historical_data_for_date_range(
                        symbol, from_date, date
                    )
                    
                    if df is not None and len(df) > 0:
                        # Save to cache for future use
                        save_price_data(symbol, df)
                    else:
                        logger.error(f"No historical data available for {symbol} from {from_date} to {date}")
                        return 0, {}
            else:
                # Skip cache, fetch directly from API
                df = BacktestService._fetch_historical_data_for_date_range(
                    symbol, from_date, date
                )
                
                if df is None or len(df) < 100:
                    logger.error(f"Insufficient historical data for {symbol} from {from_date} to {date}")
                    return 0, {}
            
            # Filter data to only include dates up to the specified date
            if isinstance(date, str):
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            
            df = df[df.index <= date]
            
            if len(df) < 100:
                logger.error(f"Not enough historical data for {symbol} up to {date} - need at least 100 days")
                return 0, {}
            
            # Get the date's closing price
            current_price = df['Close'].iloc[-1]
            
            # Calculate indicators for the specified date
            score, indicators = BacktestService._calculate_indicators_for_date(df, current_price)
            
            logger.info(f"Calculated historical score for {symbol} on {date.strftime('%Y-%m-%d')}: {score}/5")
            return score, indicators
            
        except Exception as e:
            logger.error(f"Error calculating historical ETF score: {str(e)}")
            return 0, {}
    
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
        from simplified_market_data import SimplifiedMarketDataService
        
        try:
            # Parse date
            backtest_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Default to all ETFs if none specified
            if symbols is None or len(symbols) == 0:
                symbols = SimplifiedMarketDataService.default_etfs
            
            # Calculate scores for each symbol
            results = {}
            for symbol in symbols:
                score, indicators = BacktestService.calculate_historical_etf_score(symbol, backtest_date)
                results[symbol] = {
                    'score': score,
                    'indicators': indicators
                }
            
            # Cache result if requested
            if cache_result:
                backtest = BacktestResult(
                    date=backtest_date,
                    data=results
                )
                db.session.add(backtest)
                db.session.commit()
                logger.info(f"Cached backtest results for {date_str}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error creating backtest: {str(e)}")
            return {}
    
    @staticmethod
    def get_cached_backtest(date_str):
        """
        Get a cached backtest result
        
        Args:
            date_str (str): Date in YYYY-MM-DD format
            
        Returns:
            dict or None: Cached backtest results or None if not found
        """
        try:
            # Parse date
            backtest_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Query for cached backtest
            backtest = BacktestResult.query.filter(
                BacktestResult.date == backtest_date
            ).first()
            
            if backtest:
                logger.info(f"Retrieved cached backtest for {date_str}")
                return backtest.data
            else:
                logger.info(f"No cached backtest found for {date_str}")
                return None
        
        except Exception as e:
            logger.error(f"Error retrieving cached backtest: {str(e)}")
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
            # Get Polygon API key
            api_key = os.environ.get("POLYGON_API_KEY")
            if not api_key:
                logger.error("No Polygon API key found")
                return None
            
            # Convert dates to strings
            from_str = from_date.strftime('%Y-%m-%d')
            to_str = to_date.strftime('%Y-%m-%d')
            
            # Initialize client
            client = RESTClient(api_key=api_key)
            
            # Fetch data
            aggs = client.get_aggs(
                ticker=symbol,
                multiplier=1,
                timespan="day",
                from_=from_str,
                to=to_str,
                limit=50000  # Maximum allowed by API
            )
            
            # Convert to DataFrame
            if aggs:
                df = pd.DataFrame([{
                    'timestamp': datetime.fromtimestamp(item.timestamp / 1000),
                    'open': item.open,
                    'high': item.high,
                    'low': item.low,
                    'close': item.close,
                    'volume': item.volume
                } for item in aggs])
                
                # Set timestamp as index
                df.set_index('timestamp', inplace=True)
                
                # Rename columns
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
                
                logger.info(f"Retrieved {len(df)} historical data points for {symbol} from Polygon API")
                return df
            else:
                logger.warning(f"No historical data found for {symbol} in date range {from_str} to {to_str}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
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
            score = 0
            indicators = {}
            
            # 1. Trend 1: Price > 20 EMA
            ema_indicator = EMAIndicator(close=df['Close'], window=20)
            ema_20 = ema_indicator.ema_indicator().iloc[-1]
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
            
            # 2. Trend 2: Price > 100 EMA
            ema_indicator = EMAIndicator(close=df['Close'], window=100)
            ema_100 = ema_indicator.ema_indicator().iloc[-1]
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
            
            # 3. Snapback: RSI < 50
            rsi_indicator = RSIIndicator(close=df['Close'], window=14)
            current_rsi = rsi_indicator.rsi().iloc[-1]
            
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
            today = df.index[-1]
            seven_days_ago = today - pd.Timedelta(days=7)
            
            # Find the closest trading day on or before 7 days ago
            closest_dates = df.index[df.index <= seven_days_ago]
            
            if len(closest_dates) > 0:
                prev_week_idx = closest_dates[-1]  # Get the last date that's <= 7 days ago
                prev_week_close = df.loc[prev_week_idx, 'Close']
            else:
                # Fallback if we don't have data from 7 days ago (use 5 trading days as approximation)
                prev_week_close = df['Close'].iloc[-6] if len(df) > 5 else df['Close'].iloc[0]
            
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
            atr_3 = AverageTrueRange(high=df['High'], 
                                   low=df['Low'], 
                                   close=df['Close'], 
                                   window=3).average_true_range().iloc[-1]
            
            atr_6 = AverageTrueRange(high=df['High'], 
                                   low=df['Low'], 
                                   close=df['Close'], 
                                   window=6).average_true_range().iloc[-1]
            
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
            
            return score, indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return 0, {}