"""
Real-time Options Spread Detection System
Uses TheTradeList API for authentic bid/ask pricing and Polygon API for contract data
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class RealTimeSpreadDetector:
    """Handles real-time options spread detection with authentic pricing"""
    
    def __init__(self):
        self.polygon_api_key = os.environ.get('POLYGON_API_KEY')
        self.tradelist_api_key = os.environ.get('TRADELIST_API_KEY')
        
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
        
        # Define strategy criteria
        strategy_criteria = {
            'aggressive': {
                'dte_min': 10,
                'dte_max': 17,
                'strike_filter': lambda strike, price: strike < price  # Below current price
            },
            'balanced': {
                'dte_min': 17,
                'dte_max': 28,
                'strike_filter': lambda strike, price: strike >= price * 0.98  # Within 2% below
            },
            'conservative': {
                'dte_min': 28,
                'dte_max': 42,
                'strike_filter': lambda strike, price: strike >= price * 0.90  # Within 10% below
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
                            logger.info(f"Quote retrieved for {ticker}: bid=${data['results'][0].get('bid_price')}, ask=${data['results'][0].get('ask_price')}")
                            return data['results'][0]
                    
                    logger.warning(f"Attempt {attempt + 1}: No quote data for {ticker}, status: {response.status_code}")
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Attempt {attempt + 1}: Network error for {ticker}: {e}")
                    if attempt < 2:  # Wait before retry
                        import time
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
            
            # Calculate metrics for top spread pairs (optimize for speed)
            best_spread = None
            roi_min, roi_max = roi_ranges[strategy]
            
            # Process only first 5 pairs to ensure completion within timeout
            pairs_to_check = spread_pairs[:5]
            logger.info(f"Processing {len(pairs_to_check)} spread pairs for {strategy} (optimized for speed)")
            
            for i, (long_contract, short_contract) in enumerate(pairs_to_check):
                logger.info(f"Checking spread {i+1}/{len(pairs_to_check)}: {long_contract.get('ticker')} / {short_contract.get('ticker')}")
                metrics = self.calculate_spread_metrics(long_contract, short_contract)
                
                if metrics and roi_min <= metrics['roi'] <= roi_max:
                    logger.info(f"Found viable {strategy} spread: {metrics['roi']:.1f}% ROI")
                    if not best_spread or metrics['roi'] > best_spread['roi']:
                        best_spread = metrics
                        logger.info(f"New best {strategy} spread: {metrics['roi']:.1f}% ROI")
            
            if best_spread:
                results[strategy] = {
                    'found': True,
                    'roi': f"{best_spread['roi']:.1f}%",
                    'expiration': best_spread['expiration'],
                    'dte': best_spread['dte'],
                    'strike_price': best_spread['long_strike'],
                    'short_strike_price': best_spread['short_strike'],
                    'spread_cost': best_spread['spread_cost'],
                    'max_profit': best_spread['max_profit'],
                    'contract_symbol': best_spread['long_ticker'],
                    'short_contract_symbol': best_spread['short_ticker'],
                    'management': 'Hold to expiration',
                    'strategy_title': f"{strategy.title()} Strategy"
                }
                logger.info(f"Found {strategy} spread: {best_spread['roi']:.1f}% ROI")
            else:
                results[strategy] = {
                    'found': False,
                    'reason': f'No spreads found within {roi_min}-{roi_max}% ROI range'
                }
        
        return results

def get_real_time_spreads(symbol: str, current_price: float) -> Dict[str, Dict]:
    """Main entry point for real-time spread detection"""
    detector = RealTimeSpreadDetector()
    return detector.find_best_spreads(symbol, current_price)