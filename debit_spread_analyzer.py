"""
Debit Spread Analysis Engine - Standalone Version for Vercel Integration
Contains all functionality needed for professional-grade options trading analysis
Uses TheTradeList API with ThinkOrSwim pricing methodology
"""

import os
import requests
import json
import time
import logging
import threading
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisCacheService:
    """Redis caching service for API efficiency"""
    
    def __init__(self):
        self.redis_url = os.environ.get('UPSTASH_REDIS_REST_URL')
        self.redis_token = os.environ.get('UPSTASH_REDIS_REST_TOKEN')
        self.cache_enabled = bool(self.redis_url and self.redis_token)
        
        if self.cache_enabled:
            logger.info("Redis caching enabled with Upstash")
        else:
            logger.info("Redis caching disabled - missing credentials")
    
    def _make_redis_request(self, command: str, key: str, value: str = None) -> Optional[Dict]:
        """Make HTTP request to Upstash Redis REST API"""
        if not self.cache_enabled:
            return None
            
        try:
            url = f"{self.redis_url}/{command}/{key}"
            if value is not None:
                url += f"/{value}"
            
            headers = {
                'Authorization': f'Bearer {self.redis_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Redis request failed: {e}")
        return None
    
    def get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Get cached data from Redis"""
        result = self._make_redis_request('get', cache_key)
        if result and result.get('result'):
            try:
                cached_data = json.loads(result['result'])
                expiry_time = datetime.fromisoformat(cached_data.get('expiry', ''))
                if datetime.now(timezone.utc) < expiry_time:
                    return cached_data
            except Exception:
                pass
        return None
    
    def cache_data(self, cache_key: str, data: Any, expiry_seconds: int = 30) -> bool:
        """Cache data in Redis with expiry"""
        if not self.cache_enabled:
            return False
            
        try:
            expiry_time = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)
            cache_payload = {
                'data': data,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'expiry': expiry_time.isoformat()
            }
            
            result = self._make_redis_request('setex', cache_key, f"{expiry_seconds}/{json.dumps(cache_payload)}")
            return result is not None
        except Exception as e:
            logger.debug(f"Cache write failed: {e}")
            return False

class SessionSpreadStorage:
    """In-memory storage for spread analysis results"""
    
    def __init__(self):
        self.storage = {}
        self.lock = threading.Lock()
    
    def store_spread(self, symbol: str, strategy: str, spread_data: Dict) -> str:
        """Store spread data and return unique ID"""
        timestamp = int(time.time())
        spread_id = f"{symbol}_{strategy}_{len(self.storage)}_{timestamp}"
        
        with self.lock:
            self.storage[spread_id] = {
                'symbol': symbol,
                'strategy': strategy,
                'data': spread_data,
                'stored_at': datetime.now(),
                'id': spread_id
            }
        
        logger.info(f"Stored session spread {spread_id}: {symbol} {strategy} ROI={spread_data.get('roi', 0):.1f}%")
        return spread_id
    
    def get_spread(self, spread_id: str) -> Optional[Dict]:
        """Retrieve spread data by ID"""
        with self.lock:
            return self.storage.get(spread_id)

class DebitSpreadAnalyzer:
    """Complete debit spread analysis engine"""
    
    def __init__(self):
        self.tradelist_api_key = os.environ.get('TRADELIST_API_KEY')
        self.cache_service = RedisCacheService()
        self.spread_storage = SessionSpreadStorage()
        
        # Request tracking
        self.request_lock = threading.Lock()
        self.request_status = {
            'active_requests': 0,
            'total_requests': 0,
            'recent_requests': deque()
        }
        
        # Strategy configurations
        self.strategy_configs = {
            'aggressive': {'roi_min': 25, 'roi_max': 50, 'dte_min': 10, 'dte_max': 17},
            'balanced': {'roi_min': 12, 'roi_max': 25, 'dte_min': 17, 'dte_max': 28},
            'conservative': {'roi_min': 8, 'roi_max': 15, 'dte_min': 28, 'dte_max': 42}
        }
    
    def get_real_time_stock_price(self, symbol: str) -> Optional[float]:
        """Get real-time stock price using TheTradeList API with caching"""
        try:
            # Check cache first
            cache_key = f"stock_price_snapshot:{symbol}"
            cached_data = self.cache_service.get_cached_data(cache_key)
            
            if cached_data and cached_data.get('data', {}).get('price'):
                cached_price = cached_data['data']['price']
                logger.info(f"Cache HIT: Using cached price for {symbol}: ${cached_price}")
                return float(cached_price)
            
            logger.info(f"Cache MISS: Fetching fresh price for {symbol}")
            
            # Use exact same API endpoints as working system
            url = "https://api.thetradelist.com/v1/data/snapshot-locale"
            params = {
                'tickers': f"{symbol},",  # API requires comma after symbol
                'apiKey': self.tradelist_api_key
            }
            
            response = requests.get(url, params=params, timeout=3)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if data.get('status') == 'OK' and data.get('tickers'):
                        tickers = data['tickers']
                        
                        # Find the ticker in the list
                        for ticker_data in tickers:
                            if ticker_data.get('ticker') == symbol:
                                fmv = ticker_data.get('fmv')
                                if fmv and fmv > 0:
                                    # Cache the result
                                    self.cache_service.cache_data(cache_key, {'price': fmv}, 30)
                                    logger.info(f"API SUCCESS: FMV price for {symbol}: ${fmv}")
                                    return float(fmv)
                                break
                except Exception as json_error:
                    logger.error(f"JSON parsing error for snapshot: {json_error}")
            
            # Fallback to trader scanner endpoint
            scanner_url = "https://api.thetradelist.com/v1/data/get_trader_scanner_data.php"
            scanner_params = {
                'apiKey': self.tradelist_api_key,
                'returntype': 'json'
            }
            
            scanner_response = requests.get(scanner_url, params=scanner_params, timeout=15)
            
            if scanner_response.status_code == 200:
                try:
                    scanner_data = scanner_response.json()
                    
                    # Look for the ticker in scanner data
                    for item in scanner_data:
                        if item.get('symbol') == symbol:
                            price = float(item.get('stock_price', 0))
                            if price > 0:
                                self.cache_service.cache_data(cache_key, {'price': price}, 30)
                                logger.info(f"Scanner price for {symbol}: ${price}")
                                return price
                            break
                except Exception as scanner_error:
                    logger.error(f"Scanner endpoint error: {scanner_error}")
            
            logger.error(f"Failed to get price for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching stock price for {symbol}: {e}")
            return None
    
    def get_all_contracts(self, symbol: str) -> List[Dict]:
        """Get all options contracts for a symbol"""
        try:
            url = "https://api.thetradelist.com/v1/data/options-contracts"
            params = {
                'underlying_ticker': symbol,
                'apiKey': self.tradelist_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                contracts = data['results']
                logger.info(f"Retrieved {len(contracts)} contracts for {symbol}")
                return contracts
            
            logger.warning(f"No contracts found for {symbol}")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching contracts for {symbol}: {e}")
            return []
    
    def filter_contracts_by_strategy(self, contracts: List[Dict], strategy: str, current_price: float) -> List[Dict]:
        """Filter contracts based on strategy criteria"""
        config = self.strategy_configs.get(strategy, self.strategy_configs['balanced'])
        filtered = []
        
        for contract in contracts:
            try:
                # Only call options
                if contract.get('option_type') != 'call':
                    continue
                
                # Parse expiration and calculate DTE
                expiration_str = contract.get('expiration_date', '')
                if not expiration_str:
                    continue
                
                expiration_date = datetime.strptime(expiration_str, '%Y-%m-%d')
                dte = (expiration_date - datetime.now()).days
                
                # Filter by DTE range
                if not (config['dte_min'] <= dte <= config['dte_max']):
                    continue
                
                # Filter by strike price (reasonable range around current price)
                strike_price = float(contract.get('strike_price', 0))
                if not (current_price * 0.85 <= strike_price <= current_price * 1.15):
                    continue
                
                filtered.append(contract)
                
            except Exception as e:
                logger.debug(f"Error processing contract: {e}")
                continue
        
        logger.info(f"Filtered to {len(filtered)} {strategy} contracts from {len(contracts)} total")
        return filtered
    
    def get_options_quote(self, contract_symbol: str) -> Optional[Dict]:
        """Get real-time quote for options contract"""
        try:
            cache_key = f"options_quote:{contract_symbol}"
            cached_data = self.cache_service.get_cached_data(cache_key)
            
            if cached_data and cached_data.get('data'):
                return cached_data['data']
            
            url = "https://api.thetradelist.com/v1/data/snapshot-options"
            params = {
                'tickers': f"O:{contract_symbol}",
                'apiKey': self.tradelist_api_key
            }
            
            response = requests.get(url, params=params, timeout=3)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                for result in data['results']:
                    if result.get('name') == f"O:{contract_symbol}":
                        quote_data = {
                            'bid': result.get('bid', 0),
                            'ask': result.get('ask', 0),
                            'last': result.get('last_trade', {}).get('price', 0)
                        }
                        
                        self.cache_service.cache_data(cache_key, quote_data, 30)
                        return quote_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting quote for {contract_symbol}: {e}")
            return None
    
    def calculate_spread_metrics(self, long_contract: Dict, short_contract: Dict) -> Optional[Dict]:
        """Calculate comprehensive spread metrics using ThinkOrSwim pricing"""
        try:
            long_symbol = long_contract.get('ticker', '')
            short_symbol = short_contract.get('ticker', '')
            
            # Get quotes for both options
            long_quote = self.get_options_quote(long_symbol)
            short_quote = self.get_options_quote(short_symbol)
            
            if not long_quote or not short_quote:
                return None
            
            # Extract pricing data
            long_bid = float(long_quote.get('bid', 0))
            long_ask = float(long_quote.get('ask', 0))
            short_bid = float(short_quote.get('bid', 0))
            short_ask = float(short_quote.get('ask', 0))
            
            if any(price <= 0 for price in [long_bid, long_ask, short_bid, short_ask]):
                return None
            
            # ThinkOrSwim professional spread pricing methodology
            net_ask = long_ask - short_bid  # Cost to establish spread at worst prices
            net_bid = short_ask - long_bid  # Credit if we could reverse at best prices
            
            # Handle negative net bid (illiquid spreads)
            if net_bid < 0:
                net_bid = net_ask * 0.95  # Professional platform methodology
            
            # Calculate spread cost using professional mid-price
            spread_cost = (net_ask + net_bid) / 2
            
            # Extract strike prices and calculate metrics
            long_strike = float(long_contract.get('strike_price', 0))
            short_strike = float(short_contract.get('strike_price', 0))
            spread_width = short_strike - long_strike
            max_profit = spread_width - spread_cost
            
            # Calculate ROI
            roi = (max_profit / spread_cost * 100) if spread_cost > 0 else 0
            
            # Parse expiration
            expiration_str = long_contract.get('expiration_date', '')
            expiration_date = datetime.strptime(expiration_str, '%Y-%m-%d')
            dte = (expiration_date - datetime.now()).days
            
            logger.info(f"Spread calculated: {long_symbol}/{short_symbol}, ROI: {roi:.1f}%, Cost: ${spread_cost:.2f}")
            logger.info(f"  Quote details - Long: bid=${long_bid}, ask=${long_ask} | Short: bid=${short_bid}, ask=${short_ask}")
            logger.info(f"  ThinkOrSwim calc - Net Ask: ${net_ask:.2f}, Net Bid: ${net_bid:.2f}, Mid: ${spread_cost:.2f}")
            
            return {
                'long_strike': long_strike,
                'short_strike': short_strike,
                'spread_width': spread_width,
                'spread_cost': spread_cost,
                'max_profit': max_profit,
                'roi': roi,
                'dte': dte,
                'expiration': expiration_str,
                'long_ticker': long_symbol,
                'short_ticker': short_symbol,
                'long_price': (long_bid + long_ask) / 2,
                'short_price': (short_bid + short_ask) / 2,
                'net_ask': net_ask,
                'net_bid': net_bid
            }
            
        except Exception as e:
            logger.error(f"Error calculating spread metrics: {e}")
            return None
    
    def generate_spread_pairs(self, contracts: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """Generate valid spread pairs from contracts"""
        pairs = []
        
        # Group by expiration date
        by_expiration = {}
        for contract in contracts:
            exp_date = contract.get('expiration_date')
            if exp_date not in by_expiration:
                by_expiration[exp_date] = []
            by_expiration[exp_date].append(contract)
        
        # Generate pairs within each expiration
        for exp_date, exp_contracts in by_expiration.items():
            # Sort by strike price
            exp_contracts.sort(key=lambda x: float(x.get('strike_price', 0)))
            
            # Create spread pairs
            for i, long_contract in enumerate(exp_contracts):
                long_strike = float(long_contract.get('strike_price', 0))
                
                for short_contract in exp_contracts[i+1:]:
                    short_strike = float(short_contract.get('strike_price', 0))
                    width = short_strike - long_strike
                    
                    # Accept reasonable spread widths
                    if 0.5 <= width <= 15.0:
                        pairs.append((long_contract, short_contract))
        
        logger.info(f"Generated {len(pairs)} spread pairs")
        return pairs
    
    def find_best_spreads(self, symbol: str, current_price: float) -> Dict[str, Dict]:
        """Find best spreads for all strategies"""
        results = {}
        
        # Get all contracts
        all_contracts = self.get_all_contracts(symbol)
        if not all_contracts:
            return {
                'aggressive': {'found': False, 'reason': 'No contracts available'},
                'balanced': {'found': False, 'reason': 'No contracts available'},
                'conservative': {'found': False, 'reason': 'No contracts available'}
            }
        
        strategies = ['aggressive', 'balanced', 'conservative']
        roi_ranges = {
            'aggressive': (25, 50),
            'balanced': (12, 25),
            'conservative': (8, 15)
        }
        
        def process_single_strategy(strategy):
            """Process a single strategy"""
            logger.info(f"🚀 STARTING {strategy.upper()} STRATEGY for {symbol}")
            
            # Filter contracts by strategy
            filtered_contracts = self.filter_contracts_by_strategy(all_contracts, strategy, current_price)
            
            if not filtered_contracts:
                return strategy, {
                    'found': False,
                    'reason': f'No contracts match {strategy} criteria'
                }
            
            # Generate spread pairs
            spread_pairs = self.generate_spread_pairs(filtered_contracts)
            
            if not spread_pairs:
                return strategy, {
                    'found': False,
                    'reason': f'No viable spread pairs for {strategy}'
                }
            
            # Progressive width search: $1, $2, $5, $10
            roi_min, roi_max = roi_ranges[strategy]
            final_spread = None
            width_targets = [1.0, 2.0, 5.0, 10.0]
            
            for target_width in width_targets:
                logger.info(f"🎯 Searching for ${target_width:.0f} wide {strategy} spreads...")
                
                # Filter pairs for this width
                width_pairs = []
                for pair in spread_pairs:
                    long_contract, short_contract = pair
                    long_strike = float(long_contract.get('strike_price', 0))
                    short_strike = float(short_contract.get('strike_price', 0))
                    spread_width = short_strike - long_strike
                    
                    if abs(spread_width - target_width) <= 0.1:
                        width_pairs.append(pair)
                
                if not width_pairs:
                    continue
                
                logger.info(f"   Found {len(width_pairs)} pairs at ${target_width:.0f} width")
                
                # Analyze pairs concurrently
                best_width_spread = None
                best_width_roi = 0
                
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_pair = {
                        executor.submit(self.calculate_spread_metrics, pair[0], pair[1]): pair 
                        for pair in width_pairs[:20]  # Limit to prevent timeout
                    }
                    
                    for future in as_completed(future_to_pair):
                        try:
                            metrics = future.result()
                            if metrics:
                                roi = metrics['roi']
                                
                                if roi_min <= roi <= roi_max and roi > best_width_roi:
                                    best_width_spread = metrics
                                    best_width_roi = roi
                                    logger.info(f"   New best ${target_width:.0f} wide spread: {roi:.1f}% ROI")
                        except Exception as e:
                            logger.error(f"Error calculating spread: {e}")
                
                # If found viable spread at this width, stop searching
                if best_width_spread:
                    final_spread = best_width_spread
                    logger.info(f"✅ FOUND optimal ${target_width:.0f} wide {strategy} spread: {best_width_roi:.1f}% ROI - STOPPING search")
                    break
            
            if final_spread:
                # Add current price context
                final_spread['current_price'] = current_price
                
                # Store spread and get unique ID
                spread_id = self.spread_storage.store_spread(symbol, strategy, final_spread)
                
                return strategy, {
                    'found': True,
                    'spread_id': spread_id,
                    'roi': f"{final_spread['roi']:.1f}%",
                    'expiration': final_spread['expiration'],
                    'dte': final_spread['dte'],
                    'strike_price': final_spread['long_strike'],
                    'short_strike_price': final_spread['short_strike'],
                    'spread_cost': final_spread['spread_cost'],
                    'max_profit': final_spread['max_profit'],
                    'spread_width': final_spread['spread_width'],
                    'contract_symbol': final_spread['long_ticker'],
                    'short_contract_symbol': final_spread['short_ticker'],
                    'long_price': final_spread.get('long_price', 0),
                    'short_price': final_spread.get('short_price', 0),
                    'management': 'Hold to expiration',
                    'strategy_title': f"{strategy.title()} Strategy"
                }
            else:
                return strategy, {
                    'found': False,
                    'reason': f'No spreads found within {roi_min}-{roi_max}% ROI range'
                }
        
        # Process all strategies concurrently
        with ThreadPoolExecutor(max_workers=3) as strategy_executor:
            strategy_futures = {
                strategy_executor.submit(process_single_strategy, strategy): strategy
                for strategy in strategies
            }
            
            for future in as_completed(strategy_futures):
                strategy, result = future.result()
                results[strategy] = result
        
        return results
    
    def analyze_ticker(self, ticker: str) -> Dict:
        """Main analysis function for a ticker"""
        try:
            # Track request
            with self.request_lock:
                self.request_status['active_requests'] += 1
                self.request_status['total_requests'] += 1
                self.request_status['recent_requests'].append(datetime.now(timezone.utc))
            
            ticker = ticker.upper().strip()
            logger.info(f"API: Starting spread analysis for {ticker}")
            
            # Get current stock price
            current_price = self.get_real_time_stock_price(ticker)
            if not current_price:
                return {
                    'success': False,
                    'error': f'Unable to fetch current price for {ticker}'
                }
            
            # Analyze all strategies
            logger.info(f"API: Analyzing spread strategies for {ticker} at ${current_price}")
            all_strategies_data = self.find_best_spreads(ticker, current_price)
            
            strategies = ['aggressive', 'balanced', 'conservative']
            all_strategies_analysis = {}
            successful_strategies = 0
            
            # Process each strategy result
            for strategy in strategies:
                try:
                    strategy_data = all_strategies_data.get(strategy, {'found': False})
                    
                    if strategy_data.get('found'):
                        # Extract data from strategy results
                        long_strike = float(strategy_data.get('strike_price', 0))
                        short_strike = float(strategy_data.get('short_strike_price', 0))
                        spread_cost = float(strategy_data.get('spread_cost', 0))
                        max_profit = float(strategy_data.get('max_profit', 0))
                        
                        # Handle ROI conversion
                        roi_value = strategy_data.get('roi', 0)
                        if isinstance(roi_value, str) and roi_value.endswith('%'):
                            roi = float(roi_value.replace('%', ''))
                        else:
                            roi = float(roi_value) if roi_value else 0
                        
                        dte = int(strategy_data.get('dte', 0))
                        expiration = strategy_data.get('expiration', 'N/A')
                        long_contract = strategy_data.get('contract_symbol', 'N/A')
                        short_contract = strategy_data.get('short_contract_symbol', 'N/A')
                        
                        # Extract authentic bid/ask prices
                        long_price = float(strategy_data.get('long_price', 0))
                        short_price = float(strategy_data.get('short_price', 0))
                        
                        # Calculate metrics
                        spread_width = short_strike - long_strike
                        breakeven = long_strike + spread_cost
                        max_loss = spread_cost
                        
                        # Generate profit/loss scenarios
                        scenarios = []
                        scenario_changes = [-10, -5, -2.5, -1, 0, 1, 2.5, 5, 10]
                        
                        for change_pct in scenario_changes:
                            future_price = current_price * (1 + change_pct/100)
                            
                            # Calculate option values at expiration
                            long_call_value = max(0, future_price - long_strike)
                            short_call_value = max(0, future_price - short_strike)
                            spread_value = long_call_value - short_call_value
                            
                            # Calculate profit/loss
                            profit_loss = spread_value - spread_cost
                            scenario_roi = (profit_loss / spread_cost) * 100 if spread_cost > 0 else 0
                            outcome = "profit" if profit_loss > 0 else "loss"
                            
                            scenarios.append({
                                'price_change_percent': change_pct,
                                'future_stock_price': round(future_price, 2),
                                'spread_value_at_expiration': round(spread_value, 2),
                                'profit_loss': round(profit_loss, 2),
                                'roi_percent': round(scenario_roi, 1),
                                'outcome': outcome
                            })
                        
                        # Build strategy analysis
                        all_strategies_analysis[strategy] = {
                            'found': True,
                            'spread_details': {
                                'long_strike': round(long_strike, 2),
                                'short_strike': round(short_strike, 2),
                                'spread_width': round(spread_width, 2),
                                'spread_cost': round(spread_cost, 2),
                                'max_profit': round(max_profit, 2),
                                'max_loss': round(max_loss, 2),
                                'breakeven_price': round(breakeven, 2),
                                'roi_percent': round(roi, 1),
                                'days_to_expiration': dte,
                                'expiration_date': expiration
                            },
                            'contracts': {
                                'long_contract': long_contract,
                                'short_contract': short_contract,
                                'long_price': round(long_price, 2),
                                'short_price': round(short_price, 2)
                            },
                            'price_scenarios': scenarios,
                            'strategy_info': {
                                'strategy_name': strategy.title(),
                                'description': strategy_data.get('management', f'{strategy.title()} debit spread strategy'),
                                'risk_level': 'High' if strategy == 'aggressive' else 'Medium' if strategy == 'balanced' else 'Low'
                            }
                        }
                        
                        logger.info(f"API: Found {strategy} spread - ROI: {roi:.1f}%, Width: ${spread_width:.2f}, DTE: {dte}")
                        successful_strategies += 1
                        
                    else:
                        # No spread found for this strategy
                        all_strategies_analysis[strategy] = {
                            'found': False,
                            'error': strategy_data.get('reason', 'No suitable spreads found'),
                            'strategy_info': {
                                'strategy_name': strategy.title(),
                                'risk_level': 'High' if strategy == 'aggressive' else 'Medium' if strategy == 'balanced' else 'Low'
                            }
                        }
                        logger.info(f"API: No {strategy} spread found - {strategy_data.get('reason', 'No spreads available')}")
                
                except Exception as e:
                    logger.error(f"API: Error analyzing {strategy} strategy for {ticker}: {e}")
                    all_strategies_analysis[strategy] = {
                        'found': False,
                        'error': f'Analysis error: {str(e)}',
                        'strategy_info': {
                            'strategy_name': strategy.title(),
                            'risk_level': 'High' if strategy == 'aggressive' else 'Medium' if strategy == 'balanced' else 'Low'
                        }
                    }
            
            # Return comprehensive analysis
            logger.info(f"API: Successfully analyzed {ticker} - Found {successful_strategies}/3 strategies")
            
            return {
                'success': True,
                'ticker': ticker,
                'current_stock_price': round(current_price, 2),
                'analysis_timestamp': datetime.now().isoformat(),
                'strategies_found': successful_strategies,
                'strategies': all_strategies_analysis,
                'pricing_methodology': 'ThinkOrSwim Professional Spread Pricing',
                'data_source': 'TheTradeList API - Authentic Market Data'
            }
            
        except Exception as e:
            logger.error(f"API: Critical error analyzing {ticker}: {e}")
            return {
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }
        
        finally:
            # Clean up active request counter
            with self.request_lock:
                self.request_status['active_requests'] = max(0, self.request_status['active_requests'] - 1)
    
    def get_status(self) -> Dict:
        """Get current API status"""
        with self.request_lock:
            # Clean up old requests (last 10 seconds)
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(seconds=10)
            
            while (self.request_status['recent_requests'] and 
                   self.request_status['recent_requests'][0] < cutoff_time):
                self.request_status['recent_requests'].popleft()
            
            return {
                'status': len(self.request_status['recent_requests']),
                'total_requests': self.request_status['total_requests'],
                'active_requests': self.request_status['active_requests']
            }

# Global analyzer instance
analyzer = DebitSpreadAnalyzer()

# Main analysis function for external use
def analyze_debit_spread(ticker: str) -> Dict:
    """
    Main function to analyze debit spreads for a ticker
    
    Args:
        ticker: Stock symbol to analyze
    
    Returns:
        Dictionary with complete analysis results
    """
    return analyzer.analyze_ticker(ticker)

def get_api_status() -> Dict:
    """
    Get API status and request monitoring data
    
    Returns:
        Dictionary with status information
    """
    return analyzer.get_status()

# Example usage and testing
if __name__ == "__main__":
    # Test the analyzer
    result = analyze_debit_spread("AAPL")
    print(json.dumps(result, indent=2))