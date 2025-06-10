"""
Debit Spread Calculation Diagnostics Tool
Helps troubleshoot spread calculation logic with detailed logging
"""

import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SpreadDiagnostics:
    """Diagnostic tool for analyzing debit spread calculations"""
    
    def __init__(self):
        self.diagnostic_logs = []
    
    def log_diagnostic(self, message: str, level: str = "INFO"):
        """Add diagnostic message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {level}: {message}"
        self.diagnostic_logs.append(log_entry)
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def validate_spread_inputs(self, long_contract: Dict, short_contract: Dict, 
                             long_quote: Dict, short_quote: Dict) -> bool:
        """Validate all inputs for spread calculation"""
        
        # Validate contracts
        if not long_contract.get('ticker'):
            self.log_diagnostic("Missing long contract ticker", "ERROR")
            return False
        if not short_contract.get('ticker'):
            self.log_diagnostic("Missing short contract ticker", "ERROR")
            return False
            
        # Validate strikes
        long_strike = float(long_contract.get('strike_price', 0))
        short_strike = float(short_contract.get('strike_price', 0))
        
        if long_strike <= 0:
            self.log_diagnostic(f"Invalid long strike: {long_strike}", "ERROR")
            return False
        if short_strike <= 0:
            self.log_diagnostic(f"Invalid short strike: {short_strike}", "ERROR")
            return False
        if short_strike <= long_strike:
            self.log_diagnostic(f"Invalid strike relationship: short({short_strike}) <= long({long_strike})", "ERROR")
            return False
            
        # Validate quotes
        long_ask = long_quote.get('ask_price', 0)
        long_bid = long_quote.get('bid_price', 0)
        short_ask = short_quote.get('ask_price', 0)
        short_bid = short_quote.get('bid_price', 0)
        
        if long_ask <= 0:
            self.log_diagnostic(f"Invalid long ask price: {long_ask}", "ERROR")
            return False
        if short_bid <= 0:
            self.log_diagnostic(f"Invalid short bid price: {short_bid}", "ERROR")
            return False
            
        # Check bid/ask spreads for reasonableness
        long_spread = long_ask - long_bid
        short_spread = short_ask - short_bid
        
        if long_spread < 0:
            self.log_diagnostic(f"Negative long bid/ask spread: {long_spread}", "WARNING")
        if short_spread < 0:
            self.log_diagnostic(f"Negative short bid/ask spread: {short_spread}", "WARNING")
            
        self.log_diagnostic("All inputs validated successfully")
        return True
    
    def diagnose_spread_calculation(self, long_contract: Dict, short_contract: Dict,
                                  long_quote: Dict, short_quote: Dict) -> Optional[Dict]:
        """Perform detailed diagnostic calculation with step-by-step logging"""
        
        self.log_diagnostic("=== STARTING SPREAD DIAGNOSTIC ===")
        
        # Log contract details
        long_ticker = long_contract.get('ticker')
        short_ticker = short_contract.get('ticker')
        long_strike = float(long_contract.get('strike_price', 0))
        short_strike = float(short_contract.get('strike_price', 0))
        
        self.log_diagnostic(f"Long Contract: {long_ticker} @ ${long_strike}")
        self.log_diagnostic(f"Short Contract: {short_ticker} @ ${short_strike}")
        
        # Validate inputs
        if not self.validate_spread_inputs(long_contract, short_contract, long_quote, short_quote):
            self.log_diagnostic("Validation failed - aborting calculation", "ERROR")
            return None
        
        # Extract pricing
        long_ask = long_quote.get('ask_price', 0)
        long_bid = long_quote.get('bid_price', 0)
        short_ask = short_quote.get('ask_price', 0)
        short_bid = short_quote.get('bid_price', 0)
        
        self.log_diagnostic(f"Long Option Pricing: bid=${long_bid}, ask=${long_ask}")
        self.log_diagnostic(f"Short Option Pricing: bid=${short_bid}, ask=${short_ask}")
        
        # Calculate spread cost (buy long at ask, sell short at bid)
        spread_cost = long_ask - short_bid
        self.log_diagnostic(f"Spread Cost Calculation: ${long_ask} - ${short_bid} = ${spread_cost:.2f}")
        
        if spread_cost <= 0:
            self.log_diagnostic(f"Non-positive spread cost: ${spread_cost:.2f}", "WARNING")
        
        # Calculate spread width
        spread_width = short_strike - long_strike
        self.log_diagnostic(f"Spread Width: ${short_strike} - ${long_strike} = ${spread_width:.2f}")
        
        # Calculate max profit
        max_profit = spread_width - spread_cost
        self.log_diagnostic(f"Max Profit: ${spread_width:.2f} - ${spread_cost:.2f} = ${max_profit:.2f}")
        
        # Calculate ROI
        if spread_cost > 0:
            roi = (max_profit / spread_cost) * 100
            self.log_diagnostic(f"ROI Calculation: (${max_profit:.2f} / ${spread_cost:.2f}) × 100 = {roi:.1f}%")
        else:
            roi = 0
            self.log_diagnostic("ROI set to 0 due to non-positive spread cost", "WARNING")
        
        # Sanity checks
        if max_profit < 0:
            self.log_diagnostic(f"Negative max profit: ${max_profit:.2f}", "WARNING")
        if roi < 0:
            self.log_diagnostic(f"Negative ROI: {roi:.1f}%", "WARNING")
        
        result = {
            'long_ticker': long_ticker,
            'short_ticker': short_ticker,
            'long_strike': long_strike,
            'short_strike': short_strike,
            'long_ask': long_ask,
            'long_bid': long_bid,
            'short_ask': short_ask,
            'short_bid': short_bid,
            'spread_cost': spread_cost,
            'spread_width': spread_width,
            'max_profit': max_profit,
            'roi': roi,
            'diagnostics': self.diagnostic_logs.copy()
        }
        
        self.log_diagnostic(f"=== DIAGNOSTIC COMPLETE: ROI = {roi:.1f}% ===")
        return result
    
    def get_diagnostic_report(self) -> str:
        """Return formatted diagnostic report"""
        return "\n".join(self.diagnostic_logs)
    
    def clear_diagnostics(self):
        """Clear diagnostic log"""
        self.diagnostic_logs.clear()

def test_spread_calculation(long_strike: float, short_strike: float,
                          long_bid: float, long_ask: float,
                          short_bid: float, short_ask: float) -> Dict:
    """Test spread calculation with manual inputs"""
    
    diagnostics = SpreadDiagnostics()
    
    # Create mock contracts and quotes
    long_contract = {
        'ticker': f'TEST{long_strike}C',
        'strike_price': long_strike
    }
    short_contract = {
        'ticker': f'TEST{short_strike}C', 
        'strike_price': short_strike
    }
    long_quote = {
        'bid_price': long_bid,
        'ask_price': long_ask
    }
    short_quote = {
        'bid_price': short_bid,
        'ask_price': short_ask
    }
    
    result = diagnostics.diagnose_spread_calculation(
        long_contract, short_contract, long_quote, short_quote
    )
    
    return {
        'calculation_result': result,
        'diagnostic_report': diagnostics.get_diagnostic_report()
    }

# Example usage for troubleshooting
if __name__ == "__main__":
    # Test with sample data
    print("Testing spread calculation...")
    test_result = test_spread_calculation(
        long_strike=230.0,
        short_strike=235.0,
        long_bid=24.50,
        long_ask=24.80,
        short_bid=20.10,
        short_ask=20.35
    )
    
    print("\nDiagnostic Report:")
    print(test_result['diagnostic_report'])
    
    print("\nCalculation Result:")
    calc = test_result['calculation_result']
    if calc:
        print(f"Spread Cost: ${calc['spread_cost']:.2f}")
        print(f"Max Profit: ${calc['max_profit']:.2f}")
        print(f"ROI: {calc['roi']:.1f}%")