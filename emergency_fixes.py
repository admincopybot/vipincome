"""
Emergency Performance Fixes for High Traffic
==========================================

Quick fixes to disable resource-intensive operations during high traffic periods.
"""

import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Emergency configuration
EMERGENCY_MODE = True
DISABLE_API_CALLS = True
DISABLE_WEBSOCKET = True
DISABLE_BACKGROUND_THREADS = True

def emergency_disable(func):
    """Decorator to disable functions during emergency mode"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if EMERGENCY_MODE:
            logger.debug(f"Emergency mode: {func.__name__} disabled")
            return None
        return func(*args, **kwargs)
    return wrapper

def minimal_cache(duration=3600):
    """Simple cache for emergency performance"""
    cache = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{hash(str(args))}"
            
            if cache_key in cache:
                cached_time, cached_result = cache[cache_key]
                if time.time() - cached_time < duration:
                    return cached_result
            
            result = func(*args, **kwargs)
            cache[cache_key] = (time.time(), result)
            return result
        return wrapper
    return decorator

def emergency_sleep():
    """Add delay to reduce server load"""
    if EMERGENCY_MODE:
        time.sleep(0.05)  # 50ms delay