"""
Simplified Market Data Service for Income Machine
This module provides simplified services for fetching and scoring ETF data.
"""

import logging
import json
import time
import pandas as pd
import numpy as np
import datetime
import os
import yfinance as yf

from database import get_cached_etf_score, save_etf_score

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimplifiedMarketDataService:
    """Service to fetch and analyze market data for ETFs"""
    
    # ETF sector mappings
    etf_sectors = {
        "XLK": "Technology",
        "XLF": "Financial",
        "XLV": "Health Care",
        "XLI": "Industrial",
        "XLP": "Consumer Staples",
        "XLY": "Consumer Discretionary",
        "XLE": "Energy",
        "XLB": "Materials",
        "XLU": "Utilities",
        "XLRE": "Real Estate",
        "XLC": "Communication Services"
    }
    
    # Default ETFs to track
    default_etfs = ["XLK", "XLF", "XLV", "XLI", "XLP", "XLY", "XLE", "XLB", "XLU", "XLRE", "XLC"]
    
    # Cache to store ETF scores (symbol -> (score, price, indicators, timestamp))
    _score_cache = {}
    _price_cache = {}  # symbol -> (price, timestamp)
    
    @classmethod
    def get_etf_score(cls, symbol, force_refresh=False, price_override=None):
        """
        Get the ETF score, using cached value if available and recent.
        
        Args:
            symbol (str): The ETF symbol
            force_refresh (bool): Whether to force a data refresh
            price_override (float): Optional override for current price (e.g., from a real-time API)
            
        Returns:
            tuple: (score, current_price, indicators_dict)
        """
        try:
            # Check if we need to calculate a new score
            calculate_new_score = force_refresh
            
            # Check in-memory cache first
            cached_data = cls._score_cache.get(symbol)
            if cached_data and not force_refresh:
                score, price, indicators, timestamp = cached_data
                
                # Check if cache is still fresh (less than 60 minutes old)
                age_minutes = (time.time() - timestamp) / 60
                if age_minutes < 60:
                    logger.info(f"Using cached score for {symbol}: {score}/5 (age: {age_minutes:.1f} minutes)")
                    
                    # If price override is provided, use it but keep the same score
                    if price_override is not None:
                        logger.info(f"Price override for {symbol}: ${price_override} (cached: ${price})")
                        return score, price_override, indicators
                    
                    return score, price, indicators
                else:
                    calculate_new_score = True
            
            # Check database cache if not in memory or memory cache is stale
            if not cached_data and not force_refresh:
                db_cache = get_cached_etf_score(symbol, max_age_minutes=60)
                if db_cache:
                    score, price, indicators = db_cache
                    
                    # Store in memory cache
                    cls._score_cache[symbol] = (score, price, indicators, time.time())
                    
                    # If price override is provided, use it but keep the same score
                    if price_override is not None:
                        logger.info(f"Price override for {symbol}: ${price_override} (db cached: ${price})")
                        return score, price_override, indicators
                    
                    return score, price, indicators
                else:
                    calculate_new_score = True
            
            # Calculate new score if needed
            if calculate_new_score:
                logger.info(f"Calculating new score for {symbol}")
                
                # Fetch data
                try:
                    # Try to use Polygon API if available
                    from enhanced_polygon_client import EnhancedPolygonService
                    
                    result = EnhancedPolygonService.calculate_etf_score(symbol)
                    if result:
                        score, price, indicators = result
                        logger.info(f"Calculated score for {symbol} using Polygon.io: {score}/5")
                    else:
                        # Fallback to YFinance
                        result = cls._calculate_etf_score(symbol)
                        if result:
                            score, price, indicators = result
                            logger.info(f"Calculated score for {symbol} using yfinance: {score}/5")
                        else:
                            logger.error(f"Failed to calculate score for {symbol}")
                            return None, None, None
                
                except ImportError:
                    # Polygon API not available, use YFinance
                    logger.info(f"Polygon API not available, using yfinance for {symbol}")
                    result = cls._calculate_etf_score(symbol)
                    if result:
                        score, price, indicators = result
                        logger.info(f"Calculated score for {symbol} using yfinance: {score}/5")
                    else:
                        logger.error(f"Failed to calculate score for {symbol}")
                        return None, None, None
                
                # Use price override if provided
                if price_override is not None:
                    logger.info(f"Price override for {symbol}: ${price_override} (calculated: ${price})")
                    price = price_override
                
                # Save to database
                save_etf_score(symbol, score, price, indicators)
                
                # Store in memory cache
                cls._score_cache[symbol] = (score, price, indicators, time.time())
                
                return score, price, indicators
            
            # Should not reach here
            logger.error(f"Failed to get score for {symbol}")
            return None, None, None
        
        except Exception as e:
            logger.error(f"Error getting ETF score for {symbol}: {str(e)}")
            return None, None, None
    
    @classmethod
    def analyze_etfs(cls, symbols, force_refresh=False):
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
            try:
                # Get real-time price if available
                real_time_price = cls._get_realtime_price(symbol)
                
                # Get score with real-time price if available
                score, price, indicators = cls.get_etf_score(
                    symbol, 
                    force_refresh=force_refresh,
                    price_override=real_time_price
                )
                
                if score is not None:
                    results[symbol] = {
                        'score': score,
                        'price': price,
                        'sector': cls.etf_sectors.get(symbol, 'Unknown'),
                        'indicators': indicators
                    }
                else:
                    results[symbol] = {
                        'error': f"Failed to calculate score for {symbol}"
                    }
            
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {str(e)}")
                results[symbol] = {
                    'error': str(e)
                }
        
        return results
    
    @classmethod
    def _get_realtime_price(cls, symbol):
        """
        Get real-time price from WebSocket client if available
        
        Args:
            symbol (str): ETF symbol
            
        Returns:
            float or None: Real-time price or None if not available
        """
        try:
            # Try to import WebSocket client
            from tradelist_websocket_client import get_websocket_client
            
            # Get client instance
            ws_client = get_websocket_client()
            if ws_client:
                # Get real-time price
                price = ws_client.get_latest_price(symbol)
                if price:
                    logger.debug(f"Got real-time price for {symbol}: ${price}")
                    return price
        
        except (ImportError, Exception) as e:
            logger.debug(f"WebSocket client not available or error: {str(e)}")
        
        return None
    
    @classmethod
    def _calculate_etf_score(cls, ticker):
        """
        Calculate a score (1-5) for an ETF using Yahoo Finance data based on specific indicators:
        1. Trend 1: Price > 20 EMA on Daily Timeframe
        2. Trend 2: Price > 100 EMA on Daily Timeframe
        3. Snapback: RSI < 50 on Daily Timeframe
        4. Momentum: Price > Previous Week's Closing Price
        5. Stabilizing: 3-Day ATR < 6-Day ATR
        
        Each indicator = 1 point, total score from 0-5
        Returns tuple of (score, current_price, indicator_details_dict)
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
            
            # Fetch daily data for 2 years
            daily_data = yf.download(ticker, period='2y', interval='1d', progress=False)
            
            if daily_data.empty:
                logger.warning(f"No daily data available for {ticker}")
                return 0, 0, default_indicators
            
            # Get current price (latest close)
            current_price = daily_data['Close'].iloc[-1]
            
            # Calculate 20-day EMA
            daily_data['EMA_20'] = daily_data['Close'].ewm(span=20, adjust=False).mean()
            
            # Calculate 100-day EMA
            daily_data['EMA_100'] = daily_data['Close'].ewm(span=100, adjust=False).mean()
            
            # Calculate RSI
            delta = daily_data['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            daily_data['RSI'] = 100 - (100 / (1 + rs))
            
            # Calculate ATR
            daily_data['High-Low'] = daily_data['High'] - daily_data['Low']
            daily_data['High-Close_prev'] = abs(daily_data['High'] - daily_data['Close'].shift(1))
            daily_data['Low-Close_prev'] = abs(daily_data['Low'] - daily_data['Close'].shift(1))
            daily_data['TR'] = daily_data[['High-Low', 'High-Close_prev', 'Low-Close_prev']].max(axis=1)
            daily_data['ATR_3'] = daily_data['TR'].rolling(window=3).mean()
            daily_data['ATR_6'] = daily_data['TR'].rolling(window=6).mean()
            
            # Find previous week's close (5 trading days ago)
            prev_week_close = daily_data['Close'].shift(5).iloc[-1]
            
            # Check indicators
            indicators = default_indicators.copy()
            score = 0
            
            # 1. Trend 1: Price > 20 EMA
            if current_price > daily_data['EMA_20'].iloc[-1]:
                indicators['trend1']['pass'] = True
                score += 1
            indicators['trend1']['current'] = float(current_price)
            indicators['trend1']['threshold'] = float(daily_data['EMA_20'].iloc[-1])
            
            # 2. Trend 2: Price > 100 EMA
            if current_price > daily_data['EMA_100'].iloc[-1]:
                indicators['trend2']['pass'] = True
                score += 1
            indicators['trend2']['current'] = float(current_price)
            indicators['trend2']['threshold'] = float(daily_data['EMA_100'].iloc[-1])
            
            # 3. Snapback: RSI < 50
            if daily_data['RSI'].iloc[-1] < 50:
                indicators['snapback']['pass'] = True
                score += 1
            indicators['snapback']['current'] = float(daily_data['RSI'].iloc[-1])
            
            # 4. Momentum: Price > Previous Week's Close
            if current_price > prev_week_close:
                indicators['momentum']['pass'] = True
                score += 1
            indicators['momentum']['current'] = float(current_price)
            indicators['momentum']['threshold'] = float(prev_week_close)
            
            # 5. Stabilizing: 3-Day ATR < 6-Day ATR
            if daily_data['ATR_3'].iloc[-1] < daily_data['ATR_6'].iloc[-1]:
                indicators['stabilizing']['pass'] = True
                score += 1
            indicators['stabilizing']['current'] = float(daily_data['ATR_3'].iloc[-1])
            indicators['stabilizing']['threshold'] = float(daily_data['ATR_6'].iloc[-1])
            
            logger.info(f"Successfully calculated score for {ticker}: {score}/5")
            return score, current_price, indicators
        
        except Exception as e:
            logger.error(f"Error calculating ETF score for {ticker}: {str(e)}")
            return None, None, None