"""
TheTradeList WebSocket Client for Income Machine
This module provides WebSocket connectivity to TheTradeList for real-time price data.
"""

import logging
import json
import threading
import time
import os
import websocket
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global WebSocket client
_ws_client = None
_ws_lock = threading.Lock()
_price_data = {}  # symbol -> price data

class TradeListWebSocketClient:
    """WebSocket client for TheTradeList API"""
    
    def __init__(self):
        """Initialize client"""
        self.ws = None
        self.connected = False
        self.symbols = []
        self.last_message_time = None
        self.price_data = {}  # symbol -> price data
        self.data_timestamps = {}  # symbol -> timestamp
    
    def connect(self, symbols=None):
        """
        Connect to WebSocket server
        
        Args:
            symbols (list): List of symbols to subscribe to
            
        Returns:
            bool: True if connected, False otherwise
        """
        if self.connected and self.ws and self.ws.sock and self.ws.sock.connected:
            logger.info("Already connected to WebSocket server")
            
            # Subscribe to new symbols if provided
            if symbols:
                new_symbols = [s for s in symbols if s not in self.symbols]
                if new_symbols:
                    self.subscribe(new_symbols)
            
            return True
        
        # Save symbols
        if symbols:
            self.symbols = symbols
        
        # Clear existing data
        self.price_data = {}
        self.data_timestamps = {}
        
        try:
            # Connect to WebSocket server
            ws_url = "wss://ws.thetradelist.com:6001/IncomeMachine"
            
            logger.info(f"Connecting to WebSocket server: {ws_url}")
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Start WebSocket thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            wait_time = 0
            max_wait = 10  # seconds
            while not self.connected and wait_time < max_wait:
                time.sleep(0.5)
                wait_time += 0.5
            
            if not self.connected:
                logger.error("Failed to connect to WebSocket server")
                return False
            
            logger.info("Connected to WebSocket server")
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to WebSocket server: {str(e)}")
            self.connected = False
            return False
    
    def subscribe(self, symbols):
        """
        Subscribe to symbols
        
        Args:
            symbols (list): List of symbols to subscribe to
            
        Returns:
            bool: True if subscribed, False otherwise
        """
        if not self.connected or not self.ws:
            logger.warning("Not connected to WebSocket server")
            return False
        
        try:
            # Add symbols to list
            for symbol in symbols:
                if symbol not in self.symbols:
                    self.symbols.append(symbol)
            
            # Subscribe to each symbol
            for symbol in symbols:
                # Send subscription message
                subscribe_msg = json.dumps({
                    "action": "subscribe",
                    "symbol": symbol
                })
                
                self.ws.send(subscribe_msg)
                logger.info(f"Subscribed to {symbol}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error subscribing to symbols: {str(e)}")
            return False
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
                logger.info("Closed WebSocket connection")
            except Exception as e:
                logger.error(f"Error closing WebSocket connection: {str(e)}")
        
        self.connected = False
    
    def on_open(self, ws):
        """WebSocket on_open callback"""
        logger.info("WebSocket connection opened")
        self.connected = True
        self.last_message_time = datetime.now()
        
        # Subscribe to symbols
        if self.symbols:
            self.subscribe(self.symbols)
    
    def on_message(self, ws, message):
        """WebSocket on_message callback"""
        try:
            # Update last message time
            self.last_message_time = datetime.now()
            
            # Parse message
            data = json.loads(message)
            
            # Check if this is a price update
            if "ticker" in data and "price" in data:
                symbol = data["ticker"]
                
                # Check timestamp if provided
                if "ws_timestamp" in data:
                    # Parse timestamp
                    try:
                        ts_str = data["ws_timestamp"]
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        
                        # Check if we've seen this timestamp before
                        if symbol in self.data_timestamps and self.data_timestamps[symbol] == ts:
                            logger.warning(f"WebSocket data for {symbol} has unchanged timestamp: {ts_str}")
                        
                        # Check if data is too old (more than 1 day)
                        now = datetime.now()
                        age_days = (now - ts).total_seconds() / 86400
                        if age_days > 1:
                            logger.warning(f"WebSocket data for {symbol} is {age_days:.0f} days old. Timestamp: {ts_str}")
                        
                        # Save timestamp
                        self.data_timestamps[symbol] = ts
                    
                    except Exception as e:
                        logger.error(f"Error parsing timestamp: {str(e)}")
                
                # Add extra fields
                data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["data_source"] = "TheTradeList WebSocket"
                
                # Save data
                self.price_data[symbol] = data
                
                # Log debug message
                logger.debug(f"Received real-time data for {symbol}: ${data.get('price')}")
            
            # Check if this is a heartbeat
            elif "type" in data and data["type"] == "heartbeat":
                logger.debug("Received heartbeat from WebSocket server")
            
            # Unknown message type
            else:
                logger.debug(f"Received unknown WebSocket message: {message}")
        
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    def on_error(self, ws, error):
        """WebSocket on_error callback"""
        logger.error(f"WebSocket error: {str(error)}")
    
    def on_close(self, ws, close_status_code, close_reason):
        """WebSocket on_close callback"""
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_reason}")
        self.connected = False
    
    def get_latest_price(self, symbol):
        """
        Get latest price data for a symbol
        
        Args:
            symbol (str): Symbol to get price for
            
        Returns:
            dict or None: Price data or None if not available
        """
        if symbol in self.price_data:
            return self.price_data[symbol]
        return None
    
    def check_connection(self):
        """
        Check if WebSocket connection is still alive
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self.connected or not self.ws:
            return False
        
        # Check if we've received a message recently
        if self.last_message_time:
            elapsed = (datetime.now() - self.last_message_time).total_seconds()
            if elapsed > 60:  # No message in 60 seconds
                logger.warning(f"No WebSocket messages received in {elapsed:.1f} seconds")
                return False
        
        return True

# Function to get the singleton WebSocket client
def get_websocket_client():
    """
    Get WebSocket client (singleton)
    
    Returns:
        TradeListWebSocketClient or None: WebSocket client or None if not initialized
    """
    global _ws_client
    return _ws_client

def initialize_websocket(symbols):
    """
    Initialize WebSocket client and connect to server
    
    Args:
        symbols (list): List of symbols to subscribe to
        
    Returns:
        bool: True if initialized, False otherwise
    """
    global _ws_client, _ws_lock
    
    with _ws_lock:
        # Check if client exists
        if _ws_client:
            # Check if connected
            if _ws_client.check_connection():
                # Subscribe to new symbols
                _ws_client.subscribe(symbols)
                return True
            else:
                # Try to reconnect
                success = _ws_client.connect(symbols)
                return success
        
        # Create new client
        _ws_client = TradeListWebSocketClient()
        
        # Connect to server
        success = _ws_client.connect(symbols)
        
        return success

def close_websocket():
    """Close WebSocket connection"""
    global _ws_client, _ws_lock
    
    with _ws_lock:
        if _ws_client:
            _ws_client.close()
            _ws_client = None
            return True
    
    return False

# Function to check if WebSocket client is connected
def is_connected():
    """
    Check if WebSocket client is connected
    
    Returns:
        bool: True if connected, False otherwise
    """
    global _ws_client
    if _ws_client:
        return _ws_client.check_connection()
    return False