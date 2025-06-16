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
        """Initialize Redis connection with Upstash support"""
        
        # Check for Upstash Redis first (recommended for production)
        upstash_url = os.environ.get('UPSTASH_REDIS_REST_URL')
        upstash_token = os.environ.get('UPSTASH_REDIS_REST_TOKEN')
        
        if upstash_url and upstash_token:
            try:
                logger.info("Configuring Upstash Redis connection")
                # Use upstash-redis library for REST API
                from upstash_redis import Redis as UpstashRedis
                self.redis_client = UpstashRedis(url=upstash_url, token=upstash_token)
                
                # Test connection
                self.redis_client.set('connection_test', 'success', ex=10)
                if self.redis_client.get('connection_test') == 'success':
                    self.cache_enabled = True
                    logger.info("✅ Upstash Redis connection successful")
                    return
                    
            except ImportError:
                logger.warning("upstash-redis library not found, falling back to standard Redis")
            except Exception as e:
                logger.warning(f"Upstash Redis connection failed: {e}")
        
        # Fallback to standard Redis connections
        redis_options = [
            os.environ.get('REDIS_URL'),           # Standard Redis URL
            os.environ.get('REDISCLOUD_URL'),      # Redis Cloud
            os.environ.get('REDISTOGO_URL'),       # Redis To Go
            "redis://localhost:6379",              # Local fallback
        ]
        
        redis_options = [url for url in redis_options if url]
        
        for redis_url in redis_options:
            try:
                masked_url = redis_url.split('@')[-1] if '@' in redis_url else redis_url
                logger.info(f"Attempting Redis connection to: {masked_url}")
                
                # Handle TLS connections for external services
                if redis_url.startswith('rediss://'):
                    self.redis_client = redis.from_url(
                        redis_url, 
                        decode_responses=True,
                        socket_connect_timeout=5,
                        ssl_cert_reqs=None  # Allow self-signed certificates
                    )
                else:
                    self.redis_client = redis.from_url(
                        redis_url, 
                        decode_responses=True,
                        socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                
                # Test connection
                self.redis_client.ping()
                self.cache_enabled = True
                logger.info(f"Redis cache service initialized successfully with: {masked_url}")
                return  # Success - exit the loop
                
            except Exception as e:
                logger.warning(f"Redis connection failed for {masked_url}: {e}")
                continue
        
        # If we reach here, no Redis connection worked
        logger.error("CRITICAL: No Redis available - application cannot handle 1000 concurrent users efficiently")
        logger.error("Set REDIS_URL environment variable with external Redis service URL")
        self.cache_enabled = False
        self.redis_client = None
    
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
            logger.info(f"API URL: {url}")
            logger.info(f"API Params: {params}")
            
            response = requests.get(url, params=params, timeout=timeout)
            
            logger.info(f"API Response Status: {response.status_code}")
            logger.info(f"API Response Text: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Log results count for debugging
                if 'results' in data:
                    logger.info(f"API returned {len(data['results'])} results")
                else:
                    logger.info(f"API response keys: {list(data.keys())}")
                
                # Cache the successful response
                self.set_cached_data(cache_key, data)
                
                return data
            else:
                logger.error(f"API call failed: {endpoint}, Status: {response.status_code}, Response: {response.text}")
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
    
    def cache_spread_analysis(self, ticker: str, spread_results: Dict, expiry_seconds: int = 1800) -> bool:
        """Cache complete spread analysis results for a ticker (30 minutes default)"""
        if not self.cache_enabled:
            return False
            
        try:
            cache_key = f"spread_analysis:{ticker}:{datetime.now().strftime('%Y%m%d_%H')}"
            
            cache_data = {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'results': spread_results,
                'total_strategies': len(spread_results.get('strategies', {})),
                'current_price': spread_results.get('current_price'),
                'expires_at': (datetime.now() + timedelta(seconds=expiry_seconds)).isoformat(),
                'data_source': 'TheTradeList_API'
            }
            
            serialized_data = json.dumps(cache_data, default=str)
            self.redis_client.setex(cache_key, expiry_seconds, serialized_data)
            
            index_key = f"spread_index:{ticker}"
            self.redis_client.setex(index_key, expiry_seconds, cache_key)
            
            logger.info(f"Cached spread analysis for {ticker} - {len(spread_results.get('strategies', {}))} strategies")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache spread analysis for {ticker}: {e}")
            return False
    
    def get_cached_spread_analysis(self, ticker: str) -> Optional[Dict]:
        """Retrieve cached spread analysis results for a ticker"""
        if not self.cache_enabled:
            return None
            
        try:
            index_key = f"spread_index:{ticker}"
            cache_key = self.redis_client.get(index_key)
            
            if cache_key:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    cached_time = datetime.fromisoformat(data.get('timestamp'))
                    age_minutes = (datetime.now() - cached_time).total_seconds() / 60
                    
                    if age_minutes <= 30:
                        logger.info(f"Cache HIT: Retrieved spread analysis for {ticker} (age: {age_minutes:.1f} min)")
                        return data
                    else:
                        logger.info(f"Cache EXPIRED: Spread analysis for {ticker} is {age_minutes:.1f} minutes old")
                        return None
            
            logger.info(f"Cache MISS: No cached spread analysis found for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached spread analysis for {ticker}: {e}")
            return None

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