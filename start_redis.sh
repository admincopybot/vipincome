#!/bin/bash
# Start Redis server for Replit deployment

# Try to start Redis with minimal configuration
redis-server --daemonize yes --port 6379 --bind 127.0.0.1 --save "" --appendonly no --protected-mode no 2>/dev/null &

# Wait a moment for Redis to start
sleep 2

# Check if Redis is running
if redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "Redis server started successfully on port 6379"
else
    echo "Redis server failed to start - falling back to direct API calls"
fi