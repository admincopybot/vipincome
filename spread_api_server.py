"""
Standalone Debit Spread Analysis API Server
Simple POST endpoint: /analyze with ticker parameter
Returns comprehensive spread analysis in JSON format
"""
import os
import logging
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class SpreadAnalyzer:
    def __init__(self):
        self.polygon_key = os.environ.get("POLYGON_API_KEY")
        self.tradelist_key = os.environ.get("TRADELIST_API_KEY")
    
    def get_stock_price(self, ticker: str) -> Optional[float]:
        """Get current stock price from available APIs"""
        # Try Polygon API first (most reliable for stocks)
        if self.polygon_key:
            try:
                url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
                response = requests.get(url, params={"apikey": self.polygon_key}, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        price = float(data['results'][0]['c'])
                        logger.info(f"Got price for {ticker}: ${price}")
                        return price
            except Exception as e:
                logger.warning(f"Polygon API failed: {e}")
        
        # Try TheTradeList API as fallback
        if self.tradelist_key:
            try:
                url = f"https://api.thetradelis.com/v1/market/stock/{ticker}/price"
                headers = {"Authorization": f"Bearer {self.tradelist_key}"}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    price = float(data.get('price', 0))
                    logger.info(f"Got price for {ticker}: ${price}")
                    return price
            except Exception as e:
                logger.warning(f"TheTradeList API failed: {e}")
        
        return None
    
    def get_options_chain(self, ticker: str) -> List[Dict]:
        """Get options chain data"""
        if not self.tradelist_key:
            return []
        
        try:
            url = f"https://api.thetradelis.com/v1/options/{ticker}/chain"
            headers = {"Authorization": f"Bearer {self.tradelist_key}"}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('options', [])
        except Exception as e:
            logger.error(f"Options chain failed for {ticker}: {e}")
        
        return []
    
    def analyze_spread(self, ticker: str, current_price: float, options_chain: List[Dict]) -> Dict:
        """Analyze debit spread opportunities"""
        # Filter for calls with valid expiration dates (7-50 DTE)
        valid_calls = []
        cutoff_date = datetime.now() + timedelta(days=7)
        max_date = datetime.now() + timedelta(days=50)
        
        for option in options_chain:
            if option.get('option_type') != 'call':
                continue
            
            exp_str = option.get('expiration_date', '')
            if not exp_str:
                continue
            
            try:
                exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                if cutoff_date <= exp_date <= max_date:
                    dte = (exp_date - datetime.now()).days
                    option['dte'] = dte
                    valid_calls.append(option)
            except:
                continue
        
        if not valid_calls:
            return {'error': 'No valid call options found in 7-50 DTE range'}
        
        # Find best $1-wide debit spreads
        best_spreads = []
        
        for long_call in valid_calls:
            long_strike = float(long_call.get('strike', 0))
            long_price = float(long_call.get('last_price', 0))
            
            if long_price <= 0:
                continue
            
            # Find matching short call ($1 higher strike, same expiration)
            target_short_strike = long_strike + 1.0
            
            for short_call in valid_calls:
                short_strike = float(short_call.get('strike', 0))
                short_price = float(short_call.get('last_price', 0))
                
                if (abs(short_strike - target_short_strike) < 0.01 and 
                    short_call.get('expiration_date') == long_call.get('expiration_date') and
                    short_price > 0):
                    
                    # Calculate spread metrics
                    spread_cost = long_price - short_price
                    if spread_cost <= 0:
                        continue
                    
                    spread_width = 1.0  # $1 wide
                    max_profit = spread_width - spread_cost
                    roi = (max_profit / spread_cost) * 100
                    breakeven = long_strike + spread_cost
                    
                    # Only include spreads with reasonable ROI
                    if roi >= 5:  # At least 5% ROI
                        spread_data = {
                            'long_strike': long_strike,
                            'short_strike': short_strike,
                            'long_price': round(long_price, 2),
                            'short_price': round(short_price, 2),
                            'spread_cost': round(spread_cost, 2),
                            'max_profit': round(max_profit, 2),
                            'max_loss': round(spread_cost, 2),
                            'roi_percent': round(roi, 1),
                            'breakeven': round(breakeven, 2),
                            'expiration_date': long_call.get('expiration_date'),
                            'days_to_expiration': long_call.get('dte'),
                            'distance_otm_percent': round(((long_strike - current_price) / current_price) * 100, 1)
                        }
                        
                        # Add price scenarios
                        spread_data['price_scenarios'] = self.calculate_scenarios(
                            current_price, long_strike, short_strike, spread_cost
                        )
                        
                        best_spreads.append(spread_data)
                    break
        
        if not best_spreads:
            return {'error': 'No profitable $1-wide debit spreads found'}
        
        # Sort by ROI descending, then by days to expiration
        best_spreads.sort(key=lambda x: (-x['roi_percent'], x['days_to_expiration']))
        
        # Categorize by strategy
        aggressive = [s for s in best_spreads if s['roi_percent'] >= 25 and s['days_to_expiration'] <= 21]
        balanced = [s for s in best_spreads if 15 <= s['roi_percent'] < 25 and 14 <= s['days_to_expiration'] <= 35]
        conservative = [s for s in best_spreads if 8 <= s['roi_percent'] < 15 and s['days_to_expiration'] >= 21]
        
        return {
            'ticker': ticker,
            'current_price': current_price,
            'analysis_timestamp': datetime.now().isoformat(),
            'total_spreads_found': len(best_spreads),
            'strategies': {
                'aggressive': aggressive[:3],  # Top 3 for each strategy
                'balanced': balanced[:3],
                'conservative': conservative[:3]
            },
            'best_overall': best_spreads[:5]  # Top 5 overall
        }
    
    def calculate_scenarios(self, current_price: float, long_strike: float, 
                          short_strike: float, spread_cost: float) -> List[Dict]:
        """Calculate profit/loss scenarios"""
        scenarios = []
        percentages = [-10, -5, -2.5, -1, 0, 1, 2.5, 5, 10]
        
        for pct in percentages:
            future_price = current_price * (1 + pct/100)
            
            # Calculate spread value at expiration
            long_value = max(0, future_price - long_strike)
            short_value = max(0, future_price - short_strike)
            spread_value = long_value - short_value
            
            profit_loss = spread_value - spread_cost
            scenario_roi = (profit_loss / spread_cost) * 100 if spread_cost > 0 else 0
            
            scenarios.append({
                'price_change_percent': pct,
                'future_price': round(future_price, 2),
                'spread_value': round(spread_value, 2),
                'profit_loss': round(profit_loss, 2),
                'roi_percent': round(scenario_roi, 1),
                'outcome': 'profit' if profit_loss > 0 else 'loss' if profit_loss < 0 else 'breakeven'
            })
        
        return scenarios

analyzer = SpreadAnalyzer()

@app.route('/analyze', methods=['POST'])
def analyze_debit_spread():
    """
    Main endpoint for debit spread analysis
    POST JSON: {"ticker": "AAPL"}
    Returns: Complete spread analysis
    """
    try:
        data = request.get_json()
        if not data or 'ticker' not in data:
            return jsonify({
                'success': False,
                'error': 'Please provide ticker in JSON format: {"ticker": "AAPL"}'
            }), 400
        
        ticker = data['ticker'].upper().strip()
        logger.info(f"Analyzing debit spreads for {ticker}")
        
        # Get current stock price
        current_price = analyzer.get_stock_price(ticker)
        if not current_price:
            return jsonify({
                'success': False,
                'error': f'Unable to fetch current price for {ticker}. Please check API keys.'
            }), 400
        
        # Get options chain
        options_chain = analyzer.get_options_chain(ticker)
        if not options_chain:
            return jsonify({
                'success': False,
                'error': f'Unable to fetch options data for {ticker}. Please check API keys.'
            }), 400
        
        # Analyze spreads
        analysis = analyzer.analyze_spread(ticker, current_price, options_chain)
        
        if 'error' in analysis:
            return jsonify({
                'success': False,
                'error': analysis['error']
            }), 404
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'debit-spread-analyzer',
        'timestamp': datetime.now().isoformat(),
        'api_keys_configured': {
            'polygon': bool(analyzer.polygon_key),
            'tradelist': bool(analyzer.tradelist_key)
        }
    })

@app.route('/', methods=['GET'])
def index():
    """Simple usage instructions"""
    return jsonify({
        'service': 'Debit Spread Analysis API',
        'usage': {
            'endpoint': '/analyze',
            'method': 'POST',
            'payload': {'ticker': 'AAPL'},
            'example': 'curl -X POST -H "Content-Type: application/json" -d \'{"ticker":"AAPL"}\' http://localhost:5000/analyze'
        },
        'health_check': '/health'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)