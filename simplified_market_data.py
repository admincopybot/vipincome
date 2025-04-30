import os
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
# Removed yfinance import per user request
import talib_service_client as talib_service
import enhanced_etf_scoring
from tradelist_client import TradeListApiService
from tradelist_websocket_client import TradeListWebSocketClient, get_websocket_client

logger = logging.getLogger(__name__)

class SimplifiedMarketDataService:
    """Simplified service to fetch and analyze market data for ETFs and options"""
    
    # Dictionary mapping ETF symbols to sector names for display
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
    
    # Default list of ETFs to track if none provided
    default_etfs = ["XLK", "XLF", "XLV", "XLI", "XLP", "XLY", "XLE", "XLB", "XLU", "XLRE", "XLC"]
    
    @staticmethod
    def get_etf_data(symbols=None, force_refresh=False):
        """
        Fetch current data for a list of ETF symbols
        
        Args:
            symbols (list): List of ETF symbols to fetch data for
            force_refresh (bool): If True, bypass any caching and fetch fresh data
            
        Returns:
            dict: Dictionary with ETF data including price, sector, and calculated score
        """
        if symbols is None:
            symbols = SimplifiedMarketDataService.default_etfs
            
        results = {}
        
        start_time = time.time()
        
        for symbol in symbols:
            try:
                # Get ETF sector name
                sector_name = SimplifiedMarketDataService.etf_sectors.get(symbol, symbol)
                
                # Get price exclusively from TheTradeList API - no fallbacks
                price_data = TradeListApiService.get_current_price(symbol)
                
                # Check if we have a valid price or if there was an API error
                if price_data.get("error", False):
                    # API error occurred, use the error information provided
                    display_price = 0
                    data_source = price_data.get("data_source", "API Error")
                    error_message = price_data.get("error_message", "Unknown error")
                    logger.error(f"Error getting price for {symbol}: {error_message}")
                    
                    # Create error indicators that will be displayed to the user
                    indicators = {
                        'trend1': {'pass': False, 'current': 0, 'threshold': 0, 
                                 'description': f'API Error: {error_message}'},
                        'trend2': {'pass': False, 'current': 0, 'threshold': 0, 
                                 'description': f'Unable to fetch price data'},
                        'snapback': {'pass': False, 'current': 0, 'threshold': 0, 
                                   'description': f'Check API configuration'},
                        'momentum': {'pass': False, 'current': 0, 'threshold': 0, 
                                   'description': f'See logs for details'},
                        'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 
                                      'description': f'API Integration Status: Error'}
                    }
                    score = 0
                    price = 0
                else:
                    # Use the price from TheTradeList API
                    display_price = price_data.get("price", 0)
                    data_source = price_data.get("data_source", "TheTradeList API")
                    logger.info(f"Using {data_source} for {symbol} price data: ${display_price}")
                    
                    # Only calculate technical score if we have a valid price
                    if display_price > 0:
                        score, price, indicators = SimplifiedMarketDataService._calculate_etf_score(
                            symbol, 
                            force_refresh=force_refresh,
                            price_override=display_price
                        )
                    else:
                        # Create zeroed indicators for consistency
                        indicators = {
                            'trend1': {'pass': False, 'current': 0, 'threshold': 0, 
                                     'description': 'No price data available'},
                            'trend2': {'pass': False, 'current': 0, 'threshold': 0, 
                                     'description': 'Cannot calculate indicators'},
                            'snapback': {'pass': False, 'current': 0, 'threshold': 0, 
                                       'description': 'Price is required for calculation'},
                            'momentum': {'pass': False, 'current': 0, 'threshold': 0, 
                                       'description': 'Check API connection'},
                            'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 
                                          'description': 'API response: No price data'}
                        }
                        score = 0
                        price = 0
                
                results[symbol] = {
                    "name": sector_name,
                    "price": display_price,
                    "score": score,
                    "indicators": indicators,
                    "source": data_source
                }
                logger.info(f"Fetched data for {symbol}: ${display_price}, Score: {score}/5")
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")
                # Add basic entry if error occurred
                results[symbol] = {
                    "name": SimplifiedMarketDataService.etf_sectors.get(symbol, symbol),
                    "price": 0.0,
                    "score": 0,
                    "indicators": {
                        'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading error'},
                        'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading error'},
                        'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading error'},
                        'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading error'},
                        'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading error'}
                    },
                    "source": "error"
                }
        
        return results
    
    # Initialize the enhanced ETF scoring service as a class variable
    _etf_scoring_service = enhanced_etf_scoring.EnhancedEtfScoringService(cache_duration=3600)
    
    @staticmethod
    def _calculate_etf_score(ticker, force_refresh=False, price_override=None):
        """
        Calculate a score (1-5) for an ETF based on specific technical indicators:
        1. Trend 1: Price > 20 EMA on Daily Timeframe
        2. Trend 2: Price > 100 EMA on Daily Timeframe
        3. Snapback: RSI < 50 on Daily Timeframe
        4. Momentum: Price > Previous Week's Closing Price
        5. Stabilizing: 3-Day ATR < 6-Day ATR
        
        Args:
            ticker (str): ETF ticker symbol 
            force_refresh (bool): If True, bypass any caching and fetch fresh data
            price_override (float): If provided, use this price instead of fetching from yfinance
        
        Each indicator = 1 point, total score from 0-5
        Returns tuple of (score, current_price, indicator_details_dict)
        """
        try:
            # Use the enhanced ETF scoring system that matches TradingView
            logger.info(f"Calculating technical score for {ticker} using enhanced ETF scoring system")
            
            try:
                # Get the ETF score from the enhanced service
                # This may fail due to Yahoo Finance rate limiting
                score, current_price, indicators = SimplifiedMarketDataService._etf_scoring_service.get_etf_score(ticker, force_refresh)
                
                logger.info(f"Successfully calculated score for {ticker}: {score}/5")
                
            except Exception as calc_error:
                logger.warning(f"Error in ETF score calculation for {ticker}: {str(calc_error)}")
                
                if "Too Many Requests" in str(calc_error) or "rate limit" in str(calc_error).lower():
                    logger.warning("Yahoo Finance rate limit hit - using fallback score")
                
                # Create a default set of indicators
                indicators = {
                    'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'API rate limit reached'},
                    'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'API rate limit reached'},
                    'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'API rate limit reached'},
                    'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'API rate limit reached'},
                    'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'API rate limit reached'}
                }
                
                # Set default values
                score = 0
                current_price = 0.0
                
                # Try to get current price from WebSocket if available
                ws_client = get_websocket_client()
                if ws_client and ticker in ws_client.cached_data:
                    ws_data = ws_client.cached_data.get(ticker, {})
                    if 'price' in ws_data and ws_data['price'] > 0:
                        current_price = ws_data['price']
                        logger.info(f"Using WebSocket price for {ticker}: ${current_price}")
            
            # If we have a price override (e.g., from TheTradeList API), we'll use it for display
            # purposes but won't recalculate the technical indicators with every minor price change.
            # This helps maintain stability in the scoring system.
            if price_override is not None:
                logger.info(f"Price override for {ticker}: ${price_override} (calculated: ${current_price})")
                
                # Only use the real-time price for display purposes
                # Do NOT recalculate score based on small price movements
                # This keeps scores stable while still showing current prices
                current_price = price_override
                
                # STABLE SCORING APPROACH:
                # We're intentionally NOT updating the indicators or recalculating scores
                # based on real-time price movements. This keeps the technical analysis
                # stable and prevents scores from fluctuating with minor price changes.
                
                # Technical scores should only update on a schedule (hourly) or
                # when explicitly forced to refresh.
            
            logger.info(f"Final score for {ticker}: {score}/5")
            return score, float(current_price), indicators
            
        except Exception as e:
            logger.error(f"Error calculating ETF score: {str(e)}")
            
            # Try to get current price from WebSocket if available
            try:
                ws_client = get_websocket_client()
                if ws_client and ticker in ws_client.cached_data:
                    ws_data = ws_client.cached_data.get(ticker, {})
                    current_price = ws_data.get('price', 0.0)
                    logger.info(f"Using WebSocket price for {ticker} in error handler: ${current_price}")
                else:
                    current_price = price_override or 0.0
            except:
                current_price = price_override or 0.0
                
            # Provide default values with error information
            return 0, current_price, {
                'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': f'Error: {str(e)}'},
                'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': f'Error: {str(e)}'},
                'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': f'Error: {str(e)}'},
                'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': f'Error: {str(e)}'},
                'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': f'Error: {str(e)}'}
            }
    
    @staticmethod
    def get_options_data(symbol, strategy='Steady'):
        """
        Get debit spread options data for a specific ETF and strategy
        Returns recommendation for a call debit spread trade
        
        Note: This now tries to use TheTradeList options spreads API first,
        and falls back to synthetic data only if the API is unavailable
        """
        try:
            # Check if symbol is in our tracked ETFs
            if symbol not in SimplifiedMarketDataService.etf_sectors:
                logger.warning(f"Unrecognized ETF symbol: {symbol}")
                return None
            
            # Get price from WebSocket data
            ws_client = get_websocket_client()
            current_price = 0
            
            if ws_client and symbol in ws_client.cached_data:
                websocket_data = ws_client.cached_data.get(symbol, {})
                current_price = websocket_data.get('price', 0)
                logger.info(f"Using WebSocket price for {symbol}: ${current_price}")
            else:
                # If WebSocket data isn't available, try TradeList API
                price_data = TradeListApiService.get_current_price(symbol)
                current_price = price_data.get('price', 0)
                logger.info(f"Using TradeList API price for {symbol}: ${current_price}")
            
            # Try to get options data from the TheTradeList options spreads API
            logger.info(f"Attempting to fetch options data from TheTradeList API for {symbol} with {strategy} strategy")
            options_data = TradeListApiService.get_options_spreads(symbol, strategy)
            
            if options_data:
                logger.info(f"Successfully retrieved options data from TheTradeList API for {symbol}")
                
                # Transform API response to match our expected format if needed
                # Based on our debugging, we know the API returns a LIST of option contracts
                
                # We're using the structure in options_data
                if isinstance(options_data, dict) and 'raw_data' in options_data:
                    raw_data = options_data.get('raw_data', [])
                    options_count = options_data.get('options_count', 0)
                    logger.info(f"Received {options_count} option contracts from API")
                    
                    # Find the appropriate call options for our strategy DTE range
                    dte_ranges = {
                        'Aggressive': (7, 15),   # 7-15 days
                        'Steady': (14, 30),      # 14-30 days
                        'Passive': (30, 45)      # 30-45 days
                    }
                    min_dte, max_dte = dte_ranges.get(strategy, (14, 30))
                    
                    # Get current price from API data if available
                    # The first option should have the ETF price
                    if raw_data and len(raw_data) > 0:
                        if 'etf_price' in raw_data[0]:
                            api_price = raw_data[0].get('etf_price', 0)
                            if api_price > 0:
                                current_price = api_price
                                logger.info(f"Using ETF price from options API: ${current_price}")
                    
                    # Convert the raw data to our expected format
                    return {
                        'symbol': symbol,
                        'current_price': current_price,
                        'strategy': strategy,
                        'recommended_expiration': None,  # We'll set this later
                        'recommended_spread': None,      # We'll set this later
                        'risk_per_contract': 0,
                        'max_profit_per_contract': 0,
                        'risk_reward_ratio': 0,
                        'source': 'TheTradeList API',
                        'raw_data': raw_data,            # Include raw data for processing
                        'options_count': options_count
                    }
                else:
                    # Basic validation of the response (original format)
                    if 'strike' not in options_data or 'expiration' not in options_data:
                        logger.warning(f"Invalid options data format from API for {symbol}")
                        logger.debug(f"API response: {options_data}")
                        # Fall back to our generator if the API response doesn't have the expected fields
                        return SimplifiedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
                    
                    return options_data
            
            # If we couldn't get options data from the API, fall back to our generator
            if not current_price or current_price <= 0:
                logger.error(f"Invalid current price for {symbol}: {current_price}")
                return SimplifiedMarketDataService._generate_fallback_trade(symbol, strategy, 0)
            
            logger.info(f"No API data available. Generating fallback trade for {symbol} ({strategy}) with price ${current_price}")
            return SimplifiedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
        except Exception as e:
            logger.error(f"Error in options data for {symbol}: {str(e)}")
            return SimplifiedMarketDataService._generate_fallback_trade(symbol, strategy, 0)
    
    @staticmethod
    def _generate_fallback_trade(symbol, strategy, current_price):
        """Generate fallback trade recommendation with realistic values"""
        try:
            if not current_price or current_price <= 0:
                current_price = 100.0  # Default fallback price
            
            # Determine the increment based on ETF price
            if current_price < 50:
                increment = 0.5
            elif current_price < 100:
                increment = 1.0
            else:
                increment = 2.5
                
            # Round current price to increment and find strikes
            rounded_price = round(current_price / increment) * increment
            lower_strike = rounded_price - increment
            upper_strike = rounded_price
            spread_width = upper_strike - lower_strike
            
            # Target ROI based on strategy
            if strategy == 'Aggressive':
                target_roi = 0.30
                dte = 7
            elif strategy == 'Passive':
                target_roi = 0.16
                dte = 42
            else:  # Default to Steady
                target_roi = 0.22
                dte = 21
            
            # Calculate premium based on target ROI
            premium = round(spread_width / (1 + target_roi), 2)
            
            # Set expiration date
            expiration = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
            
            # Return simulated trade
            return {
                "strike": lower_strike,
                "upper_strike": upper_strike,
                "spread_width": spread_width,
                "expiration": expiration,
                "dte": dte,
                "roi": f"{target_roi:.0%}",
                "premium": premium,
                "pct_otm": round((lower_strike - current_price) / current_price * 100, 1),
                "max_profit": round(spread_width - premium, 2),
                "max_loss": premium
            }
        except Exception as e:
            logger.error(f"Error generating fallback trade: {str(e)}")
            # Return most basic fallback with default values
            return {
                "strike": 100.0,
                "upper_strike": 101.0,
                "spread_width": 1.0,
                "expiration": (datetime.now() + timedelta(days=21)).strftime('%Y-%m-%d'),
                "dte": 21,
                "roi": "22%",
                "premium": 0.45,
                "pct_otm": -2.0,
                "max_profit": 0.55,
                "max_loss": 0.45
            }

def update_market_data(force_refresh=False):
    """Update market data for all tracked ETFs
    
    Args:
        force_refresh (bool): If True, bypass any caching and fetch fresh data
    """
    try:
        start_time = time.time()
        # Pass force_refresh to get_etf_data to ensure fresh data
        etf_data = SimplifiedMarketDataService.get_etf_data(force_refresh=force_refresh)
        logger.info(f"Market data update completed in {time.time() - start_time:.2f} seconds")
        return etf_data
    except Exception as e:
        logger.error(f"Failed to update market data: {str(e)}")
        return {}

def get_trade_recommendation(symbol, strategy):
    """Get trade recommendation for a specific ETF and strategy"""
    try:
        return SimplifiedMarketDataService.get_options_data(symbol, strategy)
    except Exception as e:
        logger.error(f"Failed to get trade recommendation for {symbol}: {str(e)}")
        return None