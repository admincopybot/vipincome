#!/usr/bin/env python3
"""
Restore options contracts data from the CSV file to fix ranking
"""
import pandas as pd
import psycopg2
import os
from datetime import datetime

def restore_options_data():
    """Load the CSV with options contracts data and update the database"""
    
    # Read the CSV file
    csv_file = 'attached_assets/REAL_5_criteria_plus_options_20250613_231028_1750019299833.csv'
    print(f"Loading data from {csv_file}")
    
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} rows from CSV")
    
    # Connect to database
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    
    # Update each row with options contracts data
    updated_count = 0
    for _, row in df.iterrows():
        symbol = row['symbol']
        options_contracts = row['options_contracts_10_42_dte'] if pd.notna(row['options_contracts_10_42_dte']) else 0
        
        # Convert to integer if it's a string with commas
        if isinstance(options_contracts, str):
            options_contracts = int(options_contracts.replace(',', '')) if options_contracts.replace(',', '').isdigit() else 0
        
        try:
            cursor.execute("""
                UPDATE etf_scores 
                SET options_contracts_10_42_dte = %s 
                WHERE symbol = %s
            """, (options_contracts, symbol))
            
            if cursor.rowcount > 0:
                updated_count += 1
                print(f"Updated {symbol}: {options_contracts} contracts")
        except Exception as e:
            print(f"Error updating {symbol}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Successfully updated {updated_count} symbols with options contracts data")
    
    # Verify the ranking
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT symbol, total_score, options_contracts_10_42_dte, avg_volume_10d
        FROM etf_scores 
        ORDER BY total_score DESC, options_contracts_10_42_dte DESC, avg_volume_10d DESC, symbol ASC 
        LIMIT 10
    """)
    
    print("\nTop 10 after update:")
    for row in cursor.fetchall():
        print(f"{row[0]}: Score={row[1]}, Options={row[2]}, Volume={row[3]}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    restore_options_data()