import time
import threading
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections and communication with clients.
    Handles reconnection, timeouts, and message broadcasting.
    """
    
    def __init__(self, socketio):
        """
        Initialize the WebSocket manager.
        
        Args:
            socketio: Flask-SocketIO instance
        """
        self.socketio = socketio
        self.is_running = True
        self.clients = {}  # Dictionary of connected clients
        self.lock = threading.Lock()
        self.ping_interval = 25  # 25s ping interval as per project requirements
        self.timeout = 60  # 60s timeout as per project requirements
        self.max_retries = 10  # 10 retries as per project requirements
        
        # Start the manager thread
        self.manager_thread = threading.Thread(target=self._manager_loop)
        self.manager_thread.daemon = True
        self.manager_thread.start()
        
        logger.info("WebSocket manager initialized")
    
    def register_client(self, client_id, data=None):
        """
        Register a new client connection.
        
        Args:
            client_id (str): Client identifier
            data (dict, optional): Additional client data
        """
        with self.lock:
            self.clients[client_id] = {
                'connected': True,
                'last_ping': time.time(),
                'retry_count': 0,
                'data': data or {}
            }
            logger.info(f"Client {client_id} registered")
    
    def unregister_client(self, client_id):
        """
        Unregister a client connection.
        
        Args:
            client_id (str): Client identifier
        """
        with self.lock:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"Client {client_id} unregistered")
    
    def update_client_ping(self, client_id):
        """
        Update the last ping time for a client.
        
        Args:
            client_id (str): Client identifier
        """
        with self.lock:
            if client_id in self.clients:
                self.clients[client_id]['last_ping'] = time.time()
                self.clients[client_id]['retry_count'] = 0
    
    def broadcast(self, event, data, room=None):
        """
        Broadcast a message to all or specific clients.
        
        Args:
            event (str): Event name
            data (dict): Event data
            room (str, optional): Specific room/client to send to
        """
        try:
            self.socketio.emit(event, data, room=room)
            logger.debug(f"Broadcast event {event} to {room or 'all'}")
        except Exception as e:
            logger.error(f"Error broadcasting event {event}: {e}")
    
    def send_notification(self, message, client_id=None):
        """
        Send a notification message to clients.
        
        Args:
            message (str): Notification message
            client_id (str, optional): Specific client to send to
        """
        data = {
            'message': message,
            'timestamp': time.time()
        }
        self.broadcast('notification', data, room=client_id)
        logger.info(f"Notification sent: {message}")
    
    def stop(self):
        """Stop the WebSocket manager."""
        self.is_running = False
        if self.manager_thread:
            self.manager_thread.join(timeout=1.0)
        logger.info("WebSocket manager stopped")
    
    def _manager_loop(self):
        """Manager loop that monitors client connections and handles timeouts."""
        check_interval = 5  # Check every 5 seconds
        
        while self.is_running:
            try:
                # Sleep first to allow initial connections
                time.sleep(check_interval)
                
                current_time = time.time()
                
                with self.lock:
                    # Check each client for timeout
                    for client_id, client_data in list(self.clients.items()):
                        if not client_data['connected']:
                            continue
                        
                        # Calculate time since last ping
                        elapsed = current_time - client_data['last_ping']
                        
                        # If timeout exceeded, try to reconnect
                        if elapsed > self.timeout:
                            if client_data['retry_count'] < self.max_retries:
                                # Increment retry count
                                client_data['retry_count'] += 1
                                
                                # Send ping to try to reconnect
                                try:
                                    self.socketio.emit('ping', {}, room=client_id)
                                    logger.warning(f"Client {client_id} timeout, retry {client_data['retry_count']}/{self.max_retries}")
                                except Exception as e:
                                    logger.error(f"Error sending ping to {client_id}: {e}")
                            else:
                                # Max retries exceeded, mark as disconnected
                                client_data['connected'] = False
                                logger.warning(f"Client {client_id} disconnected after {self.max_retries} retries")
                                
                                # Notify other clients
                                self.send_notification(f"Client {client_id} disconnected")
                
            except Exception as e:
                logger.error(f"Error in WebSocket manager loop: {e}")
                time.sleep(check_interval)

    def send_video_frame(self, frame_data):
        """Send a video frame to all connected clients."""
        logger.info(f"Sending video frame: size={len(frame_data)} bytes")
        self.socketio.emit('video_frame', {'data': frame_data})
        logger.info("Video frame sent to clients") 