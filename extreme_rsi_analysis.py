#!/usr/bin/env python3
"""
EXTREME RSI ANALYSIS - Debug why we get 36.1 vs TradingView's 51
Comprehensive data comparison and calculation verification
"""

import requests
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def rma(series, length):
    """RMA using exact logic from pipeline"""
    return series.ewm(alpha=1 / length, adjust=False).mean()

def compute_rsi(close, length=14):
    """Compute RSI using exact PineScript logic from pipeline"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)
    return rsi

def fetch_polygon_data(symbol, timespan, multiplier, from_date, to_date):
    """Fetch data from Polygon with comprehensive logging"""
    api_key = os.environ.get('POLYGON_API_KEY')
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 5000,
        'apiKey': api_key
    }
    
    print(f"\n🔍 FETCHING DATA:")
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    response = requests.get(url, params=params, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"ERROR: {response.text}")
        return None
    
    data = response.json()
    if not data.get('results'):
        print(f"No results in response: {data}")
        return None
    
    print(f"Raw results count: {len(data['results'])}")
    
    # Convert to DataFrame
    df = pd.DataFrame(data['results'])
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
    
    print(f"DataFrame shape: {df.shape}")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    return df

def analyze_rsi_extreme(symbol='AGCO'):
    """Perform extreme analysis of RSI calculation vs TradingView"""
    
    print(f"🚨 EXTREME RSI ANALYSIS FOR {symbol}")
    print("=" * 60)
    
    # Test multiple data ranges and timeframes
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    scenarios = [
        # (description, multiplier, timespan, days_back)
        ("4H - 30 days", 4, "hour", 30),
        ("4H - 60 days", 4, "hour", 60),
        ("4H - 90 days", 4, "hour", 90),
        ("1H - 30 days (resampled)", 1, "hour", 30),
        ("1D - 365 days (daily RSI)", 1, "day", 365),
    ]
    
    results = []
    
    for desc, multiplier, timespan, days_back in scenarios:
        print(f"\n📊 SCENARIO: {desc}")
        print("-" * 40)
        
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        df = fetch_polygon_data(symbol, timespan, multiplier, start_date, end_date)
        
        if df is None or len(df) < 15:
            print(f"❌ Insufficient data: {len(df) if df is not None else 0} bars")
            continue
        
        # Resample 1H to 4H if needed
        if timespan == "hour" and multiplier == 1 and desc.endswith("(resampled)"):
            print("🔄 Resampling 1H to 4H...")
            df_4h = df.resample('4H').agg({
                'open': 'first',
                'high': 'max', 
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            df = df_4h
            print(f"After resampling: {df.shape[0]} bars")
        
        if len(df) < 15:
            print(f"❌ Still insufficient data after processing: {len(df)} bars")
            continue
        
        # Calculate RSI
        rsi_series = compute_rsi(df['close'])
        current_rsi = rsi_series.iloc[-1]
        
        # Detailed analysis
        print(f"📈 DATA SUMMARY:")
        print(f"   Bars: {len(df)}")
        print(f"   Date range: {df.index[0].strftime('%Y-%m-%d %H:%M')} to {df.index[-1].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Current price: ${df['close'].iloc[-1]:.2f}")
        print(f"   RSI: {current_rsi:.1f}")
        
        # Show last 10 price changes
        print(f"\n📊 LAST 10 PRICE CHANGES:")
        recent = df.tail(11)  # 11 to get 10 changes
        for i in range(1, len(recent)):
            prev_close = recent.iloc[i-1]['close']
            curr_close = recent.iloc[i]['close']
            change = curr_close - prev_close
            timestamp = recent.index[i]
            print(f"   {timestamp.strftime('%m-%d %H:%M')}: ${prev_close:.2f} → ${curr_close:.2f} ({change:+.2f})")
        
        # Calculate gain/loss distribution
        delta = df['close'].diff().dropna()
        gains = delta[delta > 0]
        losses = delta[delta < 0].abs()
        
        print(f"\n📈 GAIN/LOSS ANALYSIS:")
        print(f"   Total periods: {len(delta)}")
        print(f"   Gains: {len(gains)} ({len(gains)/len(delta)*100:.1f}%)")
        print(f"   Losses: {len(losses)} ({len(losses)/len(delta)*100:.1f}%)")
        print(f"   Avg gain: {gains.mean():.3f}")
        print(f"   Avg loss: {losses.mean():.3f}")
        print(f"   Gain/Loss ratio: {gains.mean()/losses.mean():.3f}")
        
        # Store result
        results.append({
            'scenario': desc,
            'bars': len(df),
            'rsi': current_rsi,
            'start_date': df.index[0],
            'end_date': df.index[-1],
            'current_price': df['close'].iloc[-1]
        })
    
    # Summary comparison
    print(f"\n🎯 RESULTS SUMMARY:")
    print("=" * 60)
    print(f"{'Scenario':<25} {'Bars':<6} {'RSI':<6} {'Date Range'}")
    print("-" * 60)
    
    for r in results:
        date_range = f"{r['start_date'].strftime('%m-%d')} to {r['end_date'].strftime('%m-%d')}"
        print(f"{r['scenario']:<25} {r['bars']:<6} {r['rsi']:<6.1f} {date_range}")
    
    print(f"\n🤔 ANALYSIS:")
    print("1. TradingView shows RSI = 51")
    print("2. Our calculations range from different values")
    print("3. Possible causes:")
    print("   - Different session times (market hours vs 24/7)")
    print("   - Different data vendors")
    print("   - TradingView using adjusted vs unadjusted prices")
    print("   - Weekend/holiday data inclusion differences")
    print("   - Rounding differences in calculations")
    
    # Try to identify the closest match
    if results:
        closest = min(results, key=lambda x: abs(x['rsi'] - 51))
        print(f"\n🎯 CLOSEST TO TRADINGVIEW (51.0):")
        print(f"   Scenario: {closest['scenario']}")
        print(f"   Our RSI: {closest['rsi']:.1f}")
        print(f"   Difference: {abs(closest['rsi'] - 51):.1f} points")

if __name__ == "__main__":
    analyze_rsi_extreme()