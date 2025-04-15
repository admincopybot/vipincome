import os
import json
import logging
from datetime import datetime, timedelta
from polygon import RESTClient
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Polygon API key
POLYGON_API_KEY = "WijHjAWtRFsnR4VEeZawON2XdEse1YYG"
client = RESTClient(api_key=POLYGON_API_KEY)

class PolygonDataService:
    """Service to fetch accurate market data from Polygon.io"""
    
    @staticmethod
    def get_etf_price(symbol):
        """Get the latest price for an ETF"""
        try:
            # Get last trade
            last_trade = client.get_last_trade(symbol)
            return last_trade.price
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
            # Set default dates if not provided
            if to_date is None:
                to_date = datetime.now()
            if from_date is None:
                # Default to 6 months for daily data
                if timespan == "day":
                    from_date = to_date - timedelta(days=180)
                # Default to 1 week for hourly data
                elif timespan == "hour":
                    from_date = to_date - timedelta(days=7)
                # Default to 1 day for minute data
                else:
                    from_date = to_date - timedelta(days=1)
            
            # Format dates for API call
            if isinstance(from_date, datetime):
                from_date = from_date.strftime('%Y-%m-%d')
            if isinstance(to_date, datetime):
                to_date = to_date.strftime('%Y-%m-%d')
            
            # Get aggregates (OHLCV data)
            aggs = client.get_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=from_date,
                to=to_date,
                limit=limit
            )
            
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': agg.timestamp,
                'open': agg.open,
                'high': agg.high,
                'low': agg.low,
                'close': agg.close,
                'volume': agg.volume,
                'vwap': getattr(agg, 'vwap', None),
                'date': datetime.fromtimestamp(agg.timestamp/1000)
            } for agg in aggs])
            
            # Set date as index
            if not df.empty:
                df.set_index('date', inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def get_options_chain(symbol, expiration_date=None):
        """
        Get options chain for a specific symbol and expiration date
        
        Parameters:
        - symbol: Underlying ticker symbol
        - expiration_date: Option expiration date (YYYY-MM-DD format)
        
        Returns:
        - Dictionary with calls and puts data
        """
        try:
            # If no expiration date provided, get the options for a symbol
            if expiration_date is None:
                options = client.list_options_contracts(
                    underlying_ticker=symbol,
                    limit=1000
                )
                
                # Extract unique expiration dates
                expirations = set()
                for option in options:
                    expirations.add(option.expiration_date)
                
                return sorted(list(expirations))
            
            # Get options for specific expiration
            calls = client.list_options_contracts(
                underlying_ticker=symbol,
                expiration_date=expiration_date,
                contract_type="call",
                limit=1000
            )
            
            puts = client.list_options_contracts(
                underlying_ticker=symbol,
                expiration_date=expiration_date,
                contract_type="put",
                limit=1000
            )
            
            # Format call options
            call_options = []
            for call in calls:
                # Get last price
                try:
                    last_quote = client.get_last_quote(call.ticker)
                    bid = last_quote.bid_price if hasattr(last_quote, 'bid_price') else 0
                    ask = last_quote.ask_price if hasattr(last_quote, 'ask_price') else 0
                    mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
                except:
                    mid_price = 0
                
                call_options.append({
                    'strike': call.strike_price,
                    'ticker': call.ticker,
                    'bid': bid if 'bid' in locals() else 0,
                    'ask': ask if 'ask' in locals() else 0,
                    'mid': mid_price
                })
            
            # Format put options
            put_options = []
            for put in puts:
                # Get last price
                try:
                    last_quote = client.get_last_quote(put.ticker)
                    bid = last_quote.bid_price if hasattr(last_quote, 'bid_price') else 0
                    ask = last_quote.ask_price if hasattr(last_quote, 'ask_price') else 0
                    mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
                except:
                    mid_price = 0
                
                put_options.append({
                    'strike': put.strike_price,
                    'ticker': put.ticker,
                    'bid': bid if 'bid' in locals() else 0,
                    'ask': ask if 'ask' in locals() else 0,
                    'mid': mid_price
                })
            
            # Sort by strike price
            call_options.sort(key=lambda x: x['strike'])
            put_options.sort(key=lambda x: x['strike'])
            
            return {
                'calls': call_options,
                'puts': put_options,
                'expiration': expiration_date
            }
        
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {str(e)}")
            return {'calls': [], 'puts': [], 'expiration': expiration_date if expiration_date else None}
    
    @staticmethod
    def calculate_etf_score(symbol):
        """
        Calculate a technical score (1-5) for an ETF based on specific indicators:
        1. Trend 1: Price > 20 EMA on Daily Timeframe
        2. Trend 2: Price > 100 EMA on Daily Timeframe
        3. Snapback: RSI < 50 on 4-hour Timeframe
        4. Momentum: Price > Previous Week's Closing Price
        5. Stabilizing: 3-Day ATR < 6-Day ATR
        
        Each indicator = 1 point, total score from 0-5
        """
        try:
            score = 0
            indicators = {}
            
            # Get daily data for trend analysis (6 months)
            daily_data = PolygonDataService.get_historical_data(symbol, timespan="day", multiplier=1)
            if daily_data.empty:
                logger.error(f"No daily data available for {symbol}")
                return 3, PolygonDataService._default_indicators()
            
            # Get 4-hour data for RSI calculation (5 days, which gives us ~30 4-hour bars)
            hourly_data = PolygonDataService.get_historical_data(
                symbol, 
                timespan="hour", 
                multiplier=4, 
                from_date=datetime.now() - timedelta(days=10)
            )
            
            # Current price
            current_price = daily_data['close'].iloc[-1]
            
            # 1. Trend 1: Price > 20 EMA on Daily Timeframe
            ema_20 = daily_data['close'].ewm(span=20, adjust=False).mean().iloc[-1]
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
            ema_100 = daily_data['close'].ewm(span=100, adjust=False).mean().iloc[-1]
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
            
            # 3. Snapback: RSI < 50 on 4-hour Timeframe
            if not hourly_data.empty and len(hourly_data) > 14:
                # Calculate RSI on 4-hour data (more accurate than using daily)
                delta = hourly_data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
            else:
                # Fallback to daily RSI if hourly not available
                delta = daily_data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
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
            
            # 4. Momentum: Above Previous Week's Closing Price (7 calendar days ago)
            # Find exactly 7 days ago or the closest trading day before that
            seven_days_ago = datetime.now() - timedelta(days=7)
            filtered_data = daily_data[daily_data.index <= seven_days_ago]
            
            if not filtered_data.empty:
                prev_week_close = filtered_data['close'].iloc[-1]
            else:
                # Fallback to 5 trading days ago if we don't have data from 7 days ago
                prev_week_close = daily_data['close'].iloc[-6] if len(daily_data) > 5 else daily_data['close'].iloc[0]
            
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
            # Calculate True Range
            high_low = daily_data['high'] - daily_data['low']
            high_close = abs(daily_data['high'] - daily_data['close'].shift())
            low_close = abs(daily_data['low'] - daily_data['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            
            # Calculate ATRs
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
            
            logger.info(f"Calculated score for {symbol}: {score}/5 using Polygon data")
            return score, indicators
            
        except Exception as e:
            logger.error(f"Error calculating ETF score with Polygon data: {str(e)}")
            return 3, PolygonDataService._default_indicators()
    
    @staticmethod
    def _default_indicators():
        """Return default indicator values in case of errors"""
        return {
            'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data unavailable'},
            'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data unavailable'},
            'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data unavailable'},
            'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data unavailable'},
            'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data unavailable'}
        }
    
    @staticmethod
    def get_call_debit_spreads(symbol, strategy='Steady'):
        """
        Get call debit spread options for a specific ETF and strategy using real-time data
        
        Parameters:
        - symbol: ETF ticker symbol
        - strategy: 'Aggressive', 'Steady', or 'Passive'
        
        Returns:
        - Dictionary with debit spread trade details
        """
        try:
            # Set DTE and ROI ranges based on strategy
            if strategy == 'Aggressive':
                target_dte_min, target_dte_max = 7, 15  # ~weekly
                target_roi_min, target_roi_max = 0.25, 0.35  # 25-35% ROI
            elif strategy == 'Passive':
                target_dte_min, target_dte_max = 30, 45  # ~monthly+
                target_roi_min, target_roi_max = 0.15, 0.20  # 15-20% ROI
            else:  # Steady (default)
                target_dte_min, target_dte_max = 14, 30  # ~bi-weekly
                target_roi_min, target_roi_max = 0.18, 0.25  # 18-25% ROI
            
            # Get current price
            current_price = PolygonDataService.get_etf_price(symbol)
            if not current_price:
                logger.error(f"Couldn't get current price for {symbol}")
                return None
            
            # Get expiration dates
            expirations = PolygonDataService.get_options_chain(symbol)
            if not expirations:
                logger.warning(f"No options expirations available for {symbol}")
                return None
            
            # Process expirations to find those within our DTE range
            valid_expirations = []
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                dte = (exp_date - datetime.now()).days
                if target_dte_min <= dte <= target_dte_max:
                    valid_expirations.append((exp, dte))
            
            # Sort by closest to middle of range
            target_dte_mid = (target_dte_min + target_dte_max) / 2
            valid_expirations.sort(key=lambda x: abs(x[1] - target_dte_mid))
            
            if not valid_expirations:
                logger.warning(f"No valid expirations in range {target_dte_min}-{target_dte_max} DTE for {symbol}")
                return None
            
            # Try to find the best spread across all valid expirations
            best_spread = None
            best_roi = 0
            best_exp = None
            best_dte = 0
            
            for expiration, dte in valid_expirations:
                options_chain = PolygonDataService.get_options_chain(symbol, expiration)
                if not options_chain or not options_chain['calls']:
                    continue
                
                calls = options_chain['calls']
                
                # Look for $1 wide spreads
                # For stocks under $100, use $1 increments
                # For stocks $100-$150, use $2.5 increments
                # For stocks over $150, use $5 increments
                if current_price < 100:
                    spread_width = 1.0
                elif current_price < 150:
                    spread_width = 2.5
                else:
                    spread_width = 5.0
                
                potential_spreads = []
                
                # Find all valid spreads
                for i in range(len(calls) - 1):
                    lower_call = calls[i]
                    upper_call = calls[i + 1]
                    
                    # Check if this is a valid width spread
                    if abs(upper_call['strike'] - lower_call['strike']) == spread_width:
                        # Calculate spread cost and return
                        spread_cost = lower_call['mid'] - upper_call['mid']
                        
                        # Skip invalid spreads
                        if spread_cost <= 0 or spread_cost >= spread_width:
                            continue
                        
                        # Calculate ROI
                        max_profit = spread_width - spread_cost
                        roi = max_profit / spread_cost
                        
                        # Calculate how far from current price
                        distance_pct = (lower_call['strike'] - current_price) / current_price
                        
                        # Store spread details
                        potential_spreads.append({
                            'lower_strike': lower_call['strike'],
                            'upper_strike': upper_call['strike'],
                            'width': spread_width,
                            'cost': spread_cost,
                            'roi': roi,
                            'distance_from_current': distance_pct
                        })
                
                if potential_spreads:
                    # We prioritize in-the-money spreads (negative distance) or closest to the money
                    sorted_spreads = sorted(potential_spreads, key=lambda x: x['distance_from_current'])
                    
                    # First try to find an in-the-money spread (safest)
                    itm_spreads = [s for s in sorted_spreads if s['lower_strike'] < current_price]
                    
                    if itm_spreads:
                        # Pick the one closest to the target ROI
                        itm_spreads.sort(key=lambda x: abs(x['roi'] - target_roi_min))
                        best_spread_for_exp = itm_spreads[0]
                    else:
                        # Otherwise get the one closest to the money
                        sorted_spreads.sort(key=lambda x: abs(x['distance_from_current']))
                        best_spread_for_exp = sorted_spreads[0]
                    
                    # See if this is better than our current best spread
                    # We prioritize having a slightly higher ROI if within our range
                    if best_spread is None or (
                        target_roi_min <= best_spread_for_exp['roi'] <= target_roi_max and 
                        best_spread_for_exp['roi'] > best_roi
                    ):
                        best_spread = best_spread_for_exp
                        best_roi = best_spread_for_exp['roi']
                        best_exp = expiration
                        best_dte = dte
            
            # If we found a valid spread
            if best_spread:
                # Calculate ROI percentage and format it
                roi_pct = best_spread['roi'] * 100
                roi_formatted = f"{roi_pct:.1f}%"
                
                # Distance from current price as percentage
                pct_distance = (best_spread['lower_strike'] - current_price) / current_price * 100
                
                # Build recommendation
                return {
                    'strategy_type': 'debit_spread',
                    'strike': float(best_spread['lower_strike']),
                    'upper_strike': float(best_spread['upper_strike']),
                    'spread_width': float(best_spread['width']),
                    'premium': float(best_spread['cost']),
                    'expiration': best_exp,
                    'dte': best_dte,
                    'pct_otm': float(pct_distance),
                    'max_profit': float(best_spread['width'] - best_spread['cost']),
                    'max_loss': float(best_spread['cost']),
                    'roi': roi_formatted
                }
            else:
                logger.warning(f"No valid debit spreads found for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting call debit spreads with Polygon: {str(e)}")
            return None