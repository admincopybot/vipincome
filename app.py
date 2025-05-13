from flask import Flask, render_template, redirect, url_for
import logging
import os
import threading
import time
from dotenv import load_dotenv

from database import init_db
from api_routes import api
from background_tasks import BackgroundTaskService
from simplified_market_data import SimplifiedMarketDataService
from tradelist_websocket_client import get_websocket_client

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "income_machine_demo")

# Initialize database
try:
    init_db(app)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")

# Register blueprints
app.register_blueprint(api, url_prefix='/api')

# Initialize WebSocket connection for real-time data
def initialize_websocket_client():
    """Initialize and connect to TheTradeList WebSocket API"""
    try:
        logger.info("Initializing WebSocket connection to TheTradeList API...")
        ws_client = get_websocket_client()
        if ws_client:
            # Add all our ETF symbols to track
            ws_client.symbols_to_track = SimplifiedMarketDataService.default_etfs.copy()
            
            # Connect to the WebSocket
            success = ws_client.connect()
            if success:
                logger.info(f"WebSocket client initialized with {len(ws_client.symbols_to_track)} symbols to track")
                return True
            else:
                logger.error("Failed to connect WebSocket client")
        else:
            logger.error("Failed to get WebSocket client instance - check API key")
    except Exception as e:
        logger.error(f"Error initializing WebSocket client: {str(e)}")
    
    return False

# Start background task service
BackgroundTaskService.start_worker()

# Initialize WebSocket connection
initialize_websocket_client()

# Routes
@app.route('/')
def index():
    """Home page (ETF Scoreboard)"""
    return render_template('index.html')

@app.route('/backtest')
def backtest():
    """Backtesting page"""
    return render_template('backtest.html')

@app.route('/how-to-use')
def how_to_use():
    """How to use page"""
    return render_template('how_to_use.html')

@app.route('/live-classes')
def live_classes():
    """Live classes page"""
    return render_template('live_classes.html')

@app.route('/special-offer')
def special_offer():
    """Special offer page"""
    return render_template('special_offer.html')

# Shutdown handler to clean up resources
def shutdown_handler():
    """Clean up resources on shutdown"""
    logger.info("Shutting down application...")
    
    # Stop background task worker
    BackgroundTaskService.stop_worker()
    
    logger.info("Shutdown complete")

# Register shutdown handler
import atexit
atexit.register(shutdown_handler)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)