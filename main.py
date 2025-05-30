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
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            padding: 30px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #2c3e50;
            margin: 0;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        .subtitle {
            color: #7f8c8d;
            font-size: 1.2em;
            margin-top: 10px;
        }
        .etf-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .etf-card {
            background: linear-gradient(145deg, #f8f9fa, #e9ecef);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border: 1px solid #dee2e6;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .etf-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .etf-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .etf-symbol {
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }
        .etf-price {
            font-size: 1.3em;
            color: #27ae60;
            font-weight: bold;
        }
        .etf-name {
            color: #7f8c8d;
            margin-bottom: 15px;
            font-size: 0.9em;
        }
        .score-display {
            text-align: center;
            margin-bottom: 20px;
        }
        .score-number {
            font-size: 3em;
            font-weight: bold;
            margin: 0;
        }
        .score-5 { color: #27ae60; }
        .score-4 { color: #f39c12; }
        .score-3 { color: #f39c12; }
        .score-2 { color: #e74c3c; }
        .score-1 { color: #e74c3c; }
        .score-0 { color: #95a5a6; }
        .score-label {
            font-size: 0.9em;
            color: #7f8c8d;
            margin-top: 5px;
        }
        .indicators {
            display: grid;
            gap: 8px;
        }
        .indicator {
            display: flex;
            align-items: center;
            padding: 8px;
            background: rgba(255,255,255,0.5);
            border-radius: 8px;
            font-size: 0.85em;
        }
        .indicator-icon {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.8em;
        }
        .indicator-pass {
            background: #27ae60;
            color: white;
        }
        .indicator-fail {
            background: #e74c3c;
            color: white;
        }
        .navigation {
            text-align: center;
            margin-top: 30px;
        }
        .nav-button {
            background: linear-gradient(145deg, #3498db, #2980b9);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1.1em;
            cursor: pointer;
            margin: 0 10px;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
        }
        .nav-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(52, 152, 219, 0.4);
        }
        .update-time {
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Income Machine</h1>
            <div class="subtitle">Sector ETF Analysis Dashboard</div>
        </div>
        
        <div class="etf-grid">
            {% for symbol, etf in etf_scores.items() %}
            <div class="etf-card">
                <div class="etf-header">
                    <div class="etf-symbol">{{ symbol }}</div>
                    <div class="etf-price">${{ "%.2f"|format(etf.price) }}</div>
                </div>
                <div class="etf-name">{{ etf.name }}</div>
                
                <div class="score-display">
                    <div class="score-number score-{{ etf.score }}">{{ etf.score }}</div>
                    <div class="score-label">out of 5</div>
                </div>
                
                <div class="indicators">
                    {% for indicator_name, indicator in etf.indicators.items() %}
                    <div class="indicator">
                        <div class="indicator-icon {{ 'indicator-pass' if indicator.pass else 'indicator-fail' }}">
                            {{ '✓' if indicator.pass else '✗' }}
                        </div>
                        <div>{{ indicator.description }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="navigation">
            <a href="/step2" class="nav-button">View Analysis Details</a>
            <a href="/step3" class="nav-button">Trading Recommendations</a>
        </div>
        
        <div class="update-time">
            Data loaded from database • Updated automatically via CSV upload
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