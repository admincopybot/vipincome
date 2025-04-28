from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import logging
import os
import threading
import time
from dotenv import load_dotenv
from datetime import datetime
import simplified_market_data as market_data  # Using simplified market data service with reliable indicators
from tradelist_client import TradeListApiService
from tradelist_websocket_client import get_websocket_client

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "income_machine_demo")

# Initialize with default data including indicators (this will be updated with real market data)
# Default indicator template for initial state
default_indicators = {
    'trend1': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading...'},
    'trend2': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading...'},
    'snapback': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading...'},
    'momentum': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading...'},
    'stabilizing': {'pass': False, 'current': 0, 'threshold': 0, 'description': 'Data loading...'}
}

etf_scores = {
    "XLC": {"name": "Communication Services", "score": 3, "price": 79.42, "indicators": default_indicators.copy()},
    "XLF": {"name": "Financial", "score": 4, "price": 47.69, "indicators": default_indicators.copy()},
    "XLV": {"name": "Health Care", "score": 3, "price": 137.98, "indicators": default_indicators.copy()},
    "XLI": {"name": "Industrial", "score": 3, "price": 127.23, "indicators": default_indicators.copy()},
    "XLP": {"name": "Consumer Staples", "score": 4, "price": 81.33, "indicators": default_indicators.copy()},
    "XLY": {"name": "Consumer Discretionary", "score": 3, "price": 189.89, "indicators": default_indicators.copy()},
    "XLE": {"name": "Energy", "score": 3, "price": 79.71, "indicators": default_indicators.copy()},
    "XLB": {"name": "Materials", "score": 3, "price": 81.38, "indicators": default_indicators.copy()},
    "XLU": {"name": "Utilities", "score": 4, "price": 77.94, "indicators": default_indicators.copy()},
    "XLRE": {"name": "Real Estate", "score": 3, "price": 40.02, "indicators": default_indicators.copy()}
}

# Data update tracking 
# Cache control variables
last_update_time = 0  # Set to 0 to force immediate update at startup
update_interval = 5 * 60  # 5 minutes (reduced to ensure more frequent real-time updates)
force_refresh = False  # Flag to force refresh regardless of time interval

def update_market_data_background():
    """Background thread to update market data periodically"""
    global etf_scores, last_update_time, force_refresh
    
    while True:
        current_time = time.time()
        
        # Update at app startup, on interval, or when forced refresh is requested
        if current_time - last_update_time > update_interval or force_refresh:
            try:
                logger.info("Updating market data...")
                # Add a cache-busting parameter to ensure fresh data
                new_data = market_data.update_market_data(force_refresh=True)
                
                if new_data and len(new_data) > 0:
                    # Update data while preserving any ETFs that might not be in the new data
                    for symbol, data in new_data.items():
                        etf_scores[symbol] = data
                    
                    last_update_time = current_time
                    force_refresh = False  # Reset the force refresh flag
                    logger.info(f"Market data updated. {len(new_data)} ETFs processed.")
                else:
                    logger.warning("No market data received in update.")
                    
            except Exception as e:
                logger.error(f"Error updating market data: {str(e)}")
        
        # Sleep for a shorter interval (30 seconds) to be more responsive to force_refresh requests
        time.sleep(30)

# Helper function that previously added star elements (now disabled)
def add_stars_to_template(template_str):
    """Previously added star elements, now just returns the original template"""
    return template_str

# Initialize WebSocket connection for real-time data
def initialize_websocket_client():
    """Initialize and connect to TheTradeList WebSocket API"""
    try:
        logger.info("Initializing WebSocket connection to TheTradeList API...")
        ws_client = get_websocket_client()
        if ws_client:
            # Add all our ETF symbols to track
            ws_client.symbols_to_track = market_data.SimplifiedMarketDataService.default_etfs.copy()
            
            # Connect to the WebSocket
            success = ws_client.connect()
            if success:
                logger.info(f"WebSocket client initialized with {len(ws_client.symbols_to_track)} symbols to track")
                
                # Register a callback to update our data when new data arrives
                ws_client.add_data_update_callback(on_websocket_data_update)
                return True
            else:
                logger.error("Failed to connect WebSocket client")
        else:
            logger.error("Failed to get WebSocket client instance - check API key")
    except Exception as e:
        logger.error(f"Error initializing WebSocket client: {str(e)}")
    
    return False

def on_websocket_data_update(updates):
    """Callback function when new data is received from WebSocket"""
    global etf_scores, force_refresh
    
    try:
        # Log the updates
        logger.info(f"Received real-time updates for {len(updates)} symbols via WebSocket")
        
        # Process each symbol that was updated
        for symbol, data in updates.items():
            if symbol in etf_scores:
                # Update our ETF scores with the new price data
                sector_name = market_data.SimplifiedMarketDataService.etf_sectors.get(symbol, symbol)
                price = data.get('price', 0)
                
                if price > 0:
                    # Immediately calculate score with this price
                    new_score, _, indicators = market_data.SimplifiedMarketDataService._calculate_etf_score(
                        symbol, 
                        force_refresh=True,
                        price_override=price
                    )
                    
                    # Update all ETF data with real-time price and fresh score
                    etf_scores[symbol]['price'] = price
                    etf_scores[symbol]['score'] = new_score
                    etf_scores[symbol]['source'] = data.get('data_source', 'TheTradeList WebSocket')
                    etf_scores[symbol]['indicators'] = indicators
                    
                    # Log the update
                    logger.info(f"Updated {symbol} price to ${price:.2f} from WebSocket with score {new_score}/5")
    except Exception as e:
        logger.error(f"Error processing WebSocket data update: {str(e)}")

# Start background thread for market data updates
update_thread = threading.Thread(target=update_market_data_background, daemon=True)
update_thread.start()

# Initialize WebSocket connection
initialize_websocket_client()

# Global CSS variable defined below with the strategy descriptions

# Create dummy data for option recommendations with debit spread structure
recommended_trades = {
    "XLC": {
        "Aggressive": {
            "strike": 77.50, "upper_strike": 78.50, "spread_width": 1.0,
            "expiration": "2025-04-19", "dte": 7, "roi": "32%", 
            "premium": 0.32, "pct_otm": -2.0, "max_profit": 0.68, "max_loss": 0.32
        },
        "Steady": {
            "strike": 77.00, "upper_strike": 78.00, "spread_width": 1.0,
            "expiration": "2025-05-02", "dte": 21, "roi": "24%", 
            "premium": 0.47, "pct_otm": -1.5, "max_profit": 0.53, "max_loss": 0.47
        },
        "Passive": {
            "strike": 76.50, "upper_strike": 77.50, "spread_width": 1.0,
            "expiration": "2025-05-23", "dte": 42, "roi": "18%", 
            "premium": 0.54, "pct_otm": -1.0, "max_profit": 0.46, "max_loss": 0.54
        }
    },
    "XLF": {
        "Aggressive": {
            "strike": 45.50, "upper_strike": 46.50, "spread_width": 1.0,
            "expiration": "2025-04-19", "dte": 7, "roi": "28%", 
            "premium": 0.35, "pct_otm": -2.5, "max_profit": 0.65, "max_loss": 0.35
        },
        "Steady": {
            "strike": 45.00, "upper_strike": 46.00, "spread_width": 1.0,
            "expiration": "2025-05-02", "dte": 21, "roi": "22%", 
            "premium": 0.48, "pct_otm": -1.8, "max_profit": 0.52, "max_loss": 0.48
        },
        "Passive": {
            "strike": 44.50, "upper_strike": 45.50, "spread_width": 1.0,
            "expiration": "2025-05-23", "dte": 42, "roi": "17%", 
            "premium": 0.56, "pct_otm": -1.2, "max_profit": 0.44, "max_loss": 0.56
        }
    },
    "XLV": {
        "Aggressive": {
            "strike": 133.50, "upper_strike": 134.50, "spread_width": 1.0,
            "expiration": "2025-04-19", "dte": 7, "roi": "26%", 
            "premium": 0.41, "pct_otm": -2.5, "max_profit": 0.59, "max_loss": 0.41
        },
        "Steady": {
            "strike": 133.00, "upper_strike": 134.00, "spread_width": 1.0,
            "expiration": "2025-05-02", "dte": 21, "roi": "19%", 
            "premium": 0.54, "pct_otm": -2.0, "max_profit": 0.46, "max_loss": 0.54
        },
        "Passive": {
            "strike": 132.50, "upper_strike": 133.50, "spread_width": 1.0,
            "expiration": "2025-05-23", "dte": 42, "roi": "14%", 
            "premium": 0.62, "pct_otm": -1.5, "max_profit": 0.38, "max_loss": 0.62
        }
    },
    "XLI": {
        "Aggressive": {
            "strike": 122.50, "upper_strike": 123.50, "spread_width": 1.0,
            "expiration": "2025-04-19", "dte": 7, "roi": "30%", 
            "premium": 0.38, "pct_otm": -2.5, "max_profit": 0.62, "max_loss": 0.38
        },
        "Steady": {
            "strike": 122.00, "upper_strike": 123.00, "spread_width": 1.0,
            "expiration": "2025-05-02", "dte": 21, "roi": "23%", 
            "premium": 0.46, "pct_otm": -2.0, "max_profit": 0.54, "max_loss": 0.46
        },
        "Passive": {
            "strike": 121.50, "upper_strike": 122.50, "spread_width": 1.0,
            "expiration": "2025-05-23", "dte": 42, "roi": "16%", 
            "premium": 0.53, "pct_otm": -1.6, "max_profit": 0.47, "max_loss": 0.53
        }
    },
    "XLP": {
        "Aggressive": {
            "strike": 78.50, "upper_strike": 79.50, "spread_width": 1.0,
            "expiration": "2025-04-19", "dte": 7, "roi": "27%", 
            "premium": 0.34, "pct_otm": -2.3, "max_profit": 0.66, "max_loss": 0.34
        },
        "Steady": {
            "strike": 78.00, "upper_strike": 79.00, "spread_width": 1.0,
            "expiration": "2025-05-02", "dte": 21, "roi": "20%", 
            "premium": 0.51, "pct_otm": -1.8, "max_profit": 0.49, "max_loss": 0.51
        },
        "Passive": {
            "strike": 77.50, "upper_strike": 78.50, "spread_width": 1.0,
            "expiration": "2025-05-23", "dte": 42, "roi": "15%", 
            "premium": 0.61, "pct_otm": -1.2, "max_profit": 0.39, "max_loss": 0.61
        }
    },
    "XLY": {
        "Aggressive": {
            "strike": 185.50, "upper_strike": 186.50, "spread_width": 1.0,
            "expiration": "2025-04-19", "dte": 7, "roi": "34%", 
            "premium": 0.30, "pct_otm": -2.2, "max_profit": 0.70, "max_loss": 0.30
        },
        "Steady": {
            "strike": 185.00, "upper_strike": 186.00, "spread_width": 1.0,
            "expiration": "2025-05-02", "dte": 21, "roi": "26%", 
            "premium": 0.45, "pct_otm": -1.7, "max_profit": 0.55, "max_loss": 0.45
        },
        "Passive": {
            "strike": 184.50, "upper_strike": 185.50, "spread_width": 1.0,
            "expiration": "2025-05-23", "dte": 42, "roi": "19%", 
            "premium": 0.51, "pct_otm": -1.3, "max_profit": 0.49, "max_loss": 0.51
        }
    },
    "XLE": {
        "Aggressive": {
            "strike": 77.00, "upper_strike": 78.00, "spread_width": 1.0,
            "expiration": "2025-04-19", "dte": 7, "roi": "31%", 
            "premium": 0.32, "pct_otm": -2.4, "max_profit": 0.68, "max_loss": 0.32
        },
        "Steady": {
            "strike": 76.50, "upper_strike": 77.50, "spread_width": 1.0,
            "expiration": "2025-05-02", "dte": 21, "roi": "24%", 
            "premium": 0.44, "pct_otm": -1.9, "max_profit": 0.56, "max_loss": 0.44
        },
        "Passive": {
            "strike": 76.00, "upper_strike": 77.00, "spread_width": 1.0,
            "expiration": "2025-05-23", "dte": 42, "roi": "18%", 
            "premium": 0.54, "pct_otm": -1.3, "max_profit": 0.46, "max_loss": 0.54
        }
    }
}

# Strategy descriptions
strategy_descriptions = {
    "Aggressive": "Weekly call debit spreads (7-15 DTE) with higher ROI potential (20-35%) targeting in-the-money positions for greater probability of success but requiring more active management.",
    "Steady": "Bi-weekly call debit spreads (14-30 DTE) balancing ROI (18-25%) with moderate management needs and balanced risk/reward ratios.",
    "Passive": "Monthly call debit spreads (30-45 DTE) with lower but steady ROI (15-20%) prioritizing high-probability trade setups and requiring less frequent management."
}

# Global CSS for Apple-like minimalist design
# Common HTML components for templates

# Removed all stars per user request
star_elements = ""

logo_header = """
<!-- Countdown Banner -->
<div class="countdown-banner">
    <div class="container">
        <span class="countdown-banner-text">Free Income Machine Experience Ends in</span>
        <span id="countdown-banner-timer">67D 04H 42M 18S</span>
    </div>
</div>

<header class="py-3 mb-4 border-bottom">
    <div class="container-fluid d-flex flex-wrap justify-content-between align-items-end" style="padding-left: 0;">
        <!-- Left section: Logo -->
        <div style="min-width: 300px; margin-left: 15px;">
            <a href="/" style="display: block;">
                <img src="/static/images/incomemachine_horizontallogo.png" alt="Nate Tucci's Income Machine" height="80" style="cursor: pointer; margin: 10px 0;">
            </a>
        </div>
        
        <!-- Right section: Navigation -->
        <nav class="d-flex flex-wrap align-items-center" style="padding-bottom: 10px;">
            <a href="/how-to-use" class="text-decoration-none mx-2" style="font-size: 14px; font-weight: 500; color: rgba(255, 255, 255, 0.8); transition: all 0.2s ease;">How to Use</a>
            <a href="/live-classes" class="text-decoration-none mx-2" style="font-size: 14px; font-weight: 500; color: rgba(255, 255, 255, 0.8); transition: all 0.2s ease;">Trade Classes</a>
            <a href="/special-offer" class="ms-2" style="font-size: 14px; font-weight: 600; color: #000; background: #FFD700; padding: 5px 10px; border-radius: 20px; text-decoration: none; transition: all 0.2s ease; box-shadow: 0 2px 8px rgba(255, 215, 0, 0.4);">Get 50% OFF</a>
        </nav>
        
        <!-- Removed countdown from navigation bar as it's now in the banner -->
    </div>
</header>
<script>
// Countdown timer to June 20, 2025
function updateCountdown() {
    const endDate = new Date("June 20, 2025 23:59:59").getTime();
    const now = new Date().getTime();
    const timeLeft = endDate - now;
    
    const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
    
    // Update the countdown timer
    const timerText = `${days}D ${hours}H ${minutes}M ${seconds}S`;
    document.getElementById("countdown-banner-timer").innerHTML = timerText;
}

// Update the countdown every second
setInterval(updateCountdown, 1000);
updateCountdown(); // Initial call
</script>
<style>
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(121, 112, 255, 0.4); transform: scale(1); }
    50% { box-shadow: 0 0 0 8px rgba(0, 200, 255, 0.2); transform: scale(1.03); }
    100% { box-shadow: 0 0 0 0 rgba(121, 112, 255, 0); transform: scale(1); }
}
nav a:hover {
    color: rgba(255, 255, 255, 1) !important;
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
}
nav a:last-child:hover {
    background: #ffc107;
    color: #000 !important;
    box-shadow: 0 4px 12px rgba(255, 215, 0, 0.5);
    transform: translateY(-1px);
}
</style>
"""

global_css = """
    /* Simple Countdown Banner */
    .countdown-banner {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 1000;
        background: linear-gradient(90deg, #00C8FF, #7970FF);
        color: white;
        text-align: center;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
        height: 30px;
        line-height: 30px;
    }
    
    .countdown-banner .container {
        padding: 0;
        height: 100%;
    }
    
    .countdown-banner-text {
        padding-right: 8px;
    }
    
    #countdown-banner-timer {
        background: rgba(255, 255, 255, 0.2);
        padding: 0 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    
    /* Add space at the top for the fixed banner */
    body {
        padding-top: 30px;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        letter-spacing: -0.015em;
        background: #151521;
        min-height: 100vh;
        color: rgba(255, 255, 255, 0.95);
        position: relative;
        overflow-x: hidden;
    }
    
    /* Vibrant background with space dust effect */
    body::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -2;
        background: 
            radial-gradient(circle at 20% 30%, rgba(41, 94, 163, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(100, 82, 255, 0.25) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.05) 0%, transparent 100%),
            linear-gradient(#151521, #161628);
        opacity: 1;
        animation: pulseBackground 15s ease-in-out infinite alternate;
    }
    
    /* Space dust particles */
    body::after {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
        background-image: 
            radial-gradient(circle at 40% 20%, rgba(255, 255, 255, 0.25) 0%, rgba(255, 255, 255, 0) 1.5%),
            radial-gradient(circle at 30% 60%, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0) 1.5%),
            radial-gradient(circle at 70% 50%, rgba(100, 210, 255, 0.2) 0%, rgba(255, 255, 255, 0) 1.5%),
            radial-gradient(circle at 60% 80%, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0) 1.5%),
            radial-gradient(circle at 20% 40%, rgba(100, 82, 255, 0.2) 0%, rgba(255, 255, 255, 0) 1.5%),
            radial-gradient(circle at 80% 30%, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0) 1.5%),
            radial-gradient(circle at 10% 70%, rgba(100, 210, 255, 0.2) 0%, rgba(255, 255, 255, 0) 1.5%),
            radial-gradient(circle at 90% 85%, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0) 1.5%);
        background-size: 200% 200%;
        animation: moveDust 40s linear infinite;
        opacity: 1;
    }
    
    @keyframes pulseBackground {
        0% {
            background-position: 0% 0%;
        }
        100% {
            background-position: 100% 100%;
        }
    }
    
    @keyframes moveDust {
        0% {
            background-position: 0% 0%;
        }
        50% {
            background-position: 100% 100%;
        }
        100% {
            background-position: 0% 0%;
        }
    }
    
    /* Stars removed as requested */
    
    /* Gradient Elements */
    .progress-bar {
        background: linear-gradient(90deg, #00C8FF, #7970FF) !important;
    }
    
    .step.active {
        background: linear-gradient(135deg, #00C8FF, #7970FF) !important;
        color: white;
    }
    
    .step.completed {
        background-color: #00C8FF !important;
        color: white;
    }
    
    .step.upcoming {
        background-color: #6c757d !important;
        color: white;
    }
    
    .btn[style*="background: linear-gradient"]:hover {
        background: linear-gradient(135deg, #33D5FF, #9088FF) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(121, 112, 255, 0.35) !important;
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
    
    .display-6 {
        font-weight: 700;
        letter-spacing: -0.04em;
    }
    
    /* Monochromatic sleek card styling */
    .card {
        border: none;
        border-radius: 16px;
        background: rgba(25, 25, 28, 0.6);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        overflow: hidden;
        margin-bottom: 1.5rem;
    }
    
    .card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
    }
    
    .card-header {
        border-bottom: none;
        padding: 1.5rem;
        background: rgba(40, 40, 45, 0.6);
    }
    
    .card-body {
        padding: 1.75rem;
    }
    
    /* Apple-style buttons */
    .btn {
        border-radius: 12px;
        font-weight: 500;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
        letter-spacing: -0.01em;
        font-size: 0.95rem;
        border: none;
    }
    
    .btn-sm {
        border-radius: 8px;
        padding: 0.4rem 1rem;
        font-size: 0.85rem;
    }
    
    .btn-outline-light {
        background: rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .btn-outline-light:hover {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.25);
        color: white;
        transform: translateY(-1px);
    }
    
    .btn-primary {
        background: rgba(100, 108, 255, 0.8);
        color: white;
    }
    
    .btn-primary:hover {
        background: rgba(110, 118, 255, 1);
        transform: translateY(-1px);
    }
    
    .btn-danger {
        background: rgba(255, 69, 58, 0.8);
        color: white;
    }
    
    .btn-danger:hover {
        background: rgba(255, 69, 58, 1);
        transform: translateY(-1px);
    }
    
    .btn-secondary {
        background: rgba(100, 100, 100, 0.3);
        color: rgba(255, 255, 255, 0.9);
    }
    
    .btn-secondary:hover {
        background: rgba(100, 100, 100, 0.4);
        color: white;
        transform: translateY(-1px);
    }
    
    .btn-success {
        background: rgba(48, 209, 88, 0.8);
    }
    
    .btn-success:hover {
        background: rgba(48, 209, 88, 1);
        transform: translateY(-1px);
    }
    
    /* Progress bars */
    .progress {
        height: 0.5rem;
        border-radius: 100px;
        overflow: hidden;
        background: rgba(40, 40, 45, 0.3);
    }
    
    /* Step indicators styled like image provided */
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin: 2.5rem 0;
        gap: 10px;
    }
    
    .step {
        flex: 1;
        border-radius: 8px;
        padding: 0.8rem 0.5rem;
        text-align: center;
        font-weight: 500;
        background: rgba(60, 60, 70, 0.3);
        color: white;
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        transition: all 0.3s ease;
        cursor: pointer;
        text-decoration: none;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .step:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .step.active {
        background: linear-gradient(90deg, #555555, #777777);
        color: white;
        font-weight: 600;
    }
    
    .step.completed {
        background: linear-gradient(90deg, #00C8FF, #0088FF);
        color: white;
        font-weight: 600;
    }
    
    .step.step1.completed {
        background: linear-gradient(90deg, #00C8FF, #30BBFF);
    }
    
    .step.step2.completed {
        background: linear-gradient(90deg, #30BBFF, #4E9FFF);
    }
    
    .step.step3 {
        background: linear-gradient(90deg, #4E9FFF, #7970FF);
    }
    
    .step.step4 {
        background: linear-gradient(90deg, #7970FF, #9760FF);
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
        background: rgba(28, 28, 30, 0.7) !important;
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
        color: rgba(255, 255, 255, 0.95) !important;
        padding: 0.75rem 1.5rem;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 0.05em;
    }
    
    td {
        padding: 1.25rem 1.5rem;
        vertical-align: middle;
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    tbody tr {
        background: rgba(28, 28, 30, 0.8);
        border-radius: 12px;
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    tbody tr:hover {
        transform: scale(1.01);
        background: rgba(38, 38, 40, 0.85);
        cursor: pointer;
    }
    
    tbody td:first-child {
        border-radius: 12px 0 0 12px;
        font-weight: 600;
    }
    
    tbody td:last-child {
        border-radius: 0 12px 12px 0;
    }
    
    .table {
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Strategy card styling - with modern gradients */
    .card-aggressive .card-header {
        background: linear-gradient(135deg, rgba(100, 82, 255, 0.8), rgba(255, 69, 58, 0.8));
        border-top: none;
        border-radius: 8px 8px 0 0;
    }
    
    .card-steady .card-header {
        background: linear-gradient(135deg, rgba(64, 156, 255, 0.8), rgba(100, 82, 255, 0.8));
        border-top: none;
        border-radius: 8px 8px 0 0;
    }
    
    .card-passive .card-header {
        background: linear-gradient(135deg, rgba(40, 210, 255, 0.8), rgba(64, 156, 255, 0.8));
        border-top: none;
        border-radius: 8px 8px 0 0;
    }
    
    /* Modern badge styling */
    .badge {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 500;
        letter-spacing: -0.01em;
    }
    
    .badge.bg-primary {
        background: rgba(100, 108, 255, 0.8) !important;
    }
    
    /* Logo style */
    .logo-text {
        letter-spacing: -0.05em;
        font-weight: 700;
        font-size: 1.4rem;
    }
    
    /* Container refinement */
    .container {
        padding: 2rem;
        max-width: 1200px;
    }
    
    /* Progress bar colors */
    .progress-bar-score-0 { background-color: rgba(255, 69, 58, 0.5) !important; }
    .progress-bar-score-1 { background-color: rgba(255, 69, 58, 0.7) !important; }
    .progress-bar-score-2 { background-color: rgba(255, 159, 10, 0.7) !important; }
    .progress-bar-score-3 { background-color: rgba(100, 210, 255, 0.7) !important; }
    .progress-bar-score-4 { background-color: rgba(48, 209, 88, 0.7) !important; }
    .progress-bar-score-5 { background-color: rgba(48, 209, 88, 0.9) !important; }
    
    /* Footer refinement */
    footer {
        color: rgba(255, 255, 255, 0.5);
        font-size: 0.9rem;
        padding-top: 2rem;
    }
"""

# Route for Step 1: ETF Scoreboard (Home Page)
@app.route('/')
def index():
    # Find the ETF with the highest score
    highest_score = 0
    recommended_etf = None
    
    for etf, data in etf_scores.items():
        if data['score'] > highest_score:
            highest_score = data['score']
            recommended_etf = etf
    
    # Sort ETFs by score from highest to lowest
    sorted_etfs = dict(sorted(etf_scores.items(), key=lambda item: item[1]['score'], reverse=True))
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine DEMO - Daily ETF Scoreboard</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.0/font/bootstrap-icons.css">
        <style>
            {{ global_css }}
            
            /* Page-specific styles */
            .progress-bar-score-0 { width: 0%; }
            .progress-bar-score-1 { width: 20%; }
            .progress-bar-score-2 { width: 40%; }
            .progress-bar-score-3 { width: 60%; }
            .progress-bar-score-4 { width: 80%; }
            .progress-bar-score-5 { width: 100%; }
            .step-indicator {
                display: flex;
                justify-content: space-between;
                margin-bottom: 2rem;
            }
            .step {
                width: 23%;
                text-align: center;
                padding: 0.5rem 0;
                border-radius: 4px;
                position: relative;
            }
            .step.active {
                background-color: var(--bs-primary);
                color: white;
            }
            .step.completed {
                background-color: var(--bs-success);
                color: white;
            }
            .step.upcoming {
                background-color: var(--bs-secondary);
                color: white;
            }
            .recommended-asset {
                position: absolute;
                top: -12px;
                left: 50%;
                transform: translateX(-50%);
                background: #FFD700;
                color: #000;
                font-size: 0.75rem;
                font-weight: 700;
                padding: 6px 15px;
                border-radius: 50px;
                box-shadow: 0 2px 8px rgba(255, 215, 0, 0.4);
                white-space: nowrap;
                z-index: 100;
                min-height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .trophy-icon {
                color: #000;
                margin-right: 6px;
                font-size: 14px;
            }
            .card-highlight {
                transform: scale(1.02);
                box-shadow: 0 8px 25px rgba(255, 215, 0, 0.2) !important;
                border: 1px solid rgba(255, 215, 0, 0.3) !important;
            }
            .btn[style*="background: linear-gradient"]:hover {
                background: linear-gradient(135deg, #33D5FF, #9088FF) !important;
                transform: translateY(-2px);
                box-shadow: 0 6px 15px rgba(121, 112, 255, 0.35) !important;
            }
            .btn[style*="background: #FFD700"]:hover {
                background: #ffc107 !important;
                transform: translateY(-2px);
                box-shadow: 0 6px 15px rgba(255, 215, 0, 0.35) !important;
            }
            .btn[style*="background: #00C8FF"]:hover {
                background: #33D5FF !important;
                transform: translateY(-2px);
                box-shadow: 0 6px 15px rgba(0, 200, 255, 0.35) !important;
            }
            .progress-bar {
                background: linear-gradient(90deg, #00C8FF, #7970FF) !important;
            }
        </style>
    </head>
    <body data-bs-theme="dark">
        <!-- Countdown Banner -->
        <div class="countdown-banner">
            <div class="container">
                <span class="countdown-banner-text">Free Income Machine Experience Ends in</span>
                <span id="countdown-banner-timer"></span>
            </div>
        </div>
        
        <script>
        // Countdown timer to June 20, 2025
        function updateCountdown() {
            const endDate = new Date("June 20, 2025 23:59:59").getTime();
            const now = new Date().getTime();
            const timeLeft = endDate - now;
            
            const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
            
            document.getElementById("countdown-banner-timer").innerHTML = 
                days + "D " + hours + "H " + minutes + "M " + seconds + "S";
        }

        // Update the countdown every second
        setInterval(updateCountdown, 1000);
        updateCountdown(); // Initial call
        </script>
        
        <div class="container py-4">
            {{ logo_header|safe }}
            {% if all_zero_prices %}
            <div class="alert alert-danger mb-4" role="alert">
                <h4 class="alert-heading"><i class="bi bi-exclamation-triangle-fill"></i> API Connection Issue</h4>
                <p>The TradeList API is currently unavailable. The system is showing placeholder data until the connection is restored.</p>
                <hr>
                <p class="mb-0">Our team has been notified and is working to resolve this issue. Please check back later.</p>
            </div>
            {% endif %}
            
            <div class="step-indicator mb-4">
                <a href="#" class="step step1 active">
                    Step 1: Scoreboard
                </a>
                <!-- Hide all future steps -->
            </div>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">Daily ETF Scoreboard</h2>
                    <p class="fs-5">Select an ETF with a score of 3+ for the highest probability income opportunity.</p>
                </div>
            </div>
    
            <div class="row">
                {% for etf, data in etfs.items() %}
                <div class="col-md-4 mb-4">
                    <div class="card h-100 position-relative {{ 'card-highlight' if etf == recommended_etf else '' }}" style="background: rgba(28, 28, 30, 0.8); border-radius: 20px; overflow: visible; border: none; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); transition: all 0.3s ease;">

                        <div class="card-body p-4">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h3 class="card-title mb-0" style="font-weight: 700; font-size: 1.8rem; letter-spacing: -0.02em;">{{ etf }}</h3>
                                <span class="badge" style="font-size: 0.9rem; padding: 0.5rem 1rem; border-radius: 20px; background: {{ 'linear-gradient(135deg, #00C8FF, #7970FF)' if data.score >= 4 else '#FFD700' if data.score >= 3 else '#6c757d' }}; color: {{ '#fff' if data.score >= 4 else '#000' if data.score >= 3 else '#fff' }};">{{ data.score }}/5</span>
                            </div>
                            
                            <p class="text-light mb-1" style="font-size: 1.1rem; opacity: 0.9;">{{ data.name }}</p>
                            {% if data.price > 0 %}
                                <p class="text-light mb-3" style="font-size: 1.5rem; font-weight: 600;">${{ "%.2f"|format(data.price) }}</p>
                            {% else %}
                                <p class="text-danger mb-3" style="font-size: 1.1rem; font-weight: 500;">
                                    <i class="bi bi-exclamation-triangle-fill"></i> API Connection Issue
                                </p>
                                <p class="text-light mb-3" style="font-size: 0.9rem; opacity: 0.7;">
                                    The TradeList API is currently unavailable
                                </p>
                            {% endif %}
                            
                            <div class="progress mb-4" style="height: 8px; background: rgba(40, 40, 45, 0.3); overflow: hidden; border-radius: 100px;">
                                <div class="progress-bar progress-bar-score-{{ data.score }}" role="progressbar" 
                                    aria-valuenow="{{ data.score * 20 }}" aria-valuemin="0" aria-valuemax="100" style="width: {{ data.score * 20 }}%;">
                                </div>
                            </div>
                            
                            <div class="d-grid">
                                {% if etf == recommended_etf %}
                                    <a href="{{ url_for('step2', etf=etf) }}" class="btn" style="background: #FFD700; color: #000; border-radius: 14px; padding: 0.8rem; font-weight: 600; letter-spacing: -0.01em; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(255, 215, 0, 0.2);">
                                        <i class="bi bi-trophy-fill" style="margin-right: 5px;"></i> Recommended Asset
                                    </a>
                                    <div class="text-center mt-2" style="font-size: 0.8rem; color: #FFD700; font-weight: 600;">
                                        Select {{ etf }}
                                    </div>
                                {% else %}
                                    <a href="{{ url_for('step2', etf=etf) }}" class="btn" style="background: linear-gradient(135deg, #00C8FF, #7970FF); color: white; border-radius: 14px; padding: 0.8rem; font-weight: 500; letter-spacing: -0.01em; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(121, 112, 255, 0.2);">
                                        Select {{ etf }}
                                    </a>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Create a structured display order: recommended ETF at top, then rest sorted by score
    ordered_etfs = {}
    
    # First add the recommended ETF (if any)
    if recommended_etf:
        ordered_etfs[recommended_etf] = sorted_etfs[recommended_etf]
        
    # Then add all other ETFs sorted by score
    for etf, data in sorted_etfs.items():
        if etf != recommended_etf:
            ordered_etfs[etf] = data
    
    return render_template_string(template, etfs=ordered_etfs, global_css=global_css, logo_header=logo_header, recommended_etf=recommended_etf)

# Route for Step 2: Asset Review
@app.route('/step2')
def step2():
    etf = request.args.get('etf')
    if etf not in etf_scores:
        return redirect(url_for('index'))
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine DEMO - Asset Review - {{ etf }}</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            {{ global_css }}
            
            /* Page-specific styles */
            .progress-bar-score-0 { width: 0%; }
            .progress-bar-score-1 { width: 20%; }
            .progress-bar-score-2 { width: 40%; }
            .progress-bar-score-3 { width: 60%; }
            .progress-bar-score-4 { width: 80%; }
            .progress-bar-score-5 { width: 100%; }
            .step-indicator {
                display: flex;
                justify-content: space-between;
                margin-bottom: 2rem;
            }
            .step {
                width: 23%;
                text-align: center;
                padding: 0.5rem 0;
                border-radius: 4px;
                position: relative;
            }
            .step.active {
                background-color: var(--bs-primary);
                color: white;
            }
            .step.completed {
                background-color: var(--bs-success);
                color: white;
            }
            .step.upcoming {
                background-color: var(--bs-secondary);
                color: white;
            }
        </style>
    </head>
    <body data-bs-theme="dark">
        <!-- Countdown Banner -->
        <div class="countdown-banner">
            <div class="container">
                <span class="countdown-banner-text">Free Income Machine Experience Ends in</span>
                <span id="countdown-banner-timer"></span>
            </div>
        </div>
        
        <script>
        // Countdown timer to June 20, 2025
        function updateCountdown() {
            const endDate = new Date("June 20, 2025 23:59:59").getTime();
            const now = new Date().getTime();
            const timeLeft = endDate - now;
            
            const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
            
            document.getElementById("countdown-banner-timer").innerHTML = 
                days + "D " + hours + "H " + minutes + "M " + seconds + "S";
        }

        // Update the countdown every second
        setInterval(updateCountdown, 1000);
        updateCountdown(); // Initial call
        </script>
        
        <div class="container py-4">
            {{ logo_header|safe }}
            
            <div class="step-indicator mb-4">
                <a href="{{ url_for('index') }}" class="step step1 completed">
                    Step 1: Scoreboard
                </a>
                <a href="#" class="step step2 active">
                    Step 2: Asset Review
                </a>
                <!-- Hide all future steps -->
            </div>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">{{ etf }} - {{ etf_data.name }} Sector ETF</h2>
                    <p class="fs-5">Review the selected ETF details before choosing an income strategy.</p>
                </div>
            </div>
    
            <div class="row">
                <div class="col-md-6">
                    <div class="card mb-4" style="background: rgba(28, 28, 30, 0.7); border-radius: 20px; overflow: hidden;">
                        <div class="card-header" style="background: rgba(28, 28, 30, 0.9); border: none;">
                            <h4>ETF Details</h4>
                        </div>
                        <div class="card-body">
                            <p><strong>Symbol:</strong> {{ etf }}</p>
                            <p><strong>Sector:</strong> {{ etf_data.name }}</p>
                            {% if etf_data.price > 0 %}
                                <p><strong>Current Price:</strong> ${{ "%.2f"|format(etf_data.price) }}</p>
                            {% else %}
                                <p class="text-danger">
                                    <strong>Price Data:</strong> 
                                    <span class="badge bg-danger">API Connection Issue</span>
                                </p>
                                <p class="text-light" style="font-size: 0.9rem; opacity: 0.7;">
                                    The TradeList API is currently unavailable
                                </p>
                            {% endif %}
                            <p><strong>Score:</strong> {{ etf_data.score }}/5</p>
                            <div class="progress mb-3" style="height: 8px; background: rgba(40, 40, 45, 0.3); overflow: hidden; border-radius: 100px;">
                                <div class="progress-bar progress-bar-score-{{ etf_data.score }}" role="progressbar" 
                                     aria-valuenow="{{ etf_data.score * 20 }}" aria-valuemin="0" aria-valuemax="100">
                                </div>
                            </div>
                            
                            <div class="mt-4">
                                <h6 class="fw-bold">Technical Indicators:</h6>
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <span><strong>Short Term Trend</strong></span>
                                            <span class="badge rounded-pill" style="background: {{ 'linear-gradient(135deg, #00C8FF, #7970FF)' if etf_data.indicators.trend1.pass else '#6c757d' }}">
                                                {{ '✓' if etf_data.indicators.trend1.pass else '✗' }}
                                            </span>
                                        </div>
                                    </li>
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <span><strong>Long Term Trend</strong></span>
                                            <span class="badge rounded-pill" style="background: {{ 'linear-gradient(135deg, #00C8FF, #7970FF)' if etf_data.indicators.trend2.pass else '#6c757d' }}">
                                                {{ '✓' if etf_data.indicators.trend2.pass else '✗' }}
                                            </span>
                                        </div>
                                    </li>
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <span><strong>Snapback Position</strong></span>
                                            <span class="badge rounded-pill" style="background: {{ 'linear-gradient(135deg, #00C8FF, #7970FF)' if etf_data.indicators.snapback.pass else '#6c757d' }}">
                                                {{ '✓' if etf_data.indicators.snapback.pass else '✗' }}
                                            </span>
                                        </div>
                                    </li>
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <span><strong>Weekly Momentum</strong></span>
                                            <span class="badge rounded-pill" style="background: {{ 'linear-gradient(135deg, #00C8FF, #7970FF)' if etf_data.indicators.momentum.pass else '#6c757d' }}">
                                                {{ '✓' if etf_data.indicators.momentum.pass else '✗' }}
                                            </span>
                                        </div>
                                    </li>
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <span><strong>Stabilizing</strong></span>
                                            <span class="badge rounded-pill" style="background: {{ 'linear-gradient(135deg, #00C8FF, #7970FF)' if etf_data.indicators.stabilizing.pass else '#6c757d' }}">
                                                {{ '✓' if etf_data.indicators.stabilizing.pass else '✗' }}
                                            </span>
                                        </div>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card mb-4" style="background: rgba(28, 28, 30, 0.7); border-radius: 20px; overflow: hidden;">
                        <div class="card-header" style="background: rgba(28, 28, 30, 0.9); border: none;">
                            <h4>Income Potential</h4>
                        </div>
                        <div class="card-body">
                            <p>Based on the current score of <strong>{{ etf_data.score }}/5</strong>, 
                            {{ etf }} could be a {{ 'strong' if etf_data.score >= 4 else 'moderate' if etf_data.score >= 2 else 'weak' }} 
                            candidate for generating options income.</p>
                            
                            <p>The score is calculated using 5 technical indicators, with 1 point awarded for each condition met. Higher scores indicate more favorable market conditions for income opportunities.</p>
                            
                            <p><small>Data is automatically refreshed every 15 minutes during market hours.</small></p>
                            
                            <div class="d-grid gap-2 mt-4">
                                <a href="{{ url_for('step3', etf=etf) }}" class="btn btn-primary" style="padding: 0.8rem 1.5rem; border-radius: 14px; font-weight: 500; letter-spacing: -0.01em;">
                                    Choose Income Strategy →
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
    
            <div class="mt-3">
                <a href="{{ url_for('index') }}" class="btn btn-secondary">← Back to Scoreboard</a>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, etf=etf, etf_data=etf_scores[etf], global_css=global_css, logo_header=logo_header)

# Route for Step 3: Strategy Selection
@app.route('/step3')
def step3():
    etf = request.args.get('etf')
    if etf not in etf_scores:
        return redirect(url_for('index'))
    
    # Get real-time trade recommendations for each strategy
    aggressive_trade = market_data.get_trade_recommendation(etf, 'Aggressive')
    steady_trade = market_data.get_trade_recommendation(etf, 'Steady')
    passive_trade = market_data.get_trade_recommendation(etf, 'Passive')
    
    # Create a dictionary of trades for easier access in the template
    trades = {
        'Aggressive': aggressive_trade,
        'Steady': steady_trade,
        'Passive': passive_trade
    }
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine DEMO - Strategy Selection for {{ etf }}</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            {{ global_css }}
            
            /* Page-specific styles */
            .progress-bar-score-0 { width: 0%; }
            .progress-bar-score-1 { width: 20%; }
            .progress-bar-score-2 { width: 40%; }
            .progress-bar-score-3 { width: 60%; }
            .progress-bar-score-4 { width: 80%; }
            .progress-bar-score-5 { width: 100%; }
            .step-indicator {
                display: flex;
                justify-content: space-between;
                margin-bottom: 2rem;
            }
            .step {
                width: 23%;
                text-align: center;
                padding: 0.5rem 0;
                border-radius: 4px;
                position: relative;
            }
            .step.active {
                background-color: var(--bs-primary);
                color: white;
            }
            .step.completed {
                background-color: var(--bs-success);
                color: white;
            }
            .step.upcoming {
                background-color: var(--bs-secondary);
                color: white;
            }
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container py-4">
            {{ logo_header|safe }}
            
            <div class="step-indicator mb-4">
                <a href="{{ url_for('index') }}" class="step step1 completed">
                    Step 1: Scoreboard
                </a>
                <a href="{{ url_for('step2', etf=etf) }}" class="step step2 completed">
                    Step 2: Asset Review
                </a>
                <a href="#" class="step step3 active">
                    Step 3: Strategy
                </a>
                <!-- Hide all future steps -->
            </div>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">Choose an Income Strategy for {{ etf }}</h2>
                    <p class="fs-5">Select the income opportunity approach that matches your income goals and risk tolerance.</p>
                </div>
            </div>
    
            <form action="{{ url_for('step4') }}" method="get">
                <input type="hidden" name="etf" value="{{ etf }}">
                
                <style>
                    .strategy-card {
                        transition: all 0.2s ease-in-out;
                        cursor: pointer;
                        border: 2px solid transparent;
                    }
                    .strategy-card:hover {
                        transform: translateY(-5px);
                        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
                    }
                    .strategy-card input[type="radio"] {
                        position: absolute;
                        opacity: 0;
                    }
                    .strategy-card input[type="radio"]:checked + .card {
                        border: 2px solid var(--bs-info);
                        box-shadow: 0 0 15px var(--bs-info);
                    }
                    .card-header h4 {
                        margin-bottom: 0;
                    }
                    .income-metrics {
                        background: linear-gradient(45deg, rgba(100, 210, 255, 0.1), rgba(180, 100, 255, 0.1));
                        border-radius: 8px;
                        padding: 10px;
                        margin-top: 10px;
                    }
                </style>
                
                <div class="row">
                    <div class="col-md-4">
                        <label class="strategy-card w-100">
                            <input type="radio" name="strategy" id="aggressive" value="Aggressive" required>
                            <div class="card card-aggressive mb-4">
                                <div class="card-header">
                                    <h4 class="fw-bold text-white">Aggressive Income</h4>
                                </div>
                                <div class="card-body">
                                    <h5 class="card-title">Higher Risk, Higher Reward</h5>
                                    <div class="income-metrics">
                                        <ul class="list-group list-group-flush mb-3">
                                            <li class="list-group-item"><strong>DTE:</strong> {{ trades.Aggressive.dte }} days</li>
                                            <li class="list-group-item"><strong>Target ROI:</strong> {{ trades.Aggressive.roi }}</li>
                                            <li class="list-group-item"><strong>Strike Selection:</strong> {{ "%.1f"|format(trades.Aggressive.pct_otm) }}% OTM</li>
                                            <li class="list-group-item"><strong>Management:</strong> Weekly attention needed</li>
                                        </ul>
                                    </div>
                                    <p class="card-text">{{ strategy_descriptions.Aggressive }}</p>
                                </div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="col-md-4">
                        <label class="strategy-card w-100">
                            <input type="radio" name="strategy" id="steady" value="Steady" required>
                            <div class="card card-steady mb-4">
                                <div class="card-header">
                                    <h4 class="fw-bold text-white">Steady Income</h4>
                                </div>
                                <div class="card-body">
                                    <h5 class="card-title">Balanced Approach</h5>
                                    <div class="income-metrics">
                                        <ul class="list-group list-group-flush mb-3">
                                            <li class="list-group-item"><strong>DTE:</strong> {{ trades.Steady.dte }} days</li>
                                            <li class="list-group-item"><strong>Target ROI:</strong> {{ trades.Steady.roi }}</li>
                                            <li class="list-group-item"><strong>Strike Selection:</strong> {{ "%.1f"|format(trades.Steady.pct_otm) }}% OTM</li>
                                            <li class="list-group-item"><strong>Management:</strong> Bi-weekly attention</li>
                                        </ul>
                                    </div>
                                    <p class="card-text">{{ strategy_descriptions.Steady }}</p>
                                </div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="col-md-4">
                        <label class="strategy-card w-100">
                            <input type="radio" name="strategy" id="passive" value="Passive" required>
                            <div class="card card-passive mb-4">
                                <div class="card-header">
                                    <h4 class="fw-bold text-white">Passive Income</h4>
                                </div>
                                <div class="card-body">
                                    <h5 class="card-title">Lower Risk, Consistent Income</h5>
                                    <div class="income-metrics">
                                        <ul class="list-group list-group-flush mb-3">
                                            <li class="list-group-item"><strong>DTE:</strong> {{ trades.Passive.dte }} days</li>
                                            <li class="list-group-item"><strong>Target ROI:</strong> {{ trades.Passive.roi }}</li>
                                            <li class="list-group-item"><strong>Strike Selection:</strong> {{ "%.1f"|format(trades.Passive.pct_otm) }}% OTM</li>
                                            <li class="list-group-item"><strong>Management:</strong> Monthly attention</li>
                                        </ul>
                                    </div>
                                    <p class="card-text">{{ strategy_descriptions.Passive }}</p>
                                </div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <div class="d-grid gap-2 col-6 mx-auto mt-3">
                    <button type="submit" class="btn btn-primary btn-lg">Get Trade Recommendation →</button>
                </div>
                
                <div class="mt-3">
                    <a href="{{ url_for('step2', etf=etf) }}" class="btn btn-secondary">← Back to Asset Review</a>
                </div>
            </form>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, etf=etf, strategy_descriptions=strategy_descriptions, global_css=global_css, logo_header=logo_header, trades=trades)

# Route for Step 4: Trade Details
@app.route('/step4')
def step4():
    etf = request.args.get('etf')
    strategy = request.args.get('strategy')
    
    if etf not in etf_scores or strategy not in ['Aggressive', 'Steady', 'Passive']:
        return redirect(url_for('index'))
    
    # Get real-time trade recommendation from market data service
    try:
        logger.info(f"Getting trade recommendation for {etf} with {strategy} strategy")
        trade = market_data.get_trade_recommendation(etf, strategy)
        
        # Format the trade data to match our template expectations for debit spreads
        formatted_trade = {
            "strike": trade.get("strike", 0),
            "upper_strike": trade.get("upper_strike", 0),
            "spread_width": trade.get("spread_width", 1.0),
            "expiration": trade.get("expiration", "N/A"),
            "dte": trade.get("dte", 0),
            "roi": trade.get("roi", "N/A"),
            "premium": trade.get("premium", 0),
            "pct_otm": trade.get("pct_otm", 0),
            "max_profit": trade.get("max_profit", 0),
            "max_loss": trade.get("max_loss", 0)
        }
        
        logger.info(f"Trade recommendation received: {formatted_trade}")
        
    except Exception as e:
        logger.error(f"Error getting trade recommendation: {str(e)}")
        # Fallback to static data if real-time data fails
        if etf in recommended_trades and strategy in recommended_trades[etf]:
            formatted_trade = recommended_trades[etf][strategy]
            logger.warning(f"Using fallback trade data for {etf} {strategy}")
        else:
            # Create a default recommendation with debit spread structure
            current_price = etf_scores[etf]["price"]
            lower_strike = round(current_price * 0.99, 2)  # 1% ITM
            upper_strike = round(lower_strike + 1, 2)
            premium = round(current_price * 0.025, 2)  # 2.5% of current price
            max_profit = round(1 - premium, 2)
            
            formatted_trade = {
                "strike": lower_strike,
                "upper_strike": upper_strike,
                "spread_width": 1.0,
                "expiration": "N/A",
                "dte": 14,
                "roi": "20-25%",
                "premium": premium,
                "pct_otm": -1.0,  # 1% ITM
                "max_profit": max_profit,
                "max_loss": premium
            }
    
    trade = formatted_trade
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine DEMO - Trade Details - {{ etf }} {{ strategy }}</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            {{ global_css }}
            
            /* Page-specific styles */
            .progress-bar-score-0 { width: 0%; }
            .progress-bar-score-1 { width: 20%; }
            .progress-bar-score-2 { width: 40%; }
            .progress-bar-score-3 { width: 60%; }
            .progress-bar-score-4 { width: 80%; }
            .progress-bar-score-5 { width: 100%; }
            .step-indicator {
                display: flex;
                justify-content: space-between;
                margin-bottom: 2rem;
            }
            .step {
                width: 23%;
                text-align: center;
                padding: 0.5rem 0;
                border-radius: 4px;
                position: relative;
            }
            .step.active {
                background-color: var(--bs-primary);
                color: white;
            }
            .step.completed {
                background-color: var(--bs-success);
                color: white;
            }
            .step.upcoming {
                background-color: var(--bs-secondary);
                color: white;
            }
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container py-4">
            {{ logo_header|safe }}
            
            <div class="step-indicator mb-4">
                <a href="{{ url_for('index') }}" class="step step1 completed">
                    Step 1: Scoreboard
                </a>
                <a href="{{ url_for('step2', etf=etf) }}" class="step step2 completed">
                    Step 2: Asset Review
                </a>
                <a href="{{ url_for('step3', etf=etf) }}" class="step step3 completed">
                    Step 3: Strategy
                </a>
                <a href="#" class="step step4 active">
                    Step 4: Trade Details
                </a>
            </div>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">Recommended Trade</h2>
                    <p class="fs-5">{{ etf }} income opportunity with {{ strategy }} strategy</p>
                </div>
            </div>
    
            <div class="card mb-4">
                <div class="card-header">
                    <h4>Income Trade Details</h4>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <h5>Debit Spread Setup</h5>
                                <div class="p-4 rounded income-trade-box" style="background: linear-gradient(45deg, rgba(100, 210, 255, 0.1), rgba(180, 100, 255, 0.1)); border-radius: 12px;">
                                    <p class="mb-2">Buy to Open the {{ trade.expiration }} ${{ "%.2f"|format(trade.strike) }} CALL on {{ etf }}</p>
                                    <p>Sell to Open the {{ trade.expiration }} ${{ "%.2f"|format(trade.upper_strike) }} CALL on {{ etf }}</p>
                                    <hr style="border-color: rgba(255, 255, 255, 0.1);">
                                    <p class="mb-0"><strong>Expiration:</strong> {{ trade.expiration }} ({{ trade.dte }} days)</p>
                                    <p class="mb-0"><strong>Spread Width:</strong> ${{ "%.2f"|format(trade.spread_width) }}</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <div class="mb-3">
                                <h5>Debit Spread Metrics</h5>
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Entry Cost:</strong></span>
                                        <span>${{ "%.2f"|format(trade.premium) }} per share</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Target ROI:</strong></span>
                                        <span>{{ trade.roi }}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Max Risk Per Contract:</strong></span>
                                        <span>${{ "%.2f"|format(trade.premium * 100) }}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Max Profit Per Contract:</strong></span>
                                        <span>${{ "%.2f"|format(trade.max_profit * 100) }}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center" style="background: rgba(100, 210, 255, 0.05);">
                                        <span><strong>ITM/OTM Status:</strong></span>
                                        <span class="badge" style="background-color: {{ '#00C8FF' if trade.pct_otm < 0 else '#FFD700' }}; color: {{ '#fff' if trade.pct_otm < 0 else '#000' }};">
                                            {% if trade.pct_otm < 0 %}
                                                {{ "%.1f"|format(-trade.pct_otm) }}% ITM
                                            {% else %}
                                                {{ "%.1f"|format(trade.pct_otm) }}% OTM
                                            {% endif %}
                                        </span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    
                    <div class="alert alert-info mt-3" style="background-color: rgba(100, 210, 255, 0.1); border: none; border-radius: 12px; color: rgba(255, 255, 255, 0.9); padding: 1.25rem;">
                        <strong>Real-Time Data:</strong> This recommendation is based on current market data using 
                        Yahoo Finance API. Options data is refreshed when you request a new trade.
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h4>ETF Information</h4>
                        </div>
                        <div class="card-body">
                            <h5>{{ etf }} - {{ etf_data.name }} Sector ETF</h5>
                            <p><strong>Current Price:</strong> ${{ "%.2f"|format(etf_data.price) }}</p>
                            <p><strong>Strength Score:</strong> {{ etf_data.score }}/5</p>
                            <div class="progress mb-3" style="height: 8px;">
                                <div class="progress-bar progress-bar-score-{{ etf_data.score }}" role="progressbar" 
                                    aria-valuenow="{{ etf_data.score * 20 }}" aria-valuemin="0" aria-valuemax="100">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card card-{{ strategy.lower() }} mb-4">
                        <div class="card-header">
                            <h4>{{ strategy }} Strategy</h4>
                        </div>
                        <div class="card-body">
                            <p>{{ strategy_descriptions[strategy] }}</p>
                            <p><strong>Days To Expiration:</strong> {{ trade.dte }} days</p>
                            <p><strong>Target ROI:</strong> {{ trade.roi }}</p>
                        </div>
                    </div>
                </div>
            </div>
    
            <div class="mt-3">
                <a href="{{ url_for('step3', etf=etf) }}" class="btn btn-secondary me-2">← Back to Strategy Selection</a>
                <a href="{{ url_for('index') }}" class="btn btn-primary">Start New Trade Search</a>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(
        template, 
        etf=etf, 
        strategy=strategy, 
        etf_data=etf_scores[etf], 
        trade=trade,
        strategy_descriptions=strategy_descriptions,
        global_css=global_css,
        logo_header=logo_header
    )

# Route for How to Use page
@app.route('/how-to-use')
def how_to_use():
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>How to Use the Income Machine</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            {{ global_css }}
        </style>
    </head>
    <body data-bs-theme="dark">

        <div class="container py-4">
            {{ logo_header|safe }}
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">How to Use the Income Machine</h2>
                    <p class="fs-5">Learn how to get the most out of this powerful options income tool.</p>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header">
                    <h4 class="mb-0">Step-by-Step Guide</h4>
                </div>
                <div class="card-body">
                    <h5>1. Check the ETF Scoreboard</h5>
                    <p>The scoreboard ranks sector ETFs based on their current income potential. Higher scores (4-5) indicate stronger opportunities.</p>
                    
                    <h5>2. Select an ETF</h5>
                    <p>Click on an ETF with a good score to view more details about its current price and income potential.</p>
                    
                    <h5>3. Choose a Strategy</h5>
                    <p>Select between Aggressive, Steady, or Passive strategies based on your risk tolerance and how actively you want to manage your positions.</p>
                    
                    <h5>4. Review Trade Details</h5>
                    <p>See the specific income opportunity trade recommendation with strike price, expiration, potential return, and other key metrics.</p>
                </div>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, global_css=global_css, logo_header=logo_header, )

# Route for Live Classes page
@app.route('/live-classes')
def live_classes():
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine LIVE Trade Classes</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            {{ global_css }}
        </style>
    </head>
    <body data-bs-theme="dark">

        <div class="container py-4">
            {{ logo_header|safe }}
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">LIVE Trade Classes</h2>
                    <p class="fs-5">Join our weekly live sessions to learn advanced options income strategies directly from expert traders.</p>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header">
                    <h4 class="mb-0">Upcoming LIVE Classes</h4>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-4">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h5 class="mb-0">Beginners Options Income</h5>
                                </div>
                                <div class="card-body">
                                    <p><strong>Date:</strong> Every Monday, 7:00 PM ET</p>
                                    <p><strong>Duration:</strong> 60 minutes</p>
                                    <p>Learn the basics of creating income opportunities and generating consistent income with lower-risk strategies.</p>
                                    <div class="d-grid">
                                        <a href="/special-offer" class="btn btn-primary">Register Now</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6 mb-4">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h5 class="mb-0">Advanced Theta Strategies</h5>
                                </div>
                                <div class="card-body">
                                    <p><strong>Date:</strong> Every Wednesday, 8:00 PM ET</p>
                                    <p><strong>Duration:</strong> 90 minutes</p>
                                    <p>Master higher-return strategies including custom spreads, rolls, and calendar trades.</p>
                                    <div class="d-grid">
                                        <a href="/special-offer" class="btn btn-primary">Register Now</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, global_css=global_css, logo_header=logo_header, )

# Route for Special Offer page
@app.route('/special-offer')
def special_offer():
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Get Full Access for 50% OFF</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            {{ global_css }}
        </style>
    </head>
    <body data-bs-theme="dark">

        <div class="container py-4">
            {{ logo_header|safe }}
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3 text-center">
                    <h2 class="display-5 fw-bold">SPECIAL LIMITED-TIME OFFER</h2>
                    <p class="fs-4">Get full access to Income Machine at 50% off the regular price</p>
                    <p>Offer expires in: <span class="badge" style="background-color: rgba(255, 69, 58, 0.8); padding: 0.6rem 1rem; border-radius: 8px; font-weight: 500;">48 hours 23 minutes</span></p>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-8">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h4 class="mb-0">Income Machine Full Access Includes:</h4>
                        </div>
                        <div class="card-body">
                            <ul class="list-group list-group-flush mb-4">
                                <li class="list-group-item"><strong>✓</strong> Real-time ETF and options data feeds</li>
                                <li class="list-group-item"><strong>✓</strong> Advanced strategy algorithms</li>
                                <li class="list-group-item"><strong>✓</strong> Position tracking and management tools</li>
                                <li class="list-group-item"><strong>✓</strong> Email alerts for trade opportunities</li>
                                <li class="list-group-item"><strong>✓</strong> Weekly LIVE trading sessions</li>
                                <li class="list-group-item"><strong>✓</strong> Access to all recorded training sessions</li>
                                <li class="list-group-item"><strong>✓</strong> Priority email support</li>
                            </ul>
                            
                            <div class="text-center mb-3">
                                <span class="text-decoration-line-through fs-4" style="color: rgba(255, 255, 255, 0.5);">Regular Price: $197/month</span>
                                <p class="fs-1 fw-bold" style="color: rgba(48, 209, 88, 0.9);">Special Offer: $97/month</p>
                            </div>
                            
                            <div class="d-grid">
                                <a href="#" class="btn btn-lg py-3" style="background: rgba(48, 209, 88, 0.8); color: white; border-radius: 12px; transition: all 0.3s ease;">GET 50% OFF NOW</a>
                            </div>
                            <p class="text-center mt-2 small" style="color: rgba(255, 255, 255, 0.7);">No contracts. Cancel anytime.</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h4 class="mb-0">Testimonials</h4>
                        </div>
                        <div class="card-body">
                            <div class="mb-3" style="border-left: 3px solid rgba(100, 210, 255, 0.5); padding-left: 1rem;">
                                <p class="fst-italic">"The Income Machine has helped me generate an extra $1,500 per month in reliable options income. The recommended trades are clear and easy to execute."</p>
                                <p style="color: rgba(255, 255, 255, 0.7);">— Michael R.</p>
                            </div>
                            <div class="mb-3" style="border-left: 3px solid rgba(100, 210, 255, 0.5); padding-left: 1rem;">
                                <p class="fst-italic">"I've tried other options advisory services, but the Income Machine provides the most consistent returns with less risk."</p>
                                <p style="color: rgba(255, 255, 255, 0.7);">— Sarah T.</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card mb-4">
                        <div class="card-header">
                            <h4 class="mb-0">100% Money-Back Guarantee</h4>
                        </div>
                        <div class="card-body">
                            <p>Try Income Machine risk-free for 30 days. If you're not completely satisfied, we'll refund your subscription fee. No questions asked.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, global_css=global_css, logo_header=logo_header, )

# API test endpoints
@app.route('/api/test/websocket')
def test_websocket():
    """Test endpoint for TheTradeList WebSocket connection and data
    
    Query Parameters:
    - ticker: The ETF symbol to check (default: all)
    """
    ticker = request.args.get('ticker')
    
    # Get the WebSocket client
    ws_client = get_websocket_client()
    if not ws_client:
        return jsonify({
            'status': 'error',
            'message': 'WebSocket client not initialized - check API key',
            'api_key_set': os.environ.get('TRADELIST_API_KEY') is not None
        })
    
    # Check connection status
    connection_status = {
        'is_connected': ws_client.is_connected,
        'session_id': ws_client.session_id if ws_client.session_id else None,
        'symbols_tracking': ws_client.symbols_to_track,
        'reconnect_attempts': ws_client._reconnect_attempts
    }
    
    # Get data for a specific ticker or all data
    if ticker:
        data = ws_client.get_latest_price(ticker)
        
        # If no data for the requested ticker, try to subscribe
        if not data and ws_client.is_connected and ws_client.session_id:
            ws_client.subscribe_to_symbol(ticker)
            data = None  # Will be updated on next cycle
    else:
        data = ws_client.get_all_latest_data()
    
    return jsonify({
        'status': 'success',
        'connection': connection_status,
        'data': data,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/test/tradelist')
def test_tradelist_api():
    """Test endpoint for TheTradeList API integration with detailed diagnostics
    
    Query Parameters:
    - ticker: The ETF symbol to test with (default: XLK)
    - force_raw_api: Set to 'true' to test the raw API directly (default: false)
    - return_type: 'json' or 'csv' format (default: json)
    - min_stock_vol: Minimum stock volume (default: 0)
    - min_total_points: Minimum total points (default: 0)
    """
    from datetime import datetime
    import requests  # For direct API testing
    
    # Parse query parameters
    test_ticker = request.args.get('ticker', 'XLK')
    force_raw_api = request.args.get('force_raw_api', 'false').lower() == 'true'
    return_type = request.args.get('return_type', 'json')
    min_stock_vol = int(request.args.get('min_stock_vol', '0'))
    min_total_points = int(request.args.get('min_total_points', '0'))
    
    # Prepare response object
    response = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request_params": {
            "ticker": test_ticker,
            "force_raw_api": force_raw_api,
            "return_type": return_type,
            "min_stock_vol": min_stock_vol,
            "min_total_points": min_total_points
        },
        "environment": {
            "api_key_set": bool(os.environ.get("TRADELIST_API_KEY")),
            "api_enabled": TradeListApiService.USE_TRADELIST_API,
            "api_endpoints": {
                "scanner": f"{TradeListApiService.TRADELIST_API_BASE_URL}{TradeListApiService.TRADELIST_SCANNER_ENDPOINT}",
                "highs_lows": f"{TradeListApiService.TRADELIST_API_BASE_URL}{TradeListApiService.TRADELIST_HIGHS_LOWS_ENDPOINT}"
            }
        }
    }
    
    # Test #1: API Health Check
    api_health = TradeListApiService.api_health_check()
    response["api_status"] = api_health
    
    # Test #2: Get price data through our client (always uses fallback if API fails)
    ticker_data = TradeListApiService.get_current_price(test_ticker)
    response["ticker_data"] = ticker_data
    
    # Test #3: Direct API call if requested (for diagnostics)
    if force_raw_api:
        try:
            # Get API key
            api_key = os.environ.get("TRADELIST_API_KEY", "")
            
            # Make direct API request
            api_url = f"{TradeListApiService.TRADELIST_API_BASE_URL}{TradeListApiService.TRADELIST_SCANNER_ENDPOINT}"
            params = {
                "returntype": return_type,
                "apiKey": api_key,
                "stockvol": min_stock_vol,
                "totalpoints": min_total_points
            }
            
            # First request with no redirects
            direct_response = requests.get(api_url, params=params, timeout=15, allow_redirects=False)
            
            # Record initial response
            initial_response = {
                "status_code": direct_response.status_code,
                "headers": dict(direct_response.headers),
                "url": direct_response.url
            }
            
            # If we got a redirect, follow it manually
            if direct_response.status_code == 302:
                redirect_url = direct_response.headers.get('Location')
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'User-Agent': 'IncomeMachineMVP/1.0'
                }
                
                redirected_response = requests.get(
                    f"{TradeListApiService.TRADELIST_API_BASE_URL}/{redirect_url}", 
                    headers=headers,
                    timeout=15
                )
                
                # Add redirect results
                redirect_info = {
                    "redirect_url": redirect_url,
                    "status_code": redirected_response.status_code,
                    "content_preview": redirected_response.text[:300] + ('...' if len(redirected_response.text) > 300 else '')
                }
                response["raw_api_test"] = {
                    "initial_request": initial_response,
                    "redirect_followup": redirect_info
                }
            else:
                # Just record the initial response
                initial_response["content_preview"] = direct_response.text[:300] + ('...' if len(direct_response.text) > 300 else '')
                response["raw_api_test"] = {
                    "initial_request": initial_response
                }
                
        except Exception as e:
            response["raw_api_test"] = {
                "error": str(e)
            }
    
    # Test #4: Get raw data via our client method
    if force_raw_api:
        try:
            # Get data with our client method
            raw_data = TradeListApiService.get_tradelist_data(
                test_ticker, 
                return_type=return_type,
                min_stock_vol=min_stock_vol,
                min_total_points=min_total_points
            )
            
            response["tradelist_api_data"] = raw_data
            
        except Exception as e:
            response["tradelist_api_data"] = {
                "error": str(e)
            }
    
    return jsonify(response)

# Run the Flask application
if __name__ == '__main__':
    print("Visit http://127.0.0.1:5000/ to view the Income Machine DEMO.")
    app.run(host="0.0.0.0", port=5000, debug=True)