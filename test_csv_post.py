#!/usr/bin/env python3
"""
Test CSV POST Upload
Simulates how your bulk analysis sends CSV data via POST request
"""

import requests
import json
import os

def test_csv_post_upload():
    """Test CSV upload via POST request (simulating your bulk analysis)"""
    
    # Sample CSV data matching your bulk analysis output format
    csv_data = """symbol,current_price,total_score,avg_volume_10d,options_contracts_10_42_dte,trend1_pass,trend1_current,trend1_threshold,trend1_description,trend2_pass,trend2_current,trend2_threshold,trend2_description,snapback_pass,snapback_current,snapback_threshold,snapback_description,momentum_pass,momentum_current,momentum_threshold,momentum_description,stabilizing_pass,stabilizing_current,stabilizing_threshold,stabilizing_description,data_age_hours
NVDA,143.10,5,180820565,234,True,143.10,140.50,Current Price > 20-day EMA,True,143.10,135.75,Current Price > 100-day EMA,True,45.2,50.0,RSI < 50 (4-hour),True,143.10,142.20,Current Price > Previous Week Close,True,2.8,3.2,3-day ATR < 6-day ATR,6
CSCO,65.19,4,14634981,150,True,65.19,64.85,Current Price > 20-day EMA,True,65.19,62.30,Current Price > 100-day EMA,True,48.8,50.0,RSI < 50 (4-hour),False,65.19,65.25,Current Price > Previous Week Close,True,1.9,2.4,3-day ATR < 6-day ATR,8
WMB,60.20,4,8203562,100,True,60.20,59.85,Current Price > 20-day EMA,True,60.20,58.75,Current Price > 100-day EMA,True,48.1,50.0,RSI < 50 (4-hour),False,60.20,60.35,Current Price > Previous Week Close,True,1.5,1.8,3-day ATR < 6-day ATR,12
AIG,84.86,4,3429725,52,True,84.86,83.90,Current Price > 20-day EMA,True,84.86,82.15,Current Price > 100-day EMA,True,46.7,50.0,RSI < 50 (4-hour),True,84.86,84.61,Current Price > Previous Week Close,False,2.1,1.9,3-day ATR < 6-day ATR,10
SWKS,92.33,4,2156789,44,True,92.33,91.75,Current Price > 20-day EMA,True,92.33,89.50,Current Price > 100-day EMA,True,47.3,50.0,RSI < 50 (4-hour),True,92.33,92.10,Current Price > Previous Week Close,False,2.5,2.3,3-day ATR < 6-day ATR,14
AAPL,225.50,3,45123456,180,True,225.50,223.00,Current Price > 20-day EMA,True,225.50,220.00,Current Price > 100-day EMA,False,52.1,50.0,RSI < 50 (4-hour),True,225.50,224.80,Current Price > Previous Week Close,False,3.2,3.0,3-day ATR < 6-day ATR,5"""

    # Get the application URL (using localhost for testing)
    base_url = "http://0.0.0.0:5000"
    upload_url = f"{base_url}/upload_csv"
    
    print("🚀 TESTING CSV POST UPLOAD")
    print("=" * 50)
    print(f"📡 Target URL: {upload_url}")
    csv_lines = csv_data.split('\n')
    print(f"📊 CSV Records: {len(csv_lines) - 1}")  # Subtract header
    
    try:
        # Method 1: Send as form data (csv_text field)
        print("\n📤 Method 1: Sending CSV as form data...")
        response = requests.post(
            upload_url,
            data={'csv_text': csv_data},
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📝 Response Content: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ Upload successful: {result}")
            except:
                print(f"✅ Upload successful (non-JSON response)")
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server may not be running")
        return False
    except Exception as e:
        print(f"❌ Error during upload: {str(e)}")
        return False

def test_server_status():
    """Check if the server is running"""
    try:
        response = requests.get("http://0.0.0.0:5000", timeout=5)
        print(f"✅ Server is running (Status: {response.status_code})")
        return True
    except:
        print("❌ Server is not responding")
        return False

if __name__ == "__main__":
    print("🔍 CHECKING SERVER STATUS")
    if test_server_status():
        print("\\n" + "=" * 50)
        success = test_csv_post_upload()
        if success:
            print("\\n✅ CSV POST UPLOAD TEST PASSED")
            print("🔧 Your bulk analysis POST requests will work correctly")
        else:
            print("\\n❌ CSV POST UPLOAD TEST FAILED")
    else:
        print("\\n⚠️ Server not running - start the application first")