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
    # Get ETF data from database
    etf_data = get_etf_data_from_database()
    
    # Generate the ETF cards HTML
    etf_cards_html = ""
    for symbol, data in etf_data.items():
        score = data['score']
        price = data['price']
        sector = data['sector']
        
        # Color coding based on score
        if score >= 4:
            card_class = "etf-card-high"
        elif score >= 3:
            card_class = "etf-card-medium"
        else:
            card_class = "etf-card-low"
        
        # Generate indicator checkboxes
        indicators_html = ""
        for criterion, details in data['indicators'].items():
            checked = "checked" if details['pass'] else ""
            indicators_html += f'''
                <div class="indicator-row">
                    <input type="checkbox" {checked} disabled>
                    <span class="indicator-description">{details['description']}</span>
                </div>
            '''
        
        etf_cards_html += f'''
        <div class="etf-card {card_class}" data-symbol="{symbol}">
            <div class="etf-header">
                <h3>{symbol}</h3>
                <div class="etf-price">${price:.2f}</div>
            </div>
            <div class="etf-sector">{sector}</div>
            <div class="etf-score">
                <div class="score-display">
                    <span class="score-number">{score}</span>
                    <span class="score-total">/5</span>
                </div>
            </div>
            <div class="etf-indicators">
                {indicators_html}
            </div>
            <div class="card-actions">
                <button class="btn-primary" onclick="selectETF('{symbol}')">Select for Analysis</button>
            </div>
        </div>
        '''
    
    template = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine - ETF Technical Analysis Dashboard</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 40px;
                color: white;
            }}
            
            .header h1 {{
                font-size: 3rem;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            
            .header p {{
                font-size: 1.2rem;
                opacity: 0.9;
            }}
            
            .dashboard {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 25px;
                margin-bottom: 40px;
            }}
            
            .etf-card {{
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border-left: 5px solid #ddd;
            }}
            
            .etf-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0,0,0,0.3);
            }}
            
            .etf-card-high {{
                border-left-color: #28a745;
                background: linear-gradient(145deg, #ffffff 0%, #f8fff9 100%);
            }}
            
            .etf-card-medium {{
                border-left-color: #ffc107;
                background: linear-gradient(145deg, #ffffff 0%, #fffef8 100%);
            }}
            
            .etf-card-low {{
                border-left-color: #dc3545;
                background: linear-gradient(145deg, #ffffff 0%, #fff8f8 100%);
            }}
            
            .etf-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }}
            
            .etf-header h3 {{
                font-size: 1.8rem;
                color: #333;
                font-weight: bold;
            }}
            
            .etf-price {{
                font-size: 1.4rem;
                font-weight: bold;
                color: #2c3e50;
                background: #ecf0f1;
                padding: 5px 12px;
                border-radius: 8px;
            }}
            
            .etf-sector {{
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 20px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .etf-score {{
                text-align: center;
                margin-bottom: 25px;
            }}
            
            .score-display {{
                display: inline-block;
                background: linear-gradient(45deg, #3498db, #2980b9);
                color: white;
                padding: 15px 25px;
                border-radius: 50px;
                font-size: 1.5rem;
                font-weight: bold;
                box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
            }}
            
            .score-number {{
                font-size: 2rem;
            }}
            
            .score-total {{
                opacity: 0.8;
            }}
            
            .etf-indicators {{
                margin-bottom: 25px;
            }}
            
            .indicator-row {{
                display: flex;
                align-items: flex-start;
                margin-bottom: 12px;
                padding: 8px;
                border-radius: 6px;
                background: #f8f9fa;
            }}
            
            .indicator-row input[type="checkbox"] {{
                margin-right: 12px;
                margin-top: 2px;
                transform: scale(1.2);
            }}
            
            .indicator-description {{
                font-size: 0.85rem;
                color: #555;
                line-height: 1.4;
                flex: 1;
            }}
            
            .card-actions {{
                text-align: center;
            }}
            
            .btn-primary {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .btn-primary:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }}
            
            .status-bar {{
                background: rgba(255,255,255,0.1);
                color: white;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 30px;
                backdrop-filter: blur(10px);
            }}
            
            @media (max-width: 768px) {{
                .dashboard {{
                    grid-template-columns: 1fr;
                }}
                
                .header h1 {{
                    font-size: 2rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 Income Machine</h1>
                <p>ETF Technical Analysis Dashboard - Database Display Mode</p>
            </div>
            
            <div class="status-bar">
                <strong>📊 Data Source:</strong> Database | <strong>📈 ETFs Analyzed:</strong> {len(etf_data)} | <strong>🕒 Last Update:</strong> {datetime.now().strftime('%H:%M:%S')}
            </div>
            
            <div class="dashboard">
                {etf_cards_html}
            </div>
        </div>
        
        <script>
            function selectETF(symbol) {{
                alert(`Selected ${{symbol}} for detailed analysis. This would redirect to step 2 with calculations from database.`);
                // In the full app, this would redirect to step 2 with the selected ETF
                // window.location.href = `/step2?etf=${{symbol}}`;
            }}
            
            // Auto-refresh data every 30 seconds (in real app, this would call API)
            setInterval(function() {{
                console.log('In production, this would refresh data from database...');
            }}, 30000);
        </script>
    </body>
    </html>
    '''
    
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