"""
Income Machine - Web application for ETF spread analysis
"""

import os
import logging
import threading
import time
import atexit
from datetime import datetime, timedelta
from functools import wraps
import json

from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from db_init import db, init_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)

# Configure app
app.secret_key = os.environ.get("SESSION_SECRET", "income-machine-secret-key")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
init_app(app)

# Dictionary to track real-time price updates (symbol -> price)
price_updates = {}

# Flag to track whether the WebSocket client is connected
websocket_connected = False

# Background thread for real-time price updates
update_thread = None
stop_update_thread = threading.Event()

def initialize_websocket_client():
    """Initialize and connect to TheTradeList WebSocket API"""
    try:
        from tradelist_websocket_client import initialize_websocket
        from simplified_market_data import SimplifiedMarketDataService
        
        # Get ETF symbols to track
        symbols = SimplifiedMarketDataService.default_etfs
        
        # Initialize WebSocket
        result = initialize_websocket(symbols)
        
        if result:
            global websocket_connected
            websocket_connected = True
            logger.info("WebSocket client initialized successfully")
        else:
            logger.warning("Failed to initialize WebSocket client")
        
        return result
    
    except Exception as e:
        logger.error(f"Error initializing WebSocket client: {str(e)}")
        return False

def start_update_thread():
    """Start background thread for ETF price updates"""
    global update_thread, stop_update_thread
    
    if update_thread and update_thread.is_alive():
        logger.info("Update thread already running")
        return
    
    # Clear event flag
    stop_update_thread.clear()
    
    # Start thread
    update_thread = threading.Thread(target=update_prices_thread)
    update_thread.daemon = True
    update_thread.start()
    
    logger.info("Started ETF price update thread")

def stop_update_thread():
    """Stop background thread for ETF price updates"""
    global update_thread, stop_update_thread
    
    if not update_thread or not update_thread.is_alive():
        logger.info("Update thread not running")
        return
    
    # Set event flag to stop thread
    stop_update_thread.set()
    
    # Wait for thread to stop (with timeout)
    update_thread.join(timeout=5)
    
    if update_thread.is_alive():
        logger.warning("Update thread did not stop cleanly")
    else:
        logger.info("Stopped ETF price update thread")

def update_prices_thread():
    """Background thread for updating ETF prices"""
    try:
        from tradelist_websocket_client import get_websocket_client
        from simplified_market_data import SimplifiedMarketDataService
        
        # Get ETF symbols to track
        symbols = SimplifiedMarketDataService.default_etfs
        logger.info(f"Starting price updates for {len(symbols)} ETFs")
        
        # Flag to recalculate scores periodically (every 15 minutes)
        last_score_update = datetime.now()
        
        while not stop_update_thread.is_set():
            try:
                # Get WebSocket client
                ws_client = get_websocket_client()
                
                if not ws_client:
                    logger.warning("WebSocket client not available")
                    time.sleep(10)
                    continue
                
                # Get latest prices
                updates = {}
                for symbol in symbols:
                    price_data = ws_client.get_latest_price(symbol)
                    if price_data:
                        updates[symbol] = price_data
                
                # Update price_updates dictionary
                if updates:
                    global price_updates
                    price_updates.update(updates)
                    logger.info(f"Received data for {len(updates)} symbols via WebSocket")
                
                # Update ETF scores (every 15 minutes)
                now = datetime.now()
                if (now - last_score_update).total_seconds() > 900:  # 15 minutes
                    logger.info("Scheduled recalculation of ETF technical scores (15-minute interval)")
                    for symbol in symbols:
                        try:
                            # Get real-time price
                            price_data = updates.get(symbol)
                            price = price_data.get('price') if price_data else None
                            
                            # Force refresh of score
                            SimplifiedMarketDataService.get_etf_score(symbol, force_refresh=True, price_override=price)
                        except Exception as e:
                            logger.warning(f"Error calculating new score for {symbol}: {str(e)}")
                    
                    # Update timestamp
                    last_score_update = now
                
                # Update existing scores with new prices
                for symbol, price_data in updates.items():
                    try:
                        price = price_data.get('price') if price_data else None
                        if price:
                            # Get cached score (don't recalculate)
                            score, old_price, indicators = SimplifiedMarketDataService.get_etf_score(
                                symbol, 
                                force_refresh=False,
                                price_override=price
                            )
                            if score is not None and price != old_price:
                                logger.info(f"Updated {symbol} price to ${price} from WebSocket (keeping score {score}/5)")
                    except Exception as e:
                        logger.warning(f"Error updating price for {symbol}: {str(e)}")
                
                # Sleep for 5 seconds
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Error in update thread: {str(e)}")
                time.sleep(10)
        
        logger.info("ETF price update thread stopped")
    
    except Exception as e:
        logger.error(f"Error in update thread (outer): {str(e)}")

# Define routes
@app.route('/')
def index():
    """Home page (ETF Scoreboard)"""
    try:
        from simplified_market_data import SimplifiedMarketDataService
        
        # Get ETF scores
        etf_scores = SimplifiedMarketDataService.analyze_etfs(
            SimplifiedMarketDataService.default_etfs
        )
        
        # Create list of ETFs with scores and prices
        etfs = []
        for symbol, data in etf_scores.items():
            if 'error' in data:
                continue
                
            etf = {
                'symbol': symbol,
                'score': data.get('score', 0),
                'price': data.get('price', 0),
                'sector': data.get('sector', 'Unknown'),
                'indicators': data.get('indicators', {})
            }
            etfs.append(etf)
        
        # Sort ETFs by score (highest first)
        etfs.sort(key=lambda x: x['score'], reverse=True)
        
        return render_template('index.html', 
                              etfs=etfs, 
                              websocket_connected=websocket_connected)
    
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/backtest')
def backtest():
    """Backtesting page"""
    try:
        return render_template('backtest.html')
    
    except Exception as e:
        logger.error(f"Error rendering backtest page: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/how-to-use')
def how_to_use():
    """How to use page"""
    try:
        return render_template('how_to_use.html')
    
    except Exception as e:
        logger.error(f"Error rendering how to use page: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/live-classes')
def live_classes():
    """Live classes page"""
    try:
        return render_template('live_classes.html')
    
    except Exception as e:
        logger.error(f"Error rendering live classes page: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/special-offer')
def special_offer():
    """Special offer page"""
    try:
        return render_template('special_offer.html')
    
    except Exception as e:
        logger.error(f"Error rendering special offer page: {str(e)}")
        return render_template('error.html', error=str(e))

@app.teardown_appcontext
def shutdown_session(exception=None):
    """Clean up database session on app context teardown"""
    db.session.remove()

# Register cleanup functions
@atexit.register
def shutdown_handler():
    """Clean up resources on shutdown"""
    logger.info("Shutting down application...")
    
    # Stop update thread
    stop_update_thread()
    
    # Stop background tasks
    try:
        from background_tasks import BackgroundTaskService
        BackgroundTaskService.stop_worker()
    except (ImportError, Exception) as e:
        logger.warning(f"Error stopping background tasks: {str(e)}")
    
    # Close WebSocket connection
    try:
        from tradelist_websocket_client import close_websocket
        close_websocket()
    except (ImportError, Exception) as e:
        logger.warning(f"Error closing WebSocket: {str(e)}")

# Initialize database
with app.app_context():
    # Import models here
    import models
    
    # Create database tables
    db.create_all()
    
    # Initialize database
    from database import init_db
    init_db(app)
    
    # Initialize WebSocket client
    initialize_websocket_client()
    
    # Start ETF price update thread
    start_update_thread()
    
    # Start background task worker
    try:
        from background_tasks import BackgroundTaskService
        BackgroundTaskService.start_worker()
    except (ImportError, Exception) as e:
        logger.warning(f"Error starting background task worker: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)