#!/usr/bin/env python3
"""
Test the automated spread pipeline functionality
"""
import json
from automated_spread_pipeline import SpreadPipeline

def test_pipeline():
    """Test the pipeline components"""
    print("Testing Automated Spread Analysis Pipeline")
    print("=" * 50)
    
    pipeline = SpreadPipeline()
    
    # Test 1: Check API endpoints
    print("1. Testing API connectivity...")
    print(f"   Source: {pipeline.tickers_endpoint}")
    print(f"   Destination: {pipeline.spreads_endpoint}")
    
    # Test 2: Fetch top tickers
    print("\n2. Fetching top tickers...")
    ticker_data = pipeline.fetch_top_tickers()
    
    if ticker_data:
        tickers = ticker_data.get('tickers', [])
        scores = ticker_data.get('criteria_scores', {})
        print(f"   ✓ Retrieved {len(tickers)} tickers: {tickers}")
        print(f"   ✓ Scores: {scores}")
        
        # Test 3: Analyze one ticker
        if tickers:
            test_ticker = tickers[0]
            print(f"\n3. Testing spread analysis for {test_ticker}...")
            
            analysis = pipeline.analyze_ticker_spreads(test_ticker)
            
            if 'error' not in analysis:
                print(f"   ✓ Analysis successful for {test_ticker}")
                print(f"   ✓ Total spreads found: {analysis.get('total_spreads_found', 0)}")
                
                # Show best spreads by strategy
                strategies = analysis.get('strategies', {})
                for strategy, spreads in strategies.items():
                    if spreads:
                        best = spreads[0]
                        print(f"   ✓ Best {strategy}: ${best.get('long_strike')}/{best.get('short_strike')} "
                              f"ROI: {best.get('roi_percent', 0):.1f}% DTE: {best.get('days_to_expiration')}")
                
                # Test 4: Format data for API
                print(f"\n4. Testing data formatting...")
                for strategy in ['aggressive', 'balanced', 'conservative']:
                    best_spread = pipeline.select_best_spread_by_strategy(analysis, strategy)
                    if best_spread:
                        payload = pipeline.format_spread_data(test_ticker, best_spread, strategy)
                        print(f"   ✓ {strategy} payload ready: {payload['symbol']} "
                              f"ROI: {payload['spread_data']['roi']}%")
                
                print(f"\n5. Pipeline test completed successfully!")
                print(f"   Ready to process: {', '.join(tickers)}")
                
                # Show sample payload structure
                print(f"\nSample payload structure:")
                if strategies.get('aggressive'):
                    sample = pipeline.format_spread_data(test_ticker, strategies['aggressive'][0], 'aggressive')
                    print(json.dumps(sample, indent=2))
                
            else:
                print(f"   ✗ Analysis failed: {analysis['error']}")
        else:
            print("   ✗ No tickers to test")
    else:
        print("   ✗ Failed to fetch tickers")
        print("   Note: The source API might not be ready yet")

if __name__ == '__main__':
    test_pipeline()