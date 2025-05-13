import os
import logging
from polygon import RESTClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_polygon_methods():
    """Test available methods in the Polygon API client"""
    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        logger.error("No Polygon API key found in environment variables")
        return False
    
    # Initialize client
    client = RESTClient(api_key=api_key)
    logger.info(f"Initialized Polygon client with API key: {api_key[:4]}...{api_key[-4:]}")
    
    # Print available methods
    methods = [method for method in dir(client) if not method.startswith('_')]
    logger.info(f"Available methods ({len(methods)}):")
    for method in sorted(methods):
        logger.info(f"- {method}")
    
    # Try a simple ticker info query
    try:
        logger.info("Attempting to get ticker info for SPY...")
        ticker_details = client.get_ticker_details("SPY")
        logger.info(f"Response: {ticker_details}")
    except Exception as e:
        logger.error(f"Error getting ticker details: {str(e)}")
    
    # Try a simple news query (which often works with lower permissions)
    try:
        logger.info("Attempting to get news for SPY...")
        news = client.get_ticker_news("SPY", limit=1)
        for n in news:
            logger.info(f"News: {n.title}")
            break
    except Exception as e:
        logger.error(f"Error getting news: {str(e)}")
    
    return True

if __name__ == "__main__":
    success = test_polygon_methods()
    print(f"Polygon API method test {'succeeded' if success else 'failed'}")