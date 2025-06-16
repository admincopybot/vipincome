#!/usr/bin/env python3
"""
Test the new options contracts update endpoint
"""

import requests
import json

def test_options_contracts_endpoint():
    """Test the POST endpoint for updating options contracts"""
    
    url = "http://0.0.0.0:5000/update_options_contracts"
    
    print("Testing options contracts update endpoint...")
    print(f"POST {url}")
    
    try:
        response = requests.post(url, timeout=60)  # 60 second timeout for API calls
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"Updated: {result.get('updated_count', 0)} tickers")
            print(f"Total: {result.get('total_tickers', 0)} tickers")
            
            contracts = result.get('contracts', {})
            print("\nContracts found:")
            for symbol, count in contracts.items():
                status = "✅" if count >= 100 else "❌"
                print(f"  {symbol}: {count} contracts {status}")
                
        else:
            print(f"❌ Failed: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_options_contracts_endpoint()