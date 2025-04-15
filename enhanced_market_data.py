import os
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from enhanced_polygon_client import EnhancedPolygonService

logger = logging.getLogger(__name__)

class EnhancedMarketDataService:
    """Enhanced service to fetch and analyze market data for ETFs and options"""
    
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
    def get_etf_data(symbols=None):
        """
        Fetch current data for a list of ETF symbols using Polygon.io for scoring
        and Yahoo Finance as backup
        Returns a dictionary with ETF data including price, sector, and calculated score
        """
        if symbols is None:
            symbols = EnhancedMarketDataService.default_etfs
            
        results = {}
        
        for symbol in symbols:
            try:
                # Get ETF sector name
                sector_name = EnhancedMarketDataService.etf_sectors.get(symbol, symbol)
                
                # Try Polygon.io first
                try:
                    logger.info(f"Fetching data for {symbol} using Enhanced Polygon service")
                    # Get current price from Polygon
                    current_price = EnhancedPolygonService.get_etf_price(symbol)
                    
                    if current_price:
                        # Calculate score using Polygon
                        score, indicators = EnhancedPolygonService.calculate_etf_score(symbol)
                        
                        results[symbol] = {
                            "name": sector_name,
                            "price": current_price,
                            "score": score,
                            "indicators": indicators,
                            "source": "polygon"
                        }
                        logger.info(f"Fetched data for {symbol}: ${current_price}, Score: {score}/5")
                        continue
                    else:
                        logger.error(f"Failed to get price for {symbol} from Polygon")
                except Exception as e:
                    logger.error(f"Polygon data fetch failed for {symbol}: {str(e)}")
                
                # Fallback to Yahoo Finance
                logger.info(f"Falling back to Yahoo Finance for {symbol}")
                # Fetch data and calculate score using Yahoo Finance
                score, price, indicators = EnhancedMarketDataService._calculate_etf_score(symbol)
                
                results[symbol] = {
                    "name": sector_name,
                    "price": price,
                    "score": score,
                    "indicators": indicators,
                    "source": "yfinance"
                }
                logger.info(f"Fetched data for {symbol}: ${price}, Score: {score}/5")
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")
                # Add basic entry if error occurred
                results[symbol] = {
                    "name": EnhancedMarketDataService.etf_sectors.get(symbol, symbol),
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
    
    @staticmethod
    def _calculate_etf_score(ticker):
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
            # Get historical data (last 6 months)
            hist_data = yf.download(ticker, period="6mo", progress=False)
            
            if hist_data.empty or len(hist_data) < 100:
                logger.error(f"Not enough historical data for {ticker}")
                return 0, 0.0, {}
            
            # Get current price
            current_price = hist_data['Close'].iloc[-1]
            score = 0
            indicators = {}
            
            # 1. Trend 1: Price > 20 EMA on Daily Timeframe using TA library
            ema_indicator = EMAIndicator(close=hist_data['Close'], window=20)
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
            
            # 2. Trend 2: Price > 100 EMA on Daily Timeframe
            ema_indicator = EMAIndicator(close=hist_data['Close'], window=100)
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
            
            # 3. Snapback: RSI < 50 on Daily Timeframe
            rsi_indicator = RSIIndicator(close=hist_data['Close'], window=14)
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
            
            # 4. Momentum: Above Previous Week's Closing Price (using calendar days)
            # Find exactly 7 calendar days ago or the closest trading day before that
            today = hist_data.index[-1]
            seven_days_ago = today - pd.Timedelta(days=7)
            
            # Find the closest trading day on or before 7 days ago
            closest_dates = hist_data.index[hist_data.index <= seven_days_ago]
            
            if len(closest_dates) > 0:
                prev_week_idx = closest_dates[-1]  # Get the last date that's <= 7 days ago
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
            atr_3 = AverageTrueRange(high=hist_data['High'], 
                                   low=hist_data['Low'], 
                                   close=hist_data['Close'], 
                                   window=3).average_true_range().iloc[-1]
            
            atr_6 = AverageTrueRange(high=hist_data['High'], 
                                   low=hist_data['Low'], 
                                   close=hist_data['Close'], 
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
            
            logger.info(f"Calculated score: {score}/5 using technical indicators")
            return score, float(current_price), indicators
            
        except Exception as e:
            logger.error(f"Error calculating score for {ticker}: {str(e)}")
            return 0, 0.0, {}
    
    @staticmethod
    def get_options_data(symbol, strategy='Steady'):
        """
        Get debit spread options data for a specific ETF and strategy using Yahoo Finance
        Returns recommendation for a call debit spread trade
        """
        try:
            # Check if symbol is in our tracked ETFs
            if symbol not in EnhancedMarketDataService.etf_sectors:
                logger.warning(f"Unrecognized ETF symbol: {symbol}")
                return None
            
            # First, get latest price data
            ticker_data = yf.Ticker(symbol)
            current_price = ticker_data.history(period="1d")['Close'].iloc[-1]
            
            if not current_price or current_price <= 0:
                logger.error(f"Invalid current price for {symbol}: {current_price}")
                return EnhancedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
            try:
                # Get options chain data
                # Strategy determines days to expiration (DTE)
                # Aggressive: 7-15 days, Steady: 14-30 days, Passive: 30-45 days
                if strategy == 'Aggressive':
                    expiry_days = 14  # Aim for 2 weeks out
                elif strategy == 'Passive':
                    expiry_days = 45  # Aim for 6 weeks out
                else:  # Default to Steady
                    expiry_days = 30  # Aim for 4 weeks out
                
                # Find appropriate expiration date
                today = datetime.now()
                target_date = today + timedelta(days=expiry_days)
                
                # Get available expiration dates
                expirations = ticker_data.options
                
                if not expirations or len(expirations) == 0:
                    logger.warning(f"No options expirations available for {symbol}")
                    return EnhancedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
                
                # Find expiration closest to our target
                expiration = None
                min_diff = float('inf')
                
                for exp in expirations:
                    exp_date = datetime.strptime(exp, '%Y-%m-%d')
                    diff = abs((exp_date - target_date).days)
                    
                    if diff < min_diff:
                        min_diff = diff
                        expiration = exp
                
                if not expiration:
                    logger.warning(f"Failed to find suitable expiration for {symbol}")
                    return EnhancedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
                
                # Calculate actual DTE
                exp_date = datetime.strptime(expiration, '%Y-%m-%d')
                dte = (exp_date - today).days
                
                # Get options chain for this expiration
                options = ticker_data.option_chain(expiration)
                calls = options.calls
                
                if calls.empty:
                    logger.warning(f"No call options found for {symbol} on {expiration}")
                    return EnhancedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
                
                # Determine the standard option increment based on ETF price
                if current_price < 50:
                    increment = 0.5
                elif current_price < 100:
                    increment = 1.0
                else:
                    increment = 2.5
                
                # Target ROI based on strategy
                # Aggressive: 30%, Steady: 22%, Passive: 16%
                if strategy == 'Aggressive':
                    target_roi = 0.30
                elif strategy == 'Passive':
                    target_roi = 0.16
                else:  # Default to Steady
                    target_roi = 0.22
                
                # Find strikes close to current price (prefer slightly ITM)
                itm_calls = calls[calls['strike'] <= current_price]
                
                if itm_calls.empty:
                    # If no ITM options, use the closest OTM
                    sorted_calls = calls.sort_values('strike')
                    lower_strike = sorted_calls.iloc[0]['strike']
                else:
                    # Use closest ITM strike
                    sorted_itm = itm_calls.sort_values('strike', ascending=False)
                    lower_strike = sorted_itm.iloc[0]['strike']
                
                # Round to standard option increments
                lower_strike = round(lower_strike / increment) * increment
                
                # Upper strike is 1 increment higher for simplicity
                upper_strike = lower_strike + increment
                
                # Get actual premiums if available
                # Optimal trade based on target ROI
                spread_width = upper_strike - lower_strike
                target_premium = spread_width / (1 + target_roi)
                
                # Find actual premiums if possible
                lower_option = calls[calls['strike'] == lower_strike]
                upper_option = calls[calls['strike'] == upper_strike]
                
                if not lower_option.empty and not upper_option.empty:
                    # Use mid-price for calculations
                    lower_premium = (lower_option.iloc[0]['ask'] + lower_option.iloc[0]['bid']) / 2
                    upper_premium = (upper_option.iloc[0]['ask'] + upper_option.iloc[0]['bid']) / 2
                    actual_premium = lower_premium - upper_premium
                else:
                    # Fallback to theoretical premium
                    actual_premium = target_premium
                
                # Calculate ROI: (spread_width - premium) / premium
                roi = (spread_width - actual_premium) / actual_premium if actual_premium > 0 else target_roi
                
                # Calculate percent OTM/ITM
                pct_difference = (lower_strike - current_price) / current_price * 100
                
                trade = {
                    "strike": lower_strike,
                    "upper_strike": upper_strike,
                    "spread_width": spread_width,
                    "expiration": expiration,
                    "dte": dte,
                    "roi": f"{roi:.0%}",
                    "premium": round(actual_premium, 2),
                    "pct_otm": round(pct_difference, 1),
                    "max_profit": round(spread_width - actual_premium, 2),
                    "max_loss": round(actual_premium, 2)
                }
                
                logger.info(f"Generated {strategy} trade for {symbol}: {trade}")
                return trade
                
            except Exception as e:
                logger.error(f"Error getting options data for {symbol}: {str(e)}")
                return EnhancedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
        except Exception as e:
            logger.error(f"Error in options data for {symbol}: {str(e)}")
            return EnhancedMarketDataService._generate_fallback_trade(symbol, strategy, current_price)
    
    @staticmethod
    def _generate_fallback_trade(symbol, strategy, current_price):
        """Generate fallback trade recommendation with realistic values"""
        if current_price <= 0:
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

def update_market_data():
    """Update market data for all tracked ETFs"""
    try:
        start_time = time.time()
        etf_data = EnhancedMarketDataService.get_etf_data()
        logger.info(f"Market data update completed in {time.time() - start_time:.2f} seconds")
        return etf_data
    except Exception as e:
        logger.error(f"Failed to update market data: {str(e)}")
        return {}

def get_trade_recommendation(symbol, strategy):
    """Get trade recommendation for a specific ETF and strategy"""
    try:
        return EnhancedMarketDataService.get_options_data(symbol, strategy)
    except Exception as e:
        logger.error(f"Failed to get trade recommendation for {symbol}: {str(e)}")
        return None