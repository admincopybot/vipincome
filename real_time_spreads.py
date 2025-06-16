"""
Real-time Options Spread Detection System
Uses TheTradeList API exclusively for authentic pricing and contract data
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)



class RealTimeSpreadDetector:
    """Handles real-time options spread detection with authentic pricing"""
    
    def __init__(self):
        self.tradelist_api_key = os.environ.get('TRADELIST_API_KEY')
    
    def get_real_time_stock_price(self, symbol: str) -> Optional[float]:
        """Get real-time stock price using TheTradeList API with Redis caching"""
        try:
            # Use Redis cached stock price function
            from redis_cache_service import cache_service
            
            # Check cache first (30-second expiry)
            cache_key = f"stock_price_snapshot:{symbol}"
            cached_data = cache_service.get_cached_data(cache_key)
            
            if cached_data and cached_data.get('data', {}).get('price'):
                cached_price = cached_data['data']['price']
                logger.info(f"Cache HIT: Using cached price for {symbol}: ${cached_price}")
                return float(cached_price)
            
            logger.info(f"Cache MISS: Fetching fresh price for {symbol}")
            
            # First try snapshot endpoint for FMV (Fair Market Value)
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
                                    # Cache the result for 30 seconds
                                    cache_service.set_cached_data(cache_key, {'price': fmv})
                                    logger.info(f"API SUCCESS: Cached FMV price for {symbol}: ${fmv}")
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
                    
                    # Find the specific ticker
                    if isinstance(scanner_data, list):
                        for item in scanner_data:
                            if item.get('symbol') == symbol:
                                last_price = item.get('lastprice')
                                if last_price and float(last_price) > 0:
                                    # Cache the result for 30 seconds
                                    cache_service.set_cached_data(cache_key, {'price': last_price})
                                    logger.info(f"API FALLBACK: Cached scanner price for {symbol}: ${last_price}")
                                    return float(last_price)
                        
                except Exception as json_error:
                    logger.error(f"JSON parsing error for scanner: {json_error}")
                                
            logger.error(f"No valid price found for {symbol} from TheTradeList API")
            return None
            
        except Exception as e:
            logger.error(f"Exception in get_real_time_stock_price for {symbol}: {e}")
            return None
        
    def calculate_dte(self, expiration_date: str) -> int:
        """Calculate days to expiration from expiration date string"""
        try:
            exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
            today = datetime.now()
            return (exp_date - today).days
        except:
            return 0
    
    def get_all_contracts(self, symbol: str) -> List[Dict]:
        """Fetch ALL option contracts for a symbol from TheTradeList API using Redis cache"""
        try:
            if not self.tradelist_api_key:
                logger.error("TheTradeList API key not configured")
                return []
            
            # Use cached function from redis_cache_service
            from redis_cache_service import get_options_contracts_cached
            
            logger.info(f"📥 Fetching contracts for {symbol} from TheTradeList API (with Redis cache)")
            contracts = get_options_contracts_cached(symbol, self.tradelist_api_key)
            
            # Filter for call options only and add required fields
            call_contracts = []
            for contract in contracts:
                # Log the first few contracts to debug structure
                if len(call_contracts) < 3:
                    logger.info(f"DEBUG Contract structure: {contract}")
                
                if contract.get('contract_type') == 'call':  # API uses 'contract_type' not 'option_type'
                    # Ensure contract has all required fields for spread calculation
                    processed_contract = {
                        'ticker': contract.get('ticker'),  # Option ticker symbol
                        'strike_price': contract.get('strike_price', 0),
                        'expiration_date': contract.get('expiration_date'),
                        'option_type': 'call',  # Standardize to 'option_type' for internal use
                        'underlying_ticker': contract.get('underlying_ticker', symbol),
                        'dte': self.calculate_dte(contract.get('expiration_date', ''))
                    }
                    call_contracts.append(processed_contract)
            
            logger.info(f"📥 TOTAL CONTRACTS FETCHED: {len(call_contracts)} call contracts for {symbol}")
            return call_contracts
                
        except Exception as e:
            logger.error(f"Error fetching contracts: {e}")
            return []
    
    def filter_contracts_by_strategy(self, contracts: List[Dict], strategy: str, current_price: float) -> List[Dict]:
        """Filter contracts by DTE and strike price criteria for each strategy"""
        filtered = []
        
        # Define strategy criteria - Allow wide strike ranges, let spread generation handle short call restriction
        strategy_criteria = {
            'aggressive': {
                'dte_min': 1,
                'dte_max': 15,
                'strike_filter': lambda strike, price: price * 0.75 <= strike <= price * 1.25  # Wide range for long/short combinations
            },
            'balanced': {
                'dte_min': 7,
                'dte_max': 30,
                'strike_filter': lambda strike, price: price * 0.70 <= strike <= price * 1.30  # Wide range for long/short combinations
            },
            'conservative': {
                'dte_min': 15,
                'dte_max': 50,
                'strike_filter': lambda strike, price: price * 0.65 <= strike <= price * 1.35  # Wide range for long/short combinations
            }
        }
        
        criteria = strategy_criteria.get(strategy)
        if not criteria:
            logger.info(f"❌ No criteria found for strategy: {strategy}")
            return []
        
        logger.info(f"🔍 DETAILED FILTERING for {strategy.upper()} strategy:")
        logger.info(f"   Current price: ${current_price}")
        logger.info(f"   DTE range: {criteria['dte_min']}-{criteria['dte_max']} days")
        logger.info(f"   Strike range: ${current_price * (0.75 if strategy == 'aggressive' else 0.70 if strategy == 'balanced' else 0.65):.2f} - ${current_price * (1.25 if strategy == 'aggressive' else 1.30 if strategy == 'balanced' else 1.35):.2f}")
        logger.info(f"   Total contracts to check: {len(contracts)}")
        
        dte_passed = 0
        strike_passed = 0
        both_passed = 0
        
        for i, contract in enumerate(contracts):
            # Calculate DTE
            expiration = contract.get('expiration_date', '')
            dte = self.calculate_dte(expiration)
            strike = float(contract.get('strike_price', 0))
            
            # Detailed logging for first 5 contracts
            if i < 5:
                logger.info(f"   Contract {i+1}: Strike=${strike}, DTE={dte}, Exp={expiration}")
            
            # Check DTE range
            dte_ok = criteria['dte_min'] <= dte <= criteria['dte_max']
            if dte_ok:
                dte_passed += 1
            
            # Check strike price criteria  
            strike_ok = criteria['strike_filter'](strike, current_price)
            if strike_ok:
                strike_passed += 1
            
            # Both criteria must pass
            if dte_ok and strike_ok:
                both_passed += 1
                contract['dte'] = dte
                filtered.append(contract)
                if len(filtered) <= 3:  # Log first few that pass
                    logger.info(f"   ✅ PASSED: Strike=${strike}, DTE={dte}")
            elif i < 10:  # Log first 10 failures
                logger.info(f"   ❌ FAILED: Strike=${strike}, DTE={dte} (DTE_OK:{dte_ok}, STRIKE_OK:{strike_ok})")
        
        logger.info(f"🔍 FILTERING RESULTS for {strategy.upper()}:")
        logger.info(f"   DTE passed: {dte_passed}/{len(contracts)}")
        logger.info(f"   Strike passed: {strike_passed}/{len(contracts)}")
        logger.info(f"   Both passed: {both_passed}/{len(contracts)}")
        logger.info(f"   Final filtered contracts: {len(filtered)}")
        
        return filtered
    
    def generate_spread_pairs(self, contracts: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """Generate ALL possible debit spread pairs from filtered contracts, prioritized by width"""
        pairs = []
        
        # Group by expiration date
        by_expiration = {}
        for contract in contracts:
            exp_date = contract.get('expiration_date')
            if exp_date not in by_expiration:
                by_expiration[exp_date] = []
            by_expiration[exp_date].append(contract)
        
        # Generate ALL possible pairs within each expiration
        for exp_date, exp_contracts in by_expiration.items():
            # Sort by strike price
            exp_contracts.sort(key=lambda x: float(x.get('strike_price', 0)))
            
            for i, long_contract in enumerate(exp_contracts):
                for j, short_contract in enumerate(exp_contracts[i+1:], i+1):
                    long_strike = float(long_contract.get('strike_price', 0))
                    short_strike = float(short_contract.get('strike_price', 0))
                    
                    # Ensure proper debit spread structure
                    if long_strike >= short_strike:
                        continue
                    
                    # CRITICAL: For debit spreads, short call must be below current price
                    current_price = getattr(self, 'current_price', 260)  # Use stored current price
                    if short_strike >= current_price:
                        continue
                    
                    # Add spread pairs with MAXIMUM $10 width restriction
                    spread_width = short_strike - long_strike
                    if 0 < spread_width <= 10.0:  # Only spreads up to $10 wide
                        pairs.append((long_contract, short_contract))
        
        # Sort pairs by width priority: $1 first, then $2.50, then $5, then others
        def width_priority(pair):
            long_contract, short_contract = pair
            width = float(short_contract.get('strike_price', 0)) - float(long_contract.get('strike_price', 0))
            
            # Priority order: $1, $2.50, $5, $0.50, $10, others
            if abs(width - 1.0) < 0.01:
                return 1  # $1 spreads get highest priority
            elif abs(width - 2.5) < 0.01:
                return 2  # $2.50 spreads second
            elif abs(width - 5.0) < 0.01:
                return 3  # $5 spreads third
            elif abs(width - 0.5) < 0.01:
                return 4  # $0.50 spreads fourth
            elif abs(width - 10.0) < 0.01:
                return 5  # $10 spreads fifth
            else:
                return 6 + width  # All other widths by size
        
        # Sort by priority (lower number = higher priority)
        pairs.sort(key=width_priority)
        
        logger.info(f"Generated {len(pairs)} total spread pairs (MAX $10 wide), prioritized by width ($1, $2.50, $5, etc.)")
        return pairs
    
    def get_real_time_quote(self, ticker: str) -> Optional[Dict]:
        """Get real-time bid/ask quote from TheTradeList API with retry mechanism"""
        try:
            url = "https://api.thetradelist.com/v1/data/last-quote"
            params = {
                'ticker': ticker,
                'apiKey': self.tradelist_api_key
            }
            
            # Add timeout and retry for network issues
            for attempt in range(2):
                try:
                    response = requests.get(url, params=params, timeout=3)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') == 'OK' and data.get('results'):
                            quote = data['results'][0]
                            logger.info(f"Quote retrieved for {ticker}: bid=${quote.get('bid_price')}, ask=${quote.get('ask_price')}")
                            return quote
                    
                    logger.warning(f"Attempt {attempt + 1}: No quote data for {ticker}, status: {response.status_code}")
                    

                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Attempt {attempt + 1}: Network error for {ticker}: {e}")
                    if attempt < 2:
                        time.sleep(1)
                    continue
                
                break
            
            logger.error(f"Failed to get quote for {ticker} after 3 attempts")
            return None
            
        except Exception as e:
            logger.error(f"Critical error getting quote for {ticker}: {e}")
            return None
    
    def calculate_spread_metrics(self, long_contract: Dict, short_contract: Dict) -> Optional[Dict]:
        """Calculate spread cost, max profit, and ROI using real-time pricing"""
        try:
            # Get real-time quotes
            long_ticker = long_contract.get('ticker')
            short_ticker = short_contract.get('ticker')
            
            if not long_ticker or not short_ticker:
                return None
            
            long_quote = self.get_real_time_quote(long_ticker)
            short_quote = self.get_real_time_quote(short_ticker)
            
            if not long_quote or not short_quote:
                return None
            
            # Calculate spread cost using mid prices (standard for ROI calculations)
            long_bid = long_quote.get('bid_price', 0)
            long_ask = long_quote.get('ask_price', 0)
            short_bid = short_quote.get('bid_price', 0)
            short_ask = short_quote.get('ask_price', 0)
            
            if long_bid <= 0 or long_ask <= 0 or short_bid <= 0 or short_ask <= 0:
                return None
            
            # Use mid prices for both legs
            long_price = (long_bid + long_ask) / 2
            short_price = (short_bid + short_ask) / 2
            
            spread_cost = long_price - short_price
            
            # Calculate max profit
            long_strike = float(long_contract.get('strike_price', 0))
            short_strike = float(short_contract.get('strike_price', 0))
            spread_width = short_strike - long_strike
            max_profit = spread_width - spread_cost
            
            # Calculate ROI
            if spread_cost > 0:
                roi = (max_profit / spread_cost) * 100
            else:
                roi = 0
            
            # Log spread calculation details
            logger.info(f"Spread calculated: {long_ticker}/{short_ticker}, ROI: {roi:.1f}%, Cost: ${spread_cost:.2f}")
            

            
            return {
                'long_ticker': long_ticker,
                'short_ticker': short_ticker,
                'long_strike': long_strike,
                'short_strike': short_strike,
                'long_price': long_price,
                'short_price': short_price,
                'spread_cost': spread_cost,
                'spread_width': spread_width,
                'max_profit': max_profit,
                'roi': roi,
                'expiration': long_contract.get('expiration_date'),
                'dte': long_contract.get('dte', 0)
            }
            
        except Exception as e:
            logger.error(f"Error calculating spread metrics: {e}")
            return None
    
    def find_best_spreads(self, symbol: str, current_price: float) -> Dict[str, Dict]:
        """Main function to find best spreads for all strategies"""
        results = {}
        
        # Store context for webhook logging
        self.current_symbol = symbol
        self.current_price = current_price
        
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
            """Process a single strategy with concurrent spread checking"""
            logger.info(f"🚀 STARTING {strategy.upper()} STRATEGY for {symbol}")
            logger.info(f"   Total contracts available: {len(all_contracts)}")
            
            # Store current strategy for webhook context
            self.current_strategy = strategy
            
            # Filter contracts by strategy criteria
            logger.info(f"🔍 CALLING FILTER for {strategy} strategy...")
            filtered_contracts = self.filter_contracts_by_strategy(
                all_contracts, strategy, current_price
            )
            logger.info(f"🔍 FILTER COMPLETE for {strategy}: {len(filtered_contracts)} contracts")
            
            if not filtered_contracts:
                logger.info(f"❌ {strategy.upper()} FAILED: No contracts passed filtering")
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
            
            # PROGRESSIVE WIDTH SEARCH: Start with $1, then $2, then $5, then $10
            roi_min, roi_max = roi_ranges[strategy]
            final_spread = None
            
            # Define width search order: tightest spreads first
            width_targets = [1.0, 2.0, 5.0, 10.0]
            
            for target_width in width_targets:
                logger.info(f"🎯 Searching for ${target_width:.0f} wide {strategy} spreads...")
                
                # Filter pairs for this specific width
                width_pairs = []
                for pair in spread_pairs:
                    long_contract, short_contract = pair
                    long_strike = float(long_contract.get('strike_price', 0))
                    short_strike = float(short_contract.get('strike_price', 0))
                    spread_width = short_strike - long_strike
                    
                    # Allow small tolerance for width matching
                    if abs(spread_width - target_width) <= 0.1:
                        width_pairs.append(pair)
                
                if not width_pairs:
                    logger.info(f"   No ${target_width:.0f} wide pairs found")
                    continue
                
                logger.info(f"   Found {len(width_pairs)} pairs at ${target_width:.0f} width")
                
                # Analyze these width-specific pairs
                best_width_spread = None
                best_width_roi = 0
                
                def calculate_single_spread(pair_data):
                    i, (long_contract, short_contract) = pair_data
                    return self.calculate_spread_metrics(long_contract, short_contract)
                
                # Use ThreadPoolExecutor for concurrent calculations
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_pair = {
                        executor.submit(calculate_single_spread, (i, pair)): pair 
                        for i, pair in enumerate(width_pairs)
                    }
                    
                    # Process results as they complete
                    for future in as_completed(future_to_pair):
                        pair = future_to_pair[future]
                        long_contract, short_contract = pair
                        
                        try:
                            metrics = future.result()
                            if metrics:
                                spread_width = metrics['spread_width']
                                roi = metrics['roi']
                                
                                if roi_min <= roi <= roi_max:
                                    logger.info(f"   Found viable ${target_width:.0f} wide spread: {roi:.1f}% ROI")
                                    
                                    # Track best for this width
                                    if roi > best_width_roi:
                                        best_width_spread = metrics
                                        best_width_roi = roi
                                        logger.info(f"   New best ${target_width:.0f} wide spread: {roi:.1f}% ROI")
                        except Exception as e:
                            logger.error(f"Error calculating spread metrics: {str(e)}")
                
                # If we found a viable spread at this width, use it and stop searching
                if best_width_spread:
                    final_spread = best_width_spread
                    logger.info(f"✅ FOUND optimal ${target_width:.0f} wide {strategy} spread: {best_width_roi:.1f}% ROI - STOPPING search")
                    break
                else:
                    logger.info(f"   No viable ${target_width:.0f} wide spreads found, trying next width...")
            
            # If no spreads found in any width category
            if not final_spread:
                logger.info(f"❌ No viable {strategy} spreads found in any width category")
            
            if final_spread:
                width_value = final_spread['spread_width']
                spread_type = f"${width_value:.2f} spread"
                logger.info(f"Selected best {strategy} {spread_type}: {final_spread['roi']:.1f}% ROI, ${final_spread['spread_width']:.2f} width")
                
                # Store authentic spread and get unique session ID
                from spread_storage import spread_storage
                
                # Add current price to spread data
                final_spread['current_price'] = current_price
                
                spread_id = spread_storage.store_spread(symbol, strategy, final_spread)
                
                return strategy, {
                    'found': True,
                    'spread_id': spread_id,  # Unique ID for Step 4 retrieval
                    'roi': f"{final_spread['roi']:.1f}%",
                    'expiration': final_spread['expiration'],
                    'dte': final_spread['dte'],
                    'strike_price': final_spread['long_strike'],
                    'short_strike_price': final_spread['short_strike'],
                    'spread_cost': final_spread['spread_cost'],
                    'max_profit': final_spread['max_profit'],
                    'spread_width': final_spread['spread_width'],  # Add spread width for Step 3 display
                    'contract_symbol': final_spread['long_ticker'],
                    'short_contract_symbol': final_spread['short_ticker'],
                    'management': 'Hold to expiration',
                    'strategy_title': f"{strategy.title()} Strategy"
                }
            else:
                return strategy, {
                    'found': False,
                    'reason': f'No spreads found within {roi_min}-{roi_max}% ROI range'
                }
        
        # Process all strategies concurrently
        logger.info(f"Starting concurrent processing of all three strategies for {symbol}")
        logger.info(f"Available contracts: {len(all_contracts)}")
        logger.info(f"Current price: ${current_price}")
        
        with ThreadPoolExecutor(max_workers=3) as strategy_executor:
            # Submit all strategies for concurrent processing
            strategy_futures = {
                strategy_executor.submit(process_single_strategy, strategy): strategy
                for strategy in strategies
            }
            
            # Collect results as they complete
            for future in as_completed(strategy_futures):
                strategy, result = future.result()
                results[strategy] = result
                logger.info(f"Completed processing for {strategy} strategy: {result}")
        
        return results

def get_real_time_spreads(symbol: str, current_price: Optional[float] = None) -> Dict[str, Dict]:
    """Main entry point for real-time spread detection"""
    detector = RealTimeSpreadDetector()
    
    # Get real-time price from TheTradeList API if not provided, with Polygon fallback
    if current_price is None:
        current_price = detector.get_real_time_stock_price(symbol)
        
        # Fallback to Polygon API if TheTradeList fails
        if current_price is None:
            logger.info(f"TheTradeList API failed for {symbol}, trying Polygon API fallback")
            try:
                from enhanced_polygon_client import EnhancedPolygonService
                current_price = EnhancedPolygonService.get_etf_price(symbol)
                if current_price:
                    logger.info(f"Polygon fallback successful: {symbol} = ${current_price}")
                else:
                    logger.error(f"Both TheTradeList and Polygon APIs failed for {symbol}")
            except Exception as e:
                logger.error(f"Polygon fallback failed: {e}")
        
        if current_price is None:
            logger.error(f"Failed to get real-time price for {symbol} from all sources")
            return {
                'aggressive': {'found': False, 'reason': 'Failed to get current stock price'},
                'balanced': {'found': False, 'reason': 'Failed to get current stock price'},
                'conservative': {'found': False, 'reason': 'Failed to get current stock price'}
            }
    
    # Add logging for the actual price being used
    logger.info(f"Using real-time price ${current_price:.2f} for {symbol} spread detection")
    
    return detector.find_best_spreads(symbol, current_price)