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
            
            # Update etf_scores with exact same structure as before
            etf_scores[symbol] = {
                "name": sector_mappings.get(symbol, "Unknown Sector"),
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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1d29;
            color: white;
            min-height: 100vh;
        }
        
        .top-banner {
            background: linear-gradient(90deg, #00bcd4 0%, #673ab7 100%);
            padding: 8px 0;
            text-align: center;
            color: white;
            font-size: 14px;
        }
        
        .header {
            background: #1a1d29;
            padding: 15px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #2a2d3a;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #00bcd4, #673ab7);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 20px;
        }
        
        .logo-text {
            font-size: 18px;
            font-weight: bold;
        }
        
        .nav-menu {
            display: flex;
            gap: 30px;
            align-items: center;
        }
        
        .nav-item {
            color: #b0b3b8;
            text-decoration: none;
            font-size: 14px;
        }
        
        .nav-item:hover {
            color: white;
        }
        
        .get-offer-btn {
            background: #ffd700;
            color: #1a1d29;
            padding: 8px 16px;
            border-radius: 20px;
            text-decoration: none;
            font-weight: bold;
            font-size: 12px;
        }
        
        .step-header {
            background: linear-gradient(90deg, #00bcd4 0%, #673ab7 100%);
            padding: 15px 40px;
            text-align: center;
            color: white;
            font-size: 18px;
            font-weight: bold;
        }
        
        .main-content {
            padding: 40px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .dashboard-title {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .dashboard-subtitle {
            color: #b0b3b8;
            margin-bottom: 10px;
            font-size: 16px;
        }
        
        .update-info {
            color: #888;
            font-size: 14px;
            margin-bottom: 40px;
        }
        
        .etf-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .etf-card {
            background: #2a2d3a;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #3a3d4a;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .etf-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        
        .etf-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }
        
        .etf-symbol {
            font-size: 24px;
            font-weight: bold;
        }
        
        .etf-score {
            background: #00bcd4;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        
        .etf-name {
            color: #b0b3b8;
            margin-bottom: 15px;
            font-size: 14px;
        }
        
        .etf-price {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        
        .progress-bar {
            background: #3a3d4a;
            height: 6px;
            border-radius: 3px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00bcd4, #673ab7);
            transition: width 0.3s ease;
        }
        
        .action-buttons {
            display: flex;
            gap: 10px;
        }
        
        .btn-recommended {
            background: #ffd700;
            color: #1a1d29;
            padding: 12px 20px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            font-size: 14px;
            text-align: center;
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
        }
        
        .btn-select {
            background: linear-gradient(90deg, #00bcd4, #673ab7);
            color: white;
            padding: 12px 20px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            font-size: 14px;
            text-align: center;
            flex: 1;
        }
        
        .btn-select:hover, .btn-recommended:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .crown-icon {
            color: #ffd700;
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
        <h1 class="dashboard-title">Daily ETF Scoreboard</h1>
        <p class="dashboard-subtitle">Select an ETF with a score of 3+ for the highest probability income opportunity.</p>
        <p class="update-info">Prices and scores update automatically</p>
        
        <div class="etf-grid">
            {% for symbol, etf in etf_scores.items() %}
            {% if loop.index <= 10 %}
            <div class="etf-card">
                <div class="etf-header">
                    <div class="etf-symbol">{{ symbol }}</div>
                    <div class="etf-score">{{ etf.score }}/5</div>
                </div>
                <div class="etf-name">{{ etf.name }}</div>
                <div class="etf-price">${{ "%.2f"|format(etf.price) }}</div>
                
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{ (etf.score / 5 * 100) }}%"></div>
                </div>
                
                <div class="action-buttons">
                    {% if etf.score >= 4 %}
                    <a href="#" class="btn-recommended">
                        <span class="crown-icon">👑</span> Recommended Asset
                    </a>
                    <a href="#" class="btn-select" style="background: #4a4d5a; font-size: 12px;">Select {{ symbol }}</a>
                    {% else %}
                    <a href="#" class="btn-select">Select {{ symbol }}</a>
                    {% endif %}
                </div>
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