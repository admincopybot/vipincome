"""
Real-time Options Spread Detection System
Uses TheTradeList API for authentic bid/ask pricing and Polygon API for contract data
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
        self.polygon_api_key = os.environ.get('POLYGON_API_KEY')
        self.tradelist_api_key = os.environ.get('TRADELIST_API_KEY')
    
    def get_real_time_stock_price(self, symbol: str) -> Optional[float]:
        """Get real-time stock price using TheTradeList API - PRIMARY PRICING SOURCE"""
        try:
            logger.info(f"🔍 FETCHING PRICE for {symbol} from TheTradeList API")
            
            # First try snapshot endpoint for FMV (Fair Market Value)
            url = "https://api.thetradelist.com/v1/data/snapshot-locale"
            params = {
                'tickers': f"{symbol},",  # API requires comma after symbol
                'apiKey': self.tradelist_api_key
            }
            
            logger.info(f"📡 SNAPSHOT API CALL: URL={url}")
            logger.info(f"📡 SNAPSHOT PARAMS: tickers={symbol}, (with comma)")
            logger.info(f"📡 SNAPSHOT API KEY: {'Present' if self.tradelist_api_key else 'MISSING'}")
            
            response = requests.get(url, params=params, timeout=3)
            
            logger.info(f"📡 SNAPSHOT RESPONSE: Status={response.status_code}")
            logger.info(f"📡 SNAPSHOT RESPONSE TEXT: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"📡 SNAPSHOT JSON DATA: {data}")
                    
                    if data.get('status') == 'OK' and data.get('tickers'):
                        tickers = data['tickers']
                        logger.info(f"📡 SNAPSHOT TICKERS: {len(tickers)} found")
                        
                        # Find the ticker in the list
                        for ticker_data in tickers:
                            if ticker_data.get('ticker') == symbol:
                                logger.info(f"📡 SNAPSHOT {symbol} DATA: {ticker_data}")
                                fmv = ticker_data.get('fmv')
                                if fmv and fmv > 0:
                                    logger.info(f"✅ TheTradeList FMV price for {symbol}: ${fmv}")
                                    return float(fmv)
                                else:
                                    logger.warning(f"❌ FMV for {symbol} is null or zero: {fmv}")
                                break
                        else:
                            available_tickers = [t.get('ticker') for t in tickers]
                            logger.warning(f"❌ {symbol} not found in snapshot tickers: {available_tickers}")
                    else:
                        logger.warning(f"❌ Snapshot API status not OK or no results: status={data.get('status')}, has_results={bool(data.get('results'))}")
                except Exception as json_error:
                    logger.error(f"❌ JSON parsing error for snapshot: {json_error}")
            else:
                logger.error(f"❌ Snapshot API HTTP error: {response.status_code} - {response.text}")
            
            # Fallback to trader scanner endpoint
            logger.info(f"🔄 FALLBACK: Trying trader scanner for {symbol}")
            scanner_url = "https://api.thetradelist.com/v1/data/get_trader_scanner_data.php"
            scanner_params = {
                'apiKey': self.tradelist_api_key,
                'returntype': 'json'
            }
            
            logger.info(f"📡 SCANNER API CALL: URL={scanner_url}")
            logger.info(f"📡 SCANNER PARAMS: returntype=json")
            
            scanner_response = requests.get(scanner_url, params=scanner_params, timeout=15)
            
            logger.info(f"📡 SCANNER RESPONSE: Status={scanner_response.status_code}")
            
            if scanner_response.status_code == 200:
                try:
                    scanner_data = scanner_response.json()
                    logger.info(f"📡 SCANNER DATA TYPE: {type(scanner_data)}")
                    logger.info(f"📡 SCANNER DATA LENGTH: {len(scanner_data) if isinstance(scanner_data, list) else 'Not a list'}")
                    
                    # Find the specific ticker
                    if isinstance(scanner_data, list):
                        found_symbols = []
                        for item in scanner_data:
                            item_symbol = item.get('symbol')
                            found_symbols.append(item_symbol)
                            if item_symbol == symbol:
                                logger.info(f"📡 FOUND {symbol} in scanner data: {item}")
                                last_price = item.get('lastprice')
                                if last_price and float(last_price) > 0:
                                    logger.info(f"✅ TheTradeList scanner price for {symbol}: ${last_price}")
                                    return float(last_price)
                                else:
                                    logger.warning(f"❌ Scanner lastprice for {symbol} is invalid: {last_price}")
                        
                        logger.warning(f"❌ {symbol} not found in scanner data. Available symbols: {found_symbols[:10]}...")
                    else:
                        logger.error(f"❌ Scanner data is not a list: {type(scanner_data)}")
                        
                except Exception as json_error:
                    logger.error(f"❌ JSON parsing error for scanner: {json_error}")
                    logger.error(f"❌ Scanner response text: {scanner_response.text[:500]}")
            else:
                logger.error(f"❌ Scanner API HTTP error: {scanner_response.status_code} - {scanner_response.text}")
                                
            logger.error(f"❌ FINAL RESULT: No valid price found for {symbol} from TheTradeList API")
            return None
            
        except Exception as e:
            logger.error(f"❌ EXCEPTION in get_real_time_stock_price for {symbol}: {e}")
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
        """Fetch ALL option contracts for a symbol from Polygon API with pagination"""
        try:
            all_contracts = []
            url = f"https://api.polygon.io/v3/reference/options/contracts"
            next_url = None
            page_count = 0
            
            while True:
                page_count += 1
                logger.info(f"📥 Fetching contracts page {page_count} for {symbol}")
                
                if next_url:
                    # Use next_url for pagination
                    response = requests.get(f"{next_url}&apikey={self.polygon_api_key}")
                else:
                    # Initial request
                    params = {
                        'underlying_ticker': symbol,
                        'contract_type': 'call',  # Only call options for debit spreads
                        'limit': 1000,  # Maximum per page
                        'apikey': self.polygon_api_key
                    }
                    response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    contracts = data.get('results', [])
                    all_contracts.extend(contracts)
                    
                    logger.info(f"📥 Page {page_count}: {len(contracts)} contracts (Total: {len(all_contracts)})")
                    
                    # Check for pagination
                    next_url = data.get('next_url')
                    if not next_url or len(contracts) == 0:
                        break
                        
                    # Safety limit to prevent infinite loops
                    if page_count >= 10:
                        logger.warning(f"⚠️  Reached page limit (10), stopping at {len(all_contracts)} contracts")
                        break
                else:
                    logger.error(f"Polygon API error: {response.status_code}")
                    break
            
            logger.info(f"📥 TOTAL CONTRACTS FETCHED: {len(all_contracts)} call contracts for {symbol}")
            return all_contracts
                
        except Exception as e:
            logger.error(f"Error fetching contracts: {e}")
            return []
    
    def filter_contracts_by_strategy(self, contracts: List[Dict], strategy: str, current_price: float) -> List[Dict]:
        """Filter contracts by DTE and strike price criteria for each strategy"""
        filtered = []
        
        # Define strategy criteria - Allow wide strike ranges, let spread generation handle short call restriction
        strategy_criteria = {
            'aggressive': {
                'dte_min': 10,
                'dte_max': 17,
                'strike_filter': lambda strike, price: float(price) * 0.75 <= float(strike) <= float(price) * 1.25  # Wide range for long/short combinations
            },
            'balanced': {
                'dte_min': 17,
                'dte_max': 28,
                'strike_filter': lambda strike, price: float(price) * 0.70 <= float(strike) <= float(price) * 1.30  # Wide range for long/short combinations
            },
            'conservative': {
                'dte_min': 28,
                'dte_max': 42,
                'strike_filter': lambda strike, price: float(price) * 0.65 <= float(strike) <= float(price) * 1.35  # Wide range for long/short combinations
            }
        }
        
        criteria = strategy_criteria.get(strategy)
        if not criteria:
            logger.info(f"❌ No criteria found for strategy: {strategy}")
            return []
        
        logger.info(f"🔍 DETAILED FILTERING for {strategy.upper()} strategy:")
        logger.info(f"   Current price: ${current_price}")
        logger.info(f"   DTE range: {criteria['dte_min']}-{criteria['dte_max']} days")
        logger.info(f"   Strike range: ${float(current_price) * (0.75 if strategy == 'aggressive' else 0.70 if strategy == 'balanced' else 0.65):.2f} - ${float(current_price) * (1.25 if strategy == 'aggressive' else 1.30 if strategy == 'balanced' else 1.35):.2f}")
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
        """Generate OPTIMIZED spread pairs - LIMITED to prevent memory timeouts"""
        pairs = []
        
        # MEMORY OPTIMIZATION: Limit total contracts processed
        if len(contracts) > 100:
            contracts = contracts[:100]  # Only process top 100 contracts
            logger.info(f"🔧 MEMORY OPTIMIZATION: Limited to {len(contracts)} contracts to prevent timeouts")
        
        # Group by expiration date
        by_expiration = {}
        for contract in contracts:
            exp_date = contract.get('expiration_date')
            if exp_date not in by_expiration:
                by_expiration[exp_date] = []
            by_expiration[exp_date].append(contract)
        
        current_price = getattr(self, 'current_price', 260)
        max_pairs_per_width = 20  # STRICT limit per width to prevent memory issues
        
        # Process each expiration separately
        for exp_date, exp_contracts in by_expiration.items():
            exp_contracts.sort(key=lambda x: float(x.get('strike_price', 0)))
            
            # Generate pairs by width priority - STOP when we have enough
            width_counts = {1.0: 0, 2.5: 0, 5.0: 0}
            
            for i, long_contract in enumerate(exp_contracts):
                if sum(width_counts.values()) >= 60:  # Total limit across all widths
                    break
                    
                for j, short_contract in enumerate(exp_contracts[i+1:], i+1):
                    long_strike = float(long_contract.get('strike_price', 0))
                    short_strike = float(short_contract.get('strike_price', 0))
                    
                    # Basic validation
                    if long_strike >= short_strike:
                        continue
                    if short_strike >= current_price:
                        continue
                    
                    spread_width = short_strike - long_strike
                    
                    # Only track priority widths
                    if abs(spread_width - 1.0) < 0.01 and width_counts[1.0] < max_pairs_per_width:
                        pairs.append((long_contract, short_contract))
                        width_counts[1.0] += 1
                    elif abs(spread_width - 2.5) < 0.01 and width_counts[2.5] < max_pairs_per_width:
                        pairs.append((long_contract, short_contract))
                        width_counts[2.5] += 1
                    elif abs(spread_width - 5.0) < 0.01 and width_counts[5.0] < max_pairs_per_width:
                        pairs.append((long_contract, short_contract))
                        width_counts[5.0] += 1
        
        # Sort by width priority
        def width_priority(pair):
            long_contract, short_contract = pair
            width = float(short_contract.get('strike_price', 0)) - float(long_contract.get('strike_price', 0))
            if abs(width - 1.0) < 0.01:
                return 1
            elif abs(width - 2.5) < 0.01:
                return 2
            elif abs(width - 5.0) < 0.01:
                return 3
            else:
                return 4
        
        pairs.sort(key=width_priority)
        
        logger.info(f"🔧 OPTIMIZED: Generated {len(pairs)} spread pairs (limited to prevent timeouts)")
        return pairs
    
    def get_real_time_quote(self, ticker: str) -> Optional[Dict]:
        """Get real-time bid/ask quote from TheTradeList API with AGGRESSIVE throttling"""
        try:
            # AGGRESSIVE THROTTLING: 2-second delay between each API call
            time.sleep(2.0)
            
            url = "https://api.thetradelist.com/v1/data/last-quote"
            params = {
                'ticker': ticker,
                'apiKey': self.tradelist_api_key
            }
            
            # Reduced retries to prevent timeout loops
            for attempt in range(1):  # Only 1 attempt instead of 2
                try:
                    response = requests.get(url, params=params, timeout=5)  # Longer timeout
                    
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


def get_real_time_spreads_with_early_termination(symbol: str, current_price: float) -> Dict:
    """
    POST TRIGGER ONLY: Early termination version that stops after finding 2 viable strategies
    This function is ONLY used by the POST trigger endpoint to prevent worker timeouts
    Normal Step 3 analysis uses get_real_time_spreads() which remains unchanged
    """
    logger.info(f"🚀 EARLY TERMINATION MODE: Starting analysis for {symbol}")
    
    detector = RealTimeSpreadDetector()
    
    # Get real-time stock price if not provided
    if current_price is None:
        current_price = detector.get_real_time_stock_price(symbol)
        
        if current_price is None:
            logger.error(f"Failed to get real-time price for {symbol}")
            return {
                'aggressive': {'found': False, 'reason': 'Failed to get current stock price'},
                'balanced': {'found': False, 'reason': 'Failed to get current stock price'},
                'conservative': {'found': False, 'reason': 'Failed to get current stock price'}
            }
    
    logger.info(f"Using real-time price ${current_price:.2f} for {symbol} early termination analysis")
    
    # Fetch contracts from TheTradeList API 
    contracts = detector.fetch_options_contracts(symbol)
    if not contracts:
        logger.warning(f"No contracts found for {symbol}")
        return {
            'aggressive': {'found': False, 'reason': 'No options contracts available'},
            'balanced': {'found': False, 'reason': 'No options contracts available'},  
            'conservative': {'found': False, 'reason': 'No options contracts available'}
        }
    
    # Store contracts for processing
    detector.contracts = contracts
    detector.current_price = current_price
    
    # EARLY TERMINATION LOGIC: Stop after finding 2 viable strategies
    results = {}
    strategies_found = 0
    target_strategies = 2
    
    # Strategy order: aggressive first (usually fastest), then conservative, then balanced
    strategy_order = ['aggressive', 'conservative', 'balanced']
    
    logger.info(f"🎯 TARGET: Will stop after finding {target_strategies} viable strategies")
    
    for strategy in strategy_order:
        if strategies_found >= target_strategies:
            logger.info(f"✅ EARLY TERMINATION: Found {strategies_found} strategies, stopping analysis")
            break
            
        logger.info(f"🔍 Processing {strategy} strategy...")
        try:
            strategy_name, result = detector.find_best_spread(strategy)
            results[strategy_name] = result
            
            if result.get('found', False):
                strategies_found += 1
                logger.info(f"✅ {strategy} strategy SUCCESS ({strategies_found}/{target_strategies})")
            else:
                logger.info(f"❌ {strategy} strategy failed")
                
        except Exception as e:
            logger.error(f"Error processing {strategy}: {str(e)}")
            results[strategy] = {
                'found': False,
                'error': str(e)
            }
    
    # Fill in empty results for strategies we didn't process due to early termination
    for strategy in strategy_order:
        if strategy not in results:
            results[strategy] = {
                'found': False,
                'reason': 'Skipped due to early termination'
            }
    
    logger.info(f"📊 EARLY TERMINATION COMPLETE: {strategies_found} viable strategies found")
    return results