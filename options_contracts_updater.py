#!/usr/bin/env python3
"""
Options Contracts Updater
Fetches real options contracts from TheTradeList API for top tickers
and updates database with authentic contract counts (10-50 DTE)
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from database_models import ETFDatabase
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class OptionsContractsUpdater:
    def __init__(self):
        self.api_key = os.environ.get('TRADELIST_API_KEY')
        if not self.api_key:
            raise ValueError("TRADELIST_API_KEY environment variable not set")
        
        self.base_url = "https://api.thetradelist.com/v1"
        self.db = ETFDatabase()
        
    def get_top_tickers(self, limit: int = 10) -> List[Dict]:
        """Get top tickers ranked by score + trading volume"""
        all_etfs = self.db.get_all_etfs()
        
        # Sort by Score → Volume → Symbol for top rankings
        sorted_etfs = sorted(
            all_etfs.items(),
            key=lambda x: (
                -x[1]['total_score'],  # Highest score first
                -x[1].get('avg_volume_10d', 0),  # Highest volume first
                x[0]  # Alphabetical order for symbol
            )
        )
        
        return [{'symbol': symbol, 'data': data} for symbol, data in sorted_etfs[:limit]]
    
    def fetch_options_contracts(self, symbol: str) -> int:
        """
        Fetch options contracts from TheTradeList API for a symbol
        Returns count of current call options contracts
        """
        try:
            logger.info(f"🔍 Fetching options contracts for {symbol}")
            
            # TheTradeList trader scanner endpoint (correct format from documentation)
            url = f"{self.base_url}/data/get_trader_scanner_data.php"
            
            params = {
                'apiKey': self.api_key,
                'returntype': 'json',
                'totalpoints': 0,  # Get all results
                'marketcap': 0,
                'stockvol': 0,
                'optionvol': 0
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"❌ API error for {symbol}: Status {response.status_code}")
                return 0
                
            data = response.json()
            
            # Find the specific symbol in the results
            if not isinstance(data, list):
                logger.warning(f"❌ Unexpected data format for {symbol}")
                return 0
            
            # Search for our symbol in the results
            for item in data:
                if item.get('symbol') == symbol:
                    # Get current number of call options (this is the actual contracts count)
                    contracts_count = item.get('current_number_of_call_options', 0)
                    
                    # Convert to integer if it's a string
                    if isinstance(contracts_count, str):
                        try:
                            contracts_count = int(float(contracts_count))
                        except ValueError:
                            contracts_count = 0
                    
                    logger.info(f"✅ {symbol}: Found {contracts_count} call options contracts")
                    return contracts_count
            
            # Symbol not found in scanner results
            logger.warning(f"❌ {symbol} not found in trader scanner results")
            return 0
            
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout fetching options for {symbol}")
            return 0
        except Exception as e:
            logger.error(f"❌ Error fetching options for {symbol}: {str(e)}")
            return 0
    
    def update_options_contracts(self) -> Dict:
        """
        Main function: Update options contracts for top 10 tickers
        Returns summary of updates
        """
        logger.info("🚀 Starting options contracts update for top 10 tickers")
        
        # Get top 10 tickers
        top_tickers = self.get_top_tickers(10)
        
        if not top_tickers:
            return {'success': False, 'error': 'No tickers found'}
        
        updated_contracts = {}
        successful_updates = 0
        
        for ticker_info in top_tickers:
            symbol = ticker_info['symbol']
            
            try:
                # Fetch authentic options contracts count
                contracts_count = self.fetch_options_contracts(symbol)
                updated_contracts[symbol] = contracts_count
                
                # Update database with new contracts count
                self.db.update_options_contracts(symbol, contracts_count)
                successful_updates += 1
                
                logger.info(f"📊 Updated {symbol}: {contracts_count} contracts")
                
            except Exception as e:
                logger.error(f"❌ Failed to update {symbol}: {str(e)}")
                updated_contracts[symbol] = 0
        
        logger.info(f"✅ Options contracts update complete: {successful_updates}/{len(top_tickers)} successful")
        
        return {
            'success': True,
            'updated_count': successful_updates,
            'total_tickers': len(top_tickers),
            'contracts': updated_contracts,
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Standalone execution for testing"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        updater = OptionsContractsUpdater()
        result = updater.update_options_contracts()
        
        if result['success']:
            print(f"✅ Successfully updated {result['updated_count']} tickers")
            for symbol, count in result['contracts'].items():
                print(f"  {symbol}: {count} contracts")
        else:
            print(f"❌ Update failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")

if __name__ == "__main__":
    main()