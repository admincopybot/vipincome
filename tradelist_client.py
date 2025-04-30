import os
import json
import logging
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TradeListApiService:
    """Service to fetch ETF data from TheTradeList API with yfinance fallback"""
    
    # API Constants
    # API endpoints based on official documentation
    TRADELIST_API_BASE_URL = "https://api.thetradelist.com/v1/data"
    TRADELIST_SCANNER_ENDPOINT = "/get_trader_scanner_data.php"
    TRADELIST_HIGHS_LOWS_ENDPOINT = "/get_highs_lows.php"
    TRADELIST_OPTIONS_SPREADS_ENDPOINT = "/options-spreads"
    
    # API Documentation reference
    API_DOCUMENTATION = """
    Trader Scanner Data Endpoint:
    GET https://api.thetradelist.com/v1/data/get_trader_scanner_data.php
    
    Parameters:
    - totalpoints (optional, default: 0): Minimum total points threshold
    - marketcap (optional, default: 0): Minimum market capitalization
    - stockvol (optional, default: 0): Minimum stock volume
    - optionvol (optional, default: 0): Minimum options volume
    - returntype (optional, default: 'csv'): 'csv' or 'json'
    - apiKey (required): Your API key
    
    Highs and Lows Endpoint:
    GET https://api.thetradelist.com/v1/data/get_highs_lows.php
    
    Parameters:
    - price (optional, default: 0): Minimum stock price 
    - volume (optional, default: 0): Minimum trading volume
    - extreme (optional): Filter for 'high' or 'low' only
    - returntype (optional, default: 'csv'): 'csv' or 'json'
    - apiKey (required): Your API key
    
    Options Spreads Endpoint:
    GET https://api.thetradelist.com/v1/data/options-spreads
    
    Parameters:
    - symbol (required): ETF symbol (e.g., 'XLK', 'XLF')
    - strategy (required): Trading strategy ('Aggressive', 'Steady', 'Passive')
    - apiKey (required): Your API key
    """
    
    # List of ETFs that are supported by TheTradeList API
    # (ensures we don't make API calls for symbols that the API doesn't support)
    TRADELIST_SUPPORTED_ETFS = ["XLK", "XLF", "XLV", "XLI", "XLP", "XLY", "XLE", "XLB", "XLU", "XLRE", "XLC", "SPY"]
    
    # Controls whether to use the API; set to false to disable completely (for troubleshooting)
    USE_TRADELIST_API = os.environ.get("USE_TRADELIST_API", "true").lower() == "true"
    
    @staticmethod
    def _get_api_key():
        """Get the API key from environment variables with fallback mechanism"""
        api_key = os.environ.get("TRADELIST_API_KEY") or os.environ.get("POLYGON_API_KEY")
        if not api_key:
            logger.error("No API key found in environment variables (TRADELIST_API_KEY or POLYGON_API_KEY)")
        return api_key
    
    @staticmethod
    def get_current_price(ticker):
        """Get the current price and change data for a ticker using TheTradeList API only (no fallback)"""
        try:
            # Check if API is enabled
            if not TradeListApiService.USE_TRADELIST_API:
                logger.error(f"TheTradeList API is disabled. Set USE_TRADELIST_API=true to enable.")
                return None
            
            # Check if ticker is supported
            if ticker not in TradeListApiService.TRADELIST_SUPPORTED_ETFS:
                logger.error(f"Symbol {ticker} is not supported by TheTradeList API")
                return None
            
            # Get API key
            api_key = TradeListApiService._get_api_key()
            if not api_key:
                return None
                
            # Make API call to trader scanner endpoint which contains current price and change data
            data = TradeListApiService.get_tradelist_data(ticker, return_type="json")
            
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.error(f"No data returned from TheTradeList API for {ticker}")
                return TradeListApiService._create_error_response(ticker, "No data returned")
            
            # Find the ticker in the results
            ticker_data = None
            for item in data:
                if item.get('symbol') == ticker:
                    ticker_data = item
                    break
            
            if not ticker_data:
                logger.error(f"Ticker {ticker} not found in API response")
                return TradeListApiService._create_error_response(ticker, "Symbol not found in response")
            
            # Extract price and change data
            price = float(ticker_data.get('lastprice', 0))
            change = float(ticker_data.get('percentchange', 0))
            volume = int(ticker_data.get('volume', 0))
            total_points = int(ticker_data.get('totalpoints', 0))
            
            return {
                'symbol': ticker,
                'price': price,
                'change': change,
                'volume': volume,
                'total_points': total_points,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'TheTradeList'
            }
        except Exception as e:
            logger.error(f"Error getting current price for {ticker}: {str(e)}")
            # Try to get price from yfinance as fallback
            return TradeListApiService._get_price_from_yfinance(ticker)
    
    @staticmethod
    def _create_error_response(ticker, error_message):
        """Create an error response object for when API fails"""
        return {
            'symbol': ticker,
            'price': 0,
            'change': 0,
            'volume': 0,
            'total_points': 0,
            'error': error_message,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'Error'
        }
    
    @staticmethod
    def _get_price_from_yfinance(ticker):
        """Get price data using yfinance as fallback"""
        try:
            logger.info(f"Falling back to yfinance for {ticker} price data")
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(period="1d")
            
            if data.empty:
                return TradeListApiService._create_error_response(ticker, "No data from yfinance")
            
            latest = data.iloc[-1]
            price = float(latest['Close'])
            
            # Calculate change if possible
            change = 0
            if len(data) > 1:
                prev_close = float(data.iloc[-2]['Close'])
                if prev_close > 0:
                    change = (price - prev_close) / prev_close * 100
            
            return {
                'symbol': ticker,
                'price': price,
                'change': change,
                'volume': int(latest.get('Volume', 0)),
                'total_points': 0,  # We don't have this from yfinance
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'yfinance'
            }
        except Exception as e:
            logger.error(f"Error in yfinance fallback for {ticker}: {str(e)}")
            return TradeListApiService._create_error_response(ticker, f"Fallback failed: {str(e)}")
    
    @staticmethod
    def get_tradelist_data(ticker, return_type="json", min_stock_vol=0, min_option_vol=0, min_market_cap=0, min_total_points=0):
        """
        Get data from TheTradeList API using the Trader Scanner Data Endpoint
        
        Parameters:
        - ticker: The stock symbol to filter by (not in the official params but we'll filter results)
        - return_type: 'json' or 'csv'
        - min_stock_vol: Minimum stock volume filter
        - min_option_vol: Minimum options volume filter
        - min_market_cap: Minimum market capitalization filter
        - min_total_points: Minimum total points threshold
        
        Returns list of ticker data or None if error
        """
        try:
            # Check if API is enabled
            if not TradeListApiService.USE_TRADELIST_API:
                logger.error(f"TheTradeList API is disabled. Set USE_TRADELIST_API=true to enable.")
                return None
            
            # Get API key
            api_key = TradeListApiService._get_api_key()
            if not api_key:
                return None
                
            # Construct API URL
            url = f"{TradeListApiService.TRADELIST_API_BASE_URL}{TradeListApiService.TRADELIST_SCANNER_ENDPOINT}"
            
            # Build query parameters according to the API documentation
            params = {
                "returntype": return_type,
                "apiKey": api_key,
                "stockvol": min_stock_vol,
                "optionvol": min_option_vol,
                "marketcap": min_market_cap,
                "totalpoints": min_total_points
            }
            
            logger.info(f"Making request to TheTradeList API for {ticker} with params: {params}")
            
            # Make API request with redirect following disabled (to see actual redirect)
            response = requests.get(url, params=params, timeout=15, allow_redirects=False)
            
            # Check if we got a redirect and handle it explicitly
            if response.status_code == 302:
                redirect_url = response.headers.get('Location')
                logger.warning(f"API returned redirect to: {redirect_url}")
                
                # Parse the redirect URL properly (with null checks)
                if redirect_url is None:
                    logger.error("Received a 302 redirect but no Location header was provided")
                    full_redirect_url = "https://api.thetradelist.com"
                elif redirect_url.startswith('http'):
                    full_redirect_url = redirect_url
                else:
                    # Assume relative URL
                    base_url = "https://api.thetradelist.com"
                    full_redirect_url = f"{base_url}{redirect_url}"
                
                # Follow the redirect manually
                logger.info(f"Following redirect to: {full_redirect_url}")
                response = requests.get(full_redirect_url, timeout=15)
            
            # Now handle the actual response (either direct or after redirect)
            if response.status_code != 200:
                logger.error(f"Error from TheTradeList API: {response.status_code} - {response.text}")
                return None
            
            # Parse the response based on return_type
            if return_type.lower() == 'json':
                # Handle JSON response
                try:
                    if not response.text.strip():
                        logger.error("Empty response received from API")
                        return None
                    
                    data = response.json()
                    logger.debug(f"Received JSON data: {data}")
                    
                    # Filter by ticker if provided
                    if ticker and ticker != "":
                        if isinstance(data, list):
                            # Filter the list to keep only the ticker we want
                            filtered_data = [item for item in data if item.get('symbol') == ticker]
                            return filtered_data
                    
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON response: {str(e)}")
                    logger.error(f"Response text: {response.text[:1000]}")  # Log first 1000 chars only
                    return None
            else:
                # Handle CSV response (just return as text)
                data = response.text
                
                # Filter by ticker if needed (would need CSV parsing)
                # For now, just return the raw CSV
                return data
                
        except Exception as e:
            logger.error(f"Error fetching data from TheTradeList: {str(e)}")
            return None
    
    @staticmethod
    def get_historical_data(symbol, timespan="day", period="2y"):
        """
        Get historical price data for technical analysis using yfinance
        This is a fallback for when we don't have historical data in TheTradeList API
        
        Parameters:
        - symbol: Ticker symbol
        - timespan: "day" (daily data), "hour" (hourly data), etc.
        - period: Time period to fetch (e.g., "2y" for 2 years)
        
        Returns:
        - pandas DataFrame with OHLCV data
        """
        try:
            # Use yfinance to fetch historical data
            logger.info(f"Fetching {timespan} historical data for {symbol} using yfinance")
            ticker = yf.Ticker(symbol)
            
            # Map timespan to interval
            interval_map = {
                "minute": "1m",
                "hour": "1h",
                "day": "1d",
                "week": "1wk",
                "month": "1mo"
            }
            interval = interval_map.get(timespan, "1d")
            
            # Fetch the data
            df = ticker.history(period=period, interval=interval)
            
            # Basic sanity check
            if df.empty:
                logger.warning(f"No historical data found for {symbol}")
                return None
                
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    @staticmethod
    def get_options_spreads(symbol, strategy):
        """
        Get options spread data for a specific ETF and strategy
        
        Parameters:
        - symbol: ETF symbol (e.g., 'XLK', 'XLF')
        - strategy: Trading strategy ('Aggressive', 'Steady', 'Passive')
        
        Returns:
        - dict: Options spread data including current price, expiration dates, and spreads
        """
        try:
            # Check if API is enabled
            if not TradeListApiService.USE_TRADELIST_API:
                logger.error(f"TheTradeList API is disabled. Set USE_TRADELIST_API=true to enable.")
                return None
            
            # Check if ticker is supported
            if symbol not in TradeListApiService.TRADELIST_SUPPORTED_ETFS:
                logger.error(f"Symbol {symbol} is not supported by TheTradeList API")
                return None
            
            # Get API key
            api_key = TradeListApiService._get_api_key()
            if not api_key:
                return None
                
            # Construct API URL
            url = f"{TradeListApiService.TRADELIST_API_BASE_URL}{TradeListApiService.TRADELIST_OPTIONS_SPREADS_ENDPOINT}"
            
            # Validate strategy parameter
            if strategy not in ["Aggressive", "Steady", "Passive"]:
                logger.error(f"Invalid strategy: {strategy}. Must be 'Aggressive', 'Steady', or 'Passive'")
                return None
            
            # Build query parameters
            params = {
                "symbol": symbol,
                "strategy": strategy,
                "apiKey": api_key
            }
            
            logger.info(f"Making request to TheTradeList Options Spreads API for {symbol} with strategy {strategy}")
            
            # Make API request
            response = requests.get(url, params=params, timeout=15)
            
            # Log the response for debugging
            logger.debug(f"TheTradeList Options API response status: {response.status_code}")
            
            # Check for successful response and parse
            if response.status_code == 200:
                try:
                    if not response.text.strip():
                        logger.error("Empty response received from Options Spreads API")
                        return None
                    
                    # Parse JSON response
                    data = response.json()
                    logger.info(f"Received options spreads data type: {type(data)}")
                    
                    # Basic validation of the response structure
                    if isinstance(data, list):
                        logger.info(f"Received options spreads data as list with {len(data)} items")
                        # The response format appears to be a list, let's convert it to a dictionary
                        return {
                            "raw_data": data,
                            "symbol": symbol,
                            "strategy": strategy,
                            "options_count": len(data),
                            "source": "TheTradeList API"
                        }
                    elif not isinstance(data, dict):
                        logger.error(f"Invalid response format from Options Spreads API: {type(data)}")
                        return None
                    
                    # Return the options spread data
                    return data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON response from Options Spreads API: {str(e)}")
                    logger.error(f"Response text: {response.text[:1000]}")  # Log first 1000 chars only
                    return None
            else:
                logger.error(f"Error from TheTradeList Options Spreads API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching options spread data for {symbol}: {str(e)}")
            return None
    
    @staticmethod
    def api_health_check():
        """Check if TheTradeList API is available and API key is valid"""
        try:
            # Check if API is enabled in configuration
            if not TradeListApiService.USE_TRADELIST_API:
                return {
                    "status": "disabled",
                    "message": "TheTradeList API is explicitly disabled by configuration",
                    "feature_enabled": False
                }
                
            # Check if API key exists
            api_key = TradeListApiService._get_api_key()
            if not api_key:
                return {
                    "status": "error",
                    "message": "No API key found in environment variables (TRADELIST_API_KEY or POLYGON_API_KEY)",
                    "feature_enabled": TradeListApiService.USE_TRADELIST_API
                }
            
            # Test API with a basic connection check
            url = f"{TradeListApiService.TRADELIST_API_BASE_URL}{TradeListApiService.TRADELIST_SCANNER_ENDPOINT}"
            params = {
                "returntype": "json",
                "apiKey": api_key,
                "stockvol": 0,
                "totalpoints": 0
            }
            
            # Make a test API request with no redirects
            response = requests.get(url, params=params, timeout=15, allow_redirects=False)
            
            # Handle redirects for health check similar to main API calls
            if response.status_code == 302:
                redirect_url = response.headers.get('Location')
                logger.info(f"Health check: API returned redirect to: {redirect_url}")
                
                # Parse the redirect URL properly (with null checks)
                if redirect_url is None:
                    logger.error("Health check: Received a 302 redirect but no Location header was provided")
                    full_redirect_url = "https://api.thetradelist.com"
                elif redirect_url.startswith('http'):
                    full_redirect_url = redirect_url
                else:
                    # Assume relative URL
                    base_url = "https://api.thetradelist.com"
                    full_redirect_url = f"{base_url}{redirect_url}"
                
                # Follow the redirect manually
                logger.info(f"Health check: Following redirect to: {full_redirect_url}")
                response = requests.get(full_redirect_url, timeout=15)
            
            # Now handle the actual response (either direct or after redirect)
            if response.status_code == 200:
                try:
                    # Try to parse JSON to ensure it's a valid response
                    if not response.text.strip():
                        return {
                            "status": "error",
                            "message": "API returned empty response on health check",
                            "feature_enabled": True
                        }
                    
                    # Parse JSON
                    data = response.json()
                    
                    # Additional validation of the response structure
                    if isinstance(data, list) and len(data) > 0:
                        # API is healthy
                        return {
                            "status": "ok",
                            "message": "TheTradeList API is available and working correctly",
                            "data_count": len(data),
                            "feature_enabled": True
                        }
                    else:
                        # API returns valid JSON but in wrong format
                        return {
                            "status": "warning",
                            "message": "API connection successful but returned unexpected data structure",
                            "data": data,
                            "feature_enabled": True
                        }
                    
                except json.JSONDecodeError as e:
                    # API returns non-JSON response
                    return {
                        "status": "error",
                        "message": f"API returned invalid JSON response: {str(e)}",
                        "response_preview": response.text[:200] + "...",  # First 200 chars only
                        "feature_enabled": True
                    }
            else:
                # API returns error status code
                return {
                    "status": "error",
                    "message": f"API returned error status code: {response.status_code}",
                    "response_preview": response.text[:200] + "...",  # First 200 chars only
                    "feature_enabled": True
                }
                
        except requests.exceptions.RequestException as e:
            # Network/connection error
            return {
                "status": "error",
                "message": f"Network error connecting to API: {str(e)}",
                "feature_enabled": TradeListApiService.USE_TRADELIST_API
            }
        except Exception as e:
            # Any other error
            return {
                "status": "error",
                "message": f"Unexpected error in API health check: {str(e)}",
                "feature_enabled": TradeListApiService.USE_TRADELIST_API
            }