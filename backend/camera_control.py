import cv2
import time
import threading
import logging
import base64
import numpy as np
from LOBOROBOT import LOBOROBOT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraControl:
    """
    Controls the camera and gimbal for the 4WD car.
    Handles video streaming and camera positioning.
    """
    
    def __init__(self):
        """Initialize the camera control module."""
        self.robot = LOBOROBOT()
        self.camera = None
        self.is_running = True
        self.frame_buffer = []
        self.max_buffer_size = 3  # 3-frame buffer as per project requirements
        self.lock = threading.Lock()
        self.camera_thread = None
        
        # Gimbal position (pan, tilt)
        self.pan = 80  # Default 80° as per project requirements
        self.tilt = 40  # Default 40° as per project requirements
        
        # Camera settings
        self.width = 320
        self.height = 240
        self.fps = 10
        self.jpeg_quality = 70  # 70% JPEG quality as per project requirements
        
        # Initialize camera
        self._init_camera()
        
        # Start camera thread
        self.start()
        
        logger.info("Camera control initialized")
    
    def _init_camera(self):
        """Initialize the camera with the specified settings."""
        try:
            self.camera = cv2.VideoCapture(0)  # Use default camera
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            if not self.camera.isOpened():
                logger.error("Failed to open camera")
                return False
            
            logger.info(f"Camera initialized: {self.width}x{self.height} @ {self.fps}fps")
            return True
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            return False
    
    def start(self):
        """Start the camera control thread."""
        self.is_running = True
        self.camera_thread = threading.Thread(target=self._camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        logger.info("Camera thread started")
    
    def stop(self):
        """Stop the camera control thread and release resources."""
        self.is_running = False
        if self.camera_thread:
            self.camera_thread.join(timeout=1.0)
        
        if self.camera:
            self.camera.release()
        
        # Reset gimbal to default position
        self.set_gimbal_position(80, 40)
        
        logger.info("Camera control stopped")
    
    def set_gimbal_position(self, pan, tilt):
        """
        Set the gimbal position.
        
        Args:
            pan (int): Pan angle (35°-125°)
            tilt (int): Tilt angle (0°-85°)
        """
        # Ensure values are within range
        pan = max(35, min(125, pan))
        tilt = max(0, min(85, tilt))
        
        # Update stored values
        self.pan = pan
        self.tilt = tilt
        
        # Set servo angles
        try:
            # Assuming channel 0 is pan and channel 1 is tilt
            self.robot.set_servo_angle(0, pan)
            self.robot.set_servo_angle(1, tilt)
            logger.debug(f"Gimbal position set to pan={pan}°, tilt={tilt}°")
        except Exception as e:
            logger.error(f"Error setting gimbal position: {e}")
    
    def get_latest_frame(self):
        """
        Get the latest frame from the buffer.
        
        Returns:
            str: Base64 encoded JPEG image
        """
        with self.lock:
            if not self.frame_buffer:
                return None
            return self.frame_buffer[-1]
    
    def get_frame_buffer(self):
        """
        Get the entire frame buffer.
        
        Returns:
            list: List of Base64 encoded JPEG images
        """
        with self.lock:
            return self.frame_buffer.copy()
    
    def _camera_loop(self):
        """Camera loop that captures frames at the specified FPS."""
        frame_interval = 1.0 / self.fps
        last_frame_time = time.time()
        
        while self.is_running:
            try:
                current_time = time.time()
                elapsed = current_time - last_frame_time
                
                # Maintain frame rate
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                    continue
                
                last_frame_time = current_time
                
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    logger.warning("Failed to capture frame")
                    time.sleep(0.1)
                    continue
                
                # Encode frame to JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                # Convert to base64 for transmission
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                
                # Update frame buffer
                with self.lock:
                    self.frame_buffer.append(jpg_as_text)
                    # Keep buffer size limited
                    while len(self.frame_buffer) > self.max_buffer_size:
                        self.frame_buffer.pop(0)
                
            except Exception as e:
                logger.error(f"Error in camera loop: {e}")
                time.sleep(0.1) 