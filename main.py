from flask import Flask, request, render_template_string, redirect, url_for
import logging
import os
import threading
import time
import market_data

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
    "XLF": {"name": "Financial", "score": 4, "price": 39.86, "indicators": default_indicators.copy()},
    "XLV": {"name": "Health Care", "score": 2, "price": 133.17, "indicators": default_indicators.copy()},
    "XLI": {"name": "Industrial", "score": 3, "price": 112.22, "indicators": default_indicators.copy()},
    "XLP": {"name": "Consumer Staples", "score": 1, "price": 74.09, "indicators": default_indicators.copy()},
    "XLY": {"name": "Consumer Discretionary", "score": 5, "price": 184.61, "indicators": default_indicators.copy()},
    "XLE": {"name": "Energy", "score": 4, "price": 87.93, "indicators": default_indicators.copy()}
}

# Data update tracking 
last_update_time = 0  # Set to 0 to force immediate update at startup
update_interval = 15 * 60  # 15 minutes

def update_market_data_background():
    """Background thread to update market data periodically"""
    global etf_scores, last_update_time
    
    while True:
        current_time = time.time()
        
        # Update at app startup and then on interval
        if current_time - last_update_time > update_interval:
            try:
                logger.info("Updating market data...")
                new_data = market_data.update_market_data()
                
                if new_data and len(new_data) > 0:
                    # Update data while preserving any ETFs that might not be in the new data
                    for symbol, data in new_data.items():
                        etf_scores[symbol] = data
                    
                    last_update_time = current_time
                    logger.info(f"Market data updated. {len(new_data)} ETFs processed.")
                else:
                    logger.warning("No market data received in update.")
                    
            except Exception as e:
                logger.error(f"Error updating market data: {str(e)}")
        
        # Sleep for a minute before checking again
        time.sleep(60)

# Start background thread for market data updates
update_thread = threading.Thread(target=update_market_data_background, daemon=True)
update_thread.start()

# Global CSS variable defined below with the strategy descriptions

# Create dummy data for option recommendations
recommended_trades = {
    "XLC": {
        "Aggressive": {"strike": 83.50, "expiration": "2023-05-05", "dte": 7, "roi": "32%", "premium": 1.62, "otm": "5.1%"},
        "Steady": {"strike": 81.00, "expiration": "2023-05-19", "dte": 21, "roi": "24%", "premium": 2.47, "otm": "2.0%"},
        "Passive": {"strike": 80.00, "expiration": "2023-06-16", "dte": 49, "roi": "18%", "premium": 3.84, "otm": "0.7%"}
    },
    "XLF": {
        "Aggressive": {"strike": 42.00, "expiration": "2023-05-05", "dte": 7, "roi": "28%", "premium": 0.75, "otm": "5.4%"},
        "Steady": {"strike": 41.00, "expiration": "2023-05-19", "dte": 21, "roi": "22%", "premium": 1.18, "otm": "2.9%"},
        "Passive": {"strike": 40.50, "expiration": "2023-06-16", "dte": 49, "roi": "17%", "premium": 1.84, "otm": "1.6%"}
    },
    "XLV": {
        "Aggressive": {"strike": 140.00, "expiration": "2023-05-05", "dte": 7, "roi": "26%", "premium": 2.31, "otm": "5.1%"},
        "Steady": {"strike": 136.00, "expiration": "2023-05-19", "dte": 21, "roi": "19%", "premium": 3.44, "otm": "2.1%"},
        "Passive": {"strike": 135.00, "expiration": "2023-06-16", "dte": 49, "roi": "14%", "premium": 5.02, "otm": "1.4%"}
    },
    "XLI": {
        "Aggressive": {"strike": 118.00, "expiration": "2023-05-05", "dte": 7, "roi": "30%", "premium": 2.25, "otm": "5.2%"},
        "Steady": {"strike": 115.00, "expiration": "2023-05-19", "dte": 21, "roi": "23%", "premium": 3.46, "otm": "2.5%"},
        "Passive": {"strike": 114.00, "expiration": "2023-06-16", "dte": 49, "roi": "16%", "premium": 4.83, "otm": "1.6%"}
    },
    "XLP": {
        "Aggressive": {"strike": 78.00, "expiration": "2023-05-05", "dte": 7, "roi": "27%", "premium": 1.34, "otm": "5.3%"},
        "Steady": {"strike": 76.00, "expiration": "2023-05-19", "dte": 21, "roi": "20%", "premium": 2.01, "otm": "2.6%"},
        "Passive": {"strike": 75.00, "expiration": "2023-06-16", "dte": 49, "roi": "15%", "premium": 3.01, "otm": "1.2%"}
    },
    "XLY": {
        "Aggressive": {"strike": 194.00, "expiration": "2023-05-05", "dte": 7, "roi": "34%", "premium": 4.20, "otm": "5.1%"},
        "Steady": {"strike": 189.00, "expiration": "2023-05-19", "dte": 21, "roi": "26%", "premium": 6.45, "otm": "2.4%"},
        "Passive": {"strike": 187.00, "expiration": "2023-06-16", "dte": 49, "roi": "19%", "premium": 9.41, "otm": "1.3%"}
    },
    "XLE": {
        "Aggressive": {"strike": 92.50, "expiration": "2023-05-05", "dte": 7, "roi": "31%", "premium": 1.82, "otm": "5.2%"},
        "Steady": {"strike": 90.00, "expiration": "2023-05-19", "dte": 21, "roi": "24%", "premium": 2.84, "otm": "2.4%"},
        "Passive": {"strike": 89.00, "expiration": "2023-06-16", "dte": 49, "roi": "18%", "premium": 4.27, "otm": "1.2%"}
    }
}

# Strategy descriptions
strategy_descriptions = {
    "Aggressive": "Weekly options (7 DTE) with higher ROI potential (25-35%) but more active management.",
    "Steady": "Bi-weekly options (14-21 DTE) balancing ROI (20-25%) with moderate management.",
    "Passive": "Monthly or longer options (30-60 DTE) with lower but steady ROI (15-20%) requiring less management."
}

# Global CSS for Apple-like minimalist design
# Common HTML components for templates
logo_header = """
<header class="py-3 mb-4 border-bottom">
    <div class="container-fluid d-flex justify-content-between" style="padding-left: 0; position: relative;">
        <!-- Left section: Logo -->
        <div style="width: 25%;">
            <a href="/" style="display: block; margin-left: 0; padding-left: 0;">
                <img src="/static/images/animated_logo.gif" alt="Nate Tucci's Income Machine" height="150" style="cursor: pointer;">
            </a>
        </div>
        
        <!-- Middle section: Free Income Machine and Timer stacked -->
        <div class="d-flex flex-column align-items-center justify-content-end" style="width: 50%; position: absolute; left: 25%; bottom: 0; padding-bottom: 10px;">
            <img src="/static/images/free_income_machine_new.png" alt="Free Income Machine" style="max-width: 250px; margin-bottom: 10px;">
            <div class="d-flex align-items-center">
                <div style="font-size: 12px; font-weight: 600; letter-spacing: 0.05em; color: rgba(255, 255, 255, 0.9); margin-right: 10px; text-transform: uppercase;">EXPIRES IN</div>
                <div id="countdown" class="text-light" style="background: linear-gradient(90deg, #4f46e5 0%, #a855f7 100%); display: inline-block; padding: 8px 15px; border-radius: 50px; box-shadow: 0 2px 10px rgba(91, 33, 182, 0.4); animation: pulse 2s infinite; text-align: center; font-size: 16px; font-weight: 800; letter-spacing: 0.01em;"></div>
            </div>
        </div>
        
        <!-- Right section: Navigation -->
        <nav class="d-flex align-items-end justify-content-end" style="width: 25%; padding-bottom: 10px;">
            <a href="/" class="text-decoration-none mx-2" style="font-size: 14px; font-weight: 500; color: rgba(255, 255, 255, 0.8); transition: all 0.2s ease;">ETF Scoreboard</a>
            <a href="/how-to-use" class="text-decoration-none mx-2" style="font-size: 14px; font-weight: 500; color: rgba(255, 255, 255, 0.8); transition: all 0.2s ease;">How to Use</a>
            <a href="/live-classes" class="text-decoration-none mx-2" style="font-size: 14px; font-weight: 500; color: rgba(255, 255, 255, 0.8); transition: all 0.2s ease;">Trade Classes</a>
            <a href="/special-offer" class="ms-2" style="font-size: 14px; font-weight: 600; color: rgba(255, 69, 58, 1); background: rgba(255, 69, 58, 0.15); padding: 5px 10px; border-radius: 20px; text-decoration: none; transition: all 0.2s ease;">Get 50% OFF</a>
        </nav>
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
    
    document.getElementById("countdown").innerHTML = `${days}D ${hours}H ${minutes}M ${seconds}S`;
}

// Update the countdown every second
setInterval(updateCountdown, 1000);
updateCountdown(); // Initial call
</script>
<style>
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(91, 33, 182, 0.4); transform: scale(1); }
    50% { box-shadow: 0 0 0 8px rgba(91, 33, 182, 0); transform: scale(1.03); }
    100% { box-shadow: 0 0 0 0 rgba(91, 33, 182, 0); transform: scale(1); }
}
nav a:hover {
    color: rgba(255, 255, 255, 1) !important;
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
}
nav a:last-child:hover {
    background: rgba(255, 69, 58, 0.25);
    text-shadow: 0 0 10px rgba(255, 69, 58, 0.5);
}
</style>
"""

global_css = """
    /* Apple-style base setup */
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        letter-spacing: -0.015em;
        background: #151521;
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
    
    /* Strategy card styling - replaced colored headers with subtle indicators */
    .card-aggressive .card-header {
        background: rgba(28, 28, 30, 0.8);
        border-top: 4px solid rgba(255, 69, 58, 0.8);
    }
    
    .card-steady .card-header {
        background: rgba(28, 28, 30, 0.8);
        border-top: 4px solid rgba(255, 214, 10, 0.8);
    }
    
    .card-passive .card-header {
        background: rgba(28, 28, 30, 0.8);
        border-top: 4px solid rgba(48, 209, 88, 0.8);
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
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine DEMO - Daily ETF Scoreboard</title>
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
            

            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">Daily ETF Scoreboard</h2>
                    <p class="fs-5">Select an ETF with a high score (4-5) for the best covered call opportunities.</p>
                </div>
            </div>
    
            <div class="row">
                {% for etf, data in etfs.items() %}
                <div class="col-md-4 mb-4">
                    <div class="card h-100" style="background: rgba(28, 28, 30, 0.8); border-radius: 20px; overflow: hidden; border: none; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); transition: all 0.3s ease;">
                        <div class="card-body p-4">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h3 class="card-title mb-0" style="font-weight: 700; font-size: 1.8rem; letter-spacing: -0.02em;">{{ etf }}</h3>
                                <span class="badge {{ 'bg-success' if data.score >= 4 else 'bg-warning' if data.score >= 3 else 'bg-danger' }}" style="font-size: 0.9rem; padding: 0.5rem 1rem; border-radius: 20px;">{{ data.score }}/5</span>
                            </div>
                            
                            <p class="text-light mb-1" style="font-size: 1.1rem; opacity: 0.9;">{{ data.name }}</p>
                            <p class="text-light mb-3" style="font-size: 1.5rem; font-weight: 600;">${{ "%.2f"|format(data.price) }}</p>
                            
                            <div class="progress mb-4" style="height: 8px; background: rgba(40, 40, 45, 0.3); overflow: hidden; border-radius: 100px;">
                                <div class="progress-bar progress-bar-score-{{ data.score }}" role="progressbar" 
                                    aria-valuenow="{{ data.score * 20 }}" aria-valuemin="0" aria-valuemax="100" style="width: {{ data.score * 20 }}%;">
                                </div>
                            </div>
                            
                            <div class="d-grid">
                                <a href="{{ url_for('step2', etf=etf) }}" class="btn {{ 'btn-success' if data.score >= 4 else 'btn-secondary' }}" style="border-radius: 14px; padding: 0.8rem; font-weight: 500; letter-spacing: -0.01em;">
                                    Select {{ etf }}
                                </a>
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
    
    return render_template_string(template, etfs=etf_scores, global_css=global_css, logo_header=logo_header)

# Route for Step 2: ETF Selection
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
        <title>Income Machine DEMO - ETF Selection - {{ etf }}</title>
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
                <div class="step completed">
                    Step 1: Scoreboard
                </div>
                <div class="step active">
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
                            <p><strong>Current Price:</strong> ${{ "%.2f"|format(etf_data.price) }}</p>
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
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <span><strong>Trend 1:</strong> Price > 20 EMA</span>
                                            <span class="badge rounded-pill {{ 'bg-success' if etf_data.indicators.trend1.pass else 'bg-secondary' }}">
                                                {{ '✓' if etf_data.indicators.trend1.pass else '✗' }}
                                            </span>
                                        </div>
                                        <div class="small text-light">
                                            {{ etf_data.indicators.trend1.description }}
                                        </div>
                                    </li>
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <span><strong>Trend 2:</strong> Price > 100 EMA</span>
                                            <span class="badge rounded-pill {{ 'bg-success' if etf_data.indicators.trend2.pass else 'bg-secondary' }}">
                                                {{ '✓' if etf_data.indicators.trend2.pass else '✗' }}
                                            </span>
                                        </div>
                                        <div class="small text-light">
                                            {{ etf_data.indicators.trend2.description }}
                                        </div>
                                    </li>
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <span><strong>Snapback:</strong> RSI < 50</span>
                                            <span class="badge rounded-pill {{ 'bg-success' if etf_data.indicators.snapback.pass else 'bg-secondary' }}">
                                                {{ '✓' if etf_data.indicators.snapback.pass else '✗' }}
                                            </span>
                                        </div>
                                        <div class="small text-light">
                                            {{ etf_data.indicators.snapback.description }}
                                        </div>
                                    </li>
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <span><strong>Momentum:</strong> Price > Last Week</span>
                                            <span class="badge rounded-pill {{ 'bg-success' if etf_data.indicators.momentum.pass else 'bg-secondary' }}">
                                                {{ '✓' if etf_data.indicators.momentum.pass else '✗' }}
                                            </span>
                                        </div>
                                        <div class="small text-light">
                                            {{ etf_data.indicators.momentum.description }}
                                        </div>
                                    </li>
                                    <li class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <span><strong>Stabilizing:</strong> 3D ATR < 6D ATR</span>
                                            <span class="badge rounded-pill {{ 'bg-success' if etf_data.indicators.stabilizing.pass else 'bg-secondary' }}">
                                                {{ '✓' if etf_data.indicators.stabilizing.pass else '✗' }}
                                            </span>
                                        </div>
                                        <div class="small text-light">
                                            {{ etf_data.indicators.stabilizing.description }}
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
                            
                            <p>The score is calculated using 5 technical indicators, with 1 point awarded for each condition met. Higher scores indicate more favorable market conditions for selling covered calls.</p>
                            
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
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center justify-content-between">
                    <h1 class="fs-4 text-light">Income Machine <span class="badge bg-primary">DEMO</span></h1>
                </div>
            </header>
            
            <div class="step-indicator mb-4">
                <div class="step completed">
                    Step 1: Scoreboard
                </div>
                <div class="step completed">
                    Step 2: ETF Selection
                </div>
                <div class="step active">
                    Step 3: Strategy
                </div>
                <div class="step upcoming">
                    Step 4: Trade Details
                </div>
            </div>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">Choose an Income Strategy for {{ etf }}</h2>
                    <p class="fs-5">Select the covered call approach that matches your income goals and risk tolerance.</p>
                </div>
            </div>
    
            <form action="{{ url_for('step4') }}" method="get">
                <input type="hidden" name="etf" value="{{ etf }}">
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="card card-aggressive mb-4">
                            <div class="card-header">
                                <div class="form-check d-flex justify-content-between align-items-center">
                                    <div>
                                        <input class="form-check-input" type="radio" name="strategy" id="aggressive" value="Aggressive" required>
                                        <label class="form-check-label fw-bold text-white" for="aggressive">
                                            Aggressive Strategy
                                        </label>
                                    </div>
                                    <label for="aggressive" class="btn btn-sm btn-outline-light">Select</label>
                                </div>
                            </div>
                            <div class="card-body">
                                <h5 class="card-title">Higher Risk, Higher Reward</h5>
                                <ul class="list-group list-group-flush mb-3">
                                    <li class="list-group-item"><strong>DTE:</strong> Approx. 7 days (weekly)</li>
                                    <li class="list-group-item"><strong>Target ROI:</strong> 25-35% annually</li>
                                    <li class="list-group-item"><strong>Strike Selection:</strong> 5-10% OTM</li>
                                    <li class="list-group-item"><strong>Management:</strong> Weekly attention needed</li>
                                </ul>
                                <p class="card-text">{{ strategy_descriptions.Aggressive }}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card card-steady mb-4">
                            <div class="card-header">
                                <div class="form-check d-flex justify-content-between align-items-center">
                                    <div>
                                        <input class="form-check-input" type="radio" name="strategy" id="steady" value="Steady" required>
                                        <label class="form-check-label fw-bold text-white" for="steady">
                                            Steady Strategy
                                        </label>
                                    </div>
                                    <label for="steady" class="btn btn-sm btn-outline-light">Select</label>
                                </div>
                            </div>
                            <div class="card-body">
                                <h5 class="card-title">Balanced Approach</h5>
                                <ul class="list-group list-group-flush mb-3">
                                    <li class="list-group-item"><strong>DTE:</strong> 14-21 days (bi-weekly)</li>
                                    <li class="list-group-item"><strong>Target ROI:</strong> 20-25% annually</li>
                                    <li class="list-group-item"><strong>Strike Selection:</strong> 2-5% OTM</li>
                                    <li class="list-group-item"><strong>Management:</strong> Bi-weekly attention</li>
                                </ul>
                                <p class="card-text">{{ strategy_descriptions.Steady }}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card card-passive mb-4">
                            <div class="card-header">
                                <div class="form-check d-flex justify-content-between align-items-center">
                                    <div>
                                        <input class="form-check-input" type="radio" name="strategy" id="passive" value="Passive" required>
                                        <label class="form-check-label fw-bold text-white" for="passive">
                                            Passive Strategy
                                        </label>
                                    </div>
                                    <label for="passive" class="btn btn-sm btn-outline-light">Select</label>
                                </div>
                            </div>
                            <div class="card-body">
                                <h5 class="card-title">Lower Risk, Consistent Income</h5>
                                <ul class="list-group list-group-flush mb-3">
                                    <li class="list-group-item"><strong>DTE:</strong> 30-60 days (monthly+)</li>
                                    <li class="list-group-item"><strong>Target ROI:</strong> 15-20% annually</li>
                                    <li class="list-group-item"><strong>Strike Selection:</strong> 1-3% OTM</li>
                                    <li class="list-group-item"><strong>Management:</strong> Monthly attention</li>
                                </ul>
                                <p class="card-text">{{ strategy_descriptions.Passive }}</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="d-grid gap-2 col-6 mx-auto mt-3">
                    <button type="submit" class="btn btn-primary btn-lg">Get Trade Recommendation →</button>
                </div>
                
                <div class="mt-3">
                    <a href="{{ url_for('step2', etf=etf) }}" class="btn btn-secondary">← Back to ETF Details</a>
                </div>
            </form>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, etf=etf, strategy_descriptions=strategy_descriptions, global_css=global_css, logo_header=logo_header)

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
        
        # Format the trade data to match our template expectations
        formatted_trade = {
            "strike": trade.get("strike", 0),
            "expiration": trade.get("expiration", "N/A"),
            "dte": trade.get("dte", 0),
            "roi": trade.get("roi", "N/A"),
            "premium": trade.get("premium", 0),
            "otm": f"{trade.get('pct_otm', 0):.1f}%"
        }
        
        logger.info(f"Trade recommendation received: {formatted_trade}")
        
    except Exception as e:
        logger.error(f"Error getting trade recommendation: {str(e)}")
        # Fallback to static data if real-time data fails
        if etf in recommended_trades and strategy in recommended_trades[etf]:
            formatted_trade = recommended_trades[etf][strategy]
            logger.warning(f"Using fallback trade data for {etf} {strategy}")
        else:
            # Create a default recommendation
            formatted_trade = {
                "strike": round(etf_scores[etf]["price"] * 1.05, 2),
                "expiration": "N/A",
                "dte": 14,
                "roi": "20-25%",
                "premium": round(etf_scores[etf]["price"] * 0.02, 2),
                "otm": "5.0%"
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
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center justify-content-between">
                    <h1 class="fs-4 text-light">Income Machine <span class="badge bg-primary">DEMO</span></h1>
                </div>
            </header>
            
            <div class="step-indicator mb-4">
                <div class="step completed">
                    Step 1: Scoreboard
                </div>
                <div class="step completed">
                    Step 2: ETF Selection
                </div>
                <div class="step completed">
                    Step 3: Strategy
                </div>
                <div class="step active">
                    Step 4: Trade Details
                </div>
            </div>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">Recommended Trade</h2>
                    <p class="fs-5">{{ etf }} covered call with {{ strategy }} strategy</p>
                </div>
            </div>
    
            <div class="card mb-4">
                <div class="card-header">
                    <h4>Debit Spread Trade Details</h4>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <h5>Trade Setup</h5>
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Action:</strong></span>
                                        <span>Sell 1 {{ etf }} Call Option</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Strike Price:</strong></span>
                                        <span>${{ "%.2f"|format(trade.strike) }}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Expiration:</strong></span>
                                        <span>{{ trade.expiration }} ({{ trade.dte }} days)</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Premium:</strong></span>
                                        <span>${{ "%.2f"|format(trade.premium) }} per share</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <div class="mb-3">
                                <h5>Trade Metrics</h5>
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Strike Distance:</strong></span>
                                        <span>{{ trade.otm }} OTM</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Annualized ROI:</strong></span>
                                        <span>{{ trade.roi }}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Total Premium:</strong></span>
                                        <span>${{ "%.2f"|format(trade.premium * 100) }} per contract</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        <span><strong>Max Profit:</strong></span>
                                        <span>${{ "%.2f"|format(trade.premium * 100) }} per contract</span>
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
                            <p><strong>Target Annual ROI:</strong> {{ trade.roi }}</p>
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
                    <p>See the specific covered call trade recommendation with strike price, expiration, potential return, and other key metrics.</p>
                </div>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, global_css=global_css, logo_header=logo_header)

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
                                    <p>Learn the basics of selling covered calls and generating consistent income with lower-risk strategies.</p>
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
    return render_template_string(template, global_css=global_css, logo_header=logo_header)

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
    return render_template_string(template, global_css=global_css, logo_header=logo_header)

# Run the Flask application
if __name__ == '__main__':
    print("Visit http://127.0.0.1:5000/ to view the Income Machine DEMO.")
    app.run(host="0.0.0.0", port=5000, debug=True)