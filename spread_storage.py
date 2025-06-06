"""
Session-Based Spread Storage for Real-Time Quotes
Stores authentic spread data temporarily for Step 4 retrieval
"""
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SessionSpreadStorage:
    def __init__(self):
        self.spreads = {}  # In-memory storage
        self.next_id = 1
    
    def store_spread(self, symbol: str, strategy: str, spread_data: dict) -> str:
        """
        Store authentic spread data and return unique spread_id
        
        Args:
            symbol: Stock symbol
            strategy: aggressive, balanced, conservative  
            spread_data: Complete spread metrics from real-time detection
            
        Returns:
            spread_id: Unique identifier for this session spread
        """
        spread_id = f"{symbol}_{strategy}_{self.next_id}_{int(time.time())}"
        self.next_id += 1
        
        # Store complete spread data for Step 4
        self.spreads[spread_id] = {
            'symbol': symbol,
            'strategy': strategy,
            'long_contract': spread_data.get('long_ticker', ''),
            'short_contract': spread_data.get('short_ticker', ''),
            'long_strike': float(spread_data.get('long_strike', 0)),
            'short_strike': float(spread_data.get('short_strike', 0)),
            'expiration': spread_data.get('expiration', ''),
            'dte': int(spread_data.get('dte', 0)),
            'spread_cost': float(spread_data.get('spread_cost', 0)),
            'max_profit': float(spread_data.get('max_profit', 0)),
            'roi': float(spread_data.get('roi', 0)),
            'current_price': float(spread_data.get('current_price', 0)),
            'long_price': float(spread_data.get('long_price', 0)),
            'short_price': float(spread_data.get('short_price', 0)),
            'spread_width': float(spread_data.get('spread_width', 0)),
            'timestamp': time.time()
        }
        
        logger.info(f"Stored session spread {spread_id}: {symbol} {strategy} ROI={spread_data.get('roi', 0):.1f}%")
        return spread_id
    
    def get_spread(self, spread_id: str) -> Optional[dict]:
        """
        Retrieve authentic spread data by ID
        
        Args:
            spread_id: Unique spread identifier
            
        Returns:
            Complete spread data for Step 4 analysis
        """
        if spread_id in self.spreads:
            spread_data = self.spreads[spread_id]
            logger.info(f"Retrieved session spread {spread_id}: {spread_data['symbol']} {spread_data['strategy']}")
            return spread_data
        else:
            logger.warning(f"Spread {spread_id} not found in session")
            return None
    
    def cleanup_old_spreads(self, max_age_minutes: int = 30):
        """Remove spreads older than specified minutes"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_minutes * 60)
        
        old_spreads = [
            spread_id for spread_id, data in self.spreads.items()
            if data['timestamp'] < cutoff_time
        ]
        
        for spread_id in old_spreads:
            del self.spreads[spread_id]
        
        if old_spreads:
            logger.info(f"Cleaned up {len(old_spreads)} old session spreads")

# Global session instance
spread_storage = SessionSpreadStorage()