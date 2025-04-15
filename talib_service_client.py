import requests
import json
import pandas as pd
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

def send_to_talib_service(endpoint, payload, base_url="https://5218d07b-482e-43f3-8a01-fbca2786e42c-00-3t4oeu4n8zr8l.riker.replit.dev"):
    """Send data to the TA-Lib microservice"""
    try:
        response = requests.post(
            f"{base_url}/api{endpoint}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception when calling TA-Lib service: {str(e)}")
        return None

def check_rsi_condition(ticker, timeframe='4H', period="1mo"):
    """Check if RSI is below 50 using the microservice"""
    try:
        # Get data from yfinance
        data = yf.download(ticker, period=period, interval="1h", progress=False)
        
        if data.empty:
            logger.error(f"No data returned for {ticker}")
            return None
        
        # Resample to desired timeframe
        resampled = data.resample(timeframe).agg({'Close': 'last'})
        close_data = resampled['Close'].dropna().tail(30)
        close_prices = [float(x) for x in close_data.values]
        
        # Prepare payload for the microservice
        payload = {
            "close": close_prices,
            "timeperiod": 14
        }
        
        # Send to the TA-Lib microservice
        result = send_to_talib_service("/indicators/rsi", payload)
        
        if result and "last_value" in result:
            current_rsi = result["last_value"]
            is_below_50 = current_rsi < 50 if current_rsi else False
            return {
                "ticker": ticker,
                "current_rsi": current_rsi,
                "is_below_50": is_below_50,
                "timeframe": timeframe
            }
        return None
    except Exception as e:
        logger.error(f"Error checking RSI condition for {ticker}: {str(e)}")
        return None

def get_etf_technical_score(ticker, period="6mo"):
    """Get the 5-factor ETF score from the microservice"""
    try:
        # Get data from yfinance
        data = yf.download(ticker, period=period, interval="1d", progress=False)
        
        if data.empty:
            logger.error(f"No data returned for {ticker}")
            return None
        
        # Prepare data for the microservice
        close_data = data['Close'].dropna().tail(100)
        high_data = data['High'].dropna().tail(100)
        low_data = data['Low'].dropna().tail(100)
        
        # Convert to regular lists for JSON serialization
        close_prices = [float(x) for x in close_data.values]
        high_prices = [float(x) for x in high_data.values]
        low_prices = [float(x) for x in low_data.values]
        
        # Calculate previous week closing price
        weekly_data = data.resample('W-FRI').agg({'Close': 'last'})
        prev_week_close = float(weekly_data['Close'].iloc[-2])
        
        # Prepare payload
        payload = {
            "close": close_prices,
            "high": high_prices,
            "low": low_prices,
            "prev_week_close": prev_week_close
        }
        
        # Send to the TA-Lib microservice
        return send_to_talib_service("/etf/score", payload)
    except Exception as e:
        logger.error(f"Error getting technical score for {ticker}: {str(e)}")
        return None

def screen_etfs_with_talib_service(etf_list, base_url="https://5218d07b-482e-43f3-8a01-fbca2786e42c-00-3t4oeu4n8zr8l.riker.replit.dev"):
    """Screen multiple ETFs using the TA-Lib microservice"""
    results = []
    
    for ticker in etf_list:
        logger.info(f"Analyzing {ticker}...")
        
        # Check RSI condition (Snapback)
        rsi_result = check_rsi_condition(ticker, timeframe='4H')
        
        # Get complete technical score
        score_result = get_etf_technical_score(ticker)
        
        if rsi_result and score_result:
            results.append({
                "ticker": ticker,
                "rsi_4h": rsi_result["current_rsi"],
                "snapback_condition": rsi_result["is_below_50"],
                "technical_score": score_result["etf_score"],
                "score_details": score_result["factors"]
            })
    
    return results

def check_snapback_condition(ticker):
    """Quick check if a specific ETF meets the Snapback condition (RSI < 50 on 4HR)"""
    try:
        # Get data
        data = yf.download(ticker, period="1mo", interval="1h", progress=False)
        resampled = data.resample('4H').agg({'Close': 'last'})
        close_data = resampled['Close'].dropna().tail(30)
        close_prices = [float(x) for x in close_data.values]
        
        # Send request to the TA-Lib microservice
        response = requests.post(
            "https://5218d07b-482e-43f3-8a01-fbca2786e42c-00-3t4oeu4n8zr8l.riker.replit.dev/api/indicators/rsi",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "close": close_prices,
                "timeperiod": 14
            })
        )
        
        if response.status_code == 200:
            result = response.json()
            current_rsi = result["last_value"]
            
            logger.info(f"{ticker} 4-hour RSI: {current_rsi:.2f}")
            if current_rsi < 50:
                logger.info(f"✓ {ticker} MEETS Snapback condition (RSI < 50)")
                return True, current_rsi
            else:
                logger.info(f"✗ {ticker} does NOT meet Snapback condition (RSI < 50)")
                return False, current_rsi
        else:
            logger.error(f"Error checking {ticker}: {response.status_code}")
            return None, None
    except Exception as e:
        logger.error(f"Error in snapback check for {ticker}: {str(e)}")
        return None, None

# Example usage (commented out)
# if __name__ == "__main__":
#     # Example 1: Check if XLF has RSI below 50 on 4H timeframe (Snapback condition)
#     xlf_rsi = check_rsi_condition("XLF", timeframe='4H')
#     
#     if xlf_rsi and xlf_rsi["is_below_50"]:
#         print(f"XLF meets Snapback condition: RSI = {xlf_rsi['current_rsi']:.2f}")
#     else:
#         print(f"XLF does not meet Snapback condition: RSI = {xlf_rsi['current_rsi']:.2f}")
#     
#     # Example 2: Get complete ETF 5-factor technical score
#     spy_score = get_etf_technical_score("SPY")
#     
#     if spy_score:
#         print(f"\nSPY ETF Technical Score: {spy_score['etf_score']}/5")
#         for factor, details in spy_score['factors'].items():
#             status = "✓" if details['pass'] else "✗"
#             print(f"- {factor}: {status}")
#     
#     # Example 3: Screen multiple ETFs
#     etfs_to_screen = ["SPY", "QQQ", "XLF", "IWM", "EEM"]
#     screening_results = screen_etfs_with_talib_service(etfs_to_screen)
#     
#     # Print summary table
#     print("\nETF Screening Results:")
#     print(f"{'Ticker':<6} {'4H RSI':<8} {'Snapback':<10} {'Score':<6}")
#     print("-" * 32)
#     
#     for etf in screening_results:
#         print(f"{etf['ticker']:<6} {etf['rsi_4h']:<8.2f} {'Yes' if etf['snapback_condition'] else 'No':<10} {etf['technical_score']}/5")