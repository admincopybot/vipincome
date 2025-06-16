#!/usr/bin/env python3
"""
Test script for the debit spread API
"""
import subprocess
import time
import requests
import json
import sys

def test_debit_spread_api():
    """Test the isolated debit spread API"""
    print("Starting debit spread API server...")
    
    # Start the API server
    process = subprocess.Popen(['python3', 'spread_api_server.py'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        # Test health endpoint
        print("Testing health endpoint...")
        health_response = requests.get('http://localhost:5001/health', timeout=5)
        print(f"Health check status: {health_response.status_code}")
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"Service: {health_data.get('service')}")
            print(f"API keys configured: {health_data.get('api_keys_configured')}")
        
        # Test main endpoint with AAPL
        print("\nTesting debit spread analysis for AAPL...")
        test_data = {'ticker': 'AAPL'}
        api_response = requests.post('http://localhost:5001/analyze', 
                                   json=test_data, 
                                   timeout=30)
        
        print(f"Analysis status: {api_response.status_code}")
        
        if api_response.status_code == 200:
            result = api_response.json()
            success = result.get('success', False)
            print(f"Success: {success}")
            
            if success:
                data = result.get('data', {})
                print(f"Ticker: {data.get('ticker')}")
                print(f"Current price: ${data.get('current_price')}")
                print(f"Total spreads found: {data.get('total_spreads_found', 0)}")
                
                # Show best spread
                best = data.get('best_overall', [])
                if best:
                    top_spread = best[0]
                    print(f"\nBest spread found:")
                    print(f"  Long strike: ${top_spread.get('long_strike')}")
                    print(f"  Short strike: ${top_spread.get('short_strike')}")
                    print(f"  Spread cost: ${top_spread.get('spread_cost')}")
                    print(f"  Max profit: ${top_spread.get('max_profit')}")
                    print(f"  ROI: {top_spread.get('roi_percent')}%")
                    print(f"  Days to expiration: {top_spread.get('days_to_expiration')}")
                    print(f"  Expiration date: {top_spread.get('expiration_date')}")
                    
                    # Show a few price scenarios
                    scenarios = top_spread.get('price_scenarios', [])
                    if scenarios:
                        print(f"\nPrice scenarios:")
                        for scenario in scenarios[:5]:  # Show first 5
                            pct = scenario.get('price_change_percent')
                            future_price = scenario.get('future_price')
                            profit_loss = scenario.get('profit_loss')
                            outcome = scenario.get('outcome')
                            print(f"  {pct:+.1f}%: ${future_price:.2f} -> ${profit_loss:.2f} ({outcome})")
                else:
                    print("No spreads found")
            else:
                print(f"Error: {result.get('error')}")
        else:
            print(f"Error response: {api_response.text}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        # Clean up
        process.terminate()
        process.wait()
        print("\nAPI server stopped")

if __name__ == '__main__':
    test_debit_spread_api()