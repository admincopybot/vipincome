"""
Dedicated Debit Spread Analysis API
Isolated endpoint for debit spread calculations - returns JSON only
"""
import os
import logging
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "debit-spread-api-key")

class DebitSpreadCalculator:
    """Core debit spread calculation logic"""
    
    def __init__(self):
        self.polygon_api_key = os.environ.get("POLYGON_API_KEY")
        self.tradelist_api_key = os.environ.get("TRADELIST_API_KEY")
    
    def get_current_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price from available APIs"""
        # Try TheTradeList API first
        if self.tradelist_api_key:
            try:
                url = f"https://api.thetradelis.com/v1/market/stock/{symbol}/price"
                headers = {"Authorization": f"Bearer {self.tradelist_api_key}"}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return float(data.get('price', 0))
            except Exception as e:
                logger.warning(f"TheTradeList API failed for {symbol}: {e}")
        
        # Fallback to Polygon API
        if self.polygon_api_key:
            try:
                url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
                params = {"apikey": self.polygon_api_key}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        return float(data['results'][0]['c'])
            except Exception as e:
                logger.warning(f"TheTradeList API failed for {symbol}: {e}")
        
        return None
    
    def get_options_data(self, symbol: str, expiration_date: str) -> List[Dict]:
        """Get options chain data for a specific expiration"""
        if not self.tradelist_api_key:
            return []
        
        try:
            url = f"https://api.thetradelis.com/v1/options/{symbol}/chain"
            headers = {"Authorization": f"Bearer {self.tradelist_api_key}"}
            params = {"expiration": expiration_date}
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json().get('options', [])
        except Exception as e:
            logger.error(f"Options data fetch failed for {symbol}: {e}")
        
        return []
    
    def find_valid_expirations(self, symbol: str, min_dte: int = 7, max_dte: int = 50) -> List[str]:
        """Find valid expiration dates within DTE range"""
        if not self.tradelist_api_key:
            return []
        
        try:
            url = f"https://api.thetradelis.com/v1/options/{symbol}/expirations"
            headers = {"Authorization": f"Bearer {self.tradelist_api_key}"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                expirations = response.json().get('expirations', [])
                valid_exps = []
                
                for exp_date in expirations:
                    try:
                        exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
                        dte = (exp_dt - datetime.now()).days
                        if min_dte <= dte <= max_dte:
                            valid_exps.append(exp_date)
                    except:
                        continue
                
                return sorted(valid_exps)
        except Exception as e:
            logger.error(f"Expirations fetch failed for {symbol}: {e}")
        
        return []
    
    def calculate_spread_metrics(self, long_option: Dict, short_option: Dict, current_price: float) -> Dict:
        """Calculate comprehensive spread analysis"""
        try:
            # Extract option data
            long_strike = float(long_option.get('strike', 0))
            short_strike = float(short_option.get('strike', 0))
            long_price = float(long_option.get('last_price', 0))
            short_price = float(short_option.get('last_price', 0))
            
            # Basic spread calculations
            spread_cost = long_price - short_price
            spread_width = short_strike - long_strike
            max_profit = spread_width - spread_cost
            max_loss = spread_cost
            roi = (max_profit / spread_cost * 100) if spread_cost > 0 else 0
            breakeven = long_strike + spread_cost
            
            # Days to expiration
            exp_date_str = long_option.get('expiration_date', '')
            if exp_date_str:
                exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
                dte = (exp_date - datetime.now()).days
            else:
                dte = 0
            
            # Price scenario analysis
            scenarios = self._calculate_price_scenarios(
                current_price, long_strike, short_strike, spread_cost
            )
            
            # Greeks and additional metrics
            long_delta = float(long_option.get('delta', 0))
            short_delta = float(short_option.get('delta', 0))
            spread_delta = long_delta - short_delta
            
            long_theta = float(long_option.get('theta', 0))
            short_theta = float(short_option.get('theta', 0))
            spread_theta = long_theta - short_theta
            
            return {
                'success': True,
                'spread_analysis': {
                    'basic_metrics': {
                        'spread_cost': round(spread_cost, 2),
                        'spread_width': round(spread_width, 2),
                        'max_profit': round(max_profit, 2),
                        'max_loss': round(max_loss, 2),
                        'roi_percent': round(roi, 1),
                        'breakeven_price': round(breakeven, 2),
                        'days_to_expiration': dte
                    },
                    'option_details': {
                        'long_option': {
                            'strike': long_strike,
                            'price': long_price,
                            'delta': long_delta,
                            'theta': long_theta
                        },
                        'short_option': {
                            'strike': short_strike,
                            'price': short_price,
                            'delta': short_delta,
                            'theta': short_theta
                        },
                        'spread_greeks': {
                            'delta': round(spread_delta, 3),
                            'theta': round(spread_theta, 3)
                        }
                    },
                    'market_conditions': {
                        'current_stock_price': current_price,
                        'distance_to_long_strike': round(((long_strike - current_price) / current_price * 100), 1),
                        'probability_itm_estimate': self._estimate_probability_itm(current_price, long_strike, dte)
                    },
                    'price_scenarios': scenarios
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Calculation error: {str(e)}'
            }
    
    def _calculate_price_scenarios(self, current_price: float, long_strike: float, 
                                 short_strike: float, spread_cost: float) -> List[Dict]:
        """Calculate profit/loss scenarios at different price points"""
        scenarios = []
        scenario_percentages = [-15, -10, -5, -2.5, -1, 0, 1, 2.5, 5, 10, 15]
        
        for change_pct in scenario_percentages:
            future_price = current_price * (1 + change_pct/100)
            
            # Calculate intrinsic values at expiration
            long_intrinsic = max(0, future_price - long_strike)
            short_intrinsic = max(0, future_price - short_strike)
            spread_value = long_intrinsic - short_intrinsic
            
            # Calculate profit/loss
            profit_loss = spread_value - spread_cost
            scenario_roi = (profit_loss / spread_cost * 100) if spread_cost > 0 else 0
            
            scenarios.append({
                'price_change_percent': change_pct,
                'future_stock_price': round(future_price, 2),
                'spread_value_at_expiration': round(spread_value, 2),
                'profit_loss': round(profit_loss, 2),
                'roi_percent': round(scenario_roi, 1),
                'outcome': 'profit' if profit_loss > 0 else 'loss' if profit_loss < 0 else 'breakeven'
            })
        
        return scenarios
    
    def _estimate_probability_itm(self, current_price: float, strike: float, dte: int) -> float:
        """Simple probability ITM estimate based on moneyness and time"""
        if dte <= 0:
            return 100.0 if current_price > strike else 0.0
        
        # Simple model: further OTM = lower probability, more time = higher probability
        moneyness = (strike - current_price) / current_price
        time_factor = min(dte / 30, 1.0)  # Normalize to ~1 month
        
        if moneyness <= 0:  # ITM
            base_prob = 70.0
        else:  # OTM
            base_prob = max(10.0, 50.0 - (moneyness * 100))
        
        # Adjust for time
        adjusted_prob = base_prob * (0.5 + 0.5 * time_factor)
        return round(min(95.0, max(5.0, adjusted_prob)), 1)
    
    def find_best_spreads(self, symbol: str, current_price: float, 
                         strategy: str = 'balanced') -> Dict:
        """Find optimal debit spreads based on strategy"""
        strategy_configs = {
            'aggressive': {'roi_min': 25, 'roi_max': 50, 'dte_min': 7, 'dte_max': 21},
            'balanced': {'roi_min': 15, 'roi_max': 35, 'dte_min': 14, 'dte_max': 35},
            'conservative': {'roi_min': 8, 'roi_max': 25, 'dte_min': 21, 'dte_max': 50}
        }
        
        config = strategy_configs.get(strategy, strategy_configs['balanced'])
        
        # Find valid expirations
        expirations = self.find_valid_expirations(symbol, config['dte_min'], config['dte_max'])
        if not expirations:
            return {
                'success': False,
                'error': 'No valid expiration dates found'
            }
        
        best_spreads = []
        
        for exp_date in expirations[:3]:  # Check first 3 expirations
            options_chain = self.get_options_data(symbol, exp_date)
            if not options_chain:
                continue
            
            # Filter for calls only
            calls = [opt for opt in options_chain if opt.get('option_type') == 'call']
            
            # Find $1 wide spreads
            for i, long_opt in enumerate(calls):
                long_strike = float(long_opt.get('strike', 0))
                
                # Look for short option $1 higher
                for short_opt in calls:
                    short_strike = float(short_opt.get('strike', 0))
                    if abs(short_strike - long_strike - 1.0) < 0.01:  # $1 wide
                        
                        spread_analysis = self.calculate_spread_metrics(
                            long_opt, short_opt, current_price
                        )
                        
                        if spread_analysis['success']:
                            metrics = spread_analysis['spread_analysis']['basic_metrics']
                            roi = metrics['roi_percent']
                            
                            # Filter by strategy criteria
                            if config['roi_min'] <= roi <= config['roi_max']:
                                best_spreads.append({
                                    'expiration_date': exp_date,
                                    'long_strike': long_strike,
                                    'short_strike': short_strike,
                                    'roi': roi,
                                    'spread_cost': metrics['spread_cost'],
                                    'analysis': spread_analysis
                                })
        
        if not best_spreads:
            return {
                'success': False,
                'error': f'No spreads found matching {strategy} strategy criteria'
            }
        
        # Sort by ROI and return best
        best_spreads.sort(key=lambda x: x['roi'], reverse=True)
        best_spread = best_spreads[0]
        
        return {
            'success': True,
            'strategy': strategy,
            'best_spread': best_spread,
            'alternatives': best_spreads[1:min(5, len(best_spreads))]  # Up to 4 alternatives
        }

# Initialize calculator
calculator = DebitSpreadCalculator()

@app.route('/api/debit-spread', methods=['POST'])
def analyze_debit_spread():
    """
    API endpoint for debit spread analysis
    POST data: {"ticker": "AAPL", "strategy": "balanced"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        ticker = data.get('ticker', '').upper().strip()
        if not ticker:
            return jsonify({
                'success': False,
                'error': 'Ticker symbol is required'
            }), 400
        
        strategy = data.get('strategy', 'balanced').lower()
        if strategy not in ['aggressive', 'balanced', 'conservative']:
            strategy = 'balanced'
        
        # Get current stock price
        current_price = calculator.get_current_stock_price(ticker)
        if not current_price:
            return jsonify({
                'success': False,
                'error': f'Unable to fetch current price for {ticker}'
            }), 400
        
        # Find and analyze best spreads
        result = calculator.find_best_spreads(ticker, current_price, strategy)
        
        if not result['success']:
            return jsonify(result), 404
        
        # Add timestamp and metadata
        result['metadata'] = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'current_price': current_price,
            'strategy_requested': strategy
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'debit-spread-api',
        'timestamp': datetime.now().isoformat(),
        'apis_configured': {
            'polygon': bool(calculator.polygon_api_key),
            'tradelist': bool(calculator.tradelist_api_key)
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)