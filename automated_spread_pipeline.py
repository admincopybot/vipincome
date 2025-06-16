"""
Automated Debit Spread Analysis Pipeline
Fetches top tickers from API, analyzes spreads, and sends results back
"""
import os
import logging
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from spread_api_server import SpreadAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpreadPipeline:
    def __init__(self):
        self.analyzer = SpreadAnalyzer()
        self.tickers_endpoint = "https://001e4434-2e2e-4e25-b65b-8b894c786e9d-00-26sv8d7lbk7i3.worf.replit.dev/api/top-tickers"
        self.spreads_endpoint = "https://001e4434-2e2e-4e25-b65b-8b894c786e9d-00-26sv8d7lbk7i3.worf.replit.dev/api/spreads-update"
        
    def fetch_top_tickers(self) -> Optional[Dict]:
        """Fetch top 3 tickers from the API"""
        try:
            logger.info(f"Fetching top tickers from {self.tickers_endpoint}")
            response = requests.get(self.tickers_endpoint, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                tickers = data.get('tickers', [])
                logger.info(f"Received {len(tickers)} tickers: {tickers}")
                return data
            else:
                logger.error(f"Failed to fetch tickers: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return None
    
    def analyze_ticker_spreads(self, ticker: str) -> Dict:
        """Analyze debit spreads for a single ticker"""
        logger.info(f"Analyzing spreads for {ticker}")
        
        try:
            # Get current stock price
            current_price = self.analyzer.get_stock_price(ticker)
            if not current_price:
                logger.error(f"Failed to get price for {ticker}")
                return {'error': f'Unable to fetch price for {ticker}'}
            
            logger.info(f"{ticker} current price: ${current_price:.2f}")
            
            # Get options chain
            options_chain = self.analyzer.get_options_chain(ticker)
            if not options_chain:
                logger.error(f"Failed to get options chain for {ticker}")
                return {'error': f'Unable to fetch options for {ticker}'}
            
            logger.info(f"Retrieved {len(options_chain)} options for {ticker}")
            
            # Analyze spreads
            analysis = self.analyzer.analyze_spread(ticker, current_price, options_chain)
            
            if 'error' in analysis:
                logger.error(f"Analysis failed for {ticker}: {analysis['error']}")
                return analysis
            
            logger.info(f"Found {analysis.get('total_spreads_found', 0)} spreads for {ticker}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return {'error': str(e)}
    
    def select_best_spread_by_strategy(self, analysis: Dict, strategy: str) -> Optional[Dict]:
        """Select the best spread for a given strategy"""
        strategies = analysis.get('strategies', {})
        strategy_spreads = strategies.get(strategy, [])
        
        if strategy_spreads:
            return strategy_spreads[0]  # First one is best (sorted by ROI)
        
        # Fallback to best overall if strategy not available
        best_overall = analysis.get('best_overall', [])
        if best_overall:
            return best_overall[0]
        
        return None
    
    def format_spread_data(self, ticker: str, spread: Dict, strategy: str) -> Dict:
        """Format spread data for the API payload"""
        return {
            "symbol": ticker,
            "strategy_type": strategy,
            "spread_data": {
                "long_strike": spread.get('long_strike'),
                "short_strike": spread.get('short_strike'),
                "long_price": spread.get('long_price'),
                "short_price": spread.get('short_price'),
                "cost": spread.get('spread_cost'),
                "max_profit": spread.get('max_profit'),
                "max_loss": spread.get('max_loss'),
                "roi": spread.get('roi_percent'),
                "breakeven": spread.get('breakeven'),
                "expiration_date": spread.get('expiration_date'),
                "dte": spread.get('days_to_expiration'),
                "distance_otm_percent": spread.get('distance_otm_percent'),
                "price_scenarios": spread.get('price_scenarios', []),
                "analysis_timestamp": datetime.now().isoformat()
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
        logger.info("Starting automated spread analysis pipeline")
        
        # Fetch top tickers
        ticker_data = self.fetch_top_tickers()
        if not ticker_data:
            logger.error("Failed to fetch top tickers, aborting pipeline")
            return
        
        tickers = ticker_data.get('tickers', [])
        if not tickers:
            logger.error("No tickers received, aborting pipeline")
            return
        
        logger.info(f"Processing {len(tickers)} tickers: {tickers}")
        
        # Process each ticker
        for ticker in tickers:
            logger.info(f"Processing ticker: {ticker}")
            
            # Analyze spreads for this ticker
            analysis = self.analyze_ticker_spreads(ticker)
            
            if 'error' in analysis:
                logger.error(f"Skipping {ticker} due to analysis error: {analysis['error']}")
                continue
            
            # Try each strategy and send the best spread for each
            strategies = ['aggressive', 'balanced', 'conservative']
            
            for strategy in strategies:
                best_spread = self.select_best_spread_by_strategy(analysis, strategy)
                
                if best_spread:
                    # Format and send the data
                    payload = self.format_spread_data(ticker, best_spread, strategy)
                    success = self.send_spread_results(payload)
                    
                    if success:
                        logger.info(f"✓ Sent {ticker} {strategy} spread: ROI {best_spread.get('roi_percent', 0):.1f}%")
                    else:
                        logger.error(f"✗ Failed to send {ticker} {strategy} spread")
                else:
                    logger.warning(f"No {strategy} spread found for {ticker}")
                
                # Small delay between requests to be respectful
                time.sleep(1)
            
            logger.info(f"Completed processing {ticker}")
            
            # Delay between tickers
            time.sleep(2)
        
        logger.info("Pipeline processing completed")
    
    def run_continuous(self, interval_minutes: int = 15):
        """Run the pipeline continuously at specified intervals"""
        logger.info(f"Starting continuous pipeline with {interval_minutes} minute intervals")
        
        while True:
            try:
                self.process_pipeline()
                logger.info(f"Pipeline completed, waiting {interval_minutes} minutes for next run...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Pipeline stopped by user")
                break
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                logger.info("Waiting 5 minutes before retry...")
                time.sleep(300)  # Wait 5 minutes before retry

def main():
    """Main entry point"""
    pipeline = SpreadPipeline()
    
    # Run once for testing
    logger.info("Running pipeline once for testing...")
    pipeline.process_pipeline()
    
    # Ask user if they want continuous mode
    print("\nPipeline test completed. Would you like to run continuously? (y/n)")
    choice = input().lower().strip()
    
    if choice == 'y':
        try:
            interval = int(input("Enter interval in minutes (default 15): ") or "15")
            pipeline.run_continuous(interval)
        except ValueError:
            pipeline.run_continuous(15)
    else:
        logger.info("Pipeline finished")

if __name__ == '__main__':
    main()