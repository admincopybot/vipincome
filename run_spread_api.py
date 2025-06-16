#!/usr/bin/env python3
"""
Simple runner for the debit spread API server
"""
from spread_api_server import app

if __name__ == '__main__':
    print("Starting Debit Spread Analysis API Server...")
    print("POST to /analyze with JSON: {\"ticker\": \"AAPL\"}")
    print("Health check: GET /health")
    app.run(host='0.0.0.0', port=5000, debug=False)