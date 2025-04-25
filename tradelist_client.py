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
    # TODO: Update with correct API endpoint information once provided
    # Current endpoints don't return expected data format
    TRADELIST_API_BASE_URL = "https://api.thetradelist.com/v1/data"
    TRADELIST_SCANNER_ENDPOINT = "/get_trader_scanner_data.php"
    
    # Add info about API documentation
    API_DOCUMENTATION = "Refer to TheTradeList API documentation for up-to-date endpoint information"
    TRADELIST_SUPPORTED_ETFS = ["XLC", "XLF", "XLV", "XLI", "XLP", "XLY", "XLE", "XLB", "XLU", "XLRE", "XLC"]
    
    # Feature flag to control API usage
    USE_TRADELIST_API = os.environ.get("USE_TRADELIST_API", "true").lower() == "true"
    
    @staticmethod
    def get_current_price(ticker):
        """Get the current price and change data for a ticker using TheTradeList API with yfinance fallback"""
        try:
            # First attempt to get data from TheTradeList API if enabled and ticker is supported
            if TradeListApiService.USE_TRADELIST_API and ticker in TradeListApiService.TRADELIST_SUPPORTED_ETFS:
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
                    logger.warning(f"No data returned from TheTradeList API for {ticker}")
            
            # Fall back to yfinance if TheTradeList API fails, is disabled, or ticker not supported
            logger.info(f"Falling back to yfinance for {ticker}")
            return TradeListApiService._get_price_from_yfinance(ticker)
        
        except Exception as e:
            logger.error(f"Error getting price data for {ticker}: {str(e)}")
            # Fall back to yfinance in case of any error
            return TradeListApiService._get_price_from_yfinance(ticker)
    
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
    def get_tradelist_data(ticker, return_type="json"):
        """Get data from TheTradeList API"""
        try:
            # Ensure API key is available
            api_key = os.environ.get("TRADELIST_API_KEY")
            if not api_key:
                logger.error("TheTradeList API key not found in environment variables")
                return None
                
            # Construct API URL
            url = f"{TradeListApiService.TRADELIST_API_BASE_URL}{TradeListApiService.TRADELIST_SCANNER_ENDPOINT}"
            
            # Build query parameters
            params = {
                "returntype": return_type,
                "apiKey": api_key,
                "symbol": ticker  # Add specific symbol parameter to filter server-side
            }
            
            logger.info(f"Making request to TheTradeList API for {ticker}")
            
            # Make API request with redirect following enabled
            response = requests.get(url, params=params, timeout=10, allow_redirects=True)
            
            # Log the complete response for debugging
            logger.debug(f"TheTradeList API response status: {response.status_code}")
            logger.debug(f"TheTradeList API response headers: {response.headers}")
            logger.debug(f"TheTradeList API response content: {response.text[:200]}...")  # Truncate to avoid huge logs
            
            # Check for successful response and parse accordingly
            if response.status_code == 200:
                # Try to parse as JSON first
                try:
                    if return_type.lower() == "json" and response.text.strip().startswith(('[', '{')):
                        data = response.json()
                        # Filter to only get the requested ticker if not already filtered server-side
                        if isinstance(data, list):
                            ticker_data = [item for item in data if item.get("symbol") == ticker]
                            return ticker_data
                        elif isinstance(data, dict) and data.get("symbol") == ticker:
                            return [data]  # Return as list for consistency
                        else:
                            logger.warning(f"Received JSON data but couldn't find ticker {ticker} in response")
                    else:
                        logger.warning(f"Response doesn't appear to be valid JSON format: {response.text[:50]}...")
                except Exception as json_error:
                    logger.error(f"Failed to parse JSON from API response: {str(json_error)}")
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
            # Check if API key exists
            api_key = os.environ.get("TRADELIST_API_KEY")
            if not api_key:
                return {
                    "status": "error",
                    "message": "TheTradeList API key not found in environment variables",
                    "feature_enabled": TradeListApiService.USE_TRADELIST_API
                }
            
            # Test API with a sample call
            test_ticker = "XLK"  # Use a common ETF for testing
            test_data = TradeListApiService.get_tradelist_data(test_ticker)
            
            if test_data is not None:
                return {
                    "status": "success",
                    "message": "TheTradeList API is operational",
                    "feature_enabled": TradeListApiService.USE_TRADELIST_API,
                    "sample_data": test_data[:1] if test_data else []  # Include just the first item to avoid verbose output
                }
            else:
                return {
                    "status": "error",
                    "message": "TheTradeList API call failed",
                    "feature_enabled": TradeListApiService.USE_TRADELIST_API
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during API health check: {str(e)}",
                "feature_enabled": TradeListApiService.USE_TRADELIST_API
            }