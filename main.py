import os
import logging
from flask import Flask, render_template, jsonify, request, redirect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "income-machine-secret-key")

# Dictionary to track ETF data
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

@app.route('/')
def index():
    """Home page (ETF Scoreboard)"""
    etfs = []
    for symbol, sector in etf_sectors.items():
        etf = {
            'symbol': symbol,
            'score': 3,  # Default score
            'price': 100.0,  # Default price
            'sector': sector
        }
        etfs.append(etf)
    
    return render_template('index.html', etfs=etfs)

@app.route('/step2')
def step2():
    """Asset Review page (Step 2)"""
    # Get ETF symbol from query parameter
    etf_symbol = request.args.get('etf', 'XLK')  # Default to XLK if not provided
    
    # Check if ETF is valid
    if etf_symbol not in etf_sectors:
        return redirect('/')
    
    # Generate ETF data
    import random
    score = random.randint(1, 5)
    
    # Create sample indicators (5 technical factors)
    indicators = {
        'trend1': {'name': 'Short-Term Trend', 'pass': score >= 1, 'description': 'Price above 20-day EMA'},
        'trend2': {'name': 'Long-Term Trend', 'pass': score >= 2, 'description': 'Price above 50-day EMA'},
        'snapback': {'name': 'Snapback Potential', 'pass': score >= 3, 'description': 'RSI showing bullish momentum'},
        'momentum': {'name': 'Weekly Momentum', 'pass': score >= 4, 'description': 'Weekly close is positive'},
        'stabilizing': {'name': 'Volatility Stabilization', 'pass': score >= 5, 'description': 'ATR is decreasing'}
    }
    
    etf_data = {
        'symbol': etf_symbol,
        'sector': etf_sectors[etf_symbol],
        'score': score,
        'price': round(50 + random.random() * 150, 2),
        'indicators': indicators
    }
    
    return render_template('step2.html', etf=etf_data)

@app.route('/step3')
def step3():
    """Strategy Selection page (Step 3)"""
    # Get ETF symbol from query parameter
    etf_symbol = request.args.get('etf', 'XLK')  # Default to XLK if not provided
    
    # Check if ETF is valid
    if etf_symbol not in etf_sectors:
        return redirect('/')
    
    # Generate ETF data
    import random
    score = random.randint(1, 5)
    current_price = round(50 + random.random() * 150, 2)
    
    # Strategy definitions
    strategies = {
        'aggressive': {
            'name': 'Aggressive Income',
            'description': 'Higher return potential with more risk',
            'dte_range': '7-15 days',
            'roi': '~30%',
            'risk_level': 'High',
            'best_for': 'Experienced traders seeking higher returns',
            'example': f'${round(current_price * 0.3, 2)} potential income per spread (30% ROI)'
        },
        'steady': {
            'name': 'Steady Income',
            'description': 'Balanced risk/reward approach',
            'dte_range': '14-30 days',
            'roi': '~22%',
            'risk_level': 'Medium',
            'best_for': 'Most traders seeking consistent returns',
            'example': f'${round(current_price * 0.22, 2)} potential income per spread (22% ROI)'
        },
        'passive': {
            'name': 'Passive Income',
            'description': 'Lower risk, more consistent approach',
            'dte_range': '30-45 days',
            'roi': '~16%',
            'risk_level': 'Low',
            'best_for': 'Conservative traders prioritizing safety',
            'example': f'${round(current_price * 0.16, 2)} potential income per spread (16% ROI)'
        }
    }
    
    etf_data = {
        'symbol': etf_symbol,
        'sector': etf_sectors[etf_symbol],
        'score': score,
        'price': current_price
    }
    
    return render_template('step3.html', etf=etf_data, strategies=strategies)

@app.route('/step4')
def step4():
    """Trade Details page (Step 4)"""
    # Get ETF symbol and strategy from query parameters
    etf_symbol = request.args.get('etf', 'XLK')  # Default to XLK if not provided
    strategy_type = request.args.get('strategy', 'steady')  # Default to steady if not provided
    
    # Check if ETF is valid
    if etf_symbol not in etf_sectors:
        return redirect('/')
    
    # Check if strategy is valid
    valid_strategies = ['aggressive', 'steady', 'passive']
    if strategy_type not in valid_strategies:
        strategy_type = 'steady'  # Default to steady if invalid
    
    # Generate ETF data
    import random
    score = random.randint(1, 5)
    current_price = round(50 + random.random() * 150, 2)
    
    # Map strategy type to widget parameters
    strategy_params = {
        'aggressive': {'title': 'Aggressive Income Strategy', 'dte_min': 7, 'dte_max': 15, 'roi': 30},
        'steady': {'title': 'Steady Income Strategy', 'dte_min': 14, 'dte_max': 30, 'roi': 22},
        'passive': {'title': 'Passive Income Strategy', 'dte_min': 30, 'dte_max': 45, 'roi': 16}
    }
    
    etf_data = {
        'symbol': etf_symbol,
        'sector': etf_sectors[etf_symbol],
        'score': score,
        'price': current_price
    }
    
    selected_strategy = strategy_params[strategy_type]
    selected_strategy['type'] = strategy_type
    
    return render_template('step4.html', etf=etf_data, strategy=selected_strategy)

@app.route('/api/etfs')
def get_etfs():
    """Get ETF data as JSON"""
    etfs = []
    for symbol, sector in etf_sectors.items():
        etf = {
            'symbol': symbol,
            'score': 3,  # Default score
            'price': 100.0,  # Default price
            'sector': sector
        }
        etfs.append(etf)
    
    return jsonify(etfs)

@app.route('/api/etf/scores')
def get_etf_scores():
    """Get ETF scores data as JSON"""
    result = {}
    
    for symbol, sector in etf_sectors.items():
        # Generate a sample score between 1 and 5
        import random
        score = random.randint(1, 5)
        
        # Create sample indicators (5 technical factors)
        # Each has a pass/fail status matching the overall score
        indicators = {
            'trend1': {'name': 'Short-Term Trend', 'pass': score >= 1},
            'trend2': {'name': 'Long-Term Trend', 'pass': score >= 2},
            'snapback': {'name': 'Snapback Potential', 'pass': score >= 3},
            'momentum': {'name': 'Weekly Momentum', 'pass': score >= 4},
            'stabilizing': {'name': 'Volatility Stabilization', 'pass': score >= 5}
        }
        
        result[symbol] = {
            'score': score,
            'price': round(50 + random.random() * 150, 2),  # Random price between 50 and 200
            'indicators': indicators
        }
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)