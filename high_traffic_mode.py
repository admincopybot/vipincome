"""
High Traffic Performance Mode
============================

Emergency optimizations for handling high traffic loads by implementing
aggressive caching and disabling non-essential operations.
"""

import time
import logging
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Global cache for emergency mode
emergency_cache = {}
cache_timestamps = {}

# Performance configuration
HIGH_TRAFFIC_MODE = True
CACHE_DURATION = 1800  # 30 minutes
MAX_CACHE_SIZE = 1000

def aggressive_cache(duration=CACHE_DURATION):
    """Aggressive caching decorator for high traffic scenarios"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Check if cached result exists and is still valid
            if cache_key in emergency_cache:
                cache_time = cache_timestamps.get(cache_key, 0)
                if time.time() - cache_time < duration:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return emergency_cache[cache_key]
            
            # Cache miss - execute function
            logger.debug(f"Cache miss for {func.__name__} - executing")
            result = func(*args, **kwargs)
            
            # Store in cache with timestamp
            emergency_cache[cache_key] = result
            cache_timestamps[cache_key] = time.time()
            
            # Clean old cache entries if cache is getting too large
            if len(emergency_cache) > MAX_CACHE_SIZE:
                clean_old_cache_entries()
            
            return result
        return wrapper
    return decorator

def clean_old_cache_entries():
    """Clean old cache entries to prevent memory issues"""
    current_time = time.time()
    keys_to_remove = []
    
    for key, timestamp in cache_timestamps.items():
        if current_time - timestamp > CACHE_DURATION * 2:  # Remove entries older than 2x cache duration
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        emergency_cache.pop(key, None)
        cache_timestamps.pop(key, None)
    
    if keys_to_remove:
        logger.info(f"Cleaned {len(keys_to_remove)} old cache entries")

def disable_during_high_traffic(func):
    """Decorator to disable functions during high traffic"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if HIGH_TRAFFIC_MODE:
            logger.debug(f"Function {func.__name__} disabled during high traffic mode")
            return None
        return func(*args, **kwargs)
    return wrapper

def get_cache_stats():
    """Get current cache statistics"""
    return {
        'cache_size': len(emergency_cache),
        'high_traffic_mode': HIGH_TRAFFIC_MODE,
        'cache_duration': CACHE_DURATION,
        'oldest_entry': min(cache_timestamps.values()) if cache_timestamps else None
    }

def clear_emergency_cache():
    """Clear all emergency cache"""
    global emergency_cache, cache_timestamps
    cache_count = len(emergency_cache)
    emergency_cache.clear()
    cache_timestamps.clear()
    logger.info(f"Cleared emergency cache ({cache_count} entries)")
    return cache_count