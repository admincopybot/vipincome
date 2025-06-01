"""
Clean Income Machine ETF Analyzer - Database Only Version
Displays pre-calculated ETF scoring data from database with exact same frontend
No WebSocket, API calls, or real-time calculations
"""
import logging
import os
import io
import csv
from flask import Flask, request, render_template_string, jsonify, redirect
from database_models import ETFDatabase
from csv_data_loader import CsvDataLoader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize database and CSV loader
etf_db = ETFDatabase()
csv_loader = CsvDataLoader()

def load_etf_data_from_database():
    """Load ETF data from database and update global etf_scores while keeping frontend exactly the same"""
    global etf_scores
    
    try:
        # Get all ETF data from database
        db_data = etf_db.get_all_etfs()
        
        # Default sector mappings to keep frontend naming consistent
        sector_mappings = {
            "XLC": "Communication Services",
            "XLF": "Financial", 
            "XLV": "Health Care",
            "XLI": "Industrial",
            "XLP": "Consumer Staples",
            "XLY": "Consumer Discretionary", 
            "XLE": "Energy",
            "XLB": "Materials",
            "XLU": "Utilities",
            "XLRE": "Real Estate"
        }
        
        # Convert database format to frontend format while keeping exact same structure
        for symbol, data in db_data.items():
            criteria = data['criteria']
            
            # Create indicators structure exactly as frontend expects
            indicators = {
                'trend1': {
                    'pass': criteria['trend1'],
                    'current': 0,
                    'threshold': 0,
                    'description': 'Price > 20-day EMA'
                },
                'trend2': {
                    'pass': criteria['trend2'], 
                    'current': 0,
                    'threshold': 0,
                    'description': 'Price > 100-day EMA'
                },
                'snapback': {
                    'pass': criteria['snapback'],
                    'current': 0,
                    'threshold': 50,
                    'description': 'RSI < 50'
                },
                'momentum': {
                    'pass': criteria['momentum'],
                    'current': 0,
                    'threshold': 0,
                    'description': 'Price > Previous Week Close'
                },
                'stabilizing': {
                    'pass': criteria['stabilizing'],
                    'current': 0,
                    'threshold': 0,
                    'description': '3-day ATR < 6-day ATR'
                }
            }
            
            # Only include sector name if it's a known ETF sector
            sector_name = sector_mappings.get(symbol, "")
            
            # Update etf_scores with exact same structure as before
            etf_scores[symbol] = {
                "name": sector_name,
                "score": data['total_score'],
                "price": data['current_price'],
                "indicators": indicators
            }
        
        logger.info(f"Loaded {len(db_data)} symbols from database into etf_scores")
        
    except Exception as e:
        logger.error(f"Error loading ETF data from database: {str(e)}")

# Load initial data from database
etf_scores = {}
load_etf_data_from_database()

# Initialize with default ETF structure if database is empty
if not etf_scores:
    default_indicators = {
        'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > 20-day EMA'},
        'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > 100-day EMA'},
        'snapback': {'pass': False, 'current': 0, 'threshold': 50, 'description': 'RSI < 50'},
        'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Price > Previous Week Close'},
        'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': '3-day ATR < 6-day ATR'}
    }

    etf_scores = {
        "XLC": {"name": "Communication Services", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLF": {"name": "Financial", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLV": {"name": "Health Care", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLI": {"name": "Industrial", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLP": {"name": "Consumer Staples", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLY": {"name": "Consumer Discretionary", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLE": {"name": "Energy", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLB": {"name": "Materials", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLU": {"name": "Utilities", "score": 0, "price": 0, "indicators": default_indicators.copy()},
        "XLRE": {"name": "Real Estate", "score": 0, "price": 0, "indicators": default_indicators.copy()}
    }

def synchronize_etf_scores():
    """
    Ensure all ETF scores match their indicators by recalculating scores directly from indicator values.
    This function eliminates any discrepancy between the displayed score and the actual indicator checkboxes.
    """
    global etf_scores
    
    for symbol, etf_data in etf_scores.items():
        if 'indicators' in etf_data:
            indicators = etf_data['indicators']
            
            # Count the number of criteria that pass
            score = 0
            if indicators.get('trend1', {}).get('pass', False):
                score += 1
            if indicators.get('trend2', {}).get('pass', False):
                score += 1
            if indicators.get('snapback', {}).get('pass', False):
                score += 1
            if indicators.get('momentum', {}).get('pass', False):
                score += 1
            if indicators.get('stabilizing', {}).get('pass', False):
                score += 1
            
            # Update the score to match the indicators
            etf_scores[symbol]['score'] = score

def fetch_options_data(symbol, current_price):
    """Fetch options data from Polygon API and process for each strategy"""
    import requests
    from datetime import datetime, timedelta
    
    api_key = os.environ.get('POLYGON_API_KEY')
    if not api_key:
        return {
            'passive': {'error': 'API key not configured'},
            'steady': {'error': 'API key not configured'},
            'aggressive': {'error': 'API key not configured'}
        }
    
    try:
        # Fetch options contracts
        url = f"https://api.polygon.io/v3/reference/options/contracts"
        params = {
            'underlying_ticker': symbol,
            'limit': 1000,
            'apikey': api_key
        }
        
        response = requests.get(url, params=params)
        if response.status_code != 200:
            error_msg = f"API error: {response.status_code}"
            return {
                'passive': {'error': error_msg},
                'steady': {'error': error_msg},
                'aggressive': {'error': error_msg}
            }
        
        data = response.json()
        contracts = data.get('results', [])
        
        if not contracts:
            no_data_msg = f"No options contracts available for {symbol}"
            return {
                'passive': {'error': no_data_msg},
                'steady': {'error': no_data_msg},
                'aggressive': {'error': no_data_msg}
            }
        
        # Process options for each strategy
        today = datetime.now()
        strategies = process_options_strategies(contracts, current_price, today)
        
        return strategies
        
    except Exception as e:
        error_msg = f"Error fetching options data: {str(e)}"
        return {
            'passive': {'error': error_msg},
            'steady': {'error': error_msg},
            'aggressive': {'error': error_msg}
        }

def process_options_strategies(contracts, current_price, today):
    """Process options contracts based on strategy criteria"""
    from datetime import datetime, timedelta
    
    strategies = {
        'passive': {'error': 'No suitable options found'},
        'steady': {'error': 'No suitable options found'},
        'aggressive': {'error': 'No suitable options found'}
    }
    
    # Filter call options only
    call_options = [c for c in contracts if c.get('contract_type') == 'call']
    
    for contract in call_options:
        try:
            # Parse expiration date
            exp_date_str = contract.get('expiration_date')
            if not exp_date_str:
                continue
                
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
            dte = (exp_date - today).days
            
            strike_price = float(contract.get('strike_price', 0))
            if strike_price <= 0:
                continue
            
            # Check each strategy criteria
            check_strategy_fit(contract, dte, strike_price, current_price, strategies)
            
        except (ValueError, TypeError):
            continue
    
    return strategies

def check_strategy_fit(contract, dte, strike_price, current_price, strategies):
    """Check if option fits strategy criteria and calculate ROI"""
    
    # Aggressive: 10-17 DTE, strike below current price
    if 10 <= dte <= 17 and strike_price < current_price:
        roi = calculate_roi(strike_price, current_price, dte)
        if 30 <= roi <= 40:
            if strategies['aggressive'].get('error'):
                strategies['aggressive'] = create_strategy_data('Aggressive', contract, dte, roi, current_price)
    
    # Steady: 17-28 DTE, strike <2% below current price  
    elif 17 <= dte <= 28 and strike_price >= (current_price * 0.98):
        roi = calculate_roi(strike_price, current_price, dte)
        if 15 <= roi <= 25:
            if strategies['steady'].get('error'):
                strategies['steady'] = create_strategy_data('Steady', contract, dte, roi, current_price)
    
    # Passive: 28-42 DTE, strike <10% below current price
    elif 28 <= dte <= 42 and strike_price >= (current_price * 0.90):
        roi = calculate_roi(strike_price, current_price, dte)
        if 10 <= roi <= 15:
            if strategies['passive'].get('error'):
                strategies['passive'] = create_strategy_data('Passive', contract, dte, roi, current_price)

def calculate_roi(strike_price, current_price, dte):
    """Calculate estimated ROI for the option strategy"""
    # Simplified ROI calculation - can be enhanced with real option pricing
    price_diff_pct = ((strike_price - current_price) / current_price) * 100
    time_value = max(1, dte / 30)  # Time factor
    estimated_roi = abs(price_diff_pct) * time_value * 2
    return min(estimated_roi, 50)  # Cap at 50%

def create_strategy_data(strategy_name, contract, dte, roi, current_price):
    """Create formatted strategy data for display"""
    strike_price = float(contract.get('strike_price', 0))
    price_diff_pct = ((strike_price - current_price) / current_price) * 100
    
    return {
        'name': strategy_name,
        'dte': dte,
        'dte_range': get_dte_range(strategy_name),
        'roi': round(roi, 1),
        'roi_range': get_roi_range(strategy_name),
        'strike_price': strike_price,
        'current_price': current_price,
        'strike_selection': get_strike_description(strategy_name, price_diff_pct),
        'management': get_management_rule(strategy_name),
        'contract_symbol': contract.get('ticker', 'N/A'),
        'expiration_date': contract.get('expiration_date', 'N/A'),
        'contract_type': contract.get('contract_type', 'N/A'),
        'exercise_style': contract.get('exercise_style', 'N/A'),
        'shares_per_contract': contract.get('shares_per_contract', 100),
        'primary_exchange': contract.get('primary_exchange', 'N/A'),
        'cfi': contract.get('cfi', 'N/A')
    }

def get_dte_range(strategy):
    ranges = {
        'Aggressive': '10 to 17 days',
        'Steady': '17 to 28 days', 
        'Passive': '28 to 42 days'
    }
    return ranges.get(strategy, '')

def get_roi_range(strategy):
    ranges = {
        'Aggressive': '30% to 40%',
        'Steady': '15% to 25%',
        'Passive': '10% to 15%'
    }
    return ranges.get(strategy, '')

def get_strike_description(strategy, price_diff_pct):
    if strategy == 'Aggressive':
        return 'Below current price'
    elif strategy == 'Steady':
        return f'At or <2% below current price'
    else:  # Passive
        return f'At or <10% below current price'

def get_management_rule(strategy):
    rules = {
        'Aggressive': 'Check daily',
        'Steady': 'Check twice per week',
        'Passive': 'Check weekly'
    }
    return rules.get(strategy, '')

def fetch_option_snapshot(option_id, underlying_ticker):
    """Fetch real-time option data from Polygon API"""
    import requests
    
    api_key = os.environ.get('POLYGON_API_KEY')
    if not api_key:
        return {'error': 'API key not configured'}
    
    try:
        url = f"https://api.polygon.io/v3/snapshot/options/{underlying_ticker}/{option_id}"
        params = {'apikey': api_key}
        
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return {'error': f'API error: {response.status_code}'}
        
        data = response.json()
        if 'results' not in data:
            return {'error': 'No option data available'}
        
        return data['results']
        
    except Exception as e:
        return {'error': f'Error fetching option data: {str(e)}'}

def calculate_debit_spread_analysis(long_option_data, short_option_data, current_stock_price):
    """Calculate comprehensive debit spread analysis"""
    from datetime import datetime
    
    try:
        # Extract option prices
        long_price = long_option_data.get('day', {}).get('close', 0)
        short_price = short_option_data.get('day', {}).get('close', 0)
        
        # Extract strike prices
        long_strike = float(long_option_data.get('details', {}).get('strike_price', 0))
        short_strike = float(short_option_data.get('details', {}).get('strike_price', 0))
        
        # Calculate spread metrics
        spread_cost = long_price - short_price
        spread_width = short_strike - long_strike
        max_profit = spread_width - spread_cost
        roi = (max_profit / spread_cost) * 100 if spread_cost > 0 else 0
        breakeven = long_strike + spread_cost
        
        # Calculate days to expiration
        exp_date_str = long_option_data.get('details', {}).get('expiration_date', '')
        if exp_date_str:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
            days_to_exp = (exp_date - datetime.now()).days
        else:
            days_to_exp = 0
        
        # Generate price scenarios
        scenarios = []
        scenario_percentages = [-7.5, -5, -2.5, 0, 2.5, 5, 7.5]
        
        for change_pct in scenario_percentages:
            future_price = current_stock_price * (1 + change_pct/100)
            
            # Calculate intrinsic values at expiration
            long_call_value = max(0, future_price - long_strike)
            short_call_value = max(0, future_price - short_strike)
            spread_value = long_call_value - short_call_value
            
            # Calculate profit/loss
            profit = spread_value - spread_cost
            scenario_roi = (profit / spread_cost) * 100 if spread_cost > 0 else 0
            outcome = "win" if profit > 0 else "loss"
            
            scenarios.append({
                'change_percent': change_pct,
                'stock_price': future_price,
                'spread_value': spread_value,
                'profit_loss': profit,
                'roi': scenario_roi,
                'outcome': outcome
            })
        
        return {
            'spread_cost': spread_cost,
            'spread_width': spread_width,
            'max_profit': max_profit,
            'max_loss': spread_cost,
            'roi': roi,
            'breakeven': breakeven,
            'days_to_expiration': days_to_exp,
            'scenarios': scenarios,
            'long_strike': long_strike,
            'short_strike': short_strike,
            'long_price': long_price,
            'short_price': short_price
        }
        
    except Exception as e:
        return {'error': f'Calculation error: {str(e)}'}

def calculate_single_option_analysis(option_data, current_stock_price):
    """Calculate comprehensive single option analysis using real Polygon data"""
    from datetime import datetime
    
    try:
        # Extract real option data from Polygon API
        option_price = option_data.get('day', {}).get('close', 0)
        strike_price = float(option_data.get('details', {}).get('strike_price', 0))
        
        # Extract Greeks and other real data
        greeks = option_data.get('greeks', {})
        delta = greeks.get('delta', 0)
        theta = greeks.get('theta', 0)
        gamma = greeks.get('gamma', 0)
        vega = greeks.get('vega', 0)
        
        implied_vol = option_data.get('implied_volatility', 0)
        open_interest = option_data.get('open_interest', 0)
        volume = option_data.get('day', {}).get('volume', 0)
        
        # Calculate days to expiration
        exp_date_str = option_data.get('details', {}).get('expiration_date', '')
        if exp_date_str:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
            days_to_exp = (exp_date - datetime.now()).days
        else:
            days_to_exp = 0
        
        # Calculate intrinsic and time value
        intrinsic_value = max(0, current_stock_price - strike_price)
        time_value = option_price - intrinsic_value
        
        # Generate price scenarios for single option
        scenarios = []
        scenario_percentages = [-10, -7.5, -5, -2.5, 0, 2.5, 5, 7.5, 10]
        
        for change_pct in scenario_percentages:
            future_price = current_stock_price * (1 + change_pct/100)
            
            # Calculate option value at expiration (intrinsic only)
            option_value_at_exp = max(0, future_price - strike_price)
            
            # Calculate profit/loss
            profit = option_value_at_exp - option_price
            roi = (profit / option_price) * 100 if option_price > 0 else 0
            outcome = "profit" if profit > 0 else "loss"
            
            scenarios.append({
                'change_percent': change_pct,
                'stock_price': future_price,
                'option_value': option_value_at_exp,
                'profit_loss': profit,
                'roi': roi,
                'outcome': outcome
            })
        
        return {
            'option_price': option_price,
            'strike_price': strike_price,
            'current_stock_price': current_stock_price,
            'intrinsic_value': intrinsic_value,
            'time_value': time_value,
            'days_to_expiration': days_to_exp,
            'delta': delta,
            'theta': theta,
            'gamma': gamma,
            'vega': vega,
            'implied_volatility': implied_vol,
            'open_interest': open_interest,
            'volume': volume,
            'scenarios': scenarios,
            'max_loss': option_price,  # For long calls, max loss is premium paid
            'breakeven': strike_price + option_price
        }
        
    except Exception as e:
        return {'error': f'Calculation error: {str(e)}'}

@app.route('/step4/<symbol>/<strategy>/<option_id>')
def step4(symbol, strategy, option_id):
    """Step 4: Detailed Options Trade Analysis"""
    
    # Get current stock price
    current_price = None
    etf_data = etf_db.get_all_etfs()
    for etf in etf_data.get('etfs', []):
        if etf['symbol'] == symbol:
            current_price = etf['current_price']
            break
    
    if not current_price:
        current_price = 150.0  # Fallback
    
    # For debit spread, we need both long and short options
    # For now, we'll use the provided option as the long option
    # and find a suitable short option (higher strike, same expiration)
    
    long_option_data = fetch_option_snapshot(option_id, symbol)
    
    if 'error' in long_option_data:
        error_msg = long_option_data['error']
        spread_analysis = None
    else:
        # For now, let's show single option analysis with the real data we have
        # In a production system, you'd fetch available strikes from the options chain
        spread_analysis = calculate_single_option_analysis(long_option_data, current_price)
        error_msg = None
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Step 4: Trade Analysis - {{ symbol }} {{ strategy.title() }} Strategy</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: #1a202c;
            color: #ffffff;
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .top-banner {
            background: rgba(0, 12, 12, 0.8);
            text-align: center;
            padding: 8px;
            font-size: 14px;
            color: #ffffff;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            background: rgba(255, 255, 255, 0.02);
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .header-logo {
            height: 32px;
            width: auto;
        }
        
        .nav-menu {
            display: flex;
            align-items: center;
            gap: 30px;
        }
        
        .nav-item {
            color: rgba(255, 255, 255, 0.8);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s ease;
        }
        
        .nav-item:hover {
            color: #ffffff;
        }
        
        .get-offer-btn {
            background: #ffffff;
            color: #1e40af;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .get-offer-btn:hover {
            background: #f8fafc;
            transform: translateY(-1px);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        .trade-header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .strategy-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            margin-bottom: 16px;
        }
        
        .strategy-passive {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        
        .strategy-steady {
            background: rgba(59, 130, 246, 0.2);
            color: #3b82f6;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }
        
        .strategy-aggressive {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .trade-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 16px;
            color: #ffffff;
        }
        
        .trade-subtitle {
            font-size: 1.1rem;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .error-container {
            background: rgba(220, 38, 38, 0.2);
            border: 1px solid rgba(220, 38, 38, 0.4);
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            margin-bottom: 40px;
        }
        
        .error-message {
            color: #ef4444;
            font-size: 1.1rem;
            font-weight: 500;
        }
        
        .trade-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .trade-card {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 16px;
            padding: 30px;
            backdrop-filter: blur(10px);
        }
        
        .card-header {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #8b5cf6;
        }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .metric-row:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.9rem;
        }
        
        .metric-value {
            color: #ffffff;
            font-weight: 500;
            font-size: 0.9rem;
        }
        
        .scenarios-table {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 40px;
            overflow-x: auto;
        }
        
        .table-header {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #8b5cf6;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        th {
            color: rgba(255, 255, 255, 0.8);
            font-weight: 600;
            font-size: 0.9rem;
        }
        
        td {
            color: #ffffff;
            font-size: 0.9rem;
        }
        
        .profit {
            color: #22c55e;
        }
        
        .loss {
            color: #ef4444;
        }
        
        .back-to-step3 {
            margin-top: 40px;
            text-align: center;
        }
        
        .back-btn {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: rgba(255, 255, 255, 0.9);
            padding: 12px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .back-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }
        </style>
    </head>
    <body>
        <div class="top-banner">
            Free Income Machine Experience Ends in... 670 DIM 428 1485
        </div>
        
        <div class="header">
            <div class="logo">
                <img src="/static/incomemachine_logo.png" alt="Income Machine" class="header-logo">
            </div>
            <div class="nav-menu">
                <a href="#" class="nav-item">How to Use</a>
                <a href="#" class="nav-item">Trade Classes</a>
                <a href="#" class="get-offer-btn">Get 50% OFF</a>
            </div>
        </div>
        
        <div class="container">
            <div class="trade-header">
                <div class="strategy-badge strategy-{{ strategy }}">{{ strategy }} Strategy</div>
                <div class="trade-title">{{ symbol }} Call Option Analysis</div>
                <div class="trade-subtitle">Real-time options analysis using Polygon API data</div>
            </div>
            
            {% if error_msg %}
            <div class="error-container">
                <div class="error-message">{{ error_msg }}</div>
            </div>
            {% else %}
            
            <div class="trade-grid">
                <div class="trade-card">
                    <div class="card-header">Option Details</div>
                    <div class="metric-row">
                        <span class="metric-label">Strike Price:</span>
                        <span class="metric-value">${{ "%.2f"|format(spread_analysis.strike_price) }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Option Price:</span>
                        <span class="metric-value">${{ "%.2f"|format(spread_analysis.option_price) }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Current Stock:</span>
                        <span class="metric-value">${{ "%.2f"|format(spread_analysis.current_stock_price) }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Days to Expiry:</span>
                        <span class="metric-value">{{ spread_analysis.days_to_expiration }}</span>
                    </div>
                </div>
                
                <div class="trade-card">
                    <div class="card-header">Value Analysis</div>
                    <div class="metric-row">
                        <span class="metric-label">Intrinsic Value:</span>
                        <span class="metric-value">${{ "%.2f"|format(spread_analysis.intrinsic_value) }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Time Value:</span>
                        <span class="metric-value">${{ "%.2f"|format(spread_analysis.time_value) }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Max Loss:</span>
                        <span class="metric-value loss">${{ "%.2f"|format(spread_analysis.max_loss) }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Breakeven:</span>
                        <span class="metric-value">${{ "%.2f"|format(spread_analysis.breakeven) }}</span>
                    </div>
                </div>
                
                <div class="trade-card">
                    <div class="card-header">Greeks & Data</div>
                    <div class="metric-row">
                        <span class="metric-label">Delta:</span>
                        <span class="metric-value">{{ "%.4f"|format(spread_analysis.delta) }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Theta:</span>
                        <span class="metric-value">{{ "%.4f"|format(spread_analysis.theta) }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Volume:</span>
                        <span class="metric-value">{{ spread_analysis.volume }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Open Interest:</span>
                        <span class="metric-value">{{ spread_analysis.open_interest }}</span>
                    </div>
                </div>
            </div>
            
            <div class="scenarios-table">
                <div class="table-header">Price Scenarios at Expiration</div>
                <table>
                    <thead>
                        <tr>
                            <th>Stock Price Change</th>
                            <th>Stock Price</th>
                            <th>Option Value</th>
                            <th>Profit/Loss</th>
                            <th>ROI</th>
                            <th>Outcome</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for scenario in spread_analysis.scenarios %}
                        <tr>
                            <td>{{ "%+.1f"|format(scenario.change_percent) }}%</td>
                            <td>${{ "%.2f"|format(scenario.stock_price) }}</td>
                            <td>${{ "%.2f"|format(scenario.option_value) }}</td>
                            <td class="{{ scenario.outcome }}">${{ "%+.2f"|format(scenario.profit_loss) }}</td>
                            <td class="{{ scenario.outcome }}">{{ "%+.1f"|format(scenario.roi) }}%</td>
                            <td class="{{ scenario.outcome }}">{{ scenario.outcome.upper() }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            {% endif %}
            
            <div class="back-to-step3">
                <a href="/step3/{{ symbol }}" class="back-btn">← Back to Strategy Selection</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, 
                                symbol=symbol, 
                                strategy=strategy,
                                option_id=option_id,
                                current_price=current_price,
                                spread_analysis=spread_analysis,
                                error_msg=error_msg)

@app.route('/')
def index():
    # Synchronize scores before displaying
    synchronize_etf_scores()
    
    # Create the exact same template as before - keeping frontend identical
    template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Income Machine</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: white;
            min-height: 100vh;
            line-height: 1.5;
        }
        
        .top-banner {
            background: #1e40af;
            padding: 12px 0;
            text-align: center;
            color: white;
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #3b82f6;
        }
        
        .header {
            background: rgba(15, 23, 42, 0.95);
            padding: 20px 50px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #374151;
        }
        
        .logo {
            display: flex;
            align-items: center;
        }
        
        .header-logo {
            height: 50px;
            width: auto;
            object-fit: contain;
        }
        
        .nav-menu {
            display: flex;
            gap: 40px;
            align-items: center;
        }
        
        .nav-item {
            color: #94a3b8;
            text-decoration: none;
            font-size: 15px;
            font-weight: 500;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .nav-item::after {
            content: '';
            position: absolute;
            bottom: -5px;
            left: 0;
            width: 0;
            height: 2px;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            transition: width 0.3s ease;
        }
        
        .nav-item:hover {
            color: white;
        }
        
        .nav-item:hover::after {
            width: 100%;
        }
        
        .get-offer-btn {
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            color: #1a1f2e;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 700;
            font-size: 13px;
            box-shadow: 0 4px 15px rgba(251, 191, 36, 0.4);
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .get-offer-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(251, 191, 36, 0.6);
        }
        
        .step-header {
            background: rgba(15, 23, 42, 0.8);
            padding: 20px 50px;
            text-align: center;
            color: #f1f5f9;
            font-size: 20px;
            font-weight: 600;
            letter-spacing: 1px;
            border-bottom: 1px solid #374151;
        }
        
        .main-content {
            padding: 50px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .dashboard-title {
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 15px;
            color: #ffffff;
        }
        
        .dashboard-subtitle {
            color: #ffffff;
            margin-bottom: 12px;
            font-size: 18px;
            font-weight: 400;
        }
        
        .update-info {
            color: #ffffff;
            font-size: 14px;
            margin-bottom: 50px;
            font-weight: 500;
        }
        
        .etf-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
        }
        
        .etf-card {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 16px;
            padding: 30px;
            border: 1px solid #374151;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
            position: relative;
            text-decoration: none;
            color: inherit;
            display: block;
            cursor: pointer;
        }
        
        .etf-card:hover {
            transform: translateY(-4px);
            border-color: #475569;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
        }
        
        .etf-card-wrapper {
            position: relative;
        }
        
        .etf-card.blurred {
            filter: blur(3px);
            opacity: 0.6;
            pointer-events: none;
        }
        
        .etf-card.blurred::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(2px);
            z-index: 2;
        }
        
        .free-version-overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10;
            text-align: center;
            color: white;
            font-weight: 700;
            font-size: 16px;
            background: rgba(0, 0, 0, 0.9);
            padding: 20px;
            border-radius: 15px;
            border: 2px solid #fbbf24;
            box-shadow: 0 8px 25px rgba(251, 191, 36, 0.4);
            pointer-events: none;
        }
        
        .free-version-text {
            margin-bottom: 10px;
            font-size: 14px;
        }
        
        .upgrade-text {
            color: #fbbf24;
            font-size: 18px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .etf-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, #00d4ff, #7c3aed, #ec4899);
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .etf-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 25px 50px rgba(0, 212, 255, 0.15);
            border-color: rgba(0, 212, 255, 0.3);
        }
        
        .etf-card:hover::before {
            opacity: 1;
        }
        
        .card-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 20px;
            padding: 10px;
        }
        
        .ticker-symbol {
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 1.5px;
            color: #f1f5f9;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .criteria-text {
            font-size: 11px;
            color: #ffffff;
            margin-top: 8px;
            font-weight: 500;
            opacity: 0.95;
        }
        
        .current-price {
            font-size: 32px;
            font-weight: 800;
            color: #10b981;
            text-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
            margin: 10px 0;
        }
        
        .choose-btn-text {
            background: rgba(100, 116, 139, 0.2);
            color: #ffffff;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            width: 100%;
            text-align: center;
            transition: all 0.3s ease;
            border: 1px solid #475569;
        }
        
        .etf-card:hover .choose-btn-text {
            background: rgba(37, 99, 235, 0.3);
            border-color: #1d4ed8;
            color: #1d4ed8;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .header {
                padding: 15px 25px;
                flex-direction: column;
                gap: 20px;
            }
            
            .nav-menu {
                gap: 20px;
            }
            
            .main-content {
                padding: 30px 25px;
            }
            
            .dashboard-title {
                font-size: 32px;
            }
            
            .etf-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="top-banner">
        Free Income Machine Experience Ends in... 670 DIM 428 1485
    </div>
    
    <div class="header">
        <div class="logo">
            <img src="/static/incomemachine_logo.png" alt="Income Machine" class="header-logo">
        </div>
        <div class="nav-menu">
            <a href="#" class="nav-item">How to Use</a>
            <a href="#" class="nav-item">Trade Classes</a>
            <a href="#" class="get-offer-btn">Get 50% OFF</a>
        </div>
    </div>
    
    <div class="step-header">
        Step 1: Scoreboard
    </div>
    
    <div class="main-content">
        <h1 class="dashboard-title">Top Trade Opportunities</h1>
        <p class="dashboard-subtitle">High-probability income opportunities that match our criteria.</p>
        <p class="update-info">Updated daily with fresh market analysis</p>
        
        <div class="etf-grid">
            {% set sorted_etfs = etf_scores.items() | list %}
            {% for symbol, etf in sorted_etfs %}
            {% if loop.index <= 9 %}
            <div class="etf-card-wrapper">
                <a href="/step2/{{ symbol }}" class="etf-card{% if loop.index > 3 %} blurred{% endif %}">
                    <div class="card-content">
                        <div class="ticker-symbol">{{ symbol }}</div>
                        <div class="current-price">${{ "%.2f"|format(etf.price) }}</div>
                        <div class="choose-btn-text">Choose Opportunity</div>
                        <div class="criteria-text">This ticker matches ALL 5 criteria!</div>
                    </div>
                </a>
                
                {% if loop.index > 3 %}
                <div class="free-version-overlay">
                    <div class="free-version-text">You're currently viewing the</div>
                    <div class="upgrade-text">FREE Version</div>
                </div>
                {% endif %}
            </div>
            {% endif %}
            {% endfor %}
        </div>
    </div>

    <script>
        console.log('Starting real-time ETF price updates...');
        // Frontend JavaScript kept exactly the same for compatibility
    </script>
</body>
</html>
"""
    
    return render_template_string(template, etf_scores=etf_scores)

@app.route('/step2')
@app.route('/step2/<symbol>')
def step2(symbol=None):
    """Step 2: Detailed ticker analysis page"""
    if not symbol:
        return redirect('/')
    
    # Get detailed data for the symbol from database
    ticker_data = etf_db.get_ticker_details(symbol.upper())
    
    if not ticker_data:
        return redirect('/')
    
    template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ symbol }} Analysis - Income Machine</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: white;
            min-height: 100vh;
        }
        
        .top-banner {
            background: linear-gradient(90deg, #1e3a8a, #3b82f6);
            color: white;
            text-align: center;
            padding: 8px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .header {
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(10px);
            padding: 15px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #374151;
        }
        
        .logo {
            display: flex;
            align-items: center;
        }
        
        .header-logo {
            height: 50px;
            width: auto;
            object-fit: contain;
        }
        
        .nav-menu {
            display: flex;
            align-items: center;
            gap: 30px;
        }
        
        .nav-item {
            color: #cbd5e1;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s ease;
        }
        
        .nav-item:hover {
            color: #60a5fa;
        }
        
        .get-offer-btn {
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 600;
            transition: transform 0.2s ease;
        }
        
        .get-offer-btn:hover {
            transform: translateY(-2px);
        }
        
        .step-navigation {
            display: flex;
            margin: 0 40px;
            gap: 0;
        }
        
        .step-tab {
            flex: 1;
            padding: 15px 20px;
            text-align: center;
            font-weight: 600;
            text-decoration: none;
            border: none;
            transition: all 0.3s ease;
        }
        
        .step-tab.active {
            background: linear-gradient(90deg, rgba(59, 130, 246, 0.3), rgba(37, 99, 235, 0.4));
            color: #e2e8f0;
            border-bottom: 2px solid #3b82f6;
        }
        
        .step-tab.current {
            background: linear-gradient(90deg, rgba(99, 102, 241, 0.3), rgba(79, 70, 229, 0.4));
            color: #e2e8f0;
            border-bottom: 2px solid #6366f1;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        .ticker-header {
            margin-bottom: 40px;
        }
        
        .ticker-title {
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 10px;
            color: white;
        }
        
        .ticker-subtitle {
            font-size: 16px;
            color: #94a3b8;
            margin-bottom: 20px;
        }
        
        .analysis-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-top: 40px;
        }
        
        .chart-panel {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid #374151;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            grid-column: 1 / -1;
            margin-bottom: 20px;
        }
        
        .chart-container {
            height: 400px;
            position: relative;
        }
        
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .chart-title {
            font-size: 20px;
            font-weight: 700;
            color: white;
        }
        
        .price-info {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .current-price {
            font-size: 24px;
            font-weight: 700;
            color: white;
        }
        
        .price-change {
            font-size: 16px;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: 6px;
        }
        
        .price-change.positive {
            color: #10b981;
            background: rgba(16, 185, 129, 0.1);
        }
        
        .price-change.negative {
            color: #ef4444;
            background: rgba(239, 68, 68, 0.1);
        }
        
        .loading-spinner {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 400px;
            color: #94a3b8;
        }
        
        .error-message {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 400px;
            color: #ef4444;
            text-align: center;
        }
        
        .etf-details-panel {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid #374151;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .income-potential-panel {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid #374151;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .panel-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 25px;
            color: #f1f5f9;
        }
        
        .detail-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #374151;
        }
        
        .detail-item:last-child {
            border-bottom: none;
        }
        
        .detail-label {
            color: #94a3b8;
            font-weight: 500;
        }
        
        .detail-value {
            color: white;
            font-weight: 600;
        }
        
        .score-bar {
            width: 100%;
            height: 8px;
            background: rgba(55, 65, 81, 0.5);
            border-radius: 4px;
            margin: 20px 0;
            overflow: hidden;
        }
        
        .score-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        .technical-indicators {
            margin-top: 25px;
        }
        
        .indicators-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #f1f5f9;
        }
        
        .indicator-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
        }
        
        .indicator-name {
            color: #cbd5e1;
            font-weight: 500;
        }
        
        .indicator-status {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 16px;
        }
        
        .status-pass {
            background: #3b82f6;
            color: white;
        }
        
        .status-fail {
            background: #6b7280;
            color: white;
        }
        
        .score-summary {
            color: #e2e8f0;
            margin-bottom: 15px;
            line-height: 1.6;
        }
        
        .score-explanation {
            color: #94a3b8;
            margin-bottom: 15px;
            line-height: 1.5;
            font-size: 14px;
        }
        
        .data-refresh {
            color: #64748b;
            margin-bottom: 25px;
            font-size: 13px;
        }
        
        .strategy-button-container {
            margin-top: 20px;
        }
        
        .choose-strategy-btn {
            background: linear-gradient(90deg, #7c3aed, #a855f7);
            color: white;
            padding: 15px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            display: inline-block;
            width: 100%;
            text-align: center;
            transition: transform 0.2s ease;
        }
        
        .choose-strategy-btn:hover {
            transform: translateY(-2px);
        }
        
        .back-to-scoreboard {
            margin-top: 40px;
            text-align: center;
        }
        
        .back-scoreboard-btn {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid #3b82f6;
            color: #60a5fa;
            padding: 12px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .back-scoreboard-btn:hover {
            background: rgba(59, 130, 246, 0.2);
            transform: translateY(-1px);
        }
        
        @media (max-width: 768px) {
            .analysis-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
            
            .container {
                padding: 20px 10px;
            }
            
            .ticker-title {
                font-size: 36px;
            }
            
            .ticker-price {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="top-banner">
        Free Income Machine Experience Ends in... 670 DIM 428 1485
    </div>
    
    <div class="header">
        <div class="logo">
            <img src="/static/incomemachine_logo.png" alt="Income Machine" class="header-logo">
        </div>
        <div class="nav-menu">
            <a href="#" class="nav-item">How to Use</a>
            <a href="#" class="nav-item">Trade Classes</a>
            <a href="#" class="get-offer-btn">Get 50% OFF</a>
        </div>
    </div>
    
    <div class="step-navigation">
        <a href="/" class="step-tab active">Step 1: Scoreboard</a>
        <div class="step-tab current">Step 2: Asset Review</div>
    </div>
    
    <div class="container">
        <div class="ticker-header">
            <div class="ticker-title">{{ symbol }} - Stock Analysis</div>
            <div class="ticker-subtitle">Review the selected stock details before choosing an income strategy.</div>
        </div>
        
        <div class="analysis-grid">
            <div class="etf-details-panel">
                <div class="panel-title">Stock Details</div>
                <div class="detail-item">
                    <span class="detail-label">Symbol:</span>
                    <span class="detail-value">{{ symbol }}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Current Price:</span>
                    <span class="detail-value">${{ "%.2f"|format(ticker_data.current_price) }}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Score:</span>
                    <span class="detail-value">{{ ticker_data.total_score }}/5</span>
                </div>
                <div class="score-bar">
                    <div class="score-fill" style="width: {{ (ticker_data.total_score / 5 * 100) }}%"></div>
                </div>
                
                <div class="technical-indicators">
                    <div class="indicators-title">Technical Indicators:</div>
                
                    <div class="indicator-item">
                        <div class="indicator-name">Short Term Trend</div>
                        <div class="indicator-status {{ 'status-pass' if ticker_data.trend1_pass else 'status-fail' }}">
                            {{ '✓' if ticker_data.trend1_pass else '✗' }}
                        </div>
                    </div>
                    
                    <div class="indicator-item">
                        <div class="indicator-name">Long Term Trend</div>
                        <div class="indicator-status {{ 'status-pass' if ticker_data.trend2_pass else 'status-fail' }}">
                            {{ '✓' if ticker_data.trend2_pass else '✗' }}
                        </div>
                    </div>
                    
                    <div class="indicator-item">
                        <div class="indicator-name">Snapback Position</div>
                        <div class="indicator-status {{ 'status-pass' if ticker_data.snapback_pass else 'status-fail' }}">
                            {{ '✓' if ticker_data.snapback_pass else '✗' }}
                        </div>
                    </div>
                    
                    <div class="indicator-item">
                        <div class="indicator-name">Weekly Momentum</div>
                        <div class="indicator-status {{ 'status-pass' if ticker_data.momentum_pass else 'status-fail' }}">
                            {{ '✓' if ticker_data.momentum_pass else '✗' }}
                        </div>
                    </div>
                    
                    <div class="indicator-item">
                        <div class="indicator-name">Stabilizing</div>
                        <div class="indicator-status {{ 'status-pass' if ticker_data.stabilizing_pass else 'status-fail' }}">
                            {{ '✓' if ticker_data.stabilizing_pass else '✗' }}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="income-potential-panel">
                <div class="panel-title">Income Potential</div>
                <div class="score-summary">
                    Based on the current score of <strong>{{ ticker_data.total_score }}/5</strong>, {{ symbol }} could be a strong candidate for generating options income.
                </div>
                <div class="score-explanation">
                    The score is calculated using 5 technical indicators, with 1 point awarded for each condition met. Higher scores indicate more favorable market conditions for income opportunities.
                </div>
                <div class="data-refresh">
                    Data is automatically refreshed every 15 minutes during market hours.
                </div>
                <div class="strategy-button-container">
                    <a href="/step3/{{ symbol }}" class="choose-strategy-btn">Choose Income Strategy →</a>
                </div>
            </div>
        </div>
        
        <!-- Price Chart Panel -->
        <div class="chart-panel">
            <div class="chart-header">
                <div class="chart-title">{{ symbol }} - 30 Day Price Chart</div>
                <div class="price-info">
                    <div class="current-price" id="currentPrice">Loading...</div>
                    <div class="price-change" id="priceChange">Loading...</div>
                </div>
            </div>
            <div class="chart-container">
                <div class="loading-spinner" id="loadingSpinner">Loading chart data...</div>
                <div class="error-message" id="errorMessage" style="display: none;"></div>
                <canvas id="priceChart" style="display: none;"></canvas>
            </div>
        </div>
        
        <div class="back-to-scoreboard">
            <a href="/" class="back-scoreboard-btn">← Back to Scoreboard</a>
        </div>
        </div>
    </div>
    
    <script>
        let priceChart = null;
        
        // Load chart data on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadChartData('{{ symbol }}');
        });
        
        async function loadChartData(symbol) {
            const loadingSpinner = document.getElementById('loadingSpinner');
            const errorMessage = document.getElementById('errorMessage');
            const chartCanvas = document.getElementById('priceChart');
            const currentPrice = document.getElementById('currentPrice');
            const priceChange = document.getElementById('priceChange');
            
            try {
                const response = await fetch(`/api/chart_data/${symbol}`);
                const data = await response.json();
                
                if (!data.success) {
                    throw new Error(data.error || 'Failed to load chart data');
                }
                
                // Hide loading spinner and show chart
                loadingSpinner.style.display = 'none';
                chartCanvas.style.display = 'block';
                
                // Update price info
                currentPrice.textContent = `$${data.current_price.toFixed(2)}`;
                
                const changeText = `${data.price_change >= 0 ? '+' : ''}${data.price_change.toFixed(2)} (${data.price_change_pct.toFixed(2)}%)`;
                priceChange.textContent = changeText;
                priceChange.className = `price-change ${data.price_change >= 0 ? 'positive' : 'negative'}`;
                
                // Create chart
                createPriceChart(data.chart_data);
                
            } catch (error) {
                console.error('Error loading chart data:', error);
                loadingSpinner.style.display = 'none';
                errorMessage.style.display = 'flex';
                errorMessage.textContent = `Unable to load chart data: ${error.message}`;
            }
        }
        
        function createPriceChart(chartData) {
            const ctx = document.getElementById('priceChart').getContext('2d');
            
            // Prepare data for Chart.js
            const labels = chartData.map(item => item.date);
            const prices = chartData.map(item => item.close);
            
            // Destroy existing chart if it exists
            if (priceChart) {
                priceChart.destroy();
            }
            
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Close Price',
                        data: prices,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                            titleColor: '#f1f5f9',
                            bodyColor: '#e2e8f0',
                            borderColor: '#374151',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    return `Price: $${context.parsed.y.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: '#374151',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#94a3b8',
                                maxTicksLimit: 8
                            }
                        },
                        y: {
                            grid: {
                                color: '#374151',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#94a3b8',
                                callback: function(value) {
                                    return '$' + value.toFixed(2);
                                }
                            }
                        }
                    }
                }
            });
        }
        
        console.log('Step 2 loaded for {{ symbol }}');
    </script>
</body>
</html>
"""
    
    return render_template_string(template, symbol=symbol, ticker_data=ticker_data)

@app.route('/step3')
@app.route('/step3/<symbol>')
def step3(symbol=None):
    """Step 3: Income Strategy Selection"""
    # Get current price from database
    current_price = None
    etf_data = etf_db.get_all_etfs()
    for etf in etf_data.get('etfs', []):
        if etf['symbol'] == symbol:
            current_price = etf['current_price']
            break
    
    if not current_price:
        current_price = 100.0  # Fallback if not found
    
    # Fetch real options data from Polygon API
    options_data = fetch_options_data(symbol, current_price)
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Step 3: Income Strategy Selection - Income Machine</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: #1a202c;
            color: #ffffff;
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .top-banner {
            background: rgba(0, 12, 12, 0.8);
            text-align: center;
            padding: 8px;
            font-size: 14px;
            color: #ffffff;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            background: rgba(255, 255, 255, 0.02);
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .header-logo {
            height: 32px;
            width: auto;
        }
        
        .nav-menu {
            display: flex;
            align-items: center;
            gap: 30px;
        }
        
        .nav-item {
            color: rgba(255, 255, 255, 0.8);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s ease;
        }
        
        .nav-item:hover {
            color: #ffffff;
        }
        
        .get-offer-btn {
            background: #ffffff;
            color: #1e40af;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .get-offer-btn:hover {
            background: #f8fafc;
            transform: translateY(-1px);
        }
        
        .step-navigation {
            display: flex;
            margin: 0 40px;
            gap: 0;
        }
        
        .step-tab {
            flex: 1;
            padding: 15px 20px;
            text-align: center;
            font-weight: 600;
            text-decoration: none;
            border: none;
            transition: all 0.3s ease;
        }
        
        .step-tab.active {
            background: linear-gradient(90deg, rgba(59, 130, 246, 0.3), rgba(37, 99, 235, 0.4));
            color: #e2e8f0;
            border-bottom: 2px solid #3b82f6;
        }
        
        .step-tab.current {
            background: linear-gradient(90deg, rgba(99, 102, 241, 0.3), rgba(79, 70, 229, 0.4));
            color: #e2e8f0;
            border-bottom: 2px solid #6366f1;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        .ticker-header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .ticker-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 16px;
            color: #ffffff;
        }
        
        .ticker-subtitle {
            font-size: 1.1rem;
            color: rgba(255, 255, 255, 0.8);
            max-width: 600px;
            margin: 0 auto;
        }
        
        .strategies-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .strategy-card {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 16px;
            padding: 30px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .strategy-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(124, 58, 237, 0.05));
            opacity: 0;
            transition: opacity 0.3s ease;
            border-radius: 16px;
        }
        
        .strategy-card:hover::before {
            opacity: 1;
        }
        
        .strategy-card:hover {
            background: rgba(30, 41, 59, 0.9);
            border-color: rgba(139, 92, 246, 0.5);
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(139, 92, 246, 0.2);
        }
        
        .strategy-header {
            margin-bottom: 20px;
        }
        
        .strategy-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 8px;
        }
        
        .strategy-subtitle {
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.9rem;
        }
        
        .strategy-returns {
            background: rgba(34, 197, 94, 0.2);
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .returns-label {
            font-size: 0.8rem;
            color: rgba(255, 255, 255, 0.7);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        
        .returns-value {
            font-size: 1.4rem;
            font-weight: 700;
            color: #22c55e;
        }
        
        .strategy-details {
            margin-bottom: 24px;
        }
        
        .detail-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .detail-row:last-child {
            border-bottom: none;
        }
        
        .detail-label {
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.9rem;
        }
        
        .detail-value {
            color: #ffffff;
            font-weight: 500;
            font-size: 0.9rem;
        }
        
        .risk-high {
            color: #ef4444;
        }
        
        .risk-medium {
            color: #f59e0b;
        }
        
        .risk-low {
            color: #22c55e;
        }
        
        .strategy-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            color: white;
            border: 1px solid rgba(139, 92, 246, 0.5);
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            backdrop-filter: blur(10px);
            position: relative;
            z-index: 1;
        }
        
        .strategy-btn:hover {
            background: linear-gradient(135deg, #7c3aed, #6d28d9);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(139, 92, 246, 0.3);
        }
        
        .strategy-error {
            background: rgba(220, 38, 38, 0.2);
            border: 1px solid rgba(220, 38, 38, 0.4);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .error-message {
            color: #ef4444;
            font-size: 0.9rem;
            font-weight: 500;
        }
        
        .back-to-scoreboard {
            margin-top: 40px;
            text-align: center;
        }
        
        .back-scoreboard-btn {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: rgba(255, 255, 255, 0.9);
            padding: 12px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .back-scoreboard-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }
        
        @media (max-width: 768px) {
            .strategies-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
            
            .container {
                padding: 20px 10px;
            }
            
            .ticker-title {
                font-size: 2rem;
            }
            
            .strategy-card {
                padding: 20px;
            }
            
            .header {
                padding: 15px 20px;
                flex-direction: column;
                gap: 15px;
            }
            
            .nav-menu {
                gap: 20px;
            }
        }
        </style>
    </head>
    <body>
        <div class="top-banner">
            Free Income Machine Experience Ends in... 670 DIM 428 1485
        </div>
        
        <div class="header">
            <div class="logo">
                <img src="/static/incomemachine_logo.png" alt="Income Machine" class="header-logo">
            </div>
            <div class="nav-menu">
                <a href="#" class="nav-item">How to Use</a>
                <a href="#" class="nav-item">Trade Classes</a>
                <a href="#" class="get-offer-btn">Get 50% OFF</a>
            </div>
        </div>
        
        <div class="step-navigation">
            <a href="/" class="step-tab active">Step 1: Scoreboard</a>
            <a href="{% if symbol %}/step2/{{ symbol }}{% else %}#{% endif %}" class="step-tab current">Step 2: Asset Review</a>
            <div class="step-tab active">Step 3: Strategy</div>
        </div>
        
        <div class="container">
            <div class="ticker-header">
                <div class="ticker-title">{{ symbol or 'STOCK' }} - Income Strategy Selection</div>
                <div class="ticker-subtitle">Choose the income strategy that matches your risk tolerance and investment goals.</div>
            </div>
            
            <div class="strategies-grid">
                <div class="strategy-card">
                    <div class="strategy-header">
                        <h3 class="strategy-title">Passive Income</h3>
                        <p class="strategy-subtitle">{{ symbol }} Passive Income Strategy</p>
                    </div>
                    
                    {% if options_data.passive.error %}
                    <div class="strategy-error">
                        <div class="error-message">{{ options_data.passive.error }}</div>
                    </div>
                    {% else %}
                    <div class="strategy-details">
                        <div class="detail-row">
                            <span class="detail-label">DTE:</span>
                            <span class="detail-value">{{ options_data.passive.dte_range }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Target ROI:</span>
                            <span class="detail-value">{{ options_data.passive.roi_range }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Strike Selection:</span>
                            <span class="detail-value">{{ options_data.passive.strike_selection }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Management:</span>
                            <span class="detail-value">{{ options_data.passive.management }}</span>
                        </div>
                    </div>
                    {% endif %}
                    
                    <a href="/step4/{{ symbol }}/passive/{{ options_data.passive.contract_symbol if not options_data.passive.error else 'none' }}" class="strategy-btn">Select Passive Strategy</a>
                </div>
                
                <div class="strategy-card">
                    <div class="strategy-header">
                        <h3 class="strategy-title">Steady Income</h3>
                        <p class="strategy-subtitle">{{ symbol }} Steady Income Strategy</p>
                    </div>
                    
                    {% if options_data.steady.error %}
                    <div class="strategy-error">
                        <div class="error-message">{{ options_data.steady.error }}</div>
                    </div>
                    {% else %}
                    <div class="strategy-details">
                        <div class="detail-row">
                            <span class="detail-label">DTE:</span>
                            <span class="detail-value">{{ options_data.steady.dte }} days</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Target ROI:</span>
                            <span class="detail-value">{{ options_data.steady.roi }}%</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Strike Price:</span>
                            <span class="detail-value">${{ "%.2f"|format(options_data.steady.strike_price) }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Expiration:</span>
                            <span class="detail-value">{{ options_data.steady.expiration_date }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Contract ID:</span>
                            <span class="detail-value">{{ options_data.steady.contract_symbol }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Management:</span>
                            <span class="detail-value">{{ options_data.steady.management }}</span>
                        </div>
                    </div>
                    {% endif %}
                    
                    <a href="/step4/{{ symbol }}/steady/{{ options_data.steady.contract_symbol if not options_data.steady.error else 'none' }}" class="strategy-btn">Select Steady Strategy</a>
                </div>
                
                <div class="strategy-card">
                    <div class="strategy-header">
                        <h3 class="strategy-title">Aggressive Income</h3>
                        <p class="strategy-subtitle">{{ symbol }} Aggressive Income Strategy</p>
                    </div>
                    
                    {% if options_data.aggressive.error %}
                    <div class="strategy-error">
                        <div class="error-message">{{ options_data.aggressive.error }}</div>
                    </div>
                    {% else %}
                    <div class="strategy-details">
                        <div class="detail-row">
                            <span class="detail-label">DTE:</span>
                            <span class="detail-value">{{ options_data.aggressive.dte_range }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Target ROI:</span>
                            <span class="detail-value">{{ options_data.aggressive.roi_range }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Strike Selection:</span>
                            <span class="detail-value">{{ options_data.aggressive.strike_selection }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Management:</span>
                            <span class="detail-value">{{ options_data.aggressive.management }}</span>
                        </div>
                    </div>
                    {% endif %}
                    
                    <a href="/step4/{{ symbol }}/aggressive/{{ options_data.aggressive.contract_symbol if not options_data.aggressive.error else 'none' }}" class="strategy-btn">Select Aggressive Strategy</a>
                </div>
            </div>
            
            <div class="back-to-scoreboard">
                <a href="{% if symbol %}/step2/{{ symbol }}{% else %}/{% endif %}" class="back-scoreboard-btn">← Back to Analysis</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, symbol=symbol, options_data=options_data, current_price=current_price)

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    """CSV upload endpoint that updates the database with ETF scoring data from uploaded CSV
    
    Accepts:
    - File upload via 'csvfile' form field
    - Raw CSV text via 'csv_text' form field
    
    Returns:
    - Success/error response
    """
    try:
        csv_content = None
        
        # Check if file was uploaded
        if 'csvfile' in request.files:
            file = request.files['csvfile']
            if file and file.filename:
                csv_content = file.read().decode('utf-8')
        
        # Check if raw CSV text was provided
        if not csv_content and 'csv_text' in request.form:
            csv_content = request.form['csv_text']
        
        if not csv_content:
            return jsonify({'error': 'No CSV content provided'}), 400
        
        # Upload to database
        db = ETFDatabase()
        db.upload_csv_data(csv_content)
        
        # Reload ETF data from database
        load_etf_data_from_database()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully uploaded CSV data. Loaded {len(etf_scores)} symbols.'
        })
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/etf_data')
def api_etf_data():
    """API endpoint to get the latest ETF data for real-time updates in the UI
    
    Returns:
        JSON: Current ETF data including prices and scores
    """
    return jsonify(etf_scores)

@app.route('/api/chart_data/<symbol>')
def api_chart_data(symbol):
    """API endpoint to get chart data for a specific symbol using Polygon API
    
    Returns:
        JSON: Chart data with timestamps and prices
    """
    try:
        import os
        from datetime import datetime, timedelta
        import requests
        
        api_key = os.environ.get('POLYGON_API_KEY')
        if not api_key:
            return jsonify({'error': 'POLYGON_API_KEY not configured'}), 500
        
        # Get 30 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        url = f'https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime("%Y-%m-%d")}/{end_date.strftime("%Y-%m-%d")}'
        
        response = requests.get(url, params={'apikey': api_key})
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                chart_data = []
                for result in data['results']:
                    chart_data.append({
                        'timestamp': result['t'],
                        'price': result['c'],  # closing price
                        'volume': result['v']
                    })
                
                return jsonify({
                    'symbol': symbol,
                    'data': chart_data,
                    'current_price': chart_data[-1]['price'] if chart_data else None,
                    'status': 'success'
                })
            elif data.get('status') == 'DELAYED':
                # Handle delayed data - still return what we have
                chart_data = []
                if data.get('results'):
                    for result in data['results']:
                        chart_data.append({
                            'timestamp': result['t'],
                            'price': result['c'],
                            'volume': result['v']
                        })
                
                return jsonify({
                    'symbol': symbol,
                    'data': chart_data,
                    'current_price': chart_data[-1]['price'] if chart_data else None,
                    'status': 'delayed',
                    'message': 'Market data is delayed'
                })
            else:
                return jsonify({'error': f'No data available for {symbol}'}), 404
        else:
            return jsonify({'error': f'API request failed: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to fetch chart data: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
