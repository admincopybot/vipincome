#!/bin/bash

# Pure Node.js Income Machine Server
echo "Starting Node.js Income Machine Server..."

# Kill any existing processes
pkill -f gunicorn 2>/dev/null
pkill -f python 2>/dev/null

# Start the Node.js server
exec node standalone-server.js