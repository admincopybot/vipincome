"""
Robust Automated Debit Spread Analysis Pipeline
Uses TheTradeList API with Redis caching for optimal performance
"""
import os
import logging
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from redis_cache_service import cache_service, get_stock_price_cached, get_options_contracts_cached

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobustSpreadPipeline:
    def __init__(self):
        self.tradelist_key = os.environ.get("TRADELIST_API_KEY")
        self.tickers_endpoint = "https://001e4434-2e2e-4e25-b65b-8b894c786e9d-00-26sv8d7lbk7i3.worf.replit.dev/api/top-tickers"
        self.spreads_endpoint = "https://001e4434-2e2e-4e25-b65b-8b894c786e9d-00-26sv8d7lbk7i3.worf.replit.dev/api/spreads-update"
        
    def fetch_top_tickers(self) -> Optional[Dict]:
        """Fetch top 3 tickers from the API"""
        try:
            logger.info(f"Fetching top tickers from endpoint")
            response = requests.get(self.tickers_endpoint, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                tickers = data.get('tickers', [])
                logger.info(f"Received {len(tickers)} tickers: {tickers}")
                return data
            else:
                logger.error(f"Failed to fetch tickers: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return None
    
    def get_stock_price(self, ticker: str) -> Optional[float]:
        """Get current stock price from TheTradeList API"""
        if not self.tradelist_key:
            logger.error("TheTradeList API key not configured")
            return None
            
        try:
            price = get_stock_price_cached(ticker, self.tradelist_key)
            if price:
                logger.info(f"Got price for {ticker}: ${price:.2f}")
                return price
            else:
                logger.error(f"Unable to fetch price for {ticker}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")
            
        return None
    
    def get_options_contracts(self, ticker: str) -> List[Dict]:
        """Get all options contracts using Redis cache"""
        if not self.tradelist_key:
            return []
            
        try:
            contracts = get_options_contracts_cached(ticker, self.tradelist_key)
            
            # Filter for calls with 7-50 DTE range
            valid_contracts = []
            for contract in contracts:
                # Only process call options
                if contract.get('option_type') != 'call':
                    continue
                    
                exp_date = contract.get('expiration_date')
                if exp_date:
                    try:
                        exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
                        dte = (exp_dt - datetime.now()).days
                        if 7 <= dte <= 50:
                            valid_contracts.append(contract)
                    except:
                        continue
            
            logger.info(f"Found {len(valid_contracts)} valid call options for {ticker}")
            return valid_contracts
                
        except Exception as e:
            logger.error(f"Error fetching options contracts for {ticker}: {e}")
            
        return []
    
    def analyze_ticker_spreads(self, ticker: str) -> Dict:
        """Analyze debit spreads for a single ticker with Redis caching"""
        logger.info(f"Analyzing spreads for {ticker}")
        
        # Check for cached spread analysis first
        cached_analysis = cache_service.get_cached_spread_analysis(ticker)
        if cached_analysis:
            logger.info(f"Using cached spread analysis for {ticker}")
            return cached_analysis.get('results', {})
        
        try:
            # Cache miss - perform fresh analysis
            logger.info(f"Cache miss - performing fresh spread analysis for {ticker}")
            
            # Get current stock price
            current_price = self.get_stock_price(ticker)
            if not current_price:
                return {'error': f'Unable to fetch price for {ticker}'}
            
            # Get all options contracts
            contracts = self.get_options_contracts(ticker)
            if not contracts:
                return {'error': f'No valid options contracts found for {ticker}'}
            
            # Analyze spreads
            all_spreads = self.find_dollar_wide_spreads(contracts, current_price)
            
            if not all_spreads:
                return {'error': f'No profitable spreads found for {ticker}'}
            
            # Categorize by strategy
            result = self.categorize_spreads(ticker, current_price, all_spreads)
            
            # Cache the results for 30 minutes
            cache_service.cache_spread_analysis(ticker, result, expiry_seconds=1800)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return {'error': str(e)}
    
    def find_dollar_wide_spreads(self, contracts: List[Dict], current_price: float) -> List[Dict]:
        """Find $1-wide debit spreads from TheTradeList options contracts"""
        spreads = []
        
        # Sort contracts by strike price
        contracts.sort(key=lambda x: float(x.get('strike_price', 0)))
        
        for i, long_contract in enumerate(contracts):
            long_strike = float(long_contract.get('strike_price', 0))
            long_price = float(long_contract.get('last_price', 0))
            long_symbol = long_contract.get('ticker', '')
            exp_date = long_contract.get('expiration_date', '')
            
            if long_price <= 0 or not exp_date:
                continue
            
            # Look for short option $1 higher
            for short_contract in contracts[i+1:]:
                short_strike = float(short_contract.get('strike_price', 0))
                short_price = float(short_contract.get('last_price', 0))
                short_symbol = short_contract.get('ticker', '')
                
                # Must be same expiration and $1 spread
                if (short_contract.get('expiration_date') == exp_date and 
                    abs(short_strike - long_strike - 1.0) < 0.01 and 
                    short_price > 0):
                    
                    # Calculate spread metrics
                    spread_cost = long_price - short_price
                    if spread_cost <= 0:
                        continue
                    
                    max_profit = 1.0 - spread_cost
                    roi = (max_profit / spread_cost) * 100
                    
                    if roi >= 5:  # Minimum 5% ROI
                        try:
                            dte = (datetime.strptime(exp_date, '%Y-%m-%d') - datetime.now()).days
                            exp_display = datetime.strptime(exp_date, '%Y-%m-%d').strftime('%B %d')
                            
                            spread_data = {
                                'long_strike': long_strike,
                                'short_strike': short_strike,
                                'long_option_symbol': long_symbol,
                                'short_option_symbol': short_symbol,
                                'long_price': round(long_price, 2),
                                'short_price': round(short_price, 2),
                                'spread_cost': round(spread_cost, 2),
                                'max_profit': round(max_profit, 2),
                                'max_loss': round(spread_cost, 2),
                                'roi_percent': round(roi, 1),
                                'breakeven': round(long_strike + spread_cost, 2),
                                'expiration_date': exp_date,
                                'days_to_expiration': dte,
                                'distance_otm_percent': round(((long_strike - current_price) / current_price) * 100, 1),
                                'current_stock_price': round(current_price, 2),
                                'trade_construction': {
                                    'buy_description': f"Buy the ${long_strike:.0f} {exp_display} Call",
                                    'sell_description': f"Sell the ${short_strike:.0f} {exp_display} Call",
                                    'strategy_name': "Bull Call Spread"
                                }
                            }
                            
                            # Add price scenarios
                            spread_data['profit_scenarios'] = self.calculate_scenarios(
                                current_price, long_strike, short_strike, spread_cost
                            )
                            
                            spreads.append(spread_data)
                        except Exception:
                            continue
                    break
        
        return spreads
    
    def calculate_scenarios(self, current_price: float, long_strike: float, 
                          short_strike: float, spread_cost: float) -> List[Dict]:
        """Calculate profit/loss scenarios in the exact format expected"""
        scenarios = []
        percentages = [-10, -5, -2.5, -1, 0, 1, 2.5, 5, 10]
        
        for pct in percentages:
            future_price = current_price * (1 + pct/100)
            
            # Calculate spread value at expiration
            long_value = max(0, future_price - long_strike)
            short_value = max(0, future_price - short_strike)
            spread_value = long_value - short_value
            
            # Convert to per-contract profit/loss (multiply by 100 for contract size)
            profit_loss_per_contract = (spread_value - spread_cost) * 100
            
            scenarios.append({
                'stock_price': round(future_price, 2),
                'price_change': pct,
                'profit_loss': round(profit_loss_per_contract),
                'status': 'profit' if profit_loss_per_contract > 0 else 'loss'
            })
        
        return scenarios
    
    def categorize_spreads(self, ticker: str, current_price: float, spreads: List[Dict]) -> Dict:
        """Categorize spreads by strategy"""
        # Sort by ROI descending
        spreads.sort(key=lambda x: -x['roi_percent'])
        
        # Categorize by strategy
        aggressive = [s for s in spreads if s['roi_percent'] >= 25 and s['days_to_expiration'] <= 21]
        balanced = [s for s in spreads if 15 <= s['roi_percent'] < 25 and 14 <= s['days_to_expiration'] <= 35]
        conservative = [s for s in spreads if 8 <= s['roi_percent'] < 15 and s['days_to_expiration'] >= 21]
        
        return {
            'ticker': ticker,
            'current_price': current_price,
            'analysis_timestamp': datetime.now().isoformat(),
            'total_spreads_found': len(spreads),
            'strategies': {
                'aggressive': aggressive[:3],
                'balanced': balanced[:3],
                'conservative': conservative[:3]
            },
            'best_overall': spreads[:5]
        }
    
    def select_best_spread_by_strategy(self, analysis: Dict, strategy: str) -> Optional[Dict]:
        """Select the best spread for a given strategy"""
        strategies = analysis.get('strategies', {})
        strategy_spreads = strategies.get(strategy, [])
        
        if strategy_spreads:
            return strategy_spreads[0]
        
        # Fallback to best overall
        best_overall = analysis.get('best_overall', [])
        if best_overall:
            return best_overall[0]
        
        return None
    
    def format_spread_data(self, ticker: str, spread: Dict, strategy: str) -> Dict:
        """Format spread data for the API payload in exact expected structure"""
        # Map strategy names to match expected format
        strategy_mapping = {
            'aggressive': 'aggressive',
            'balanced': 'steady',
            'conservative': 'conservative'
        }
        
        return {
            "symbol": ticker,
            "strategy_type": strategy_mapping.get(strategy, strategy),
            "spread_data": {
                "long_strike": spread.get('long_strike'),
                "short_strike": spread.get('short_strike'),
                "long_option_symbol": spread.get('long_option_symbol'),
                "short_option_symbol": spread.get('short_option_symbol'),
                "cost": spread.get('spread_cost'),
                "max_profit": spread.get('max_profit'),
                "roi": spread.get('roi_percent'),
                "expiration_date": spread.get('expiration_date'),
                "dte": spread.get('days_to_expiration'),
                "long_price": spread.get('long_price'),
                "short_price": spread.get('short_price'),
                "current_stock_price": spread.get('current_stock_price'),
                "breakeven": spread.get('breakeven'),
                "profit_scenarios": spread.get('profit_scenarios', []),
                "trade_construction": spread.get('trade_construction', {})
            }
        }
    
    def send_spread_results(self, payload: Dict) -> bool:
        """Send spread analysis results to the endpoint"""
        try:
            logger.info(f"Sending spread data for {payload['symbol']} ({payload['strategy_type']})")
            
            response = requests.post(
                self.spreads_endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully sent {payload['symbol']} spread data")
                return True
            else:
                logger.error(f"Failed to send spread data: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending spread data: {e}")
            return False
    
    def process_pipeline(self):
        """Main pipeline process"""
        logger.info("Starting robust spread analysis pipeline")
        
        # Fetch top tickers
        ticker_data = self.fetch_top_tickers()
        if not ticker_data:
            logger.error("Failed to fetch top tickers")
            return
        
        tickers = ticker_data.get('tickers', [])
        if not tickers:
            logger.error("No tickers received")
            return
        
        logger.info(f"Processing {len(tickers)} tickers: {tickers}")
        
        # Process each ticker
        for ticker in tickers:
            logger.info(f"Processing ticker: {ticker}")
            
            # Analyze spreads
            analysis = self.analyze_ticker_spreads(ticker)
            
            if 'error' in analysis:
                logger.error(f"Skipping {ticker}: {analysis['error']}")
                continue
            
            # Send results for each strategy
            strategies = ['aggressive', 'balanced', 'conservative']
            
            for strategy in strategies:
                best_spread = self.select_best_spread_by_strategy(analysis, strategy)
                
                if best_spread:
                    payload = self.format_spread_data(ticker, best_spread, strategy)
                    success = self.send_spread_results(payload)
                    
                    if success:
                        logger.info(f"✓ Sent {ticker} {strategy}: ROI {best_spread.get('roi_percent', 0):.1f}%")
                    else:
                        logger.error(f"✗ Failed to send {ticker} {strategy}")
                else:
                    logger.warning(f"No {strategy} spread found for {ticker}")
                
                time.sleep(1)  # Rate limiting
            
            logger.info(f"Completed {ticker}")
            time.sleep(2)  # Delay between tickers
        
        logger.info("Pipeline completed")

def main():
    """Main entry point"""
    pipeline = RobustSpreadPipeline()
    pipeline.process_pipeline()

if __name__ == '__main__':
    main()