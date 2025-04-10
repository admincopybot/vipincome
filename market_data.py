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
                name = info.get('sector', 'Unknown Sector')
                
                # Get historical data for score calculation
                hist = ticker.history(period="1mo")
                
                # Calculate score based on multiple factors (1-5 scale)
                score = MarketDataService._calculate_etf_score(ticker, hist)
                
                result[symbol] = {
                    'name': name,
                    'price': price,
                    'score': score
                }
                
                logger.info(f"Fetched data for {symbol}: ${price}, Score: {score}/5")
                
        except Exception as e:
            logger.error(f"Error fetching ETF data: {str(e)}")
            
        return result
    
    @staticmethod
    def _calculate_etf_score(ticker, hist_data):
        """
        Calculate a score (1-5) for an ETF based on various factors:
        - Recent performance trend
        - Volatility
        - Volume trends
        - Market conditions for covered calls
        
        Higher score = better for covered call strategy
        """
        try:
            # 1. Calculate price momentum (recent performance trend)
            if len(hist_data) < 5:
                return 3  # Default score if not enough data
                
            # Calculate short-term (5-day) momentum
            recent_change = (hist_data['Close'].iloc[-1] / hist_data['Close'].iloc[-5] - 1) * 100
            
            # 2. Calculate volatility (20-day)
            volatility = hist_data['Close'].pct_change().std() * 100
            
            # 3. Volume trend
            avg_volume = hist_data['Volume'].mean()
            recent_volume = hist_data['Volume'].iloc[-5:].mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Combine factors to create score (1-5)
            # Ideal for covered calls: moderate upward momentum, good volatility, strong volume
            momentum_score = min(5, max(1, int(2.5 + recent_change / 2))) if -5 <= recent_change <= 5 else 3
            volatility_score = min(5, max(1, int(volatility / 0.5))) if 0.5 <= volatility <= 3 else 3
            volume_score = min(5, max(1, int(2 * volume_ratio))) if 0.5 <= volume_ratio <= 2.5 else 3
            
            # Final score - weighted average rounded to nearest integer
            final_score = round((momentum_score * 0.4) + (volatility_score * 0.4) + (volume_score * 0.2))
            return min(5, max(1, final_score))
            
        except Exception as e:
            logger.error(f"Error calculating ETF score: {str(e)}")
            return 3  # Default score on error
    
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