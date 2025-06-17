"""
Income Machine - Minimal Flask Bridge
Starts Node.js server and proxies all requests to it
"""

from flask import Flask, request, Response
import subprocess
import requests
import time
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key")

# Start Node.js server in background
nodejs_process = None

def start_nodejs():
    global nodejs_process
    try:
        # Kill existing Node.js processes
        subprocess.run(['pkill', '-f', 'node main.js'], check=False)
        time.sleep(1)
        
        # Start Node.js server on port 5001
        nodejs_process = subprocess.Popen(['node', 'main.js'], 
                                        env={**os.environ, 'PORT': '5001'})
        time.sleep(3)  # Wait for startup
        print("Node.js server started on port 5001")
    except Exception as e:
        print(f"Error starting Node.js: {e}")

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    """Proxy all requests to Node.js server"""
    try:
        url = f"http://localhost:5001/{path}"
        
        # Forward request with all parameters and headers
        # Use longer timeout for spread analysis endpoints to allow failover
        timeout = 45 if path == 'api/analyze_debit_spread' else 10
        
        if request.method == 'GET':
            resp = requests.get(url, 
                              params=dict(request.args), 
                              headers=dict(request.headers),
                              timeout=timeout)
        elif request.method == 'POST':
            resp = requests.post(url,
                               params=dict(request.args),
                               json=request.get_json() if request.is_json else None,
                               data=request.form if not request.is_json else None,
                               headers=dict(request.headers),
                               timeout=timeout)
        else:
            # Handle other HTTP methods
            resp = requests.request(request.method, url,
                                  params=dict(request.args),
                                  json=request.get_json() if request.is_json else None,
                                  data=request.form if not request.is_json else None,
                                  headers=dict(request.headers),
                                  timeout=timeout)
        
        # Create response with proper headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.headers.items()
                  if name.lower() not in excluded_headers]
        
        return Response(resp.content, status=resp.status_code, headers=headers)
        
    except requests.exceptions.RequestException as e:
        print(f"Proxy error: {e}")
        return """
        <html><body>
        <h2>Starting Income Machine...</h2>
        <script>setTimeout(() => location.reload(), 3000);</script>
        </body></html>
        """

# Start Node.js on import
start_nodejs()