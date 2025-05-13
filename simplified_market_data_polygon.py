import os
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
# Import our Polygon-based ETF scoring system
import enhanced_etf_scoring_polygon as polygon_etf_scoring
from tradelist_client import TradeListApiService
from tradelist_websocket_client import TradeListWebSocketClient, get_websocket_client

logger = logging.getLogger(__name__)

class SimplifiedMarketDataService:
    """Simplified service to fetch and analyze market data for ETFs and options using Polygon API"""
    
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
    
    # Default list of ETFs to track
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
        if not symbols:
            symbols = SimplifiedMarketDataService.default_etfs
        
        results = {}
        
        for symbol in symbols:
            try:
                # Get sector info
                sector = SimplifiedMarketDataService.etf_sectors.get(symbol, "Sector ETF")
                
                # First try getting price from TradeList WebSocket
                logger.info(f"Attempting to get price for {symbol} from TradeList WebSocket API")
                
                ws_client = get_websocket_client()
                if ws_client and ws_client.is_connected():
                    price_data = ws_client.get_symbol_data(symbol)
                else:
                    price_data = None
                
                # If we couldn't get data from the WebSocket
                if not price_data or "error" in price_data:
                    if price_data and "error" in price_data:
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
                        # Use the price from TradeList API
                        logger.info(f"Price data not available from WebSocket for {symbol}, trying direct API")
                        price_data = TradeListApiService.get_etf_price(symbol)
                        
                        # Check if we got valid data
                        if price_data and "error" not in price_data:
                            display_price = price_data.get("price", 0)
                            data_source = price_data.get("data_source", "TradeList API")
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
                        else:
                            # Create error indicators that will be displayed to the user
                            error_message = price_data.get("error_message", "Unknown API error") if price_data else "No data returned"
                            logger.error(f"Error getting price data for {symbol}: {error_message}")
                            
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
                    # Use the price from TradeList API
                    display_price = price_data.get("price", 0)
                    data_source = price_data.get("data_source", "TradeList API")
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
                    "symbol": symbol,
                    "sector": sector,
                    "price": price,
                    "score": score,
                    "indicators": indicators,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": data_source if 'data_source' in locals() else "unknown"
                }
                
            except Exception as e:
                logger.exception(f"Error processing ETF data for {symbol}: {str(e)}")
                results[symbol] = {
                    "symbol": symbol,
                    "sector": SimplifiedMarketDataService.etf_sectors.get(symbol, "Sector ETF"),
                    "price": 0.0,
                    "score": 0,
                    "indicators": {
                        'trend1': {'pass': False, 'current': 0, 'threshold': 0, 
                                 'description': f'Error: {str(e)}'},
                        'trend2': {'pass': False, 'current': 0, 'threshold': 0, 
                                 'description': 'Processing error'},
                        'snapback': {'pass': False, 'current': 0, 'threshold': 0, 
                                   'description': 'See logs for details'},
                        'momentum': {'pass': False, 'current': 0, 'threshold': 0, 
                                   'description': 'Exception occurred'},
                        'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 
                                      'description': 'Check server logs'}
                    },
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "error"
                }
        
        return results
    
    # Initialize the enhanced ETF scoring service as a class variable 
    # Using the Polygon version instead of yfinance
    _etf_scoring_service = polygon_etf_scoring.EnhancedEtfScoringService(cache_duration=3600)
    
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
            price_override (float): If provided, use this price instead of fetching from Polygon
        
        Each indicator = 1 point, total score from 0-5
        Returns tuple of (score, current_price, indicator_details_dict)
        """
        try:
            # First try using TradeList API for scoring if available
            try:
                logger.info(f"Attempting to calculate technical score for {ticker} using TradeList API")
                
                # Use TradeList API to calculate scores
                tradelist_score, tradelist_price, tradelist_indicators = TradeListApiService.calculate_etf_score(ticker)
                
                # If we got valid data from TradeList API
                if tradelist_score > 0 and tradelist_price > 0:
                    logger.info(f"Successfully calculated score for {ticker} using TradeList API: {tradelist_score}/5")
                    
                    # Transform indicators to the expected format for UI
                    ui_indicators = {
                        # 1. Trend 1: Price > 20/50 EMA
                        'trend1': {
                            'pass': tradelist_indicators.get('trend1', False),
                            'current': tradelist_price,
                            'threshold': 0,  # We don't have the actual EMA value
                            'description': 'Price > 20-day EMA (Short-term Trend)'
                        },
                        
                        # 2. Trend 2: Price > 100 EMA
                        'trend2': {
                            'pass': tradelist_indicators.get('trend2', False),
                            'current': tradelist_price,
                            'threshold': 0,  # We don't have the actual EMA value
                            'description': 'Price > 100-day EMA (Long-term Trend)'
                        },
                        
                        # 3. Snapback: RSI < 50
                        'snapback': {
                            'pass': tradelist_indicators.get('snapback', False),
                            'current': 0,  # We don't have the actual RSI value
                            'threshold': 50,
                            'description': 'RSI < 50 (Snapback Potential)'
                        },
                        
                        # 4. Momentum: Price > Previous Week's Close
                        'momentum': {
                            'pass': tradelist_indicators.get('momentum', False),
                            'current': tradelist_price,
                            'threshold': 0,  # We don't have the actual previous week close
                            'description': 'Price > Weekly Close (Momentum)'
                        },
                        
                        # 5. Stabilizing: Volatility decreasing
                        'stabilizing': {
                            'pass': tradelist_indicators.get('stabilizing', False),
                            'current': 0,  # We don't have the actual ATR values
                            'threshold': 0,
                            'description': 'Volatility Stabilizing'
                        }
                    }
                    
                    # Use price override if provided
                    if price_override is not None:
                        logger.info(f"Using price override for {ticker}: ${price_override} (TradeList: ${tradelist_price})")
                        tradelist_price = price_override
                    
                    return tradelist_score, float(tradelist_price), ui_indicators
            except Exception as tradelist_error:
                logger.warning(f"Error calculating score with TradeList API, falling back: {str(tradelist_error)}")
                # Fall through to enhanced scoring system
            
            # Use the enhanced ETF scoring system with Polygon.io data
            logger.info(f"Calculating technical score for {ticker} using Polygon-based ETF scoring system")
            
            try:
                # Get the ETF score from the enhanced service
                score, current_price, indicators = SimplifiedMarketDataService._etf_scoring_service.get_etf_score(ticker, force_refresh)
                
                # Use price override if provided
                if price_override is not None:
                    logger.info(f"Price override for {ticker}: ${price_override} (calculated: ${current_price})")
                    current_price = price_override
                
                logger.info(f"Final score for {ticker}: {score}/5")
                return score, float(current_price), indicators
                
            except Exception as calc_error:
                logger.warning(f"Error in ETF score calculation for {ticker}: {str(calc_error)}")
                
                # Create a default set of indicators
                indicators = {
                    'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Calculation Error'},
                    'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Calculation Error'},
                    'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Calculation Error'},
                    'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Calculation Error'},
                    'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Calculation Error'}
                }
                
                # Use just the price if that's all we have
                if price_override is not None:
                    logger.info(f"Using price override for {ticker}: ${price_override} (no score available)")
                    return 0, float(price_override), indicators
                else:
                    logger.error(f"No valid price or score available for {ticker}")
                    return 0, 0.0, indicators
                
        except Exception as e:
            logger.exception(f"Error calculating ETF score for {ticker}: {str(e)}")
            return 0, 0.0, {
                'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': f'Error: {str(e)}'},
                'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Processing error'},
                'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'See logs for details'},
                'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Exception occurred'},
                'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Check server logs'}
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
            logger.info(f"Getting options data for {symbol} with {strategy} strategy")
            
            # Attempt to get trade data from TheTradeList API
            try:
                logger.info(f"Attempting to get options data from TradeList API for {symbol} ({strategy})")
                api_data = TradeListApiService.get_options_spread(symbol, strategy)
                
                if api_data and 'error' not in api_data:
                    logger.info(f"Successfully fetched options data from TradeList API for {symbol}")
                    return api_data
                else:
                    error_msg = api_data.get('error', 'Unknown API error') if api_data else 'No data returned'
                    logger.warning(f"Error from TradeList API for {symbol}: {error_msg}, using fallback data")
            except Exception as api_error:
                logger.warning(f"Exception getting options data from API: {str(api_error)}, using fallback data")
            
            # Get current price for the ETF using Polygon API
            current_price = polygon_etf_scoring.get_current_price(symbol)
            if current_price is None:
                logger.warning(f"Could not get current price for {symbol} from Polygon API, using fallback")
                current_price = 100.0  # Safe fallback default
            
            # Generate fallback trade based on strategy and current price
            return SimplifiedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
        except Exception as e:
            logger.exception(f"Error getting options data for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def _generate_fallback_trade(symbol, strategy, current_price):
        """Generate fallback trade recommendation with realistic values"""
        # Set parameters based on strategy
        if strategy.lower() == 'aggressive':
            dte = 10  # 7-15 days
            target_roi = 0.30  # 30% target ROI
        elif strategy.lower() == 'passive':
            dte = 38  # 30-45 days
            target_roi = 0.16  # 16% target ROI 
        else:  # Default to 'steady'
            dte = 21  # 14-30 days
            target_roi = 0.22  # 22% target ROI
        
        # Calculate expiration date
        expiry_date = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        # Calculate strike prices and credit based on strategy
        # For simplicity: Long leg at 3-5% OTM, Short leg at 6-10% OTM
        if strategy.lower() == 'aggressive':
            long_strike = round(current_price * 1.03, 0)
            short_strike = round(current_price * 1.06, 0)
        elif strategy.lower() == 'passive':
            long_strike = round(current_price * 1.05, 0)
            short_strike = round(current_price * 1.10, 0)
        else:  # Default to 'steady'
            long_strike = round(current_price * 1.04, 0)
            short_strike = round(current_price * 1.08, 0)
        
        # Calculate option prices and credit
        long_premium = round(current_price * 0.03, 2)  # Approx 3% of stock price for long option
        short_premium = round(current_price * 0.015, 2)  # Approx 1.5% for short option
        net_debit = round(long_premium - short_premium, 2)
        
        # Calculate max profit
        max_profit = round((short_strike - long_strike - net_debit) * 100, 2)
        
        # Calculate expected profit based on target ROI
        expected_profit = round(net_debit * 100 * target_roi, 2)
        
        # Calculate trade details
        return {
            "symbol": symbol,
            "strategy": strategy,
            "trade_type": "Call Debit Spread",
            "expiry_date": expiry_date,
            "dte": dte,
            "current_price": current_price,
            "sentiment": "Bullish",
            "long_strike": long_strike,
            "short_strike": short_strike,
            "net_debit": net_debit,
            "contracts": 1,
            "max_profit": max_profit,
            "max_risk": round(net_debit * 100, 2),
            "max_roi": round(max_profit / (net_debit * 100) * 100, 2),
            "expected_profit": expected_profit,
            "expected_roi": round(target_roi * 100, 2),
            "data_source": "Fallback Calculation",
            "probability_of_profit": round(50 + (10 * (3 - int(strategy.lower() == 'aggressive') * 1 - int(strategy.lower() == 'passive') * -1)), 2)
        }

def update_market_data(force_refresh=False):
    """Update market data for all tracked ETFs
    
    Args:
        force_refresh (bool): If True, bypass any caching and fetch fresh data
    """
    return SimplifiedMarketDataService.get_etf_data(force_refresh=force_refresh)

def get_trade_recommendation(symbol, strategy):
    """Get trade recommendation for a specific ETF and strategy"""
    return SimplifiedMarketDataService.get_options_data(symbol, strategy)