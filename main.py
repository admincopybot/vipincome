"""
Income Machine - Node.js Bridge
Starts the Node.js server through the existing Python workflow
"""

import subprocess
import threading
import time
from flask import Flask, redirect

app = Flask(__name__)

# Global variable to track Node.js process
nodejs_process = None

def start_nodejs_server():
    """Start the Node.js server in background"""
    global nodejs_process
    
    print("Starting Income Machine Node.js server...")
    
    try:
        # Kill any existing Node.js processes
        subprocess.run(['pkill', '-f', 'node main.js'], check=False)
        time.sleep(1)
        
        # Start the Node.js server
        nodejs_process = subprocess.Popen(
            ['node', 'main.js'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        print("Node.js server started successfully")
        
    except Exception as e:
        print(f"Error starting Node.js server: {e}")

@app.route('/')
def index():
    """Serve the Node.js application directly"""
    try:
        import requests
        response = requests.get('http://localhost:5001', timeout=5)
        return response.text, response.status_code
    except:
        # If Node.js isn't responding, serve a basic redirect page
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Income Machine Loading...</title></head>
        <body>
        <script>
        setTimeout(() => {
            window.location.reload();
        }, 2000);
        </script>
        <p>Starting Income Machine Node.js server...</p>
        </body>
        </html>
        '''

@app.route('/<path:path>')
def catch_all(path):
    """Proxy all requests to the Node.js server"""
    try:
        import requests
        response = requests.get(f'http://localhost:5001/{path}', timeout=5)
        return response.text, response.status_code
    except:
        return redirect('/', code=302)

if __name__ == "__main__":
    # Start Node.js server in background thread
    nodejs_thread = threading.Thread(target=start_nodejs_server, daemon=True)
    nodejs_thread.start()
    
    # Give Node.js time to start
    time.sleep(2)
    
    # Start Flask app (this satisfies the workflow requirement)
    app.run(host='0.0.0.0', port=5001, debug=False)