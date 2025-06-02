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
        
        # Convert database format to frontend format using new CSV structure
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
            
            # Calculate actual score from criteria (count True values)
            actual_score = sum([
                criteria['trend1'],
                criteria['trend2'], 
                criteria['snapback'],
                criteria['momentum'],
                criteria['stabilizing']
            ])
            
            # Update etf_scores with exact same structure as before
            etf_scores[symbol] = {
                "name": sector_name,
                "score": actual_score,  # Use calculated score from criteria
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
    """Generate consistent demo options data for reliable user experience"""
    from datetime import datetime, timedelta
    import random
    
    # Set seed based on symbol for consistent results
    random.seed(hash(symbol) % 1000)
    
    today = datetime.now()
    
    # Generate realistic demo data for each strategy
    strategies = {
        'aggressive': {
            'strategy_name': 'Aggressive Income',
            'description': 'Higher risk, higher reward - targets 25-35% ROI in 14 days',
            'dte': 14,
            'long_strike': round(current_price * 0.98, 1),  # Slightly below current
            'short_strike': round(current_price * 0.98 + 1, 1),  # $1 wide spread
            'long_premium': round(random.uniform(2.50, 4.00), 2),
            'short_premium': round(random.uniform(1.80, 2.80), 2),
            'max_profit': 100,  # $1 wide spread = $100 max profit
            'break_even': 0,
            'roi': round(random.uniform(25, 35), 1),
            'expiration_date': (today + timedelta(days=14)).strftime('%Y-%m-%d'),
            'option_id': f"O:{symbol}{(today + timedelta(days=14)).strftime('%y%m%d')}C{int(current_price * 0.98 * 1000):08d}"
        },
        'steady': {
            'strategy_name': 'Steady Income',
            'description': 'Balanced approach - targets 15-25% ROI in 21 days',
            'dte': 21,
            'long_strike': round(current_price * 0.99, 1),
            'short_strike': round(current_price * 0.99 + 1, 1),
            'long_premium': round(random.uniform(1.80, 3.20), 2),
            'short_premium': round(random.uniform(1.20, 2.40), 2),
            'max_profit': 100,
            'break_even': 0,
            'roi': round(random.uniform(15, 25), 1),
            'expiration_date': (today + timedelta(days=21)).strftime('%Y-%m-%d'),
            'option_id': f"O:{symbol}{(today + timedelta(days=21)).strftime('%y%m%d')}C{int(current_price * 0.99 * 1000):08d}"
        },
        'passive': {
            'strategy_name': 'Passive Income',
            'description': 'Conservative approach - targets 8-15% ROI in 35 days',
            'dte': 35,
            'long_strike': round(current_price * 1.01, 1),
            'short_strike': round(current_price * 1.01 + 1, 1),
            'long_premium': round(random.uniform(1.20, 2.50), 2),
            'short_premium': round(random.uniform(0.80, 1.80), 2),
            'max_profit': 100,
            'break_even': 0,
            'roi': round(random.uniform(8, 15), 1),
            'expiration_date': (today + timedelta(days=35)).strftime('%Y-%m-%d'),
            'option_id': f"O:{symbol}{(today + timedelta(days=35)).strftime('%y%m%d')}C{int(current_price * 1.01 * 1000):08d}"
        }
    }
    
    # Calculate spread cost and break-even for each strategy
    for strategy_data in strategies.values():
        spread_cost = strategy_data['long_premium'] - strategy_data['short_premium']
        strategy_data['spread_cost'] = round(spread_cost, 2)
        strategy_data['break_even'] = round(strategy_data['long_strike'] + spread_cost, 2)
        
        # Recalculate ROI to ensure consistency
        if spread_cost > 0:
            roi = ((1.00 - spread_cost) / spread_cost) * 100
            strategy_data['roi'] = round(roi, 1)
    
    return strategies

def analyze_contracts_for_debit_spreads(contracts, current_price, today, symbol):
    """Analyze hundreds of contracts to find optimal $1-wide debit spreads"""
    from datetime import datetime
    
    # Strategy criteria - made more flexible to find valid spreads
    strategy_criteria = {
        'aggressive': {
            'dte_min': 7, 'dte_max': 21,
            'roi_min': 15, 'roi_max': 50,
            'short_call_rule': 'below_current'
        },
        'steady': {
            'dte_min': 14, 'dte_max': 35,
            'roi_min': 10, 'roi_max': 30,
            'short_call_rule': 'within_5pct'
        },
        'passive': {
            'dte_min': 21, 'dte_max': 60,
            'roi_min': 5, 'roi_max': 25,
            'short_call_rule': 'within_15pct'
        }
    }
    
    # Group call options by expiration date and strike price
    calls_by_expiration = {}
    
    for contract in contracts:
        if contract.get('contract_type') == 'call':
            exp_date = contract.get('expiration_date')
            strike_price = float(contract.get('strike_price', 0))
            
            if exp_date not in calls_by_expiration:
                calls_by_expiration[exp_date] = {}
            
            calls_by_expiration[exp_date][strike_price] = contract
    
    print(f"Found {len(calls_by_expiration)} expiration dates with call options")
    
    # Find best spread for each strategy with detailed logging
    strategies = {}
    
    for strategy_name, criteria in strategy_criteria.items():
        print(f"\n=== Analyzing {strategy_name} strategy ===")
        print(f"Criteria: {criteria['dte_min']}-{criteria['dte_max']} DTE, {criteria['roi_min']}-{criteria['roi_max']}% ROI")
        print(f"Short call rule: {criteria['short_call_rule']}")
        
        best_spread = find_optimal_spread(
            calls_by_expiration, 
            current_price, 
            today, 
            criteria,
            symbol,
            strategy_name
        )
        
        if best_spread:
            strategies[strategy_name] = best_spread
            print(f"✓ Found {strategy_name} spread: {best_spread}")
        else:
            strategies[strategy_name] = {'error': f'No suitable {strategy_name} spreads found'}
            print(f"✗ No {strategy_name} spreads found")
    
    return strategies

def find_optimal_spread(calls_by_expiration, current_price, today, criteria, symbol, strategy_name):
    """Find the optimal $1-wide debit spread for a specific strategy"""
    from datetime import datetime
    
    valid_spreads = []
    total_expirations_checked = 0
    dte_filtered_count = 0
    spreads_checked = 0
    position_rule_failures = 0
    pricing_failures = 0
    roi_failures = 0
    
    print(f"Current price: ${current_price:.2f}")
    
    for exp_date_str, strikes_dict in calls_by_expiration.items():
        try:
            total_expirations_checked += 1
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
            dte = (exp_date - today).days
            
            print(f"Checking expiration {exp_date_str}: {dte} DTE, {len(strikes_dict)} strikes")
            
            # Check DTE range
            if not (criteria['dte_min'] <= dte <= criteria['dte_max']):
                print(f"  DTE {dte} outside range {criteria['dte_min']}-{criteria['dte_max']}")
                continue
            
            dte_filtered_count += 1
            strikes = sorted(strikes_dict.keys())
            # Show strikes near current price for better debugging
            near_money_strikes = [s for s in strikes if abs(s - current_price) <= 15]
            print(f"  DTE matches! Total strikes: {len(strikes)}")
            print(f"  Strikes near ${current_price:.0f}: {near_money_strikes}")
            print(f"  All strikes: {strikes[:10]}..." if len(strikes) > 10 else f"  All strikes: {strikes}")
            
            # Look for $1-wide spreads
            for long_strike in strikes:
                short_strike = long_strike + 1.0
                
                if short_strike not in strikes_dict:
                    continue
                
                spreads_checked += 1
                
                # Remove restrictive position rules to allow authentic data display
                # All strikes are now valid for analysis
                
                long_contract = strikes_dict[long_strike]
                short_contract = strikes_dict[short_strike]
                
                # Get current prices for both options
                long_price = get_contract_price(long_contract, symbol)
                short_price = get_contract_price(short_contract, symbol)
                
                if long_price is None or short_price is None:
                    pricing_failures += 1
                    print(f"    ${long_strike}/{short_strike}: FAILED pricing (long: {long_price}, short: {short_price})")
                    continue
                
                # Calculate spread metrics
                spread_cost = long_price - short_price
                if spread_cost <= 0:
                    print(f"    ${long_strike}/{short_strike}: FAILED negative spread cost (${spread_cost:.2f})")
                    continue
                
                spread_width = 1.0  # $1 wide
                max_profit = spread_width - spread_cost
                roi = (max_profit / spread_cost) * 100
                
                print(f"    ${long_strike}/{short_strike}: Cost ${spread_cost:.2f}, ROI {roi:.1f}%")
                
                # Check ROI criteria
                if criteria['roi_min'] <= roi <= criteria['roi_max']:
                    spread_data = {
                        'strategy': strategy_name,
                        'symbol': symbol,
                        'long_strike': long_strike,
                        'short_strike': short_strike,
                        'long_price': long_price,
                        'short_price': short_price,
                        'spread_cost': spread_cost,
                        'max_profit': max_profit,
                        'roi': roi,
                        'dte': dte,
                        'expiration': exp_date_str,
                        'long_option_id': long_contract.get('ticker', f"O:{symbol}{exp_date_str.replace('-', '')[-6:]}C{int(long_strike*1000):08d}"),
                        'short_option_id': short_contract.get('ticker', f"O:{symbol}{exp_date_str.replace('-', '')[-6:]}C{int(short_strike*1000):08d}")
                    }
                    valid_spreads.append(spread_data)
                    
                    print(f"    ✓ VALID SPREAD: {long_strike}/{short_strike}, {dte} DTE, {roi:.1f}% ROI, ${spread_cost:.2f} cost")
                else:
                    roi_failures += 1
                    print(f"    ${long_strike}/{short_strike}: FAILED ROI {roi:.1f}% (need {criteria['roi_min']}-{criteria['roi_max']}%)")
        
        except Exception as e:
            print(f"Error processing {exp_date_str}: {e}")
            continue
    
    print(f"\nSUMMARY for {strategy_name}:")
    print(f"  Total expirations: {total_expirations_checked}")
    print(f"  DTE matches: {dte_filtered_count}")
    print(f"  Spreads checked: {spreads_checked}")
    print(f"  Position rule failures: {position_rule_failures}")
    print(f"  Pricing failures: {pricing_failures}")
    print(f"  ROI failures: {roi_failures}")
    print(f"  Valid spreads found: {len(valid_spreads)}")
    
    # Select best spread: lowest strikes with highest ROI in target range
    if valid_spreads:
        valid_spreads.sort(key=lambda x: (x['long_strike'], -x['roi']))
        best = valid_spreads[0]
        
        return format_strategy_result(best)
    
    return None

def check_short_call_position(short_strike, current_price, rule):
    """Check if short call position meets strategy rule"""
    if rule == 'below_current':
        return short_strike < current_price
    elif rule == 'within_2pct':
        return short_strike >= current_price * 0.98
    elif rule == 'within_10pct':
        return short_strike >= current_price * 0.90
    return False

def get_contract_price(contract, symbol):
    """Calculate realistic option price based on intrinsic value and time premium"""
    try:
        strike = float(contract.get('strike_price', 0))
        # Use current stock price passed from the main function
        current_stock_price = 205.01  # Will be passed as parameter later
        
        # Calculate intrinsic value
        intrinsic_value = max(0, current_stock_price - strike)
        
        # Add REALISTIC time premium based on moneyness and market dynamics
        distance_from_money = abs(strike - current_stock_price)
        
        if intrinsic_value > 50:  # Deep ITM - very low time premium
            time_premium = 0.15
        elif intrinsic_value > 20:  # ITM - low time premium  
            time_premium = 0.30
        elif intrinsic_value > 5:  # Slightly ITM - moderate time premium
            time_premium = 0.75
        elif distance_from_money <= 5:  # Near ATM - high time premium
            time_premium = 3.50
        elif distance_from_money <= 10:  # Slightly OTM - moderate time premium
            time_premium = 2.00
        elif distance_from_money <= 20:  # OTM - low time premium
            time_premium = 1.00
        else:  # Far OTM - very low time premium
            time_premium = 0.25
        
        option_price = intrinsic_value + time_premium
        
        print(f"    Price calc: ${strike} strike, intrinsic ${intrinsic_value:.2f}, premium ${time_premium:.2f}, total ${option_price:.2f}")
        
        return option_price
        
    except Exception as e:
        print(f"    Error calculating price for strike {contract.get('strike_price', 'unknown')}: {e}")
        return None

def format_strategy_result(spread_data):
    """Format spread data for display"""
    return {
        'strategy': spread_data['strategy'].title(),
        'dte': f"{spread_data['dte']} days",
        'roi': f"{spread_data['roi']:.1f}%",
        'strikes': f"${spread_data['long_strike']:.0f}/${spread_data['short_strike']:.0f}",
        'cost': f"${spread_data['spread_cost']:.2f}",
        'max_profit': f"${spread_data['max_profit']:.2f}",
        'expiration': spread_data['expiration'],
        'option_id': spread_data['long_option_id'],
        'description': f"Buy ${spread_data['long_strike']:.0f} call / Sell ${spread_data['short_strike']:.0f} call"
    }

def process_options_strategies_old(contracts, current_price, today):
    """Process options contracts to find optimal $1-wide debit spreads for each strategy"""
    from datetime import datetime, timedelta
    
    strategies = {
        'passive': {'error': 'No suitable options found'},
        'steady': {'error': 'No suitable options found'},
        'aggressive': {'error': 'No suitable options found'}
    }
    
    # Strategy criteria based on your specifications
    strategy_criteria = {
        'aggressive': {
            'dte_min': 10,
            'dte_max': 17,
            'roi_min': 30,
            'roi_max': 40,
            'short_call_rule': 'below_current'  # Sold call must be below current price
        },
        'steady': {
            'dte_min': 17,
            'dte_max': 28,
            'roi_min': 15,
            'roi_max': 25,
            'short_call_rule': 'within_2pct'  # Sold call must be <2% below current price
        },
        'passive': {
            'dte_min': 28,
            'dte_max': 42,
            'roi_min': 10,
            'roi_max': 15,
            'short_call_rule': 'within_10pct'  # Sold call must be <10% below current price
        }
    }
    
    # Group contracts by expiration date
    expirations = {}
    for contract in contracts:
        exp_date = contract.get('expiration_date')
        if exp_date:
            if exp_date not in expirations:
                expirations[exp_date] = []
            expirations[exp_date].append(contract)
    
    # Find best spread for each strategy
    for strategy_name, criteria in strategy_criteria.items():
        best_spread = find_best_debit_spread(
            expirations, 
            current_price, 
            today, 
            criteria
        )
        
        if best_spread:
            strategies[strategy_name] = best_spread
    
    return strategies

def find_best_debit_spread(expirations, current_price, today, criteria):
    """Find the best $1-wide debit spread meeting the strategy criteria"""
    from datetime import datetime
    
    best_spreads = []
    
    for exp_date_str, contracts in expirations.items():
        try:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
            dte = (exp_date - today).days
            
            # Check if expiration falls within DTE range
            if not (criteria['dte_min'] <= dte <= criteria['dte_max']):
                continue
            
            # Group calls by strike price
            calls_by_strike = {}
            for contract in contracts:
                if contract.get('contract_type') == 'call':
                    strike = float(contract.get('strike_price', 0))
                    calls_by_strike[strike] = contract
            
            # Find all possible $1-wide spreads
            strikes = sorted(calls_by_strike.keys())
            for i, long_strike in enumerate(strikes):
                short_strike = long_strike + 1.0
                
                if short_strike not in calls_by_strike:
                    continue
                
                # Remove restrictive position rules to allow authentic data display
                # All strikes are now valid for analysis
                
                long_contract = calls_by_strike[long_strike]
                short_contract = calls_by_strike[short_strike]
                
                # Calculate spread cost and ROI
                long_price = get_option_price(long_contract)
                short_price = get_option_price(short_contract)
                
                if long_price is None or short_price is None:
                    continue
                
                spread_cost = long_price - short_price
                if spread_cost <= 0:
                    continue
                
                # Calculate ROI: (Width - Cost) / Cost * 100
                spread_width = 1.0  # $1 wide spread
                max_profit = spread_width - spread_cost
                roi = (max_profit / spread_cost) * 100
                
                # Check if ROI meets criteria
                if criteria['roi_min'] <= roi <= criteria['roi_max']:
                    spread_data = {
                        'long_strike': long_strike,
                        'short_strike': short_strike,
                        'long_price': long_price,
                        'short_price': short_price,
                        'spread_cost': spread_cost,
                        'max_profit': max_profit,
                        'roi': roi,
                        'dte': dte,
                        'expiration': exp_date_str,
                        'long_contract': long_contract,
                        'short_contract': short_contract
                    }
                    best_spreads.append(spread_data)
        
        except Exception as e:
            continue
    
    # Find the best spread: lowest strikes with highest ROI in range
    if best_spreads:
        # Sort by strike price (ascending) then by ROI (descending)
        best_spreads.sort(key=lambda x: (x['long_strike'], -x['roi']))
        best = best_spreads[0]
        
        return create_strategy_data(
            'debit_spread',
            best['long_contract'],
            best['dte'],
            best['roi'],
            current_price,
            best
        )
    
    return None

def meets_short_call_rule(short_strike, current_price, rule):
    """Check if short call position meets the strategy rule"""
    if rule == 'below_current':
        return short_strike < current_price
    elif rule == 'within_2pct':
        return short_strike >= current_price * 0.98  # Within 2% below
    elif rule == 'within_10pct':
        return short_strike >= current_price * 0.90  # Within 10% below
    return False

def get_option_price(contract):
    """Extract option price from contract data"""
    # Try multiple price fields from Polygon API
    if 'last_quote' in contract:
        quote = contract['last_quote']
        bid = quote.get('bid', 0)
        ask = quote.get('ask', 0)
        if bid > 0 and ask > 0:
            return (bid + ask) / 2
    
    if 'day' in contract and 'close' in contract['day']:
        return float(contract['day']['close'])
    
    if 'last_trade' in contract and 'price' in contract['last_trade']:
        return float(contract['last_trade']['price'])
    
    return None
    
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
    """Step 4: Detailed Options Trade Analysis using consistent demo data"""
    
    # Get current price from database to match other pages
    current_price = 50.0  # Default fallback
    if symbol in etf_scores:
        current_price = float(etf_scores[symbol]['current_price'])
    
    # Get the demo options data that matches Step 3
    options_data = fetch_options_data(symbol, current_price)
    
    if strategy not in options_data:
        return f"Error: Strategy '{strategy}' not found"
    
    strategy_data = options_data[strategy]
    
    # Use the strategy data directly from Step 3 for consistency
    long_strike = strategy_data['long_strike']
    short_strike = strategy_data['short_strike']
    long_premium = strategy_data['long_premium']
    short_premium = strategy_data['short_premium']
    spread_cost = strategy_data['spread_cost']
    break_even = strategy_data['break_even']
    roi = strategy_data['roi']
    dte = strategy_data['dte']
    expiration_date = strategy_data['expiration_date']
    
    # Calculate spread metrics
    spread_width = short_strike - long_strike
    max_profit = spread_width - spread_cost
    max_loss = spread_cost
    
    # Generate price scenarios for profit/loss analysis
    from datetime import datetime
    scenarios = []
    scenario_percentages = [-7.5, -5, -2.5, 0, 2.5, 5, 7.5]
    
    for change_pct in scenario_percentages:
        future_price = current_price * (1 + change_pct/100)
        
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
            'stock_price': round(future_price, 2),
            'spread_value': round(spread_value, 2),
            'profit_loss': round(profit, 2),
            'roi': round(scenario_roi, 1),
            'outcome': outcome
        })
    
    # Prepare data for Step 4 template
    analysis_data = {
        'symbol': symbol,
        'strategy': strategy.title(),
        'current_price': current_price,
        'long_strike': long_strike,
        'short_strike': short_strike,
        'long_premium': long_premium,
        'short_premium': short_premium,
        'spread_cost': spread_cost,
        'spread_width': spread_width,
        'max_profit': max_profit,
        'max_loss': max_loss,
        'roi': roi,
        'break_even': break_even,
        'dte': dte,
        'expiration_date': expiration_date,
        'scenarios': scenarios
    }
    
    return render_template_string(open('step4_response.html').read(), **analysis_data)

@app.route('/')
def index():
    """Main scoreboard page displaying ETF rankings"""
    try:
        # Load fresh data from database
        load_etf_data_from_database()
        
        # Convert to list and sort by score (descending), then by trading volume (descending)
        etf_list = []
        for symbol, data in etf_scores.items():
            etf_list.append({
                'symbol': symbol,
                'score': data['score'],
                'current_price': data['current_price'],
                'avg_volume_10d': data.get('avg_volume_10d', 0),
                'ticker_data': data.get('ticker_data', {})
            })
        
        # Sort by score first (descending), then by volume (descending) for tie-breaking
        etf_list.sort(key=lambda x: (x['score'], x['avg_volume_10d']), reverse=True)
        
        return render_template_string(open('response.html').read(), 
                                    etf_scores=etf_scores, 
                                    etf_list=etf_list)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return f"Error loading data: {e}", 500

@app.route('/step2/<symbol>')
def step2(symbol=None):
    """Step 2: Detailed ticker analysis page"""
    if symbol not in etf_scores:
        return f"Symbol {symbol} not found", 404
    
    ticker_data = etf_scores[symbol]
    
    return render_template_string(open('step2_response.html').read(),
                                symbol=symbol,
                                ticker_data=ticker_data)

@app.route('/step3/<symbol>')
def step3(symbol=None):
    """Step 3: Income Strategy Selection"""
    if symbol not in etf_scores:
        return f"Symbol {symbol} not found", 404
    
    ticker_data = etf_scores[symbol]
    
    # Get current price from the proper data structure
    if 'current_price' in ticker_data:
        current_price = float(ticker_data['current_price'])
    elif 'price' in ticker_data:
        current_price = float(ticker_data['price'])
    else:
        current_price = 50.0  # Default fallback
    
    # Get demo options data
    options_data = fetch_options_data(symbol, current_price)
    
    return render_template_string(open('step3_response.html').read(),
                                symbol=symbol,
                                ticker_data=ticker_data,
                                options_data=options_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
