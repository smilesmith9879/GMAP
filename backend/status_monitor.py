import time
import threading
import logging
import psutil
import os
import platform

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StatusMonitor:
    """
    Monitors system status and performance.
    Tracks CPU usage, memory usage, temperature, and other diagnostics.
    """
    
    def __init__(self):
        """Initialize the status monitor module."""
        self.is_running = True
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # Status data
        self.cpu_usage = 0
        self.memory_usage = 0
        self.temperature = 0
        self.disk_usage = 0
        self.uptime = 0
        self.start_time = time.time()
        self.fps = 0
        self.notifications = []
        self.max_notifications = 10
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Add initial notification
        self.add_notification("System started")
        
        logger.info("Status monitor initialized")
    
    def stop(self):
        """Stop the status monitor thread."""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.info("Status monitor stopped")
    
    def get_status(self):
        """
        Get the current system status.
        
        Returns:
            dict: Dictionary containing system status information
        """
        with self.lock:
            return {
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'temperature': self.temperature,
                'disk_usage': self.disk_usage,
                'uptime': time.time() - self.start_time,
                'fps': self.fps,
                'notifications': self.notifications.copy()
            }
    
    def add_notification(self, message):
        """
        Add a notification message.
        
        Args:
            message (str): Notification message
        """
        with self.lock:
            notification = {
                'message': message,
                'timestamp': time.time()
            }
            self.notifications.append(notification)
            
            # Limit the number of stored notifications
            while len(self.notifications) > self.max_notifications:
                self.notifications.pop(0)
        
        logger.info(f"Notification added: {message}")
    
    def update_fps(self, fps):
        """
        Update the current FPS value.
        
        Args:
            fps (float): Frames per second
        """
        with self.lock:
            self.fps = fps
    
    def _monitor_loop(self):
        """Monitor loop that runs every second to update system status."""
        update_interval = 1.0  # 1Hz
        
        while self.is_running:
            try:
                # Update system status
                self._update_system_status()
                
                # Check for critical conditions
                self._check_critical_conditions()
                
                # Sleep to maintain update rate
                time.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Error in status monitor loop: {e}")
                time.sleep(update_interval)
    
    def _update_system_status(self):
        """Update system status information."""
        try:
            # Get CPU usage
            cpu_usage = psutil.cpu_percent(interval=None)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Get temperature (if available)
            temperature = 0
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            temperature = max(temperature, entry.current)
            
            # Update status data
            with self.lock:
                self.cpu_usage = cpu_usage
                self.memory_usage = memory_usage
                self.temperature = temperature
                self.disk_usage = disk_usage
            
        except Exception as e:
            logger.error(f"Error updating system status: {e}")
    
    def _check_critical_conditions(self):
        """Check for critical system conditions and add notifications."""
        with self.lock:
            # Check CPU usage
            if self.cpu_usage > 90:
                self.add_notification("CPU Overload")
            
            # Check memory usage
            if self.memory_usage > 90:
                self.add_notification("Memory Low")
            
            # Check temperature
            if self.temperature > 80:
                self.add_notification("High Temperature") 