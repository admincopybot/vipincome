#!/bin/bash

# Start the standalone Node.js Income Machine server
echo "🚀 Starting Income Machine Node.js server..."

# Kill any existing Python processes
pkill -f python
pkill -f gunicorn
pkill -f flask

# Start the Node.js server
node standalone-server.js