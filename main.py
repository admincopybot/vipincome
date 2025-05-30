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
    return render_template_string("""
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
                background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%);
                color: #ffffff;
                min-height: 100vh;
                overflow-x: hidden;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 50px;
            }
            
            .step-indicator {
                display: flex;
                justify-content: center;
                margin-bottom: 30px;
                gap: 20px;
            }
            
            .step {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 12px 24px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: all 0.3s ease;
            }
            
            .step.active {
                background: rgba(59, 130, 246, 0.15);
                border-color: rgba(59, 130, 246, 0.3);
                box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
            }
            
            .step.completed {
                background: rgba(34, 197, 94, 0.15);
                border-color: rgba(34, 197, 94, 0.3);
            }
            
            .step-number {
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.1);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: 600;
            }
            
            .step.active .step-number {
                background: #3b82f6;
                color: white;
            }
            
            .step.completed .step-number {
                background: #22c55e;
                color: white;
            }
            
            .step-text {
                font-size: 14px;
                font-weight: 500;
            }
            
            .page-title {
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 15px;
                background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .page-subtitle {
                font-size: 1.2rem;
                color: #94a3b8;
                margin-bottom: 20px;
            }
            
            .selected-stock {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                padding: 12px 20px;
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 12px;
                margin-bottom: 40px;
                font-weight: 600;
            }
            
            .strategies-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 30px;
                margin-bottom: 40px;
            }
            
            .strategy-card {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 30px;
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                overflow: hidden;
            }
            
            .strategy-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: var(--accent-color);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .strategy-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
                border-color: var(--accent-color);
            }
            
            .strategy-card:hover::before {
                opacity: 1;
            }
            
            .strategy-card.passive {
                --accent-color: #22c55e;
            }
            
            .strategy-card.steady {
                --accent-color: #3b82f6;
            }
            
            .strategy-card.aggressive {
                --accent-color: #f59e0b;
            }
            
            .strategy-header {
                display: flex;
                align-items: center;
                gap: 15px;
                margin-bottom: 20px;
            }
            
            .strategy-icon {
                width: 50px;
                height: 50px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                background: var(--accent-color);
                color: white;
            }
            
            .strategy-title {
                font-size: 1.5rem;
                font-weight: 700;
                color: #ffffff;
            }
            
            .strategy-subtitle {
                font-size: 0.9rem;
                color: #94a3b8;
                margin-top: 5px;
            }
            
            .strategy-description {
                color: #cbd5e1;
                line-height: 1.6;
                margin-bottom: 25px;
            }
            
            .strategy-features {
                list-style: none;
                margin-bottom: 25px;
            }
            
            .strategy-features li {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 8px;
                color: #e2e8f0;
                font-size: 0.9rem;
            }
            
            .strategy-features li::before {
                content: '✓';
                color: var(--accent-color);
                font-weight: bold;
                font-size: 14px;
            }
            
            .strategy-metrics {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-bottom: 25px;
            }
            
            .metric {
                text-align: center;
                padding: 15px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .metric-value {
                font-size: 1.2rem;
                font-weight: 700;
                color: var(--accent-color);
                margin-bottom: 5px;
            }
            
            .metric-label {
                font-size: 0.8rem;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .select-strategy-btn {
                width: 100%;
                padding: 15px;
                background: var(--accent-color);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .select-strategy-btn:hover {
                background: var(--accent-color);
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
            }
            
            .navigation {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 40px;
            }
            
            .nav-button {
                padding: 15px 30px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                background: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 600;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .nav-button:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.5);
                transform: translateY(-2px);
            }
            
            .back-button {
                color: #94a3b8;
            }
            
            @media (max-width: 768px) {
                .strategies-grid {
                    grid-template-columns: 1fr;
                }
                
                .navigation {
                    flex-direction: column;
                    gap: 15px;
                }
                
                .nav-button {
                    width: 100%;
                    justify-content: center;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="step-indicator">
                    <div class="step completed">
                        <div class="step-number">1</div>
                        <div class="step-text">Stock Analysis</div>
                    </div>
                    <div class="step completed">
                        <div class="step-number">2</div>
                        <div class="step-text">Technical Review</div>
                    </div>
                    <div class="step active">
                        <div class="step-number">3</div>
                        <div class="step-text">Income Strategy</div>
                    </div>
                </div>
                
                <h1 class="page-title">Choose Your Income Strategy</h1>
                <p class="page-subtitle">Select the approach that matches your risk tolerance and income goals</p>
                
                {% if symbol %}
                <div class="selected-stock">
                    <span>📊</span>
                    <span>Selected Stock: <strong>{{ symbol }}</strong></span>
                </div>
                {% endif %}
            </div>
            
            <div class="strategies-grid">
                <!-- Passive Strategy -->
                <div class="strategy-card passive" onclick="selectStrategy('passive', '{{ symbol or '' }}')">
                    <div class="strategy-header">
                        <div class="strategy-icon">🌱</div>
                        <div>
                            <div class="strategy-title">Passive Income</div>
                            <div class="strategy-subtitle">Conservative & Steady</div>
                        </div>
                    </div>
                    
                    <div class="strategy-description">
                        Perfect for beginners and conservative investors. Focus on covered calls and cash-secured puts with minimal risk and steady monthly income.
                    </div>
                    
                    <ul class="strategy-features">
                        <li>Lower risk, consistent returns</li>
                        <li>Monthly covered call writing</li>
                        <li>Capital preservation focused</li>
                        <li>Ideal for retirement accounts</li>
                        <li>Minimal time commitment</li>
                    </ul>
                    
                    <div class="strategy-metrics">
                        <div class="metric">
                            <div class="metric-value">2-4%</div>
                            <div class="metric-label">Monthly Target</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">Low</div>
                            <div class="metric-label">Risk Level</div>
                        </div>
                    </div>
                    
                    <button class="select-strategy-btn">Select Passive Strategy</button>
                </div>
                
                <!-- Steady Strategy -->
                <div class="strategy-card steady" onclick="selectStrategy('steady', '{{ symbol or '' }}')">
                    <div class="strategy-header">
                        <div class="strategy-icon">⚖️</div>
                        <div>
                            <div class="strategy-title">Steady Growth</div>
                            <div class="strategy-subtitle">Balanced & Reliable</div>
                        </div>
                    </div>
                    
                    <div class="strategy-description">
                        Balanced approach combining income and growth. Uses spreads, covered strategies, and selective wheeling for consistent performance.
                    </div>
                    
                    <ul class="strategy-features">
                        <li>Balanced risk-reward ratio</li>
                        <li>Credit spreads and iron condors</li>
                        <li>The wheel strategy integration</li>
                        <li>Growth with income focus</li>
                        <li>Moderate time investment</li>
                    </ul>
                    
                    <div class="strategy-metrics">
                        <div class="metric">
                            <div class="metric-value">4-8%</div>
                            <div class="metric-label">Monthly Target</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">Medium</div>
                            <div class="metric-label">Risk Level</div>
                        </div>
                    </div>
                    
                    <button class="select-strategy-btn">Select Steady Strategy</button>
                </div>
                
                <!-- Aggressive Strategy -->
                <div class="strategy-card aggressive" onclick="selectStrategy('aggressive', '{{ symbol or '' }}')">
                    <div class="strategy-header">
                        <div class="strategy-icon">🚀</div>
                        <div>
                            <div class="strategy-title">Aggressive Income</div>
                            <div class="strategy-subtitle">High Return Potential</div>
                        </div>
                    </div>
                    
                    <div class="strategy-description">
                        Maximum income potential using advanced strategies. Short straddles, naked options, and leveraged positions for experienced traders.
                    </div>
                    
                    <ul class="strategy-features">
                        <li>Higher income potential</li>
                        <li>Advanced option strategies</li>
                        <li>Active management required</li>
                        <li>Leveraged positions</li>
                        <li>Experience recommended</li>
                    </ul>
                    
                    <div class="strategy-metrics">
                        <div class="metric">
                            <div class="metric-value">8-15%</div>
                            <div class="metric-label">Monthly Target</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">High</div>
                            <div class="metric-label">Risk Level</div>
                        </div>
                    </div>
                    
                    <button class="select-strategy-btn">Select Aggressive Strategy</button>
                </div>
            </div>
            
            <div class="navigation">
                <a href="{% if symbol %}/step2/{{ symbol }}{% else %}/{% endif %}" class="nav-button back-button">
                    ← Back to Analysis
                </a>
                <div class="nav-button" style="opacity: 0.5; cursor: not-allowed;">
                    Continue to Execution →
                </div>
            </div>
        </div>
        
        <script>
            function selectStrategy(strategy, symbol) {
                // Show selection feedback
                const card = document.querySelector(`.strategy-card.${strategy}`);
                card.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    card.style.transform = 'scale(1)';
                }, 150);
                
                // Store selection and proceed
                localStorage.setItem('selectedStrategy', strategy);
                localStorage.setItem('selectedSymbol', symbol);
                
                // You could redirect to a detailed strategy page or show a confirmation
                alert(`${strategy.charAt(0).toUpperCase() + strategy.slice(1)} Income Strategy selected for ${symbol || 'your selection'}!\\n\\nNext: Strategy execution details will be shown.`);
                
                // Future: Redirect to detailed strategy execution page
                // window.location.href = `/strategy-execution/${strategy}/${symbol}`;
            }
            
            // Add smooth scroll and enhanced interactions
            document.addEventListener('DOMContentLoaded', function() {
                // Add hover sound effect (optional)
                const cards = document.querySelectorAll('.strategy-card');
                cards.forEach(card => {
                    card.addEventListener('mouseenter', function() {
                        this.style.transform = 'translateY(-5px) scale(1.02)';
                    });
                    
                    card.addEventListener('mouseleave', function() {
                        this.style.transform = 'translateY(0) scale(1)';
                    });
                });
            });
        </script>
    </body>
    </html>
    """, symbol=symbol)

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    """CSV upload endpoint that updates the database with ETF scoring data from uploaded CSV
    
    Accepts:
    - File upload via 'csvfile' form field
    - Raw CSV text via 'csv_text' form field
    
    Returns:
    - Success/error response
    """
    global etf_scores
    
    try:
        csv_content = None
        
        # Check for file upload
        if 'csvfile' in request.files:
            file = request.files['csvfile']
            if file and file.filename and file.filename.endswith('.csv'):
                csv_content = file.read().decode('utf-8')
                logger.info(f"Received CSV file upload: {file.filename}")
        
        # Check for raw CSV text
        elif 'csv_text' in request.form:
            csv_content = request.form['csv_text']
            logger.info("Received raw CSV text upload")
        
        # Check for JSON format (for API calls)
        elif request.is_json:
            json_data = request.get_json()
            if 'csv_content' in json_data:
                csv_content = json_data['csv_content']
                logger.info("Received CSV content via JSON")
        
        if not csv_content:
            return jsonify({
                'error': 'No CSV data provided. Send file via csvfile field, text via csv_text field, or JSON with csv_content.'
            }), 400
        
        # Upload CSV data to database
        result = etf_db.upload_csv_data(csv_content)
        
        if not result['success']:
            return jsonify({
                'error': f'Failed to upload CSV to database: {result["error"]}'
            }), 500
        
        # Refresh the global etf_scores from database
        load_etf_data_from_database()
        
        logger.info(f"Successfully uploaded {result['count']} symbols to database")
        
        # Return success response
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {result["count"]} symbols to database',
            'count': result['count']
        })
        
    except Exception as e:
        logger.error(f"Error processing CSV upload: {str(e)}")
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/etf_data')
def api_etf_data():
    """API endpoint to get the latest ETF data for real-time updates in the UI
    
    Returns:
        JSON: Current ETF data including prices and scores
    """
    # Synchronize scores before returning
    synchronize_etf_scores()
    
    return jsonify({
        'success': True,
        'data': etf_scores,
        'timestamp': 'Database data - no real-time updates'
    })

@app.route('/api/chart_data/<symbol>')
def api_chart_data(symbol):
    """API endpoint to get chart data for a specific symbol using Polygon API
    
    Returns:
        JSON: Chart data with timestamps and prices
    """
    import os
    import requests
    from datetime import datetime, timedelta
    
    try:
        # Get API key from environment
        api_key = os.environ.get('POLYGON_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Polygon API key not configured'
            }), 500
        
        # Calculate date range (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Format dates for Polygon API
        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        # Fetch daily data from Polygon
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/{from_date}/{to_date}"
        params = {
            'apikey': api_key,
            'adjusted': 'true',
            'sort': 'asc'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Polygon API returned status {response.status_code}'
            }), 500
        
        data = response.json()
        
        if data.get('status') not in ['OK', 'DELAYED'] or 'results' not in data:
            return jsonify({
                'success': False,
                'error': 'No data available for this symbol'
            }), 404
        
        # Format data for Chart.js
        chart_data = []
        for result in data['results']:
            timestamp = result['t']  # Unix timestamp in milliseconds
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
            chart_data.append({
                'date': date_str,
                'timestamp': timestamp,
                'open': result['o'],
                'high': result['h'],
                'low': result['l'],
                'close': result['c'],
                'volume': result['v']
            })
        
        # Get additional symbol info
        current_price = chart_data[-1]['close'] if chart_data else 0
        price_change = 0
        price_change_pct = 0
        
        if len(chart_data) >= 2:
            yesterday_close = chart_data[-2]['close']
            price_change = current_price - yesterday_close
            price_change_pct = (price_change / yesterday_close) * 100 if yesterday_close > 0 else 0
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'chart_data': chart_data,
            'current_price': current_price,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'data_points': len(chart_data)
        })
        
    except requests.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'Network error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)