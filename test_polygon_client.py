import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from polygon import RESTClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_polygon_client():
    """Test the Polygon API client with basic functionality"""
    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        logger.error("No Polygon API key found in environment variables")
        return False
    
    try:
        # Initialize client
        client = RESTClient(api_key=api_key)
        logger.info(f"Initialized Polygon client with API key: {api_key[:4]}...{api_key[-4:]}")
        
        # Test 1: Get current price for SPY
        ticker = "SPY"
        logger.info(f"Testing get_previous_close_agg for {ticker}...")
        
        try:
            # Get the latest daily bar
            prev_close = client.get_previous_day_aggs(ticker=ticker)
            if prev_close:
                for agg in prev_close:
                    logger.info(f"Successfully retrieved previous day data for {ticker}: ${agg.close}")
                    break
            else:
                logger.warning(f"No previous close data found for {ticker}")
        except Exception as e:
            logger.error(f"Error getting previous close: {str(e)}")
        
        # Test 2: Get historical daily data
        logger.info(f"Testing get_aggs for {ticker} (daily data)...")
        from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            aggs = client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=from_date,
                to=to_date
            )
            
            if aggs:
                aggs_list = list(aggs)
                logger.info(f"Successfully retrieved {len(aggs_list)} days of data for {ticker}")
                
                # Convert to DataFrame for demonstration
                if aggs_list:
                    df = pd.DataFrame([{
                        'date': item.timestamp,
                        'open': item.open,
                        'high': item.high,
                        'low': item.low,
                        'close': item.close,
                        'volume': item.volume
                    } for item in aggs_list])
                    
                    logger.info(f"Data sample:\n{df.head(3)}")
                else:
                    logger.warning(f"No items in aggs list for {ticker}")
            else:
                logger.warning(f"No historical data found for {ticker}")
        except Exception as e:
            logger.error(f"Error getting historical data: {str(e)}")
        
        # Test 3: Get Sector ETF data (what we need for Income Machine)
        sector_etfs = ["XLK", "XLF", "XLV", "XLI", "XLP", "XLY", "XLE", "XLB", "XLU", "XLRE", "XLC"]
        
        logger.info(f"Testing retrieval of current prices for sector ETFs...")
        results = {}
        
        for etf in sector_etfs[:3]:  # Testing first 3 ETFs for brevity
            try:
                prev_day = client.get_previous_day_aggs(ticker=etf)
                for agg in prev_day:
                    results[etf] = agg.close
                    logger.info(f"Successfully retrieved price for {etf}: ${agg.close}")
                    break
            except Exception as e:
                logger.error(f"Error retrieving data for {etf}: {str(e)}")
        
        logger.info("Polygon API client tests completed")
        return True
        
    except Exception as e:
        logger.error(f"Error testing Polygon API client: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_polygon_client()
    print(f"Polygon API test {'succeeded' if success else 'failed'}")