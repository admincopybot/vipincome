from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import logging
import os
from datetime import datetime
from app import app, db
from models import EtfScore

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ETF sector mapping for demo data
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

def initialize_demo_data():
    """Initialize database with demo data for display"""
    try:
        # Sample demo data showing various score combinations
        demo_data = [
            {
                'symbol': 'XLK',
                'current_price': 158.45,
                'total_score': 4,
                'sector': 'Technology',
                'trend1_pass': True,
                'trend1_current': 158.45,
                'trend1_threshold': 155.20,
                'trend1_description': 'Price ($158.45) is above the 20-day EMA ($155.20)',
                'trend2_pass': True,
                'trend2_current': 158.45,
                'trend2_threshold': 152.80,
                'trend2_description': 'Price ($158.45) is above the 100-day EMA ($152.80)',
                'snapback_pass': True,
                'snapback_current': 45.2,
                'snapback_threshold': 50.0,
                'snapback_description': 'RSI (45.2) is below the threshold (50)',
                'momentum_pass': True,
                'momentum_current': 158.45,
                'momentum_threshold': 156.90,
                'momentum_description': 'Current price ($158.45) is above last week\'s close ($156.90)',
                'stabilizing_pass': False,
                'stabilizing_current': 2.15,
                'stabilizing_threshold': 1.98,
                'stabilizing_description': '3-day ATR (2.15) is higher than 6-day ATR (1.98)',
                'data_age_hours': 2
            },
            {
                'symbol': 'XLF',
                'current_price': 50.95,
                'total_score': 3,
                'sector': 'Financial',
                'trend1_pass': True,
                'trend1_current': 50.95,
                'trend1_threshold': 49.80,
                'trend1_description': 'Price ($50.95) is above the 20-day EMA ($49.80)',
                'trend2_pass': False,
                'trend2_current': 50.95,
                'trend2_threshold': 51.20,
                'trend2_description': 'Price ($50.95) is below the 100-day EMA ($51.20)',
                'snapback_pass': True,
                'snapback_current': 48.7,
                'snapback_threshold': 50.0,
                'snapback_description': 'RSI (48.7) is below the threshold (50)',
                'momentum_pass': True,
                'momentum_current': 50.95,
                'momentum_threshold': 50.40,
                'momentum_description': 'Current price ($50.95) is above last week\'s close ($50.40)',
                'stabilizing_pass': False,
                'stabilizing_current': 1.85,
                'stabilizing_threshold': 1.72,
                'stabilizing_description': '3-day ATR (1.85) is higher than 6-day ATR (1.72)',
                'data_age_hours': 1
            },
            {
                'symbol': 'XLV',
                'current_price': 132.32,
                'total_score': 2,
                'sector': 'Health Care',
                'trend1_pass': False,
                'trend1_current': 132.32,
                'trend1_threshold': 133.10,
                'trend1_description': 'Price ($132.32) is below the 20-day EMA ($133.10)',
                'trend2_pass': True,
                'trend2_current': 132.32,
                'trend2_threshold': 130.50,
                'trend2_description': 'Price ($132.32) is above the 100-day EMA ($130.50)',
                'snapback_pass': False,
                'snapback_current': 52.8,
                'snapback_threshold': 50.0,
                'snapback_description': 'RSI (52.8) is above the threshold (50)',
                'momentum_pass': True,
                'momentum_current': 132.32,
                'momentum_threshold': 131.85,
                'momentum_description': 'Current price ($132.32) is above last week\'s close ($131.85)',
                'stabilizing_pass': False,
                'stabilizing_current': 1.95,
                'stabilizing_threshold': 1.80,
                'stabilizing_description': '3-day ATR (1.95) is higher than 6-day ATR (1.80)',
                'data_age_hours': 3
            },
            {
                'symbol': 'XLI',
                'current_price': 144.09,
                'total_score': 5,
                'sector': 'Industrial',
                'trend1_pass': True,
                'trend1_current': 144.09,
                'trend1_threshold': 142.30,
                'trend1_description': 'Price ($144.09) is above the 20-day EMA ($142.30)',
                'trend2_pass': True,
                'trend2_current': 144.09,
                'trend2_threshold': 140.85,
                'trend2_description': 'Price ($144.09) is above the 100-day EMA ($140.85)',
                'snapback_pass': True,
                'snapback_current': 47.3,
                'snapback_threshold': 50.0,
                'snapback_description': 'RSI (47.3) is below the threshold (50)',
                'momentum_pass': True,
                'momentum_current': 144.09,
                'momentum_threshold': 143.20,
                'momentum_description': 'Current price ($144.09) is above last week\'s close ($143.20)',
                'stabilizing_pass': True,
                'stabilizing_current': 1.65,
                'stabilizing_threshold': 1.78,
                'stabilizing_description': '3-day ATR (1.65) is lower than 6-day ATR (1.78)',
                'data_age_hours': 1
            },
            {
                'symbol': 'XLP',
                'current_price': 82.27,
                'total_score': 1,
                'sector': 'Consumer Staples',
                'trend1_pass': False,
                'trend1_current': 82.27,
                'trend1_threshold': 82.85,
                'trend1_description': 'Price ($82.27) is below the 20-day EMA ($82.85)',
                'trend2_pass': False,
                'trend2_current': 82.27,
                'trend2_threshold': 83.10,
                'trend2_description': 'Price ($82.27) is below the 100-day EMA ($83.10)',
                'snapback_pass': True,
                'snapback_current': 46.1,
                'snapback_threshold': 50.0,
                'snapback_description': 'RSI (46.1) is below the threshold (50)',
                'momentum_pass': False,
                'momentum_current': 82.27,
                'momentum_threshold': 82.90,
                'momentum_description': 'Current price ($82.27) is below last week\'s close ($82.90)',
                'stabilizing_pass': False,
                'stabilizing_current': 1.45,
                'stabilizing_threshold': 1.35,
                'stabilizing_description': '3-day ATR (1.45) is higher than 6-day ATR (1.35)',
                'data_age_hours': 2
            }
        ]
        
        # Clear existing data and insert demo data
        db.session.query(EtfScore).delete()
        
        for data in demo_data:
            etf_score = EtfScore(**data)
            db.session.add(etf_score)
        
        db.session.commit()
        logger.info(f"Initialized database with {len(demo_data)} demo ETF scores")
        
    except Exception as e:
        logger.error(f"Error initializing demo data: {e}")
        db.session.rollback()

# Initialize demo data on startup
with app.app_context():
    initialize_demo_data()

def get_etf_data_from_database():
    """Get all ETF data from database"""
    try:
        etf_scores = EtfScore.query.all()
        etf_data = {}
        
        for etf in etf_scores:
            etf_dict = etf.to_dict()
            etf_data[etf.symbol] = etf_dict
            
        return etf_data
        
    except Exception as e:
        logger.error(f"Error fetching ETF data from database: {e}")
        return {}

@app.route('/')
def index():
    # Get ETF data from database and convert to match original format
    etf_data = get_etf_data_from_database()
    
    # Convert database format to original format
    etf_scores = {}
    for symbol, data in etf_data.items():
        etf_scores[symbol] = {
            'name': data['sector'],
            'score': data['score'],
            'price': data['price']
        }
    
    # Global CSS from original design
    global_css = """
    /* Apple-style base setup */
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        letter-spacing: -0.015em;
        background: linear-gradient(160deg, #000000 0%, #121212 100%);
        min-height: 100vh;
        color: rgba(255, 255, 255, 0.95);
    }
    
    /* Typography refinement */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600;
        letter-spacing: -0.03em;
        color: rgba(255, 255, 255, 0.95);
    }
    
    p, .text-light, td, th, li {
        font-weight: 400;
        line-height: 1.6;
        color: rgba(255, 255, 255, 0.8);
    }
    
    .text-dark {
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Modern card styling with Apple's glass effects */
    .card {
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        background: rgba(40, 40, 45, 0.6);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
        margin-bottom: 1.5rem;
    }
    
    .card:hover {
        transform: scale(1.02);
        border-color: rgba(255, 255, 255, 0.2);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
    }
    
    .card-header {
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(60, 60, 70, 0.4);
        border-radius: 16px 16px 0 0 !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    
    .card-body {
        border-radius: 0 0 16px 16px;
        background: rgba(40, 40, 45, 0.3);
    }
    
    /* Modern button styling */
    .btn {
        font-weight: 500;
        border-radius: 12px;
        border: none;
        padding: 0.75rem 1.5rem;
        letter-spacing: -0.01em;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    
    .btn-primary {
        background: rgba(100, 108, 255, 0.8);
        color: white;
        box-shadow: 0 4px 15px rgba(100, 108, 255, 0.3);
    }
    
    .btn-primary:hover {
        background: rgba(100, 108, 255, 1);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(100, 108, 255, 0.4);
    }
    
    .btn-success {
        background: rgba(48, 209, 88, 0.8);
        color: white;
        box-shadow: 0 4px 15px rgba(48, 209, 88, 0.3);
    }
    
    .btn-success:hover {
        background: rgba(48, 209, 88, 1);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(48, 209, 88, 0.4);
    }
    
    .btn-secondary {
        background: rgba(60, 60, 70, 0.8);
        color: rgba(255, 255, 255, 0.9);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .btn-outline-light {
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: rgba(255, 255, 255, 0.9);
        background: rgba(255, 255, 255, 0.05);
    }
    
    .btn-outline-light:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.5);
        color: white;
        transform: translateY(-1px);
    }
    
    /* Progress bars */
    .progress {
        height: 0.5rem;
        border-radius: 100px;
        overflow: hidden;
        background: rgba(40, 40, 45, 0.3);
    }
    
    /* Step indicators styled like Apple */
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin: 2.5rem 0;
        gap: 10px;
    }
    
    .step {
        flex: 1;
        border-radius: 12px;
        padding: 1rem 0.5rem;
        text-align: center;
        font-weight: 500;
        background: rgba(60, 60, 70, 0.3);
        color: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        transition: all 0.3s ease;
    }
    
    .step.active {
        background: rgba(100, 108, 255, 0.8);
        color: white;
        font-weight: 600;
    }
    
    .step.completed {
        background: rgba(48, 209, 88, 0.6);
        color: white;
        font-weight: 600;
    }
    
    /* List group refinement */
    .list-group-item {
        border: none;
        padding: 1.25rem;
        margin-bottom: 0.5rem;
        border-radius: 12px !important;
        background: rgba(40, 40, 45, 0.4);
        color: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
    }
    
    /* Modern header */
    header {
        border: none !important;
        margin-bottom: 2rem;
        padding: 1.5rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Content area styling */
    .bg-body-tertiary {
        border-radius: 20px !important;
        background: rgba(40, 40, 45, 0.5) !important;
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        margin-bottom: 2.5rem;
    }
    
    /* Apple-style table */
    table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 0.75rem;
        margin-top: 1rem;
    }
    
    th {
        font-weight: 500;
        color: rgba(255, 255, 255, 0.7);
        padding: 0.75rem 1.5rem;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 0.05em;
    }
    
    td {
        padding: 1.25rem 1.5rem;
        vertical-align: middle;
        color: rgba(255, 255, 255, 0.9);
    }
    
    tbody tr {
        background: rgba(40, 40, 45, 0.4);
        border-radius: 12px;
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    tbody tr:hover {
        transform: scale(1.01);
        background: rgba(50, 50, 55, 0.5);
        cursor: pointer;
    }
    
    tbody td:first-child {
        border-radius: 12px 0 0 12px;
        font-weight: 600;
    }
    
    tbody td:last-child {
        border-radius: 0 12px 12px 0;
    }
    
    /* Progress bar colors */
    .progress-bar-score-0 { background-color: rgba(255, 69, 58, 0.5) !important; }
    .progress-bar-score-1 { background-color: rgba(255, 69, 58, 0.7) !important; }
    .progress-bar-score-2 { background-color: rgba(255, 159, 10, 0.7) !important; }
    .progress-bar-score-3 { background-color: rgba(100, 210, 255, 0.7) !important; }
    .progress-bar-score-4 { background-color: rgba(48, 209, 88, 0.7) !important; }
    .progress-bar-score-5 { background-color: rgba(48, 209, 88, 0.9) !important; }
    """
    
    template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine DEMO - Daily ETF Scoreboard</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            {global_css}
            
            /* Page-specific styles */
            .progress-bar-score-0 {{ width: 0%; background-color: var(--bs-danger); }}
            .progress-bar-score-1 {{ width: 20%; background-color: var(--bs-danger); }}
            .progress-bar-score-2 {{ width: 40%; background-color: var(--bs-warning); }}
            .progress-bar-score-3 {{ width: 60%; background-color: var(--bs-info); }}
            .progress-bar-score-4 {{ width: 80%; background-color: var(--bs-success); }}
            .progress-bar-score-5 {{ width: 100%; background-color: var(--bs-success); }}
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center justify-content-between">
                    <h1 class="fs-4 text-light">Income Machine <span class="badge bg-primary">DEMO</span></h1>
                    <div class="d-flex gap-3">
                        <a href="/how-to-use" class="btn btn-sm btn-outline-light">How to Use</a>
                        <a href="/live-classes" class="btn btn-sm btn-outline-light">Trade Classes</a>
                        <a href="/special-offer" class="btn btn-sm btn-danger">Get 50% OFF</a>
                    </div>
                </div>
            </header>
            
            <div class="step-indicator">
                <div class="step active">
                    Step 1: Scoreboard
                </div>
                <div class="step upcoming">
                    Step 2: ETF Selection
                </div>
                <div class="step upcoming">
                    Step 3: Strategy
                </div>
                <div class="step upcoming">
                    Step 4: Trade Details
                </div>
            </div>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">Daily ETF Scoreboard</h2>
                    <p class="fs-5">Select an ETF with a high score (4-5) for the best covered call opportunities.</p>
                </div>
            </div>
    
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>ETF</th>
                            <th>Sector</th>
                            <th>Price</th>
                            <th>Score</th>
                            <th>Strength</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''
                        <tr>
                            <td><strong>{etf}</strong></td>
                            <td>{data["name"]}</td>
                            <td>${data["price"]:.2f}</td>
                            <td>{data["score"]}/5</td>
                            <td>
                                <div class="progress">
                                    <div class="progress-bar progress-bar-score-{data["score"]}" role="progressbar" 
                                         aria-valuenow="{data["score"] * 20}" aria-valuemin="0" aria-valuemax="100">
                                    </div>
                                </div>
                            </td>
                            <td>
                                <a href="/step2?etf={etf}" class="btn btn-sm {'btn-success' if data["score"] >= 4 else 'btn-secondary'}">
                                    Select
                                </a>
                            </td>
                        </tr>
                        ''' for etf, data in etf_scores.items()])}
                    </tbody>
                </table>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO - Database Mode
            </footer>
        </div>
    </body>
    </html>
    """
    
    return template

@app.route('/api/etf-data')
def api_etf_data():
    """API endpoint to get the latest ETF data for real-time updates in the UI
    
    Returns:
        JSON: Current ETF data from database
    """
    try:
        etf_data = get_etf_data_from_database()
        return jsonify(etf_data)
    except Exception as e:
        logger.error(f"Error in API endpoint: {e}")
        return jsonify({'error': 'Failed to fetch ETF data'}), 500

@app.route('/step2')
def step2():
    return redirect(url_for('index'))

@app.route('/step3')
def step3():
    return redirect(url_for('index'))

@app.route('/step4')
def step4():
    return redirect(url_for('index'))

@app.route('/how-to-use')
def how_to_use():
    return redirect(url_for('index'))

@app.route('/live-classes')
def live_classes():
    return redirect(url_for('index'))

@app.route('/special-offer')
def special_offer():
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)