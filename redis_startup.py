#!/usr/bin/env python3
"""
Redis startup script for Replit autoscale deployment
Attempts to start Redis server before the main application
"""

import subprocess
import time
import os
import sys
import redis
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_redis_server():
    """Start Redis server in background"""
    try:
        # Try to start Redis server
        logger.info("Starting Redis server...")
        
        # Start redis-server in background
        process = subprocess.Popen([
            'redis-server', 
            '--daemonize', 'no',
            '--port', '6379',
            '--bind', '127.0.0.1',
            '--save', '',
            '--appendonly', 'no',
            '--protected-mode', 'no'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Give Redis time to start
        time.sleep(3)
        
        # Test connection
        client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        client.ping()
        
        logger.info("Redis server started successfully on port 6379")
        return process
        
    except Exception as e:
        logger.error(f"Failed to start Redis server: {e}")
        return None

def main():
    """Main function to start Redis and then the Flask app"""
    
    # Start Redis server
    redis_process = start_redis_server()
    
    if redis_process:
        logger.info("Redis is running, starting Flask application...")
    else:
        logger.warning("Redis failed to start, Flask app will use direct API calls")
    
    # Start the main Flask application
    os.execvp('gunicorn', ['gunicorn', '--bind', '0.0.0.0:5000', '--reuse-port', 'main:app'])

if __name__ == "__main__":
    main()