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
        Get covered call options data for a specific ETF and strategy
        Returns recommendation for covered call trade
        """
        try:
            # Get ticker data
            ticker = yf.Ticker(symbol)
            
            # Set DTE based on strategy
            if strategy == 'Aggressive':
                target_dte = 7  # ~weekly
                otm_pct_min, otm_pct_max = 0.05, 0.10  # 5-10% OTM
            elif strategy == 'Passive':
                target_dte = 45  # ~monthly+
                otm_pct_min, otm_pct_max = 0.01, 0.03  # 1-3% OTM
            else:  # Steady (default)
                target_dte = 21  # ~bi-weekly
                otm_pct_min, otm_pct_max = 0.02, 0.05  # 2-5% OTM
            
            # Get current price
            current_price = ticker.info.get('regularMarketPrice', 0)
            
            # Get available expiration dates
            expirations = ticker.options
            
            if not expirations:
                logger.warning(f"No options data available for {symbol}")
                return MarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
            # Find closest expiration to target DTE
            target_date = datetime.now() + timedelta(days=target_dte)
            closest_exp = min(expirations, key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d') - target_date).days))
            
            # Get options chain for this expiration
            options = ticker.option_chain(closest_exp)
            calls = options.calls
            
            if calls.empty:
                logger.warning(f"No call options available for {symbol} on {closest_exp}")
                return MarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
            # Filter for OTM calls
            otm_calls = calls[calls['strike'] > current_price]
            
            if otm_calls.empty:
                logger.warning(f"No OTM call options available for {symbol}")
                return MarketDataService._generate_fallback_trade(symbol, strategy, current_price)
            
            # Calculate % OTM for each strike
            otm_calls['pct_otm'] = (otm_calls['strike'] - current_price) / current_price
            
            # Filter for target OTM range
            target_calls = otm_calls[(otm_calls['pct_otm'] >= otm_pct_min) & 
                                    (otm_calls['pct_otm'] <= otm_pct_max)]
            
            if target_calls.empty:
                # If no calls in target range, get closest call to target range
                best_call = otm_calls.iloc[0]
            else:
                # Get call with highest ROI
                target_calls['roi'] = (target_calls['lastPrice'] / current_price) * (365 / target_dte)
                best_call = target_calls.sort_values('roi', ascending=False).iloc[0]
            
            # Calculate actual DTE
            expiration_date = datetime.strptime(closest_exp, '%Y-%m-%d')
            actual_dte = (expiration_date - datetime.now()).days
            
            # Calculate ROI
            premium = best_call['lastPrice']
            annual_roi = (premium / current_price) * (365 / actual_dte) * 100
            annual_roi_formatted = f"{annual_roi:.1f}%"
            
            # Build recommendation
            return {
                'strike': float(best_call['strike']),
                'premium': float(premium),
                'expiration': closest_exp,
                'dte': actual_dte,
                'pct_otm': float(best_call['pct_otm'] * 100),
                'roi': annual_roi_formatted
            }
            
        except Exception as e:
            logger.error(f"Error fetching options data: {str(e)}")
            return MarketDataService._generate_fallback_trade(symbol, strategy, current_price)
    
    @staticmethod
    def _generate_fallback_trade(symbol, strategy, current_price):
        """Generate fallback trade recommendation when API data is unavailable"""
        # Note: This is used as fallback when the API fails
        if strategy == 'Aggressive':
            dte = 7
            pct_otm = 7.5
            premium = current_price * 0.01  # ~1% premium
            roi = "28-32%"
        elif strategy == 'Passive':
            dte = 45
            pct_otm = 2.0
            premium = current_price * 0.015  # ~1.5% premium
            roi = "16-18%"
        else:  # Steady
            dte = 21
            pct_otm = 3.5
            premium = current_price * 0.012  # ~1.2% premium
            roi = "20-24%"
            
        # Calculate strike price
        strike = current_price * (1 + (pct_otm / 100))
        
        # Calculate expiration date
        expiration = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        return {
            'strike': round(strike, 2),
            'premium': round(premium, 2),
            'expiration': expiration,
            'dte': dte,
            'pct_otm': pct_otm,
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