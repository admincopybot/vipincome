"""
Pipeline Trigger Service
Provides endpoints to trigger the automated spread analysis pipeline
"""
import os
import logging
import threading
from datetime import datetime
from flask import Flask, jsonify, request
from automated_spread_pipeline import SpreadPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "pipeline-trigger-key")

# Global pipeline instance
pipeline = SpreadPipeline()
pipeline_running = False
pipeline_thread = None

@app.route('/trigger-pipeline', methods=['POST'])
def trigger_pipeline():
    """Trigger the spread analysis pipeline"""
    global pipeline_running, pipeline_thread
    
    try:
        if pipeline_running:
            return jsonify({
                'success': False,
                'message': 'Pipeline is already running'
            }), 400
        
        # Start pipeline in background thread
        pipeline_thread = threading.Thread(target=run_pipeline_background)
        pipeline_thread.daemon = True
        pipeline_thread.start()
        
        logger.info("Pipeline triggered successfully")
        
        return jsonify({
            'success': True,
            'message': 'Pipeline started successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error triggering pipeline: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def run_pipeline_background():
    """Run pipeline in background thread"""
    global pipeline_running
    
    try:
        pipeline_running = True
        logger.info("Starting background pipeline execution")
        pipeline.process_pipeline()
        logger.info("Background pipeline execution completed")
        
    except Exception as e:
        logger.error(f"Background pipeline error: {e}")
    finally:
        pipeline_running = False

@app.route('/pipeline-status', methods=['GET'])
def pipeline_status():
    """Get pipeline status"""
    return jsonify({
        'running': pipeline_running,
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'tickers_source': pipeline.tickers_endpoint,
            'spreads_destination': pipeline.spreads_endpoint
        }
    })

@app.route('/test-endpoints', methods=['GET'])
def test_endpoints():
    """Test connectivity to both endpoints"""
    import requests
    results = {}
    
    # Test tickers endpoint
    try:
        response = requests.get(pipeline.tickers_endpoint, timeout=10)
        results['tickers_endpoint'] = {
            'status': response.status_code,
            'accessible': response.status_code == 200,
            'response_preview': response.json() if response.status_code == 200 else response.text[:200]
        }
    except Exception as e:
        results['tickers_endpoint'] = {
            'status': 'error',
            'accessible': False,
            'error': str(e)
        }
    
    # Test spreads endpoint (just connectivity, not POST)
    try:
        response = requests.get(pipeline.spreads_endpoint.replace('/api/spreads-update', '/health'), timeout=10)
        results['spreads_endpoint'] = {
            'status': response.status_code,
            'accessible': True,
            'note': 'Health check or base endpoint accessible'
        }
    except Exception as e:
        results['spreads_endpoint'] = {
            'status': 'error',
            'accessible': False,
            'error': str(e)
        }
    
    return jsonify({
        'test_results': results,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'pipeline-trigger',
        'pipeline_running': pipeline_running,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Service information"""
    return jsonify({
        'service': 'Automated Spread Analysis Pipeline Trigger',
        'endpoints': {
            '/trigger-pipeline': 'POST - Start the analysis pipeline',
            '/pipeline-status': 'GET - Check if pipeline is running',
            '/test-endpoints': 'GET - Test connectivity to source/destination APIs',
            '/health': 'GET - Service health check'
        },
        'workflow': [
            '1. Fetches top tickers from source API',
            '2. Analyzes debit spreads for each ticker',
            '3. Sends results to destination API',
            '4. Processes all three strategies (aggressive, balanced, conservative)'
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)