"""
Flask Integration Wrapper for Debit Spread Analyzer
Easy integration into existing Vercel applications
"""

from flask import Flask, request, jsonify
from debit_spread_analyzer import analyze_debit_spread, get_api_status
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_debit_spread_routes(app: Flask):
    """
    Add debit spread analysis routes to an existing Flask app
    
    Usage in your existing Flask app:
    ```python
    from flask_integration import create_debit_spread_routes
    
    app = Flask(__name__)
    create_debit_spread_routes(app)
    ```
    """
    
    @app.route('/api/analyze_debit_spread', methods=['POST'])
    def analyze_debit_spread_endpoint():
        """
        POST endpoint for debit spread analysis
        Accepts: {"ticker": "AAPL"}
        Returns: Complete spread analysis with authentic market data
        """
        try:
            # Validate request
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                }), 400
            
            data = request.get_json()
            if not data or 'ticker' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Missing required field: ticker'
                }), 400
            
            ticker = data['ticker'].upper().strip()
            
            if not ticker or len(ticker) > 10:
                return jsonify({
                    'success': False,
                    'error': 'Invalid ticker symbol'
                }), 400
            
            # Perform analysis
            result = analyze_debit_spread(ticker)
            
            if result.get('success'):
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Endpoint error: {e}")
            return jsonify({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }), 500
    
    @app.route('/api/spread_status', methods=['GET'])
    def spread_status_endpoint():
        """GET endpoint for API status monitoring"""
        try:
            status = get_api_status()
            return jsonify(status)
        except Exception as e:
            logger.error(f"Status endpoint error: {e}")
            return jsonify({
                'error': f'Status check failed: {str(e)}'
            }), 500
    
    @app.route('/api/spread_health', methods=['GET'])
    def spread_health_endpoint():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'Debit Spread Analysis API',
            'version': '1.0'
        })

# Standalone Flask app (for testing or independent deployment)
def create_standalone_app():
    """Create a standalone Flask app with debit spread analysis"""
    app = Flask(__name__)
    app.secret_key = 'debit-spread-analyzer-key'
    
    # Add the debit spread routes
    create_debit_spread_routes(app)
    
    # Root documentation endpoint
    @app.route('/', methods=['GET'])
    def api_documentation():
        """API documentation"""
        return jsonify({
            'service': 'Debit Spread Analysis API',
            'version': '1.0',
            'description': 'Professional-grade options trading analysis with ThinkOrSwim pricing methodology',
            'endpoints': {
                'POST /api/analyze_debit_spread': {
                    'description': 'Analyze debit spreads for a ticker',
                    'input': {'ticker': 'string (required)'},
                    'example': {'ticker': 'AAPL'}
                },
                'GET /api/spread_status': {
                    'description': 'API status and request monitoring'
                },
                'GET /api/spread_health': {
                    'description': 'Health check endpoint'
                }
            },
            'data_source': 'TheTradeList API - Authentic Market Data',
            'pricing_methodology': 'ThinkOrSwim Professional Spread Pricing'
        })
    
    return app

if __name__ == '__main__':
    # Run standalone app for testing
    app = create_standalone_app()
    app.run(host='0.0.0.0', port=5000, debug=False)