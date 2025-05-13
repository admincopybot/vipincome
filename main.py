import os
import logging
from flask import Flask, render_template, jsonify

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)