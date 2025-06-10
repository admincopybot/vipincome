#!/usr/bin/env python3
"""
Restore the complete ETF database from CSV file
"""

from database_models import ETFDatabase

def restore_complete_database():
    """Load the complete ETF dataset from CSV"""
    db = ETFDatabase()
    
    try:
        with open('etf_scores_complete.csv', 'r') as f:
            csv_content = f.read()
        
        print(f"Loading complete ETF dataset...")
        db.upload_csv_data(csv_content)
        
        # Verify the data
        data = db.get_all_etfs()
        print(f"Database restored with {len(data)} records")
        
        if data:
            print("Top 5 ETFs by score:")
            for i, row in enumerate(data[:5]):
                print(f"  {row[0]}: {row[2]}")  # symbol: score
        
        return True
        
    except Exception as e:
        print(f"Error restoring database: {e}")
        return False

if __name__ == "__main__":
    restore_complete_database()