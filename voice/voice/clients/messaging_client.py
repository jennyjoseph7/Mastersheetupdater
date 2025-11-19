"""Simple synchronous messaging client to bridge audio streams with messaging server."""

import os
import json
import time
import threading
from typing import Optional, Callable, Dict, Any
from enum import Enum
from dataclasses import dataclass
from websocket import WebSocketApp
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


AUTOCRM_MESSEGING_SERVER_URL = os.environ.get(
    "AUTOCRM_MESSEGING_SERVER_URL",
    "wss://autobot-messenger.gryd.in/ws"
)


class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"


@dataclass
class ConnectionMetrics:
    """Metrics for connection monitoring"""
    messages_sent: int = 0
    messages_received: int = 0
    errors_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    last_message_time: Optional[float] = None
    connection_start_time: Optional[float] = None

    def record_sent(self, size: int):
        """Record a sent message"""
        self.messages_sent += 1
        self.bytes_sent += size
        self.last_message_time = time.time()

    def record_received(self, size: int):
        """Record a received message"""
        self.messages_received += 1
        self.bytes_received += size
        self.last_message_time = time.time()

    def record_error(self):
        """Record an error"""
        self.errors_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        uptime = time.time() - self.connection_start_time if self.connection_start_time else 0
        return {
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "errors_count": self.errors_count,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "uptime_seconds": uptime,
            "last_message_time": self.last_message_time
        }


class MessagingClient:
    """
    Simple synchronous WebSocket client for bidirectional communication.

    Handles:
    - Receiving messages from server via WebSocket
    - Sending messages back to server
    - Connection management with automatic reconnection
    - Connection health monitoring and metrics
    """

    def __init__(
        self,
        session_id: str,
        base_url: Optional[str] = None,
        on_message_callback: Optional[Callable] = None,
        on_state_change: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        tag: str = "client"
    ):
        """
        Initialize messaging client

        Args:
            session_id: Unique session identifier
            base_url: WebSocket server base URL (optional)
            on_message_callback: Callback for incoming messages
            on_state_change: Callback for connection state changes (optional)
            on_error: Callback for error events (optional)
            tag: Identifier for this connection
        """
        self.session_id = session_id
        self.base_url = base_url or AUTOCRM_MESSEGING_SERVER_URL
        self.ws_url = f"{self.base_url}?room_id={self.session_id}"

        self.ws: Optional[WebSocketApp] = None
        self.on_message_callback = on_message_callback
        self.on_state_change = on_state_change
        self.on_error = on_error
        self.tag = tag

        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.running = False

        # Metrics
        self.metrics = ConnectionMetrics()

        # Thread for running WebSocket
        self.ws_thread: Optional[threading.Thread] = None

    def _set_state(self, new_state: ConnectionState):
        """Update connection state and notify callback"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.info(f"[{self.tag}] Connection state: {old_state.value} -> {new_state.value}")

            if self.on_state_change:
                try:
                    self.on_state_change(old_state, new_state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {e}")

    def _handle_error(self, error: Exception, context: str = ""):
        """Handle errors and notify callback"""
        self.metrics.record_error()
        error_info = {
            "error": str(error),
            "type": type(error).__name__,
            "context": context,
            "session_id": self.session_id,
            "timestamp": time.time()
        }
        logger.error(f"[{self.tag}] Error in {context}: {error}")

        if self.on_error:
            try:
                self.on_error(error_info)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")

    def _on_ws_open(self, ws):
        """WebSocket open callback"""
        self._set_state(ConnectionState.CONNECTED)
        self.metrics.connection_start_time = time.time()
        logger.info(f"[{self.tag}] Connected to messaging server for session {self.session_id}")

    def _on_ws_message(self, ws, raw_message):
        """WebSocket message callback"""
        try:
            message = json.loads(raw_message)
            message_type = message.get("event", "unknown")
            message_size = len(raw_message.encode('utf-8'))

            self.metrics.record_received(message_size)
            logger.info(f"[{self.tag}] Received message: {message_type} ({message_size} bytes)")

            # Call user-defined callback if provided
            if self.on_message_callback:
                try:
                    self.on_message_callback(message)
                except Exception as e:
                    self._handle_error(e, "message_callback")

        except json.JSONDecodeError as e:
            self._handle_error(e, "json_decode")
        except Exception as e:
            self._handle_error(e, "receive_message_processing")

    def _on_ws_error(self, ws, error):
        """WebSocket error callback"""
        self._handle_error(error, "websocket")

    def _on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket close callback"""
        logger.info(f"[{self.tag}] WebSocket closed: {close_status_code} - {close_msg}")
        self._set_state(ConnectionState.DISCONNECTED)

    def connect(self) -> bool:
        """
        Establish WebSocket connection

        Returns:
            bool: True if connected successfully
        """
        try:
            self._set_state(ConnectionState.CONNECTING)
            logger.info(f"[{self.tag}] Connecting to {self.ws_url}")

            self.ws = WebSocketApp(
                self.ws_url,
                on_open=self._on_ws_open,
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close
            )

            return True

        except Exception as e:
            self._handle_error(e, "connect")
            self._set_state(ConnectionState.DISCONNECTED)
            return False

    def disconnect(self):
        """Close WebSocket connection gracefully"""
        self.running = False
        self._set_state(ConnectionState.DISCONNECTED)

        if self.ws:
            try:
                self.ws.close()
                logger.info(f"[{self.tag}] Disconnected from messaging server")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")

        # Wait for thread to finish
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)

    def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message to WebSocket server

        Args:
            message: Dictionary to send as JSON

        Returns:
            bool: True if sent successfully
        """
        if self.state != ConnectionState.CONNECTED or not self.ws:
            logger.warning(f"[{self.tag}] Cannot send message - not connected")
            return False

        try:
            message_json = json.dumps(message)
            message_size = len(message_json.encode('utf-8'))

            self.ws.send(message_json)

            self.metrics.record_sent(message_size)
            logger.debug(f"[{self.tag}] Sent message: {message.get('event', 'unknown')} ({message_size} bytes)")
            return True

        except Exception as e:
            self._handle_error(e, "send_message")
            return False

    def run(self):
        """
        Main run loop - connects and maintains connection
        """
        self.running = True

        # Initial connection
        if not self.connect():
            logger.error(f"[{self.tag}] Initial connection failed")
            return

        logger.info(f"[{self.tag}] Starting WebSocket run loop...")

        # Run WebSocket in a separate thread
        self.ws_thread = threading.Thread(target=self._run_forever, daemon=True)
        self.ws_thread.start()

        logger.info(f"[{self.tag}] WebSocket thread started")

    def _run_forever(self):
        """Run WebSocket connection forever with auto-reconnect"""
        while self.running:
            try:
                self.ws.run_forever()

                # If we exit and still running, reconnect
                if self.running:
                    logger.info(f"[{self.tag}] Connection lost, reconnecting in 5 seconds...")
                    time.sleep(5)
                    if not self.connect():
                        logger.error(f"[{self.tag}] Reconnection failed")
                        self.running = False

            except Exception as e:
                self._handle_error(e, "run_forever")
                if self.running:
                    time.sleep(5)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get connection metrics and statistics

        Returns:
            Dict containing metrics
        """
        stats = self.metrics.get_stats()
        stats.update({
            "state": self.state.value,
            "session_id": self.session_id,
            "tag": self.tag
        })
        return stats

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.state == ConnectionState.CONNECTED

    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        if not self.is_connected():
            return False

        # Check if we've received messages recently
        if self.metrics.last_message_time:
            time_since_last = time.time() - self.metrics.last_message_time
            return time_since_last < 300  # Healthy if activity within 5 minutes

        return True


def test_messaging_client():
    """Test function"""
    session_id = "test_session"

    def on_message(msg):
        logger.info(f"Test callback received: {msg}")

    client = MessagingClient(session_id, on_message_callback=on_message)
    client.run()

    # Keep running
    try:
        while True:
            time.sleep(1)
            if client.is_connected():
                # Send test message
                client.send_message({"event": "test", "data": "hello"})
    except KeyboardInterrupt:
        client.disconnect()


if __name__ == "__main__":
    test_messaging_client()
