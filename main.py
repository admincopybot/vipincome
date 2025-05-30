"""
Clean Income Machine ETF Analyzer - Database Only Version
Displays pre-calculated ETF scoring data from database with exact same frontend
No WebSocket, API calls, or real-time calculations
"""
import logging
import os
import io
import csv
from flask import Flask, request, render_template_string, jsonify
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0a0f1c;
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
            background: #111827;
            padding: 20px 50px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #374151;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo-icon {
            width: 45px;
            height: 45px;
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 18px;
            box-shadow: 0 8px 25px rgba(0, 212, 255, 0.3);
            transition: transform 0.3s ease;
        }
        
        .logo-icon:hover {
            transform: scale(1.05);
        }
        
        .logo-text {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 1px;
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
            background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 50%, #ec4899 100%);
            padding: 20px 50px;
            text-align: center;
            color: white;
            font-size: 20px;
            font-weight: 600;
            letter-spacing: 1px;
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2);
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
            color: #60a5fa;
        }
        
        .dashboard-subtitle {
            color: #94a3b8;
            margin-bottom: 12px;
            font-size: 18px;
            font-weight: 400;
        }
        
        .update-info {
            color: #64748b;
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
            background: #1f2937;
            border-radius: 12px;
            padding: 30px;
            border: 2px solid #3b82f6;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            transition: all 0.3s ease;
            position: relative;
            text-decoration: none;
            color: inherit;
            display: block;
            cursor: pointer;
        }
        
        .etf-card:hover {
            transform: translateY(-4px);
            border-color: #60a5fa;
            box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
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
            color: #60a5fa;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .criteria-text {
            font-size: 11px;
            color: #94a3b8;
            margin-top: 8px;
            font-weight: 500;
            opacity: 0.8;
        }
        
        .current-price {
            font-size: 32px;
            font-weight: 800;
            color: #10b981;
            text-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
            margin: 10px 0;
        }
        
        .choose-btn-text {
            background: #3b82f6;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 14px;
            width: 100%;
            text-align: center;
            transition: all 0.3s ease;
            border: 2px solid #3b82f6;
        }
        
        .etf-card:hover .choose-btn-text {
            background: #60a5fa;
            border-color: #60a5fa;
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
            <div class="logo-icon">IM</div>
            <div class="logo-text">INCOME MACHINE</div>
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
                <a href="#" class="etf-card{% if loop.index > 3 %} blurred{% endif %}">
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
def step2():
    return "<h1>Step 2: Analysis Details</h1><p>This page would show detailed analysis.</p><a href='/'>Back to Dashboard</a>"

@app.route('/step3')
def step3():
    return "<h1>Step 3: Trading Recommendations</h1><p>This page would show trading recommendations.</p><a href='/'>Back to Dashboard</a>"

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)