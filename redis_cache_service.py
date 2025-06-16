"""
Redis Cache Service for TheTradeList API
Implements intelligent caching with 30-second expiry for all API endpoints
"""
import os
import json
import redis
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)

class RedisCacheService:
    """Redis-based caching service for all TheTradeList API calls"""
    
    def __init__(self):
        self.redis_client = None
        self.cache_enabled = False
        self.default_expiry = 30  # 30 seconds for all cache entries
        
        # Initialize Redis connection
        self._initialize_redis()
        
    def _initialize_redis(self):
        """Initialize Redis connection with fallback handling"""
        try:
            # Try to connect to Redis
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("Redis cache service initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis not available, falling back to direct API calls: {e}")
            self.cache_enabled = False
    
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate unique cache key for API endpoint and parameters"""
        # Sort parameters for consistent key generation
        sorted_params = sorted(params.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        
        # Create hash of parameters for shorter keys
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"api:{endpoint}:{params_hash}"
    
    def get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from Redis cache"""
        if not self.cache_enabled:
            return None
            
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT for key: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.info(f"Cache MISS for key: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None
    
    def set_cached_data(self, cache_key: str, data: Dict[str, Any]) -> bool:
        """Store data in Redis cache with expiry"""
        if not self.cache_enabled:
            return False
            
        try:
            # Add timestamp to cached data
            cache_entry = {
                'data': data,
                'cached_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=self.default_expiry)).isoformat()
            }
            
            self.redis_client.setex(
                cache_key, 
                self.default_expiry, 
                json.dumps(cache_entry)
            )
            logger.info(f"Cached data for key: {cache_key} (expires in {self.default_expiry}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error writing to cache: {e}")
            return False
    
    def cached_api_call(self, endpoint: str, url: str, params: Dict[str, Any], 
                       timeout: int = 15) -> Optional[Dict[str, Any]]:
        """Make API call with intelligent caching"""
        
        # Generate cache key
        cache_key = self._generate_cache_key(endpoint, params)
        
        # Try to get from cache first
        cached_result = self.get_cached_data(cache_key)
        if cached_result:
            return cached_result.get('data')
        
        # Cache miss - make actual API call
        try:
            logger.info(f"Making API call to {endpoint} (cache miss)")
            response = requests.get(url, params=params, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                # Cache the successful response
                self.set_cached_data(cache_key, data)
                
                return data
            else:
                logger.error(f"API call failed: {endpoint}, Status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error making API call to {endpoint}: {e}")
            return None
    
    def invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching a pattern"""
        if not self.cache_enabled:
            return
            
        try:
            keys = self.redis_client.keys(f"api:{pattern}:*")
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for pattern: {pattern}")
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache_enabled:
            return {'enabled': False, 'message': 'Redis not available'}
            
        try:
            info = self.redis_client.info()
            all_keys = self.redis_client.keys("api:*")
            
            return {
                'enabled': True,
                'total_keys': len(all_keys),
                'memory_used': info.get('used_memory_human', 'Unknown'),
                'hit_rate': 'Available in Redis info',
                'uptime': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            return {'enabled': False, 'error': str(e)}

# Global cache service instance
cache_service = RedisCacheService()

# Convenience functions for specific API endpoints
def get_stock_price_cached(ticker: str, api_key: str) -> Optional[float]:
    """Get stock price with Redis caching"""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    
    url = "https://api.thetradelist.com/v1/data/range-data"
    params = {
        'ticker': ticker,
        'range': '1/day',
        'startdate': start_date,
        'enddate': end_date,
        'limit': 10,
        'next_url': '',
        'apiKey': api_key
    }
    
    data = cache_service.cached_api_call('stock_price', url, params)
    if data and data.get('results'):
        return float(data['results'][-1]['c'])
    return None

def get_options_contracts_cached(ticker: str, api_key: str) -> List[Dict]:
    """Get options contracts with Redis caching"""
    url = "https://api.thetradelist.com/v1/data/options-contracts"
    params = {
        'underlying_ticker': ticker,
        'limit': 1000,
        'apiKey': api_key
    }
    
    data = cache_service.cached_api_call('options_contracts', url, params)
    if data and data.get('results'):
        return data['results']
    return []

def get_historical_data_cached(ticker: str, start_date: str, end_date: str, 
                              api_key: str, range_type: str = '1/day') -> List[Dict]:
    """Get historical data with Redis caching"""
    url = "https://api.thetradelist.com/v1/data/range-data"
    params = {
        'ticker': ticker,
        'range': range_type,
        'startdate': start_date,
        'enddate': end_date,
        'limit': 5000,
        'next_url': '',
        'apiKey': api_key
    }
    
    data = cache_service.cached_api_call('historical_data', url, params)
    if data and data.get('results'):
        return data['results']
    return []