"""
Emergency Performance Mode for High Traffic
==========================================

This module implements aggressive performance optimizations to handle high traffic loads
by disabling all non-essential operations and implementing aggressive caching.
"""

import os
import time
from functools import wraps
from flask import g

# Performance Configuration
EMERGENCY_MODE = True
CACHE_DURATION = 3600  # 1 hour cache
DISABLE_REAL_TIME_UPDATES = True
DISABLE_BACKGROUND_POLLING = True
DISABLE_API_CALLS = True

# In-memory cache for performance
performance_cache = {}
cache_timestamps = {}

def emergency_cache(duration=CACHE_DURATION):
    """Emergency caching decorator for high traffic performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not EMERGENCY_MODE:
                return func(*args, **kwargs)
            
            # Create cache key
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Check cache
            if cache_key in performance_cache:
                cache_time = cache_timestamps.get(cache_key, 0)
                if time.time() - cache_time < duration:
                    return performance_cache[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            performance_cache[cache_key] = result
            cache_timestamps[cache_key] = time.time()
            
            return result
        return wrapper
    return decorator

def disable_api_calls(func):
    """Decorator to disable API calls during high traffic"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if DISABLE_API_CALLS:
            return None  # Return None instead of making API call
        return func(*args, **kwargs)
    return wrapper

def emergency_sleep():
    """Add small delays to reduce server load"""
    if EMERGENCY_MODE:
        time.sleep(0.1)  # 100ms delay to reduce load

def clear_emergency_cache():
    """Clear emergency cache"""
    global performance_cache, cache_timestamps
    performance_cache.clear()
    cache_timestamps.clear()

def get_emergency_status():
    """Get current emergency mode status"""
    return {
        'emergency_mode': EMERGENCY_MODE,
        'cache_size': len(performance_cache),
        'disable_real_time': DISABLE_REAL_TIME_UPDATES,
        'disable_polling': DISABLE_BACKGROUND_POLLING,
        'disable_api': DISABLE_API_CALLS
    }