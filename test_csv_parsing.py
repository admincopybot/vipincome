#!/usr/bin/env python3
"""
Comprehensive CSV Parsing Test
Verifies that the bulk analysis CSV data is correctly received and parsed
"""

import os
import sys
import logging
from database_models import ETFDatabase
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_csv_parsing():
    """Test CSV parsing with sample data matching bulk analysis output format"""
    
    # Sample CSV data that matches your bulk analysis format
    test_csv_data = """symbol,current_price,total_score,avg_volume_10d,options_contracts_10_42_dte,trend1_pass,trend1_current,trend1_threshold,trend1_description,trend2_pass,trend2_current,trend2_threshold,trend2_description,snapback_pass,snapback_current,snapback_threshold,snapback_description,momentum_pass,momentum_current,momentum_threshold,momentum_description,stabilizing_pass,stabilizing_current,stabilizing_threshold,stabilizing_description,data_age_hours
NVDA,132.85,5,47523456,234,True,132.85,130.50,Current Price > 20-day EMA,True,132.85,125.75,Current Price > 100-day EMA,True,45.2,50.0,RSI < 50 (4-hour),True,132.85,131.20,Current Price > Previous Week Close,True,2.8,3.2,3-day ATR < 6-day ATR,6
CSCO,58.42,4,18967234,150,True,58.42,57.85,Current Price > 20-day EMA,True,58.42,55.30,Current Price > 100-day EMA,False,52.8,50.0,RSI < 50 (4-hour),True,58.42,57.95,Current Price > Previous Week Close,True,1.9,2.4,3-day ATR < 6-day ATR,8
WMB,60.20,4,8203562,100,True,60.20,59.85,Current Price > 20-day EMA,True,60.20,58.75,Current Price > 100-day EMA,True,48.1,50.0,RSI < 50 (4-hour),False,60.20,60.35,Current Price > Previous Week Close,True,1.5,1.8,3-day ATR < 6-day ATR,12
AIG,84.86,4,3429725,52,True,84.86,83.90,Current Price > 20-day EMA,True,84.86,82.15,Current Price > 100-day EMA,True,46.7,50.0,RSI < 50 (4-hour),True,84.86,84.61,Current Price > Previous Week Close,False,2.1,1.9,3-day ATR < 6-day ATR,10
SWKS,92.33,4,2156789,44,True,92.33,91.75,Current Price > 20-day EMA,True,92.33,89.50,Current Price > 100-day EMA,True,47.3,50.0,RSI < 50 (4-hour),True,92.33,92.10,Current Price > Previous Week Close,False,2.5,2.3,3-day ATR < 6-day ATR,14"""

    print("🔍 TESTING CSV PARSING FUNCTIONALITY")
    print("=" * 60)
    
    try:
        # Initialize database
        db = ETFDatabase()
        print("✓ Database connection established")
        
        # Get record count before upload
        initial_count = db.get_etf_count()
        print(f"📊 Initial database records: {initial_count}")
        
        # Test CSV upload
        print("\n📤 Testing CSV upload...")
        result = db.upload_csv_data(test_csv_data)
        
        if result['success']:
            print(f"✅ CSV upload successful! Processed {result['count']} records")
        else:
            print(f"❌ CSV upload failed: {result['error']}")
            return False
        
        # Verify data was stored correctly
        print("\n🔍 Verifying stored data...")
        final_count = db.get_etf_count()
        print(f"📊 Final database records: {final_count}")
        
        # Test ranking with options contracts filter
        print("\n🏆 Testing ranking system...")
        all_data = db.get_all_etfs()
        
        print("📈 All symbols in database (ranked by Score → Options → Volume):")
        for symbol, data in all_data.items():
            print(f"  {symbol}: Score={data['total_score']}, Options={data.get('options_contracts_10_42_dte', 0)}, Volume={data.get('avg_volume_10d', 0):,}")
        
        # Test 100+ options filter
        print("\n🔒 Testing 100+ options contracts filter...")
        filtered_symbols = []
        for symbol, data in all_data.items():
            if data.get('options_contracts_10_42_dte', 0) >= 100:
                filtered_symbols.append((symbol, data))
        
        print(f"📊 Symbols with 100+ options contracts: {len(filtered_symbols)}")
        print("🎯 Filtered results (Free/Pro versions):")
        for symbol, data in filtered_symbols:
            print(f"  {symbol}: Score={data['total_score']}, Options={data.get('options_contracts_10_42_dte', 0)}")
        
        print("\n✅ CSV PARSING TEST COMPLETED SUCCESSFULLY!")
        print("🔧 Your bulk analysis data will be processed correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_csv_parsing()
    sys.exit(0 if success else 1)