from flask import Flask, request, render_template_string, redirect, url_for
import logging
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "income_machine_demo")

# Create dummy data for ETF scoreboard
etf_scores = {
    "XLC": {"name": "Communication Services", "score": 3, "price": 79.42},
    "XLF": {"name": "Financial", "score": 4, "price": 39.86},
    "XLV": {"name": "Health Care", "score": 2, "price": 133.17},
    "XLI": {"name": "Industrial", "score": 3, "price": 112.22},
    "XLP": {"name": "Consumer Staples", "score": 1, "price": 74.09},
    "XLY": {"name": "Consumer Discretionary", "score": 5, "price": 184.61},
    "XLE": {"name": "Energy", "score": 4, "price": 87.93}
}

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

# Global CSS for sleek, minimalist design (Apple meets Wall Street)
global_css = """
    /* Refined typography */
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        letter-spacing: -0.01em;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-weight: 500;
        letter-spacing: -0.03em;
    }
    
    /* Elegant card styling */
    .card {
        border: none;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
        transition: all 0.2s ease;
        overflow: hidden;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.12);
    }
    
    .card-header {
        border-bottom: none;
        padding: 1.25rem;
    }
    
    .card-body {
        padding: 1.5rem;
    }
    
    /* Refined buttons */
    .btn {
        border-radius: 8px;
        font-weight: 500;
        padding: 0.5rem 1.25rem;
        transition: all 0.2s ease;
    }
    
    .btn-primary {
        background: linear-gradient(135deg, #0056b3 0%, #007bff 100%);
        border: none;
    }
    
    .btn-primary:hover {
        background: linear-gradient(135deg, #003d80 0%, #0069d9 100%);
        transform: translateY(-1px);
    }
    
    .btn-danger {
        background: linear-gradient(135deg, #c31432 0%, #ff512f 100%);
        border: none;
    }
    
    .btn-danger:hover {
        background: linear-gradient(135deg, #a51029 0%, #e5492a 100%);
        transform: translateY(-1px);
    }
    
    /* Progress bars with animation */
    .progress {
        height: 0.75rem;
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Step indicator refinement */
    .step-indicator {
        margin: 2rem 0;
    }
    
    .step {
        border-radius: 8px;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
    }
    
    .step.active, .step.completed {
        font-weight: 600;
    }
    
    /* List group elegance */
    .list-group-item {
        border: none;
        padding: 1rem 1.25rem;
        margin-bottom: 2px;
        border-radius: 8px !important;
    }
    
    /* Clean, minimal header */
    header {
        border: none !important;
        margin-bottom: 1.5rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Jumbotron area */
    .bg-body-tertiary {
        border-radius: 16px !important;
        background: linear-gradient(45deg, rgba(25, 25, 25, 0.8) 0%, rgba(45, 45, 45, 0.8) 100%) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }
    
    /* Table refinement */
    table {
        border-collapse: separate;
        border-spacing: 0 0.5rem;
    }
    
    td, th {
        padding: 1rem 1.5rem;
        vertical-align: middle;
    }
    
    tbody tr {
        background-color: rgba(60, 60, 60, 0.4);
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    
    tbody tr:hover {
        transform: scale(1.01);
        background-color: rgba(70, 70, 70, 0.6);
        cursor: pointer;
    }
    
    tbody td:first-child {
        border-radius: 8px 0 0 8px;
    }
    
    tbody td:last-child {
        border-radius: 0 8px 8px 0;
    }
    
    /* Strategy card accents */
    .strategy-card-aggressive {
        border-left: 4px solid var(--bs-danger);
    }
    
    .strategy-card-steady {
        border-left: 4px solid var(--bs-warning);
    }
    
    .strategy-card-passive {
        border-left: 4px solid var(--bs-success);
    }
    
    /* Logo style */
    .logo-text {
        letter-spacing: -0.05em;
        font-weight: 600;
    }
    
    /* Container refinement */
    .container {
        padding: 2rem;
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
            .progress-bar-score-0 { width: 0%; background-color: var(--bs-danger); }
            .progress-bar-score-1 { width: 20%; background-color: var(--bs-danger); }
            .progress-bar-score-2 { width: 40%; background-color: var(--bs-warning); }
            .progress-bar-score-3 { width: 60%; background-color: var(--bs-info); }
            .progress-bar-score-4 { width: 80%; background-color: var(--bs-success); }
            .progress-bar-score-5 { width: 100%; background-color: var(--bs-success); }
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
                    <div class="d-flex gap-3">
                        <a href="/how-to-use" class="btn btn-sm btn-outline-light">How to Use</a>
                        <a href="/live-classes" class="btn btn-sm btn-outline-light">Trade Classes</a>
                        <a href="/special-offer" class="btn btn-sm btn-danger">Get 50% OFF</a>
                    </div>
                </div>
            </header>
            
            <div class="step-indicator mb-4">
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
                <table class="table table-hover table-dark">
                    <thead>
                        <tr>
                            <th class="text-light">ETF</th>
                            <th class="text-light">Sector</th>
                            <th class="text-light">Price</th>
                            <th class="text-light">Score</th>
                            <th class="text-light">Strength</th>
                            <th class="text-light">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for etf, data in etfs.items() %}
                        <tr>
                            <td class="text-light"><strong>{{ etf }}</strong></td>
                            <td class="text-light">{{ data.name }}</td>
                            <td class="text-light">${{ "%.2f"|format(data.price) }}</td>
                            <td class="text-light">{{ data.score }}/5</td>
                            <td>
                                <div class="progress" style="height: 20px;">
                                    <div class="progress-bar progress-bar-score-{{ data.score }}" role="progressbar" 
                                         aria-valuenow="{{ data.score * 20 }}" aria-valuemin="0" aria-valuemax="100">
                                    </div>
                                </div>
                            </td>
                            <td>
                                <a href="{{ url_for('step2', etf=etf) }}" class="btn btn-sm {{ 'btn-success' if data.score >= 4 else 'btn-secondary' }}">
                                    Select
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, etfs=etf_scores, global_css=global_css)

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
            .progress-bar-score-0 { width: 0%; background-color: var(--bs-danger); }
            .progress-bar-score-1 { width: 20%; background-color: var(--bs-danger); }
            .progress-bar-score-2 { width: 40%; background-color: var(--bs-warning); }
            .progress-bar-score-3 { width: 60%; background-color: var(--bs-info); }
            .progress-bar-score-4 { width: 80%; background-color: var(--bs-success); }
            .progress-bar-score-5 { width: 100%; background-color: var(--bs-success); }
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
                    <div class="card mb-4">
                        <div class="card-header">
                            <h4 class="text-light">ETF Details</h4>
                        </div>
                        <div class="card-body">
                            <p class="text-light"><strong>Symbol:</strong> {{ etf }}</p>
                            <p class="text-light"><strong>Sector:</strong> {{ etf_data.name }}</p>
                            <p class="text-light"><strong>Current Price:</strong> ${{ "%.2f"|format(etf_data.price) }}</p>
                            <p class="text-light"><strong>Score:</strong> {{ etf_data.score }}/5</p>
                            <div class="progress mb-3" style="height: 25px;">
                                <div class="progress-bar progress-bar-score-{{ etf_data.score }}" role="progressbar" 
                                     aria-valuenow="{{ etf_data.score * 20 }}" aria-valuemin="0" aria-valuemax="100">
                                    {{ etf_data.score }}/5
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h4 class="text-light">Income Potential</h4>
                        </div>
                        <div class="card-body">
                            <p class="text-light">Based on the current score of <strong>{{ etf_data.score }}/5</strong>, 
                            {{ etf }} could be a {{ 'strong' if etf_data.score >= 4 else 'moderate' if etf_data.score >= 2 else 'weak' }} 
                            candidate for generating options income.</p>
                            
                            <p class="text-light">The higher the score, the more favorable market conditions are for selling covered calls.</p>
                            
                            <div class="d-grid gap-2">
                                <a href="{{ url_for('step3', etf=etf) }}" class="btn btn-primary">
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
    
    return render_template_string(template, etf=etf, etf_data=etf_scores[etf], global_css=global_css)

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
            .progress-bar-score-0 { width: 0%; background-color: var(--bs-danger); }
            .progress-bar-score-1 { width: 20%; background-color: var(--bs-danger); }
            .progress-bar-score-2 { width: 40%; background-color: var(--bs-warning); }
            .progress-bar-score-3 { width: 60%; background-color: var(--bs-info); }
            .progress-bar-score-4 { width: 80%; background-color: var(--bs-success); }
            .progress-bar-score-5 { width: 100%; background-color: var(--bs-success); }
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
                        <div class="card mb-4">
                            <div class="card-header bg-danger text-white">
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
                                <h5 class="card-title text-light">Higher Risk, Higher Reward</h5>
                                <ul class="list-group list-group-flush mb-3">
                                    <li class="list-group-item bg-dark text-white"><strong>DTE:</strong> Approx. 7 days (weekly)</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Target ROI:</strong> 25-35% annually</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Strike Selection:</strong> 5-10% OTM</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Management:</strong> Weekly attention needed</li>
                                </ul>
                                <p class="card-text text-light">{{ strategy_descriptions.Aggressive }}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card mb-4">
                            <div class="card-header bg-warning text-dark">
                                <div class="form-check d-flex justify-content-between align-items-center">
                                    <div>
                                        <input class="form-check-input" type="radio" name="strategy" id="steady" value="Steady" required>
                                        <label class="form-check-label fw-bold text-dark" for="steady">
                                            Steady Strategy
                                        </label>
                                    </div>
                                    <label for="steady" class="btn btn-sm btn-outline-dark">Select</label>
                                </div>
                            </div>
                            <div class="card-body">
                                <h5 class="card-title text-light">Balanced Approach</h5>
                                <ul class="list-group list-group-flush mb-3">
                                    <li class="list-group-item bg-dark text-white"><strong>DTE:</strong> 14-21 days (bi-weekly)</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Target ROI:</strong> 20-25% annually</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Strike Selection:</strong> 2-5% OTM</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Management:</strong> Bi-weekly attention</li>
                                </ul>
                                <p class="card-text text-light">{{ strategy_descriptions.Steady }}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card mb-4">
                            <div class="card-header bg-success text-white">
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
                                <h5 class="card-title text-light">Lower Risk, Consistent Income</h5>
                                <ul class="list-group list-group-flush mb-3">
                                    <li class="list-group-item bg-dark text-white"><strong>DTE:</strong> 30-60 days (monthly+)</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Target ROI:</strong> 15-20% annually</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Strike Selection:</strong> 1-3% OTM</li>
                                    <li class="list-group-item bg-dark text-white"><strong>Management:</strong> Monthly attention</li>
                                </ul>
                                <p class="card-text text-light">{{ strategy_descriptions.Passive }}</p>
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
    
    return render_template_string(template, etf=etf, strategy_descriptions=strategy_descriptions, global_css=global_css)

# Route for Step 4: Trade Details
@app.route('/step4')
def step4():
    etf = request.args.get('etf')
    strategy = request.args.get('strategy')
    
    if etf not in etf_scores or strategy not in ['Aggressive', 'Steady', 'Passive']:
        return redirect(url_for('index'))
    
    trade = recommended_trades[etf][strategy]
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Income Machine DEMO - Trade Details - {{ etf }} {{ strategy }}</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            .progress-bar-score-0 { width: 0%; background-color: var(--bs-danger); }
            .progress-bar-score-1 { width: 20%; background-color: var(--bs-danger); }
            .progress-bar-score-2 { width: 40%; background-color: var(--bs-warning); }
            .progress-bar-score-3 { width: 60%; background-color: var(--bs-info); }
            .progress-bar-score-4 { width: 80%; background-color: var(--bs-success); }
            .progress-bar-score-5 { width: 100%; background-color: var(--bs-success); }
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
    
            <div class="row">
                <div class="col-md-6">
                    <div class="card mb-4">
                        <div class="card-header bg-primary text-white">
                            <h4 class="text-white">ETF Information</h4>
                        </div>
                        <div class="card-body">
                            <h5 class="text-light">{{ etf }} - {{ etf_data.name }} Sector ETF</h5>
                            <p class="text-light"><strong>Current Price:</strong> ${{ "%.2f"|format(etf_data.price) }}</p>
                            <p class="text-light"><strong>Strength Score:</strong> {{ etf_data.score }}/5</p>
                            <div class="progress mb-3" style="height: 20px;">
                                <div class="progress-bar progress-bar-score-{{ etf_data.score }}" role="progressbar" 
                                    aria-valuenow="{{ etf_data.score * 20 }}" aria-valuemin="0" aria-valuemax="100">
                                    {{ etf_data.score }}/5
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card mb-4">
                        <div class="card-header {{ 'bg-danger text-white' if strategy == 'Aggressive' else 'bg-warning text-dark' if strategy == 'Steady' else 'bg-success text-white' }}">
                            <h4 class="{{ 'text-white' if strategy == 'Aggressive' or strategy == 'Passive' else 'text-dark' }}">{{ strategy }} Strategy</h4>
                        </div>
                        <div class="card-body">
                            <p class="text-light">{{ strategy_descriptions[strategy] }}</p>
                            <p class="text-light"><strong>Days To Expiration:</strong> {{ trade.dte }} days</p>
                            <p class="text-light"><strong>Target Annual ROI:</strong> {{ trade.roi }}</p>
                        </div>
                    </div>
                </div>
            </div>
    
            <div class="card mb-4">
                <div class="card-header bg-success text-white">
                    <h4 class="text-white">Recommended Covered Call Trade</h4>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <h5 class="text-light">Trade Setup</h5>
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item bg-dark text-white d-flex justify-content-between align-items-center">
                                        <span><strong>Action:</strong></span>
                                        <span>Sell 1 {{ etf }} Call Option</span>
                                    </li>
                                    <li class="list-group-item bg-dark text-white d-flex justify-content-between align-items-center">
                                        <span><strong>Strike Price:</strong></span>
                                        <span>${{ "%.2f"|format(trade.strike) }}</span>
                                    </li>
                                    <li class="list-group-item bg-dark text-white d-flex justify-content-between align-items-center">
                                        <span><strong>Expiration:</strong></span>
                                        <span>{{ trade.expiration }} ({{ trade.dte }} days)</span>
                                    </li>
                                    <li class="list-group-item bg-dark text-white d-flex justify-content-between align-items-center">
                                        <span><strong>Premium:</strong></span>
                                        <span>${{ "%.2f"|format(trade.premium) }} per share</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <div class="mb-3">
                                <h5 class="text-light">Trade Metrics</h5>
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item bg-dark text-white d-flex justify-content-between align-items-center">
                                        <span><strong>Strike Distance:</strong></span>
                                        <span>{{ trade.otm }} OTM</span>
                                    </li>
                                    <li class="list-group-item bg-dark text-white d-flex justify-content-between align-items-center">
                                        <span><strong>Annualized ROI:</strong></span>
                                        <span>{{ trade.roi }}</span>
                                    </li>
                                    <li class="list-group-item bg-dark text-white d-flex justify-content-between align-items-center">
                                        <span><strong>Total Premium:</strong></span>
                                        <span>${{ "%.2f"|format(trade.premium * 100) }} per contract</span>
                                    </li>
                                    <li class="list-group-item bg-dark text-white d-flex justify-content-between align-items-center">
                                        <span><strong>Max Profit:</strong></span>
                                        <span>${{ "%.2f"|format(trade.premium * 100) }} per contract</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    
                    <div class="alert alert-info mt-3">
                        <strong>Note:</strong> This recommendation is based on dummy data for demonstration purposes.
                        Real options data would need to be fetched from a market API.
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
        global_css=global_css
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
    </head>
    <body data-bs-theme="dark">
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center justify-content-between">
                    <h1 class="fs-4 text-light">Income Machine <span class="badge bg-primary">DEMO</span></h1>
                    <div class="d-flex gap-3">
                        <a href="/" class="btn btn-sm btn-outline-light">Back to Demo</a>
                        <a href="/how-to-use" class="btn btn-sm btn-outline-light active">How to Use</a>
                        <a href="/live-classes" class="btn btn-sm btn-outline-light">Trade Classes</a>
                        <a href="/special-offer" class="btn btn-sm btn-danger">Get 50% OFF</a>
                    </div>
                </div>
            </header>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">How to Use the Income Machine</h2>
                    <p class="fs-5">Learn how to get the most out of this powerful options income tool.</p>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0">Step-by-Step Guide</h4>
                </div>
                <div class="card-body">
                    <h5 class="text-light">1. Check the ETF Scoreboard</h5>
                    <p class="text-light">The scoreboard ranks sector ETFs based on their current income potential. Higher scores (4-5) indicate stronger opportunities.</p>
                    
                    <h5 class="text-light">2. Select an ETF</h5>
                    <p class="text-light">Click on an ETF with a good score to view more details about its current price and income potential.</p>
                    
                    <h5 class="text-light">3. Choose a Strategy</h5>
                    <p class="text-light">Select between Aggressive, Steady, or Passive strategies based on your risk tolerance and how actively you want to manage your positions.</p>
                    
                    <h5 class="text-light">4. Review Trade Details</h5>
                    <p class="text-light">See the specific covered call trade recommendation with strike price, expiration, potential return, and other key metrics.</p>
                </div>
            </div>
            
            <footer class="pt-3 mt-4 text-body-secondary border-top">
                &copy; 2023 Income Machine DEMO
            </footer>
        </div>
    </body>
    </html>
    """
    return render_template_string(template)

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
    </head>
    <body data-bs-theme="dark">
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center justify-content-between">
                    <h1 class="fs-4 text-light">Income Machine <span class="badge bg-primary">DEMO</span></h1>
                    <div class="d-flex gap-3">
                        <a href="/" class="btn btn-sm btn-outline-light">Back to Demo</a>
                        <a href="/how-to-use" class="btn btn-sm btn-outline-light">How to Use</a>
                        <a href="/live-classes" class="btn btn-sm btn-outline-light active">Trade Classes</a>
                        <a href="/special-offer" class="btn btn-sm btn-danger">Get 50% OFF</a>
                    </div>
                </div>
            </header>
            
            <div class="p-4 mb-4 bg-body-tertiary rounded-3">
                <div class="container-fluid py-3">
                    <h2 class="display-6 fw-bold">LIVE Trade Classes</h2>
                    <p class="fs-5">Join our weekly live sessions to learn advanced options income strategies directly from expert traders.</p>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header bg-success text-white">
                    <h4 class="mb-0">Upcoming LIVE Classes</h4>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-4">
                            <div class="card h-100">
                                <div class="card-header bg-dark text-white">
                                    <h5 class="mb-0">Beginners Options Income</h5>
                                </div>
                                <div class="card-body bg-dark bg-opacity-50">
                                    <p class="text-light"><strong>Date:</strong> Every Monday, 7:00 PM ET</p>
                                    <p class="text-light"><strong>Duration:</strong> 60 minutes</p>
                                    <p class="text-light">Learn the basics of selling covered calls and generating consistent income with lower-risk strategies.</p>
                                    <div class="d-grid">
                                        <a href="/special-offer" class="btn btn-primary">Register Now</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6 mb-4">
                            <div class="card h-100">
                                <div class="card-header bg-dark text-white">
                                    <h5 class="mb-0">Advanced Theta Strategies</h5>
                                </div>
                                <div class="card-body bg-dark bg-opacity-50">
                                    <p class="text-light"><strong>Date:</strong> Every Wednesday, 8:00 PM ET</p>
                                    <p class="text-light"><strong>Duration:</strong> 90 minutes</p>
                                    <p class="text-light">Master higher-return strategies including custom spreads, rolls, and calendar trades.</p>
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
    return render_template_string(template)

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
    </head>
    <body data-bs-theme="dark">
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center justify-content-between">
                    <h1 class="fs-4 text-light">Income Machine <span class="badge bg-primary">DEMO</span></h1>
                    <div class="d-flex gap-3">
                        <a href="/" class="btn btn-sm btn-outline-light">Back to Demo</a>
                        <a href="/how-to-use" class="btn btn-sm btn-outline-light">How to Use</a>
                        <a href="/live-classes" class="btn btn-sm btn-outline-light">Trade Classes</a>
                        <a href="/special-offer" class="btn btn-sm btn-danger active">Get 50% OFF</a>
                    </div>
                </div>
            </header>
            
            <div class="p-4 mb-4 bg-danger rounded-3">
                <div class="container-fluid py-3 text-center">
                    <h2 class="display-5 fw-bold text-white">SPECIAL LIMITED-TIME OFFER</h2>
                    <p class="fs-4 text-white">Get full access to Income Machine at 50% off the regular price</p>
                    <p class="text-white">Offer expires in: <span class="badge bg-warning text-dark p-2">48 hours 23 minutes</span></p>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-8">
                    <div class="card mb-4">
                        <div class="card-header bg-primary text-white">
                            <h4 class="mb-0">Income Machine Full Access Includes:</h4>
                        </div>
                        <div class="card-body bg-dark">
                            <ul class="list-group list-group-flush mb-4">
                                <li class="list-group-item bg-dark text-white border-bottom border-secondary"><strong>✓</strong> Real-time ETF and options data feeds</li>
                                <li class="list-group-item bg-dark text-white border-bottom border-secondary"><strong>✓</strong> Advanced strategy algorithms</li>
                                <li class="list-group-item bg-dark text-white border-bottom border-secondary"><strong>✓</strong> Position tracking and management tools</li>
                                <li class="list-group-item bg-dark text-white border-bottom border-secondary"><strong>✓</strong> Email alerts for trade opportunities</li>
                                <li class="list-group-item bg-dark text-white border-bottom border-secondary"><strong>✓</strong> Weekly LIVE trading sessions</li>
                                <li class="list-group-item bg-dark text-white border-bottom border-secondary"><strong>✓</strong> Access to all recorded training sessions</li>
                                <li class="list-group-item bg-dark text-white"><strong>✓</strong> Priority email support</li>
                            </ul>
                            
                            <div class="text-center mb-3">
                                <span class="text-decoration-line-through text-muted fs-4">Regular Price: $197/month</span>
                                <p class="text-success fs-1 fw-bold">Special Offer: $97/month</p>
                            </div>
                            
                            <div class="d-grid">
                                <a href="#" class="btn btn-success btn-lg py-3">GET 50% OFF NOW</a>
                            </div>
                            <p class="text-center mt-2 text-light small">No contracts. Cancel anytime.</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card mb-4">
                        <div class="card-header bg-success text-white">
                            <h4 class="mb-0">Testimonials</h4>
                        </div>
                        <div class="card-body bg-dark">
                            <div class="mb-3">
                                <p class="fst-italic text-light">"The Income Machine has helped me generate an extra $1,500 per month in reliable options income. The recommended trades are clear and easy to execute."</p>
                                <p class="text-light">— Michael R.</p>
                            </div>
                            <div class="mb-3">
                                <p class="fst-italic text-light">"I've tried other options advisory services, but the Income Machine provides the most consistent returns with less risk."</p>
                                <p class="text-light">— Sarah T.</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card mb-4">
                        <div class="card-header bg-warning text-dark">
                            <h4 class="mb-0">100% Money-Back Guarantee</h4>
                        </div>
                        <div class="card-body bg-dark">
                            <p class="text-light">Try Income Machine risk-free for 30 days. If you're not completely satisfied, we'll refund your subscription fee. No questions asked.</p>
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
    return render_template_string(template)

# Run the Flask application
if __name__ == '__main__':
    print("Visit http://127.0.0.1:5000/ to view the Income Machine DEMO.")
    app.run(host="0.0.0.0", port=5000, debug=True)