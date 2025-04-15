import os
import logging
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from talib_custom import EMA, RSI, ATR, SMA

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'TA-Lib API Service'})

@app.route('/api/indicators/ema', methods=['POST'])
def calculate_ema():
    """Calculate EMA for the provided data"""
    try:
        data = request.get_json()
        if not data or 'prices' not in data or 'timeperiod' not in data:
            return jsonify({'error': 'Missing required parameters: prices, timeperiod'}), 400
        
        prices = np.array(data['prices'])
        timeperiod = int(data['timeperiod'])
        
        if len(prices) < timeperiod:
            return jsonify({'error': f'Not enough data points. Need at least {timeperiod} points.'}), 400
        
        result = EMA(prices, timeperiod)
        # Convert NaN values to None for JSON serialization
        result = result.tolist()
        result = [None if np.isnan(x) else float(x) for x in result]
        
        return jsonify({
            'indicator': 'EMA',
            'timeperiod': timeperiod,
            'values': result,
            'last_value': result[-1]
        })
    except Exception as e:
        logger.error(f"Error calculating EMA: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/indicators/rsi', methods=['POST'])
def calculate_rsi():
    """Calculate RSI for the provided data"""
    try:
        data = request.get_json()
        if not data or 'prices' not in data:
            return jsonify({'error': 'Missing required parameter: prices'}), 400
        
        prices = np.array(data['prices'])
        timeperiod = int(data.get('timeperiod', 14))
        
        if len(prices) < timeperiod + 1:
            return jsonify({'error': f'Not enough data points. Need at least {timeperiod + 1} points.'}), 400
        
        result = RSI(prices, timeperiod)
        # Convert NaN values to None for JSON serialization
        result = result.tolist()
        result = [None if np.isnan(x) else float(x) for x in result]
        
        return jsonify({
            'indicator': 'RSI',
            'timeperiod': timeperiod,
            'values': result,
            'last_value': result[-1]
        })
    except Exception as e:
        logger.error(f"Error calculating RSI: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/indicators/atr', methods=['POST'])
def calculate_atr():
    """Calculate ATR for the provided data"""
    try:
        data = request.get_json()
        if not data or 'high' not in data or 'low' not in data or 'close' not in data:
            return jsonify({'error': 'Missing required parameters: high, low, close'}), 400
        
        high = np.array(data['high'])
        low = np.array(data['low'])
        close = np.array(data['close'])
        timeperiod = int(data.get('timeperiod', 14))
        
        if len(high) < timeperiod or len(low) < timeperiod or len(close) < timeperiod:
            return jsonify({'error': f'Not enough data points. Need at least {timeperiod} points.'}), 400
        
        result = ATR(high, low, close, timeperiod)
        # Convert NaN values to None for JSON serialization
        result = result.tolist()
        result = [None if np.isnan(x) else float(x) for x in result]
        
        return jsonify({
            'indicator': 'ATR',
            'timeperiod': timeperiod,
            'values': result,
            'last_value': result[-1]
        })
    except Exception as e:
        logger.error(f"Error calculating ATR: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/etf/score', methods=['POST'])
def calculate_etf_score():
    """Calculate ETF score based on all technical indicators"""
    try:
        data = request.get_json()
        if not data or 'close' not in data or 'high' not in data or 'low' not in data:
            return jsonify({'error': 'Missing required parameters: close, high, low'}), 400
        
        close_prices = np.array(data['close'])
        high_prices = np.array(data['high'])
        low_prices = np.array(data['low'])
        
        # 1. Calculate 20 EMA
        ema_20 = EMA(close_prices, 20)
        
        # 2. Calculate 100 EMA
        ema_100 = EMA(close_prices, 100)
        
        # 3. Calculate RSI
        rsi = RSI(close_prices, 14)
        
        # 4. Get current price and week-ago price
        current_price = close_prices[-1]
        week_ago_idx = max(0, len(close_prices) - 7)
        week_ago_price = close_prices[week_ago_idx]
        
        # 5. Calculate ATR 3 and 6
        atr_full = ATR(high_prices, low_prices, close_prices, 1)
        atr_3 = np.mean(atr_full[-3:])
        atr_6 = np.mean(atr_full[-6:])
        
        # Calculate score
        score = 0
        indicators = {}
        
        # Trend 1: Price > 20 EMA
        trend1_pass = current_price > ema_20[-1]
        if trend1_pass:
            score += 1
        trend1_desc = f"Price ({current_price:.2f}) is {'above' if trend1_pass else 'below'} the 20-day EMA ({ema_20[-1]:.2f})"
        indicators['trend1'] = {
            'pass': bool(trend1_pass),
            'current': float(current_price),
            'threshold': float(ema_20[-1]),
            'description': trend1_desc
        }
        
        # Trend 2: Price > 100 EMA
        trend2_pass = current_price > ema_100[-1]
        if trend2_pass:
            score += 1
        trend2_desc = f"Price ({current_price:.2f}) is {'above' if trend2_pass else 'below'} the 100-day EMA ({ema_100[-1]:.2f})"
        indicators['trend2'] = {
            'pass': bool(trend2_pass),
            'current': float(current_price),
            'threshold': float(ema_100[-1]),
            'description': trend2_desc
        }
        
        # Snapback: RSI < 50
        current_rsi = rsi[-1]
        snapback_pass = current_rsi < 50
        if snapback_pass:
            score += 1
        snapback_desc = f"RSI ({current_rsi:.1f}) is {'below' if snapback_pass else 'above'} the threshold (50)"
        indicators['snapback'] = {
            'pass': bool(snapback_pass),
            'current': float(current_rsi),
            'threshold': 50.0,
            'description': snapback_desc
        }
        
        # Momentum: Price > Previous Week's Closing Price
        momentum_pass = current_price > week_ago_price
        if momentum_pass:
            score += 1
        momentum_desc = f"Current price ({current_price:.2f}) is {'above' if momentum_pass else 'below'} last week's close ({week_ago_price:.2f})"
        indicators['momentum'] = {
            'pass': bool(momentum_pass),
            'current': float(current_price),
            'threshold': float(week_ago_price),
            'description': momentum_desc
        }
        
        # Stabilizing: 3-Day ATR < 6-Day ATR
        stabilizing_pass = atr_3 < atr_6
        if stabilizing_pass:
            score += 1
        stabilizing_desc = f"3-day ATR ({atr_3:.2f}) is {'lower' if stabilizing_pass else 'higher'} than 6-day ATR ({atr_6:.2f})"
        indicators['stabilizing'] = {
            'pass': bool(stabilizing_pass),
            'current': float(atr_3),
            'threshold': float(atr_6),
            'description': stabilizing_desc
        }
        
        return jsonify({
            'score': score,
            'indicators': indicators,
            'current_price': float(current_price)
        })
    except Exception as e:
        logger.error(f"Error calculating ETF score: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Different port from the main app
    app.run(host='0.0.0.0', port=port, debug=True)