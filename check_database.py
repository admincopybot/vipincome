#!/usr/bin/env python3
"""
Check database status and load sample data if needed
"""

import sqlite3
from database_models import ETFDatabase
import os

def check_database_status():
    """Check the current database status"""
    db_path = 'etf_scores.db'
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist")
        return
    
    # Check table contents
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM etf_scores")
        count = cursor.fetchone()[0]
        print(f"Total ETF records in database: {count}")
        
        if count > 0:
            cursor.execute("SELECT symbol, total_score FROM etf_scores ORDER BY total_score DESC LIMIT 5")
            top_5 = cursor.fetchall()
            print(f"Top 5 ETFs by score:")
            for symbol, score in top_5:
                print(f"  {symbol}: {score}")
        else:
            print("No ETF data found in database")
            
            # Try to load from CSV file if it exists
            csv_files = ['etf_scores_complete.csv', 'sample_etf_scores.csv']
            for csv_file in csv_files:
                if os.path.exists(csv_file):
                    print(f"Found CSV file: {csv_file}")
                    with open(csv_file, 'r') as f:
                        lines = f.readlines()
                        print(f"CSV has {len(lines)} lines")
                        if len(lines) > 1:
                            print("Sample CSV header:")
                            print(lines[0][:200])
                    break
            
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        conn.close()

def load_sample_data():
    """Load sample data into database"""
    db = ETFDatabase()
    
    # Sample CSV data with top performers
    sample_csv = """symbol,current_price,total_score,avg_volume_10d,trend1_pass,trend1_current,trend1_threshold,trend1_description,trend2_pass,trend2_current,trend2_threshold,trend2_description,snapback_pass,snapback_current,snapback_threshold,snapback_description,momentum_pass,momentum_current,momentum_threshold,momentum_description,stabilizing_pass,stabilizing_current,stabilizing_threshold,stabilizing_description,calculation_timestamp,data_age_hours
NVDA,126.50,5,45000000,True,126.50,120.00,Current Price > 20-day EMA,True,126.50,115.00,Current Price > 100-day EMA,True,45.5,50.0,RSI < 50 (using 4-hour data),True,126.50,122.00,Current Price > Previous Week Close,True,2.5,3.0,3-day ATR < 6-day ATR,2025-06-10 16:00:00,2
AAPL,185.25,4,35000000,True,185.25,180.00,Current Price > 20-day EMA,True,185.25,175.00,Current Price > 100-day EMA,False,55.2,50.0,RSI < 50 (using 4-hour data),True,185.25,182.00,Current Price > Previous Week Close,True,1.8,2.2,3-day ATR < 6-day ATR,2025-06-10 16:00:00,2
MSFT,412.75,4,25000000,True,412.75,410.00,Current Price > 20-day EMA,True,412.75,405.00,Current Price > 100-day EMA,True,48.8,50.0,RSI < 50 (using 4-hour data),False,412.75,415.00,Current Price > Previous Week Close,True,3.1,3.5,3-day ATR < 6-day ATR,2025-06-10 16:00:00,2"""
    
    try:
        print("Loading sample data...")
        db.upload_csv_data(sample_csv)
        print("Sample data loaded successfully")
        
        # Verify the data
        data = db.get_all_etfs()
        print(f"Database now contains {len(data)} records")
        
    except Exception as e:
        print(f"Error loading sample data: {e}")

if __name__ == "__main__":
    print("=== Database Status Check ===")
    check_database_status()
    
    print("\n=== Loading Sample Data ===")
    load_sample_data()
    
    print("\n=== Final Status Check ===")
    check_database_status()