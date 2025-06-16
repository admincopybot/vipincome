#!/usr/bin/env python3
"""
Test authentic options data upload to verify the parsing works correctly
"""

import requests

# Simulate the authentic data from your bulk analysis (based on your troubleshooting output)
authentic_csv = """symbol,current_price,total_score,avg_volume_10d,options_contracts_10_42_dte,trend1_pass,trend1_current,trend1_threshold,trend1_description,trend2_pass,trend2_current,trend2_threshold,trend2_description,snapback_pass,snapback_current,snapback_threshold,snapback_description,momentum_pass,momentum_current,momentum_threshold,momentum_description,stabilizing_pass,stabilizing_current,stabilizing_threshold,stabilizing_description,data_age_hours
NVDA,143.10,5,180820565,200,True,143.10,140.50,Current Price > 20-day EMA,True,143.10,135.75,Current Price > 100-day EMA,True,45.2,50.0,RSI < 50 (4-hour),True,143.10,142.20,Current Price > Previous Week Close,True,2.8,3.2,3-day ATR < 6-day ATR,6
MRK,98.50,4,15234567,334,True,98.50,97.85,Current Price > 20-day EMA,True,98.50,95.30,Current Price > 100-day EMA,True,48.8,50.0,RSI < 50 (4-hour),False,98.50,98.75,Current Price > Previous Week Close,True,1.9,2.4,3-day ATR < 6-day ATR,8
SWKS,92.33,4,2156789,44,True,92.33,91.75,Current Price > 20-day EMA,True,92.33,89.50,Current Price > 100-day EMA,True,47.3,50.0,RSI < 50 (4-hour),True,92.33,92.10,Current Price > Previous Week Close,False,2.5,2.3,3-day ATR < 6-day ATR,14
EXC,41.20,3,18967234,52,True,41.20,40.85,Current Price > 20-day EMA,True,41.20,39.75,Current Price > 100-day EMA,False,52.1,50.0,RSI < 50 (4-hour),True,41.20,40.95,Current Price > Previous Week Close,False,1.8,1.9,3-day ATR < 6-day ATR,12
HOLX,75.80,3,5123456,38,True,75.80,75.25,Current Price > 20-day EMA,False,75.80,76.50,Current Price > 100-day EMA,True,46.2,50.0,RSI < 50 (4-hour),True,75.80,75.60,Current Price > Previous Week Close,False,2.2,2.1,3-day ATR < 6-day ATR,10"""

print("🧪 TESTING AUTHENTIC OPTIONS DATA UPLOAD")
print("=" * 50)

try:
    response = requests.post(
        "http://0.0.0.0:5000/upload_csv",
        data={'csv_text': authentic_csv},
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Upload Result: {result}")
        
        # Verify the data was stored correctly
        import time
        time.sleep(2)  # Give database time to process
        
        from database_models import ETFDatabase
        db = ETFDatabase()
        
        # Check specific symbols
        test_symbols = ['NVDA', 'MRK', 'SWKS', 'EXC', 'HOLX']
        print("\nVERIFYING AUTHENTIC OPTIONS DATA:")
        
        all_data = db.get_all_etfs()
        for symbol in test_symbols:
            if symbol in all_data:
                contracts = all_data[symbol].get('options_contracts_10_42_dte', 0)
                score = all_data[symbol]['total_score']
                print(f"  {symbol}: Score={score}, Options={contracts} contracts")
            else:
                print(f"  {symbol}: Not found")
        
        # Test 100+ filter
        filtered = {s: d for s, d in all_data.items() if d.get('options_contracts_10_42_dte', 0) >= 100}
        print(f"\nSymbols with 100+ options: {len(filtered)}")
        for symbol, data in filtered.items():
            print(f"  {symbol}: {data.get('options_contracts_10_42_dte', 0)} contracts")
            
    else:
        print(f"Upload failed: {response.text}")
        
except Exception as e:
    print(f"Test failed: {str(e)}")