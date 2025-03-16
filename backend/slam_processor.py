import time
import threading
import logging
import numpy as np
import cv2
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SLAMProcessor:
    """
    Handles visual SLAM processing using RTAB-Map.
    Generates 2D and 3D maps of the environment.
    """
    
    def __init__(self):
        """Initialize the SLAM processor module."""
        self.is_running = True
        self.slam_thread = None
        self.lock = threading.Lock()
        
        # SLAM data
        self.map_2d = None
        self.map_3d = None
        self.position = {'x': 0, 'y': 0, 'z': 0}
        self.orientation = {'roll': 0, 'pitch': 0, 'yaw': 0}
        
        # Map settings
        self.map_resolution = 0.05  # meters per pixel
        self.map_size = (200, 200)  # pixels
        
        # Initialize empty maps
        self._init_maps()
        
        # Start SLAM thread
        self.start()
        
        logger.info("SLAM processor initialized")
    
    def _init_maps(self):
        """Initialize empty maps."""
        # Create an empty 2D map (occupancy grid)
        self.map_2d = np.zeros(self.map_size, dtype=np.uint8)
        
        # Create an empty 3D map (point cloud)
        self.map_3d = []
        
        logger.info("Maps initialized")
    
    def start(self):
        """Start the SLAM processor thread."""
        self.is_running = True
        self.slam_thread = threading.Thread(target=self._slam_loop)
        self.slam_thread.daemon = True
        self.slam_thread.start()
        logger.info("SLAM processor thread started")
    
    def stop(self):
        """Stop the SLAM processor thread."""
        self.is_running = False
        if self.slam_thread:
            self.slam_thread.join(timeout=1.0)
        
        # Save maps before stopping
        self._save_maps()
        
        logger.info("SLAM processor stopped")
    
    def get_maps(self):
        """
        Get the current maps.
        
        Returns:
            dict: Dictionary containing 2D and 3D maps
        """
        with self.lock:
            # Convert 2D map to base64 encoded image
            _, buffer = cv2.imencode('.png', self.map_2d)
            map_2d_encoded = buffer.tobytes().hex()
            
            return {
                'map_2d': map_2d_encoded,
                'map_3d': self.map_3d,
                'position': self.position,
                'orientation': self.orientation
            }
    
    def update_position(self, position, orientation):
        """
        Update the current position and orientation.
        
        Args:
            position (dict): Position dictionary with x, y, z keys
            orientation (dict): Orientation dictionary with roll, pitch, yaw keys
        """
        with self.lock:
            self.position = position
            self.orientation = orientation
    
    def _save_maps(self):
        """Save maps to disk."""
        try:
            # Create maps directory if it doesn't exist
            if not os.path.exists('maps'):
                os.makedirs('maps')
            
            # Save 2D map as image
            cv2.imwrite('maps/map_2d.png', self.map_2d)
            
            # Save 3D map as JSON
            with open('maps/map_3d.json', 'w') as f:
                json.dump(self.map_3d, f)
            
            # Save position and orientation
            with open('maps/position.json', 'w') as f:
                json.dump({
                    'position': self.position,
                    'orientation': self.orientation
                }, f)
            
            logger.info("Maps saved to disk")
        except Exception as e:
            logger.error(f"Error saving maps: {e}")
    
    def _slam_loop(self):
        """SLAM loop that runs at 10Hz to update maps."""
        update_interval = 0.1  # 10Hz
        last_update_time = time.time()
        
        # In a real implementation, this would interface with RTAB-Map
        # For this simulation, we'll just update the maps with dummy data
        
        while self.is_running:
            try:
                current_time = time.time()
                elapsed = current_time - last_update_time
                
                # Maintain update rate
                if elapsed < update_interval:
                    time.sleep(update_interval - elapsed)
                    continue
                
                last_update_time = current_time
                
                # Update maps with simulated data
                self._update_maps_simulation()
                
            except Exception as e:
                logger.error(f"Error in SLAM loop: {e}")
                time.sleep(update_interval)
    
    def _update_maps_simulation(self):
        """
        Update maps with simulated data.
        In a real implementation, this would process camera frames and IMU data.
        """
        with self.lock:
            # Simulate robot movement
            self.position['x'] += np.random.normal(0, 0.01)
            self.position['y'] += np.random.normal(0, 0.01)
            
            # Update 2D map (add random obstacles)
            if np.random.random() < 0.1:  # 10% chance to add an obstacle
                x = np.random.randint(0, self.map_size[0])
                y = np.random.randint(0, self.map_size[1])
                radius = np.random.randint(1, 5)
                cv2.circle(self.map_2d, (x, y), radius, 255, -1)
            
            # Update 3D map (add random points)
            if np.random.random() < 0.1:  # 10% chance to add points
                num_points = np.random.randint(1, 10)
                for _ in range(num_points):
                    x = self.position['x'] + np.random.normal(0, 0.1)
                    y = self.position['y'] + np.random.normal(0, 0.1)
                    z = np.random.normal(0, 0.05)
                    
                    # Add point to 3D map
                    self.map_3d.append({
                        'x': float(x),
                        'y': float(y),
                        'z': float(z),
                        'r': np.random.randint(0, 256),
                        'g': np.random.randint(0, 256),
                        'b': np.random.randint(0, 256)
                    })
                    
                    # Limit the size of the 3D map
                    if len(self.map_3d) > 1000:
                        self.map_3d.pop(0) 