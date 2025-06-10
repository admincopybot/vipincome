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

logger = logging.getLogger(__name__)



class RealTimeSpreadDetector:
    """Handles real-time options spread detection with authentic pricing"""
    
    def __init__(self):
        self.polygon_api_key = os.environ.get('POLYGON_API_KEY')
        self.tradelist_api_key = os.environ.get('TRADELIST_API_KEY')
    
    def get_real_time_stock_price(self, symbol: str) -> Optional[float]:
        """Get real-time stock price using TheTradeList API snapshot endpoint"""
        try:
            url = "https://api.thetradelist.com/v1/data/snapshot-locale"
            params = {
                'tickers': f"{symbol},",  # API requires comma after symbol
                'apiKey': self.tradelist_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    results = data['results']
                    if symbol in results:
                        stock_data = results[symbol]
                        fmv = stock_data.get('fmv')
                        if fmv:
                            logger.info(f"Real-time price for {symbol}: ${fmv} (from TheTradeList FMV)")
                            return float(fmv)
                            
            logger.warning(f"Failed to get real-time price for {symbol} from TheTradeList API")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching real-time price for {symbol}: {e}")
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
        """Fetch ALL option contracts for a symbol from Polygon API"""
        try:
            url = f"https://api.polygon.io/v3/reference/options/contracts"
            params = {
                'underlying_ticker': symbol,
                'contract_type': 'call',  # Only call options for debit spreads
                'limit': 1000,
                'apikey': self.polygon_api_key
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                contracts = data.get('results', [])
                logger.info(f"Fetched {len(contracts)} call contracts for {symbol}")
                return contracts
            else:
                logger.error(f"Polygon API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching contracts: {e}")
            return []
    
    def filter_contracts_by_strategy(self, contracts: List[Dict], strategy: str, current_price: float) -> List[Dict]:
        """Filter contracts by DTE and strike price criteria for each strategy"""
        filtered = []
        
        # Define strategy criteria - Focus on near-the-money strikes for viable debit spreads
        strategy_criteria = {
            'aggressive': {
                'dte_min': 10,
                'dte_max': 17,
                'strike_filter': lambda strike, price: price * 0.90 <= strike < price  # 90-100% of current price
            },
            'balanced': {
                'dte_min': 17,
                'dte_max': 28,
                'strike_filter': lambda strike, price: price * 0.85 <= strike < price  # 85-100% of current price
            },
            'conservative': {
                'dte_min': 28,
                'dte_max': 42,
                'strike_filter': lambda strike, price: price * 0.80 <= strike < price  # 80-100% of current price
            }
        }
        
        criteria = strategy_criteria.get(strategy)
        if not criteria:
            return []
        
        for contract in contracts:
            # Calculate DTE
            expiration = contract.get('expiration_date', '')
            dte = self.calculate_dte(expiration)
            
            # Check DTE range
            if not (criteria['dte_min'] <= dte <= criteria['dte_max']):
                continue
            
            # Check strike price criteria
            strike = float(contract.get('strike_price', 0))
            if not criteria['strike_filter'](strike, current_price):
                continue
                
            # Add DTE to contract for later use
            contract['dte'] = dte
            filtered.append(contract)
        
        logger.info(f"Filtered to {len(filtered)} contracts for {strategy} strategy")
        return filtered
    
    def generate_spread_pairs(self, contracts: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """Generate viable debit spread pairs from filtered contracts"""
        pairs = []
        valid_widths = [0.50, 1.00, 2.50, 5.00, 10.00]
        
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
                        logger.debug(f"Rejecting spread: short strike {short_strike} >= current price {current_price}")
                        continue
                    
                    logger.debug(f"Valid spread found: Buy ${long_strike} / Sell ${short_strike} (current: ${current_price})")
                    
                    # Check if spread width matches valid intervals
                    spread_width = short_strike - long_strike
                    if spread_width in valid_widths:
                        pairs.append((long_contract, short_contract))
        
        logger.info(f"Generated {len(pairs)} viable spread pairs")
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
            for attempt in range(3):
                try:
                    response = requests.get(url, params=params, timeout=10)
                    
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
            
            # Calculate spread cost (we buy long at ASK, sell short at BID)
            long_price = long_quote.get('ask_price', 0)
            short_price = short_quote.get('bid_price', 0)
            
            if long_price <= 0 or short_price <= 0:
                return None
            
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
            
            # Prepare comprehensive webhook data
            webhook_data = {
                'timestamp': datetime.now().isoformat(),
                'calculation_type': 'spread_metrics',
                'symbol': getattr(self, 'current_symbol', 'UNKNOWN'),
                'current_price': getattr(self, 'current_price', 0),
                'long_contract': {
                    'ticker': long_ticker,
                    'strike_price': long_strike,
                    'expiration_date': long_contract.get('expiration_date'),
                    'contract_type': long_contract.get('contract_type'),
                    'dte': long_contract.get('dte', 0)
                },
                'short_contract': {
                    'ticker': short_ticker,
                    'strike_price': short_strike,
                    'expiration_date': short_contract.get('expiration_date'),
                    'contract_type': short_contract.get('contract_type'),
                    'dte': short_contract.get('dte', 0)
                },
                'long_quote': {
                    'bid_price': long_quote.get('bid_price', 0),
                    'ask_price': long_quote.get('ask_price', 0),
                    'last_price': long_quote.get('last_price', 0),
                    'volume': long_quote.get('volume', 0)
                },
                'short_quote': {
                    'bid_price': short_quote.get('bid_price', 0),
                    'ask_price': short_quote.get('ask_price', 0),
                    'last_price': short_quote.get('last_price', 0),
                    'volume': short_quote.get('volume', 0)
                },
                'calculations': {
                    'spread_cost': spread_cost,
                    'spread_width': spread_width,
                    'max_profit': max_profit,
                    'roi': roi,
                    'long_price_used': long_price,  # ASK price
                    'short_price_used': short_price  # BID price
                },
                'strategy_context': getattr(self, 'current_strategy', 'UNKNOWN')
            }
            

            
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
        
        for strategy in strategies:
            logger.info(f"Processing {strategy} strategy for {symbol}")
            
            # Store current strategy for webhook context
            self.current_strategy = strategy
            
            # Send strategy start webhook
            strategy_start_data = {
                'timestamp': datetime.now().isoformat(),
                'calculation_type': 'strategy_start',
                'symbol': symbol,
                'current_price': current_price,
                'strategy': strategy,
                'roi_range': roi_ranges[strategy],
                'total_contracts_available': len(all_contracts)
            }

            
            # Filter contracts by strategy criteria
            filtered_contracts = self.filter_contracts_by_strategy(
                all_contracts, strategy, current_price
            )
            
            if not filtered_contracts:
                results[strategy] = {
                    'found': False,
                    'reason': f'No contracts match {strategy} criteria'
                }
                continue
            
            # Generate spread pairs
            spread_pairs = self.generate_spread_pairs(filtered_contracts)
            
            if not spread_pairs:
                results[strategy] = {
                    'found': False,
                    'reason': f'No viable spread pairs for {strategy}'
                }
                continue
            
            # Calculate metrics for ALL spread pairs and prioritize $1 spreads
            best_spread = None
            best_one_dollar_spread = None
            roi_min, roi_max = roi_ranges[strategy]
            
            # Process ALL spread pairs and prioritize $1 spreads
            pairs_to_check = spread_pairs
            logger.info(f"Processing ALL {len(pairs_to_check)} spread pairs for {strategy} strategy")
            
            for i, (long_contract, short_contract) in enumerate(pairs_to_check):
                logger.info(f"Checking spread {i+1}/{len(pairs_to_check)}: {long_contract.get('ticker')} / {short_contract.get('ticker')}")
                metrics = self.calculate_spread_metrics(long_contract, short_contract)
                
                if metrics:
                    spread_width = metrics['spread_width']
                    roi = metrics['roi']
                    logger.info(f"ROI calculated: {roi:.1f}% (target: {roi_min}-{roi_max}%), Spread width: ${spread_width:.2f}")
                    
                    if roi_min <= roi <= roi_max:
                        logger.info(f"Found viable {strategy} spread: {roi:.1f}% ROI, ${spread_width:.2f} width")
                        
                        # Prioritize $1 spreads first
                        if abs(spread_width - 1.0) <= 0.01:  # $1 spread (with small tolerance)
                            if not best_one_dollar_spread or roi > best_one_dollar_spread['roi']:
                                best_one_dollar_spread = metrics
                                logger.info(f"New best $1 {strategy} spread: {roi:.1f}% ROI")
                        
                        # Track best overall spread as backup
                        if not best_spread or roi > best_spread['roi']:
                            best_spread = metrics
                            logger.info(f"New best overall {strategy} spread: {roi:.1f}% ROI")
            
            # Use $1 spread if found, otherwise use best overall spread
            final_spread = best_one_dollar_spread if best_one_dollar_spread else best_spread
            
            if final_spread:
                spread_type = "$1 spread" if final_spread == best_one_dollar_spread else "spread"
                logger.info(f"Selected best {strategy} {spread_type}: {final_spread['roi']:.1f}% ROI, ${final_spread['spread_width']:.2f} width")
            
            if final_spread:
                # Store authentic spread and get unique session ID
                from spread_storage import spread_storage
                
                # Add current price to spread data
                final_spread['current_price'] = current_price
                
                spread_id = spread_storage.store_spread(symbol, strategy, final_spread)
                
                results[strategy] = {
                    'found': True,
                    'spread_id': spread_id,  # Unique ID for Step 4 retrieval
                    'roi': f"{final_spread['roi']:.1f}%",
                    'expiration': final_spread['expiration'],
                    'dte': final_spread['dte'],
                    'strike_price': final_spread['long_strike'],
                    'short_strike_price': final_spread['short_strike'],
                    'spread_cost': final_spread['spread_cost'],
                    'max_profit': final_spread['max_profit'],
                    'contract_symbol': final_spread['long_ticker'],
                    'short_contract_symbol': final_spread['short_ticker'],
                    'management': 'Hold to expiration',
                    'strategy_title': f"{strategy.title()} Strategy"
                }
                logger.info(f"Found {strategy} spread: {final_spread['roi']:.1f}% ROI, stored as {spread_id}")
            else:
                results[strategy] = {
                    'found': False,
                    'reason': f'No spreads found within {roi_min}-{roi_max}% ROI range'
                }
        
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