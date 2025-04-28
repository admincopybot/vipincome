import os
import json
import logging
import threading
import time
import websocket
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Union

logger = logging.getLogger(__name__)

class TradeListWebSocketClient:
    """
    Client for TheTradeList's WebSocket API that provides real-time ETF data.
    
    This client connects to the WebSocket endpoint, handles the session management,
    and provides methods to subscribe to specific symbols and process the incoming data.
    
    Data is updated approximately every 5 seconds as per the API documentation.
    """
    
    # WebSocket connection details
    WS_URL = "ws://thetradelist.com:6001/IncomeMachine"
    
    # Dictionary to store the latest data for each symbol
    latest_data = {}
    
    # Dictionary to store the raw data for each symbol
    _raw_data = {}
    
    # Lock for thread-safe access to data
    data_lock = threading.Lock()
    
    def __init__(self, api_key: str, symbols_to_track: List[str] = None):
        """
        Initialize the WebSocket client.
        
        Args:
            api_key (str): The API key for TheTradeList API
            symbols_to_track (List[str], optional): List of symbols to subscribe to initially
        """
        self.api_key = api_key
        self.symbols_to_track = symbols_to_track or []
        self.session_id = None
        self.ws = None
        self.is_connected = False
        self.should_reconnect = True
        self._connect_thread = None
        self._reconnect_attempts = 0
        self.on_data_update_callbacks = []
        
    def add_data_update_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback function to be called when new data is received.
        
        Args:
            callback: Function that takes a dictionary of symbol -> data mappings
        """
        self.on_data_update_callbacks.append(callback)
        
    def _on_message(self, ws, message):
        """Callback when a message is received from the WebSocket."""
        try:
            # First message is the session ID
            if not self.session_id:
                self.session_id = message.strip()
                logger.info(f"Received session ID: {self.session_id}")
                
                # After getting session ID, subscribe to all symbols
                if self.symbols_to_track:
                    for symbol in self.symbols_to_track:
                        self.subscribe_to_symbol(symbol)
                        
                return
                
            # Try to parse as JSON
            if message.startswith('[') or message.startswith('{'):
                data = json.loads(message)
                self._process_market_data(data)
            else:
                logger.warning(f"Received non-JSON message: {message[:100]}...")
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            
    def _process_market_data(self, data):
        """Process market data from the WebSocket."""
        if not data:
            return
            
        # Convert to list if it's a single object
        items = data if isinstance(data, list) else [data]
        
        updates = {}
        
        with self.data_lock:
            # Store the raw data we received
            if isinstance(data, list):
                for item in data:
                    symbol = item.get('s')
                    if symbol:
                        self._raw_data[symbol] = item
            elif isinstance(data, dict) and 's' in data:
                symbol = data.get('s')
                self._raw_data[symbol] = data
            
            for item in items:
                # Skip if not an IM (IncomeMachine) event
                if item.get('ev') != 'IM' and item.get('ev') != 'im':
                    continue
                    
                symbol = item.get('s')
                if not symbol:
                    continue
                    
                # Store the latest data
                local_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Extract the timestamp from the WebSocket data (if available)
                ws_timestamp = item.get('t', 0)
                
                # Convert WebSocket timestamp to human-readable format
                if ws_timestamp > 0:
                    # Nanoseconds to seconds
                    ws_timestamp_seconds = ws_timestamp / 1000000000
                    ws_datetime = datetime.fromtimestamp(ws_timestamp_seconds)
                    ws_datetime_str = ws_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Log if timestamp hasn't changed since the last update
                    if symbol in self._raw_data and 't' in self._raw_data[symbol]:
                        previous_timestamp = self._raw_data[symbol].get('t', 0)
                        if previous_timestamp == ws_timestamp and previous_timestamp > 0:
                            logger.warning(f"WebSocket data for {symbol} has unchanged timestamp: {ws_datetime_str}")
                else:
                    ws_datetime_str = "Unknown"
                
                self.latest_data[symbol] = {
                    'ticker': symbol,
                    'price': item.get('p', 0),
                    'change': item.get('p', 0) - item.get('c', 0) if item.get('c') else 0,
                    'change_percent': ((item.get('p', 0) - item.get('c', 0)) / item.get('c', 1) * 100) if item.get('c') else 0,
                    'volume': item.get('v', 0),
                    'last_updated': local_timestamp,
                    'ws_timestamp': ws_datetime_str,
                    'data_source': "TheTradeList WebSocket",
                    'open': item.get('o', 0),
                    'high': item.get('h', 0),
                    'low': item.get('l', 0),
                    'close': item.get('c', 0)
                }
                updates[symbol] = self.latest_data[symbol]
                
                logger.debug(f"Received real-time data for {symbol}: ${item.get('p', 0):.2f}")
                
        # Trigger callbacks with the updates
        if updates and self.on_data_update_callbacks:
            for callback in self.on_data_update_callbacks:
                try:
                    callback(updates)
                except Exception as e:
                    logger.error(f"Error in data update callback: {str(e)}")
                
    def _on_error(self, ws, error):
        """Callback when an error occurs in the WebSocket."""
        logger.error(f"WebSocket error: {str(error)}")
        
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback when the WebSocket connection is closed."""
        self.is_connected = False
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        # Try to reconnect if needed
        if self.should_reconnect:
            self._reconnect()
            
    def _on_open(self, ws):
        """Callback when the WebSocket connection is opened."""
        self.is_connected = True
        self._reconnect_attempts = 0
        logger.info("WebSocket connection established")
            
    def _connect(self):
        """Establish a WebSocket connection."""
        logger.info(f"Connecting to {self.WS_URL}...")
        
        # Initialize WebSocket
        self.ws = websocket.WebSocketApp(
            self.WS_URL,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        # Start the WebSocket connection (this will block)
        self.ws.run_forever()
        
    def _reconnect(self):
        """Attempt to reconnect with exponential backoff."""
        if not self.should_reconnect:
            return
            
        self._reconnect_attempts += 1
        wait_time = min(30, 2 ** self._reconnect_attempts)  # Exponential backoff with max of 30 seconds
        
        logger.info(f"Attempting to reconnect in {wait_time} seconds (attempt {self._reconnect_attempts})...")
        time.sleep(wait_time)
        
        # Reset session ID so we get a new one on reconnect
        self.session_id = None
        
        # Try to connect again
        if self.should_reconnect:
            self._connect()
            
    def connect(self):
        """
        Connect to the WebSocket API in a background thread.
        
        Returns:
            bool: True if connection process started, False otherwise
        """
        if self._connect_thread and self._connect_thread.is_alive():
            logger.warning("WebSocket connection already active")
            return False
            
        self.should_reconnect = True
        self._connect_thread = threading.Thread(target=self._connect, daemon=True)
        self._connect_thread.start()
        return True
        
    def disconnect(self):
        """Disconnect from the WebSocket API."""
        self.should_reconnect = False
        if self.ws:
            self.ws.close()
            logger.info("WebSocket disconnected")
            
    def subscribe_to_symbol(self, symbol: str):
        """
        Subscribe to updates for a specific symbol.
        
        Args:
            symbol (str): The symbol to subscribe to (e.g., 'XLK', 'SPY')
            
        Returns:
            bool: True if subscription request sent, False otherwise
        """
        if not self.is_connected or not self.session_id:
            logger.warning(f"Cannot subscribe to {symbol}: Not connected or no session ID")
            
            # Add to tracking list so we subscribe when connected
            if symbol not in self.symbols_to_track:
                self.symbols_to_track.append(symbol)
                
            return False
            
        try:
            # Add to our tracking list
            if symbol not in self.symbols_to_track:
                self.symbols_to_track.append(symbol)
                
            # Create subscription message
            subscription = {
                "action": "subscribe",
                "params": symbol,
                "session_id": self.session_id
            }
            
            # Send subscription request
            self.ws.send(json.dumps(subscription))
            logger.info(f"Subscribed to {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to {symbol}: {str(e)}")
            return False
            
    def unsubscribe_from_symbol(self, symbol: str):
        """
        Unsubscribe from updates for a specific symbol.
        
        Args:
            symbol (str): The symbol to unsubscribe from
            
        Returns:
            bool: True if unsubscription request sent, False otherwise
        """
        if not self.is_connected or not self.session_id:
            logger.warning(f"Cannot unsubscribe from {symbol}: Not connected or no session ID")
            
            # Remove from tracking list
            if symbol in self.symbols_to_track:
                self.symbols_to_track.remove(symbol)
                
            return False
            
        try:
            # Remove from tracking list
            if symbol in self.symbols_to_track:
                self.symbols_to_track.remove(symbol)
                
            # Create unsubscription message
            unsubscription = {
                "action": "unsubscribe",
                "params": symbol,
                "session_id": self.session_id
            }
            
            # Send unsubscription request
            self.ws.send(json.dumps(unsubscription))
            logger.info(f"Unsubscribed from {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing from {symbol}: {str(e)}")
            return False
            
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest data for a specific symbol.
        
        Args:
            symbol (str): The symbol to get data for
            
        Returns:
            Optional[Dict[str, Any]]: The latest data for the symbol or None if not available
        """
        with self.data_lock:
            return self.latest_data.get(symbol)
            
    def get_all_latest_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all latest data for all tracked symbols.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of symbol -> data mappings
        """
        with self.data_lock:
            return self.latest_data.copy()
            
    def get_raw_data(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get the raw data received from the WebSocket.
        
        Args:
            symbol (str, optional): Specific symbol to get raw data for.
                                   If None, returns all raw data.
        
        Returns:
            Dict[str, Any]: The raw WebSocket data
        """
        with self.data_lock:
            if symbol:
                return self._raw_data.get(symbol, {})
            return self._raw_data.copy()


# Singleton instance for application-wide use
_ws_client_instance = None

def get_websocket_client():
    """Get or create the singleton WebSocket client instance."""
    global _ws_client_instance
    
    if _ws_client_instance is None:
        api_key = os.environ.get("TRADELIST_API_KEY")
        if not api_key:
            logger.error("TheTradeList API key not found in environment variables")
            return None
            
        _ws_client_instance = TradeListWebSocketClient(api_key)
        
    return _ws_client_instance