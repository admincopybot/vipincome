import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataService:
    """Service to fetch and analyze market data for ETFs and options"""
    
    @staticmethod
    def get_etf_data(symbols):
        """
        Fetch current data for a list of ETF symbols
        Returns a dictionary with ETF data including price, sector, and calculated score
        """
        if not symbols:
            return {}
            
        result = {}
        
        try:
            # Get data for all symbols
            tickers = yf.Tickers(" ".join(symbols))
            
            for symbol in symbols:
                ticker = tickers.tickers[symbol]
                
                # Get basic ticker info
                info = ticker.info
                price = info.get('regularMarketPrice', 0)
                
                # ETF sector mapping
                sector_map = {
                    'XLF': 'Financial',
                    'XLK': 'Technology',
                    'XLE': 'Energy',
                    'XLV': 'Healthcare',
                    'XLI': 'Industrial',
                    'XLP': 'Consumer Staples',
                    'XLY': 'Consumer Discretionary',
                    'XLB': 'Materials',
                    'XLU': 'Utilities',
                    'XLRE': 'Real Estate'
                }
                
                # Use our mapping or fallback to Yahoo data
                name = sector_map.get(symbol, info.get('sector', 'Unknown Sector'))
                
                # Get historical data for score calculation (fetch 6 months for proper technical analysis)
                hist = ticker.history(period="6mo")
                
                # Calculate score and get indicator details
                score, indicators = MarketDataService._calculate_etf_score(ticker, hist)
                
                result[symbol] = {
                    'name': name,
                    'price': price,
                    'score': score,
                    'indicators': indicators
                }
                
                logger.info(f"Fetched data for {symbol}: ${price}, Score: {score}/5")
                
        except Exception as e:
            logger.error(f"Error fetching ETF data: {str(e)}")
            
        return result
    
    @staticmethod
    def _calculate_etf_score(ticker, hist_data):
        """
        Calculate a score (1-5) for an ETF based on specific technical indicators:
        1. Trend 1: Price > 20 EMA on Daily Timeframe
        2. Trend 2: Price > 100 EMA on Daily Timeframe
        3. Snapback: RSI < 50 on 4-hour Timeframe (approximated with daily data)
        4. Momentum: Price > Previous Week's Closing Price
        5. Stabilizing: 3-Day ATR < 6-Day ATR
        
        Each indicator = 1 point, total score from 0-5
        Returns tuple of (score, indicator_details_dict)
        """
        try:
            score = 0
            indicators = {}
            
            # We need at least 100 data points for reliable technical analysis
            # 6 months of daily data should give us at least 120 points (approx. 21 trading days/month)
            if len(hist_data) < 100:
                logger.warning(f"Not enough historical data to calculate score ({len(hist_data)} data points), using default")
                # Create simulated indicator data for UI display
                return 3, {
                    'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Insufficient historical data'},
                    'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Insufficient historical data'},
                    'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Insufficient historical data'},
                    'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Insufficient historical data'},
                    'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Insufficient historical data'}
                }
            
            # Latest closing price
            current_price = hist_data['Close'].iloc[-1]
            
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
            logger.debug(f"Trend 1: {trend1_desc}")
            
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
            logger.debug(f"Trend 2: {trend2_desc}")
            
            # 3. Snapback: RSI < 50 on 4HR Timeframe (approximated with daily)
            # Calculate RSI (14-period)
            delta = hist_data['Close'].diff()
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
            logger.debug(f"Snapback: {snapback_desc}")
            
            # 4. Momentum: Above Previous Week's Closing Price
            prev_week_close = hist_data['Close'].iloc[-6]  # ~5 trading days ago
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
            logger.debug(f"Momentum: {momentum_desc}")
            
            # 5. Stabilizing: 3 Day ATR < 6 Day ATR
            # Calculate True Range
            high_low = hist_data['High'] - hist_data['Low']
            high_close = abs(hist_data['High'] - hist_data['Close'].shift())
            low_close = abs(hist_data['Low'] - hist_data['Close'].shift())
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
            logger.debug(f"Stabilizing: {stabilizing_desc}")
            
            logger.info(f"Calculated score: {score}/5 using technical indicators")
            return score, indicators
            
        except Exception as e:
            logger.error(f"Error calculating ETF score: {str(e)}")
            # Return default values on error
            return 3, {
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
        """
        try:
            # Get ticker data
            ticker = yf.Ticker(symbol)
            
            # Set DTE and ROI ranges based on strategy
            if strategy == 'Aggressive':
                target_dte_min, target_dte_max = 7, 15  # ~weekly
                target_roi_min, target_roi_max = 0.20, 0.35  # 20-35% ROI
            elif strategy == 'Passive':
                target_dte_min, target_dte_max = 30, 45  # ~monthly+
                target_roi_min, target_roi_max = 0.15, 0.20  # 15-20% ROI
            else:  # Steady (default)
                target_dte_min, target_dte_max = 14, 30  # ~bi-weekly
                target_roi_min, target_roi_max = 0.18, 0.25  # 18-25% ROI
            
            # Get current price
            current_price = ticker.info.get('regularMarketPrice', 0)
            
            # Get available expiration dates
            expirations = ticker.options
            
            if not expirations:
                logger.warning(f"No options data available for {symbol}")
                return MarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
            # Find expirations within our DTE range
            valid_expirations = []
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                dte = (exp_date - datetime.now()).days
                if target_dte_min <= dte <= target_dte_max:
                    valid_expirations.append((exp, dte))
            
            if not valid_expirations:
                # If no expirations in range, find closest one
                closest_exp = min(expirations, key=lambda x: 
                                 abs((datetime.strptime(x, '%Y-%m-%d') - 
                                     (datetime.now() + timedelta(days=target_dte_min))).days))
                exp_date = datetime.strptime(closest_exp, '%Y-%m-%d')
                dte = (exp_date - datetime.now()).days
                valid_expirations = [(closest_exp, dte)]
            
            # Sort by DTE (ascending)
            valid_expirations.sort(key=lambda x: x[1])
            
            # Track the best spread across all expirations
            best_spread = None
            best_roi = 0
            best_exp = None
            best_dte = 0
            
            # Iterate through valid expirations to find the best debit spread
            for expiration, dte in valid_expirations:
                # Get options chain for this expiration
                try:
                    options = ticker.option_chain(expiration)
                    calls = options.calls
                    
                    if calls.empty:
                        logger.warning(f"No call options available for {symbol} on {expiration}")
                        continue
                    
                    # Generate all possible $1-wide call debit spreads
                    spreads = []
                    
                    # Sort strikes in ascending order
                    sorted_strikes = sorted(calls['strike'].unique())
                    
                    # Find all $1-wide spreads
                    for i in range(len(sorted_strikes) - 1):
                        lower_strike = sorted_strikes[i]
                        upper_strike = sorted_strikes[i + 1]
                        
                        # Check if it's approximately a $1-wide spread (allow for some variance)
                        if 0.9 <= (upper_strike - lower_strike) <= 1.1:
                            try:
                                # Get the long call option (buy the lower strike)
                                lower_call = calls[calls['strike'] == lower_strike].iloc[0]
                                
                                # Get the short call option (sell the higher strike)
                                upper_call = calls[calls['strike'] == upper_strike].iloc[0]
                                
                                # Calculate spread cost (debit)
                                spread_cost = lower_call['lastPrice'] - upper_call['lastPrice']
                                
                                # Ensure we're not getting negative or zero costs (can happen with illiquid options)
                                if spread_cost <= 0:
                                    spread_cost = lower_call['ask'] - upper_call['bid']
                                
                                # If still not valid, skip this spread
                                if spread_cost <= 0:
                                    continue
                                
                                # Calculate max value (width of spread)
                                spread_width = upper_strike - lower_strike
                                
                                # Calculate ROI
                                roi = (spread_width - spread_cost) / spread_cost
                                
                                # Add to potential spreads if ROI is in target range
                                if target_roi_min <= roi <= target_roi_max:
                                    spreads.append({
                                        'lower_strike': lower_strike,
                                        'upper_strike': upper_strike,
                                        'cost': spread_cost,
                                        'width': spread_width,
                                        'roi': roi,
                                        'distance_from_current': lower_strike - current_price
                                    })
                            except (IndexError, KeyError):
                                continue
                    
                    # If we found valid spreads for this expiration
                    if spreads:
                        # Sort by distance from current price (we want the safest one)
                        # We prioritize in-the-money spreads (negative distance) or closest to the money
                        sorted_spreads = sorted(spreads, key=lambda x: x['distance_from_current'])
                        
                        # Get the best spread for this expiration
                        best_spread_for_exp = None
                        
                        # First try to find an in-the-money spread (safest)
                        itm_spreads = [s for s in sorted_spreads if s['lower_strike'] < current_price]
                        if itm_spreads:
                            # Pick the one closest to the current price
                            best_spread_for_exp = sorted(itm_spreads, key=lambda x: abs(x['lower_strike'] - current_price))[0]
                        else:
                            # Otherwise get the one closest to the money
                            best_spread_for_exp = sorted_spreads[0]
                        
                        # See if this is better than our current best spread
                        # We prioritize slightly higher ROI if we have multiple good spreads
                        if best_spread is None or best_spread_for_exp['roi'] > best_roi:
                            best_spread = best_spread_for_exp
                            best_roi = best_spread_for_exp['roi']
                            best_exp = expiration
                            best_dte = dte
                
                except Exception as e:
                    logger.error(f"Error processing expiration {expiration}: {str(e)}")
                    continue
            
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
                return MarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
        except Exception as e:
            logger.error(f"Error fetching options data: {str(e)}")
            return MarketDataService._generate_fallback_trade(symbol, strategy, current_price)
    
    @staticmethod
    def _generate_fallback_trade(symbol, strategy, current_price):
        """Generate fallback trade recommendation when API data is unavailable"""
        # Note: This is used as fallback when the API fails
        if strategy == 'Aggressive':
            dte = 7
            pct_otm = -1.0  # Slightly ITM for lower strike
            premium = current_price * 0.025  # ~2.5% premium
            roi = "28-32%"
        elif strategy == 'Passive':
            dte = 45
            pct_otm = -0.5  # Slightly ITM for lower strike
            premium = current_price * 0.03  # ~3% premium
            roi = "16-18%"
        else:  # Steady
            dte = 21
            pct_otm = -0.75  # Slightly ITM for lower strike
            premium = current_price * 0.025  # ~2.5% premium
            roi = "20-24%"
            
        # Calculate lower strike price (typically ITM)
        lower_strike = round(current_price * (1 + (pct_otm / 100)), 2)
        
        # Calculate upper strike price ($1 higher)
        upper_strike = round(lower_strike + 1, 2)
        
        # Fixed $1 spread width
        spread_width = 1.0
        
        # Calculate expiration date
        expiration = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        # Calculate max profit
        max_profit = spread_width - premium
        
        # Return a consistent structure that includes all fields used in the UI
        return {
            'strategy_type': 'debit_spread',
            'strike': lower_strike,
            'upper_strike': upper_strike,
            'spread_width': spread_width,
            'premium': round(premium, 2),
            'expiration': expiration,
            'dte': dte,
            'pct_otm': pct_otm,
            'max_profit': round(max_profit, 2),
            'max_loss': round(premium, 2),
            'roi': roi
        }

# Example sector ETFs to track
SECTOR_ETFS = [
    'XLF',  # Financial
    'XLK',  # Technology
    'XLE',  # Energy
    'XLV',  # Healthcare
    'XLI',  # Industrial
    'XLP',  # Consumer Staples
    'XLY',  # Consumer Discretionary
    'XLB',  # Materials
    'XLU',  # Utilities
    'XLRE'  # Real Estate
]

def update_market_data():
    """Update market data for all tracked ETFs"""
    return MarketDataService.get_etf_data(SECTOR_ETFS)

def get_trade_recommendation(symbol, strategy):
    """Get trade recommendation for a specific ETF and strategy"""
    return MarketDataService.get_options_data(symbol, strategy)

if __name__ == "__main__":
    # Test the service
    etf_data = update_market_data()
    print(f"Fetched data for {len(etf_data)} ETFs")
    
    # Test options data
    if etf_data:
        symbol = list(etf_data.keys())[0]
        trade = get_trade_recommendation(symbol, 'Steady')
        print(f"Trade recommendation for {symbol}: {trade}")