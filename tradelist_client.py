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
    """
    TRADELIST_SUPPORTED_ETFS = ["XLK", "XLF", "XLV", "XLI", "XLP", "XLY", "XLE", "XLB", "XLU", "XLRE", "XLC", "SPY"]
    
    # Feature flag to control API usage
    USE_TRADELIST_API = os.environ.get("USE_TRADELIST_API", "true").lower() == "true"
    
    @staticmethod
    def get_current_price(ticker):
        """Get the current price and change data for a ticker using TheTradeList API only (no fallback)"""
        try:
            # Check if API is enabled
            if not TradeListApiService.USE_TRADELIST_API:
                logger.error(f"TheTradeList API is disabled. Set USE_TRADELIST_API=true to enable.")
                return TradeListApiService._create_error_response(ticker, "API disabled")
            
            # Check if ticker is supported
            if ticker not in TradeListApiService.TRADELIST_SUPPORTED_ETFS:
                logger.error(f"Ticker {ticker} is not supported by TheTradeList API")
                return TradeListApiService._create_error_response(ticker, "Unsupported ticker")
            
            # Get data from TheTradeList API
            tradelist_data = TradeListApiService.get_tradelist_data(ticker)
            
            # Extract data from the response
            if tradelist_data and len(tradelist_data) > 0:
                etf_data = tradelist_data[0]
                current_price = float(etf_data.get("current_stock_price", 0))
                prev_close = float(etf_data.get("prev_week_stock_close_price", 0))
                
                # Calculate change values
                price_change = current_price - prev_close
                percent_change = (price_change / prev_close * 100) if prev_close > 0 else 0
                
                logger.info(f"Retrieved {ticker} price from TheTradeList API: ${current_price:.2f}")
                
                # Create response object matching the current structure
                return {
                    "ticker": ticker,
                    "price": current_price,
                    "change": price_change,
                    "change_percent": percent_change,
                    "volume": etf_data.get("stock_volume_by_day", 0),
                    "last_updated": etf_data.get("price_update_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "data_source": "TheTradeList API"
                }
            else:
                logger.error(f"No data returned from TheTradeList API for {ticker}")
                return TradeListApiService._create_error_response(ticker, "No data returned from API")
        
        except Exception as e:
            logger.error(f"Error getting price data for {ticker} from TheTradeList API: {str(e)}")
            return TradeListApiService._create_error_response(ticker, f"API Error: {str(e)}")
    
    @staticmethod
    def _create_error_response(ticker, error_message):
        """Create an error response object for when API fails"""
        logger.error(f"TradeList API Error for {ticker}: {error_message}")
        return {
            "ticker": ticker,
            "price": 0,
            "change": 0,
            "change_percent": 0,
            "volume": 0,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": f"TheTradeList API Error: {error_message}",
            "error": True,
            "error_message": error_message
        }
    
    @staticmethod
    def _get_price_from_yfinance(ticker):
        """Get price data using yfinance as fallback"""
        try:
            ticker_data = yf.Ticker(ticker)
            hist = ticker_data.history(period="2d")
            
            if hist.empty:
                logger.warning(f"No history data from yfinance for {ticker}")
                return {
                    "ticker": ticker,
                    "price": 0,
                    "change": 0,
                    "change_percent": 0,
                    "volume": 0,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "data_source": "yfinance (Error)"
                }
            
            # Calculate current price and changes
            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            
            price_change = current_price - prev_close
            percent_change = (price_change / prev_close * 100) if prev_close > 0 else 0
            volume = int(hist['Volume'].iloc[-1])
            
            logger.info(f"Retrieved {ticker} price from yfinance: ${current_price:.2f}")
            
            return {
                "ticker": ticker,
                "price": current_price,
                "change": price_change,
                "change_percent": percent_change,
                "volume": volume,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_source": "yfinance"
            }
        
        except Exception as e:
            logger.error(f"YFinance error for {ticker}: {str(e)}")
            return {
                "ticker": ticker,
                "price": 0,
                "change": 0,
                "change_percent": 0,
                "volume": 0,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_source": "Error"
            }
    
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
            # Ensure API key is available
            api_key = os.environ.get("TRADELIST_API_KEY")
            if not api_key:
                logger.error("TheTradeList API key not found in environment variables")
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
                
                # Follow the redirect manually with the API key in headers
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'User-Agent': 'IncomeMachineMVP/1.0'
                }
                response = requests.get(f"{TradeListApiService.TRADELIST_API_BASE_URL}/{redirect_url}", 
                                       headers=headers, timeout=15)
            
            # Log the response for debugging
            logger.debug(f"TheTradeList API response status: {response.status_code}")
            logger.debug(f"TheTradeList API response headers: {response.headers}")
            logger.debug(f"TheTradeList API response content preview: {response.text[:200]}...")
            
            # Check for successful response and parse accordingly
            if response.status_code == 200:
                # Handle different return types
                if return_type.lower() == "json":
                    try:
                        # Check if response text starts with JSON markers
                        if response.text.strip().startswith(('[', '{')):
                            data = response.json()
                            
                            # Filter to only get the requested ticker
                            if isinstance(data, list):
                                ticker_data = [item for item in data if item.get("symbol") == ticker]
                                logger.info(f"Found {len(ticker_data)} records for {ticker} in API response")
                                return ticker_data
                            elif isinstance(data, dict) and data.get("symbol") == ticker:
                                logger.info(f"Found single record for {ticker} in API response")
                                return [data]  # Return as list for consistency
                            else:
                                logger.warning(f"No data found for {ticker} in API response")
                                return []
                        else:
                            logger.warning(f"Response doesn't appear to be valid JSON: {response.text[:50]}...")
                    except Exception as json_error:
                        logger.error(f"Failed to parse JSON: {str(json_error)}")
                elif return_type.lower() == "csv":
                    try:
                        # Parse CSV data
                        csv_data = response.text.strip().split('\n')
                        if len(csv_data) >= 2:  # Header row + at least one data row
                            headers = csv_data[0].split(',')
                            
                            # Find all rows for the requested ticker
                            ticker_rows = []
                            for row in csv_data[1:]:
                                values = row.split(',')
                                if values and values[0] == ticker:
                                    # Convert to dictionary
                                    row_dict = dict(zip(headers, values))
                                    ticker_rows.append(row_dict)
                            
                            logger.info(f"Found {len(ticker_rows)} CSV rows for {ticker} in API response")
                            return ticker_rows
                        else:
                            logger.warning(f"No valid CSV data found in response")
                    except Exception as csv_error:
                        logger.error(f"Failed to parse CSV data: {str(csv_error)}")
            else:
                logger.error(f"TheTradeList API error: {response.status_code} - {response.text}")
            
            # If we got here, either parsing failed or we didn't get valid data
            logger.warning(f"Couldn't get valid data for {ticker} from TheTradeList API")
            return None
            
        except Exception as e:
            logger.error(f"Exception when calling TheTradeList API: {str(e)}")
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
            # For now, this always uses yfinance since TheTradeList API's historical data endpoint isn't specified
            interval = "1d" if timespan == "day" else "1h"
            df = yf.download(symbol, period=period, interval=interval, progress=False)
            
            if df.empty:
                logger.warning(f"No historical data available for {symbol}")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def api_health_check():
        """Check if TheTradeList API is available and API key is valid"""
        try:
            # Check if API is enabled
            if not TradeListApiService.USE_TRADELIST_API:
                return {
                    "status": "disabled",
                    "message": "TheTradeList API is explicitly disabled by configuration",
                    "feature_enabled": False
                }
                
            # Check if API key exists
            api_key = os.environ.get("TRADELIST_API_KEY")
            if not api_key:
                return {
                    "status": "error",
                    "message": "TheTradeList API key not found in environment variables. Set TRADELIST_API_KEY.",
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
            
            # If we can connect to the API endpoint, consider it a successful connectivity check
            if response.status_code == 200 or response.status_code == 302:
                # The API is responding, even if with a redirect or doesn't return proper data
                return {
                    "status": "connected", 
                    "message": f"TheTradeList API is reachable. Status code: {response.status_code}",
                    "feature_enabled": TradeListApiService.USE_TRADELIST_API,
                    "http_status": response.status_code,
                    "details": "API can be reached but may not be returning proper data format."
                }
            else:
                # The API endpoint is unreachable or returning errors
                return {
                    "status": "error",
                    "message": f"TheTradeList API responded with error status code: {response.status_code}",
                    "feature_enabled": TradeListApiService.USE_TRADELIST_API,
                    "http_status": response.status_code
                }
                
        except Exception as e:
            # Could not connect to the API at all
            return {
                "status": "error",
                "message": f"Cannot connect to TheTradeList API: {str(e)}",
                "feature_enabled": TradeListApiService.USE_TRADELIST_API
            }