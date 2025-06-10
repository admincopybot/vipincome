#!/usr/bin/env python3
"""
Load complete 292 symbols dataset into database
"""

from database_models import ETFDatabase
import csv

def load_complete_dataset():
    """Load the complete 292 symbols dataset into the database"""
    db = ETFDatabase()
    
    # Read the complete CSV file
    csv_file = 'etf_scores_complete.csv'
    
    with open(csv_file, 'r') as file:
        csv_content = file.read()
    
    # Upload to database
    print("Loading 292 symbols into database...")
    db.upload_csv_data(csv_content)
    
    # Verify the data was loaded
    count = db.get_etf_count()
    print(f"Database now contains {count} symbols")
    
    if count >= 292:
        print("✓ Complete dataset successfully loaded!")
    else:
        print(f"⚠ Warning: Expected 292 symbols, found {count}")

if __name__ == "__main__":
    load_complete_dataset()