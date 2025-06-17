#!/usr/bin/env python3
"""
Import authentic CSV data to fix database corruption
"""
import csv
import os
import psycopg2
from datetime import datetime

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')

def import_csv_data():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Clear existing data
    cur.execute("DELETE FROM etf_scores")
    print("Cleared existing corrupted data")
    
    # Import authentic CSV data
    with open('attached_assets/REAL_5_criteria_plus_options_20250613_231028_1750019299833.csv', 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            # Convert string boolean values to proper booleans
            trend1_pass = row['trend1_pass'].lower() == 'true'
            trend2_pass = row['trend2_pass'].lower() == 'true'
            snapback_pass = row['snapback_pass'].lower() == 'true'
            momentum_pass = row['momentum_pass'].lower() == 'true'
            stabilizing_pass = row['stabilizing_pass'].lower() == 'true'
            
            # Calculate authentic score from criteria
            actual_score = sum([trend1_pass, trend2_pass, snapback_pass, momentum_pass, stabilizing_pass])
            
            # Clean numeric values
            current_price = float(row['current_price'])
            avg_volume = row['avg_volume_10d'].replace(',', '').replace('"', '') if row['avg_volume_10d'] else '0'
            options_contracts = int(row['options_contracts_10_42_dte']) if row['options_contracts_10_42_dte'] else 0
            
            cur.execute("""
                INSERT INTO etf_scores (
                    symbol, current_price, total_score, trading_volume_20_day, options_contracts_10_42_dte,
                    trend1_pass, trend1_current, trend1_threshold, trend1_description,
                    trend2_pass, trend2_current, trend2_threshold, trend2_description,
                    snapback_pass, snapback_current, snapback_threshold, snapback_description,
                    momentum_pass, momentum_current, momentum_threshold, momentum_description,
                    stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
                    calculation_timestamp
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s
                )
            """, (
                row['symbol'], current_price, actual_score, avg_volume, options_contracts,
                trend1_pass, row['trend1_current'], row['trend1_threshold'], row['trend1_description'],
                trend2_pass, row['trend2_current'], row['trend2_threshold'], row['trend2_description'],
                snapback_pass, row['snapback_current'], row['snapback_threshold'], row['snapback_description'],
                momentum_pass, row['momentum_current'], row['momentum_threshold'], row['momentum_description'],
                stabilizing_pass, row['stabilizing_current'], row['stabilizing_threshold'], row['stabilizing_description'],
                datetime.now()
            ))
            count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"Successfully imported {count} tickers with authentic criteria data")

if __name__ == "__main__":
    import_csv_data()