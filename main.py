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

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    """Proxy all requests to Node.js server"""
    try:
        url = f"http://localhost:5001/{path}"
        resp = requests.get(url, params=request.args, timeout=10)
        return Response(resp.content, status=resp.status_code, 
                       headers=dict(resp.headers))
    except requests.exceptions.RequestException:
        return """
        <html><body>
        <h2>Starting Income Machine...</h2>
        <script>setTimeout(() => location.reload(), 3000);</script>
        </body></html>
        """

# Start Node.js on import
start_nodejs()