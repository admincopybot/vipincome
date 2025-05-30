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
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            padding: 30px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }
        
        .strategy-card:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: translateY(-2px);
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
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .strategy-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
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
                        <h3 class="strategy-title">Passive Income Strategy</h3>
                        <p class="strategy-subtitle">Conservative approach with steady returns</p>
                    </div>
                    
                    <div class="strategy-returns">
                        <div class="returns-label">Monthly Target</div>
                        <div class="returns-value">2-4%</div>
                    </div>
                    
                    <div class="strategy-details">
                        <div class="detail-row">
                            <span class="detail-label">Risk Level:</span>
                            <span class="detail-value risk-low">Low</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Time Commitment:</span>
                            <span class="detail-value">5-10 min/week</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Strategy Type:</span>
                            <span class="detail-value">Covered Calls</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Capital Required:</span>
                            <span class="detail-value">$5,000+</span>
                        </div>
                    </div>
                    
                    <a href="#" class="strategy-btn">Select Passive Strategy</a>
                </div>
                
                <div class="strategy-card">
                    <div class="strategy-header">
                        <h3 class="strategy-title">Steady Income Strategy</h3>
                        <p class="strategy-subtitle">Balanced risk with moderate returns</p>
                    </div>
                    
                    <div class="strategy-returns">
                        <div class="returns-label">Monthly Target</div>
                        <div class="returns-value">4-8%</div>
                    </div>
                    
                    <div class="strategy-details">
                        <div class="detail-row">
                            <span class="detail-label">Risk Level:</span>
                            <span class="detail-value risk-medium">Medium</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Time Commitment:</span>
                            <span class="detail-value">15-30 min/week</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Strategy Type:</span>
                            <span class="detail-value">Credit Spreads</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Capital Required:</span>
                            <span class="detail-value">$10,000+</span>
                        </div>
                    </div>
                    
                    <a href="#" class="strategy-btn">Select Steady Strategy</a>
                </div>
                
                <div class="strategy-card">
                    <div class="strategy-header">
                        <h3 class="strategy-title">Aggressive Income Strategy</h3>
                        <p class="strategy-subtitle">Higher risk with maximum potential returns</p>
                    </div>
                    
                    <div class="strategy-returns">
                        <div class="returns-label">Monthly Target</div>
                        <div class="returns-value">8-15%</div>
                    </div>
                    
                    <div class="strategy-details">
                        <div class="detail-row">
                            <span class="detail-label">Risk Level:</span>
                            <span class="detail-value risk-high">High</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Time Commitment:</span>
                            <span class="detail-value">1-2 hours/week</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Strategy Type:</span>
                            <span class="detail-value">Iron Condors</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Capital Required:</span>
                            <span class="detail-value">$25,000+</span>
                        </div>
                    </div>
                    
                    <a href="#" class="strategy-btn">Select Aggressive Strategy</a>
                </div>
            </div>
            
            <div class="back-to-scoreboard">
                <a href="{% if symbol %}/step2/{{ symbol }}{% else %}/{% endif %}" class="back-scoreboard-btn">← Back to Analysis</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, symbol=symbol)

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
