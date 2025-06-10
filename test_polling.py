#!/usr/bin/env python3
"""
Test the background polling functionality manually
"""

import requests
import json
from database_models import ETFDatabase

def test_criteria_polling():
    """Test polling the external API for criteria updates"""
    
    # Initialize database
    db = ETFDatabase()
    
    # Get current top 3 tickers
    db_data = db.get_all_etfs()
    if len(db_data) >= 3:
        top_3_tickers = [row[0] for row in db_data[:3]]
        print(f"Current top 3 tickers: {top_3_tickers}")
        
        # Test API call for first ticker
        test_ticker = top_3_tickers[0]
        print(f"\nTesting API call for {test_ticker}...")
        
        try:
            response = requests.post(
                "https://1-symbol-5-criteria-post.replit.app/analyze",
                json={"ticker": test_ticker},
                timeout=10
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                criteria_data = response.json()
                print(f"Response data: {criteria_data}")
                
                # Get current database data for comparison
                current_data = db.get_ticker_details(test_ticker)
                if current_data:
                    print(f"\nCurrent database criteria for {test_ticker}:")
                    print(f"  Trend1: {current_data.get('trend1', {}).get('pass')}")
                    print(f"  Trend2: {current_data.get('trend2', {}).get('pass')}")
                    print(f"  Snapback: {current_data.get('snapback', {}).get('pass')}")
                    print(f"  Momentum: {current_data.get('momentum', {}).get('pass')}")
                    print(f"  Stabilizing: {current_data.get('stabilizing', {}).get('pass')}")
                    print(f"  Total Score: {current_data.get('total_score')}")
                    
                    # Compare with new data
                    print(f"\nNew API criteria for {test_ticker}:")
                    print(f"  Criteria1: {criteria_data.get('criteria1')}")
                    print(f"  Criteria2: {criteria_data.get('criteria2')}")
                    print(f"  Criteria3: {criteria_data.get('criteria3')}")
                    print(f"  Criteria4: {criteria_data.get('criteria4')}")
                    print(f"  Criteria5: {criteria_data.get('criteria5')}")
                    
                    # Calculate new score
                    new_score = sum(1 for k, v in criteria_data.items() if v is True)
                    print(f"  New Score: {new_score}")
                    
                    if new_score != current_data.get('total_score'):
                        print(f"\n✓ Score change detected! {current_data.get('total_score')} -> {new_score}")
                    else:
                        print(f"\n- No score change detected")
                
            else:
                print(f"API call failed: {response.text}")
                
        except Exception as e:
            print(f"Error testing API: {str(e)}")
    else:
        print("Not enough tickers in database")

if __name__ == "__main__":
    test_criteria_polling()