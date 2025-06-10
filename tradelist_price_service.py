"""
TheTradeList Price Service - Centralized pricing using TheTradeList API
Replaces all Polygon pricing calls with TheTradeList for consistency
"""

import os
import requests
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class TradeListPriceService:
    """Centralized service for fetching current prices using TheTradeList API"""
    
    @staticmethod
    def get_current_price(symbol: str) -> Optional[float]:
        """
        Get current stock price using TheTradeList API
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price as float or None if failed
        """
        try:
            api_key = os.environ.get('TRADELIST_API_KEY')
            if not api_key:
                logger.error("TheTradeList API key not found")
                return None
            
            # Use TheTradeList snapshot endpoint
            url = "https://api.thetradelist.com/v1/data/snapshot-locale"
            params = {
                'tickers': f"{symbol},",  # API requires comma after symbol
                'apiKey': api_key
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
                            logger.info(f"TheTradeList price for {symbol}: ${fmv}")
                            return float(fmv)
                            
            logger.warning(f"Failed to get price for {symbol} from TheTradeList")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    @staticmethod
    def get_price_data(symbol: str) -> Optional[Dict]:
        """
        Get comprehensive price data using TheTradeList API
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with price, change, volume data or None if failed
        """
        try:
            api_key = os.environ.get('TRADELIST_API_KEY')
            if not api_key:
                logger.error("TheTradeList API key not found")
                return None
            
            # Use trader scanner endpoint for more comprehensive data
            url = "https://api.thetradelist.com/v1/data/get_trader_scanner_data.php"
            params = {
                'apiKey': api_key,
                'returntype': 'json'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Find the specific ticker in the response
                ticker_data = None
                if isinstance(data, list):
                    for item in data:
                        if item.get('symbol') == symbol:
                            ticker_data = item
                            break
                elif isinstance(data, dict) and symbol in data:
                    ticker_data = data[symbol]
                
                if ticker_data:
                    return {
                        'symbol': symbol,
                        'price': float(ticker_data.get('lastprice', 0)),
                        'change': float(ticker_data.get('percentchange', 0)),
                        'volume': int(ticker_data.get('volume', 0)),
                        'source': 'TheTradeList'
                    }
                    
            logger.warning(f"No data found for {symbol} in TheTradeList response")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching comprehensive data for {symbol}: {e}")
            return None