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
    
    def __init__(self, robot=None):
        """
        Initialize the camera control module.
        
        Args:
            robot (LOBOROBOT, optional): An instance of LOBOROBOT. If None, a new instance will be created.
        """
        if robot is None:
            self.robot = LOBOROBOT()
            logger.info("Created new LOBOROBOT instance in CameraControl")
        else:
            self.robot = robot
            logger.info("Using shared LOBOROBOT instance in CameraControl")
            
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
            
            # Set initial gimbal position
            self.set_gimbal_position(self.pan, self.tilt)
            
            logger.info(f"Camera initialized: {self.width}x{self.height} @ {self.fps}fps")
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            self.camera = None
    
    def start(self):
        """Start the camera control thread."""
        if self.camera_thread is None:
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
            self.camera_thread = None
        
        # Release camera
        if self.camera:
            self.camera.release()
            self.camera = None
        
        logger.info("Camera control stopped")
    
    def set_gimbal_position(self, pan, tilt):
        """
        Set the gimbal position for the camera.
        
        Args:
            pan (int): Pan angle in degrees (35-125)
            tilt (int): Tilt angle in degrees (0-85)
        """
        # Ensure values are within range
        pan = max(35, min(125, pan))
        tilt = max(0, min(85, tilt))
        
        # Update stored values
        self.pan = pan
        self.tilt = tilt
        
        try:
            # Set servo positions
            self.robot.Servo(1, pan)  # Pan servo
            self.robot.Servo(0, tilt)  # Tilt servo
            logger.info(f"Gimbal position set to pan={pan}, tilt={tilt}")
        except Exception as e:
            logger.error(f"Error setting gimbal position: {e}")
    
    def get_latest_frame(self):
        """
        Get the latest frame from the camera.
        
        Returns:
            str: Base64 encoded JPEG image or None if no frame is available
        """
        with self.lock:
            if not self.frame_buffer:
                return None
            
            # Return the latest frame
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
        """Main camera loop that captures frames and updates the buffer."""
        last_frame_time = time.time()
        actual_fps = 0
        
        while self.is_running:
            try:
                if self.camera is None or not self.camera.isOpened():
                    logger.warning("Camera not available, attempting to reinitialize...")
                    self._init_camera()
                    time.sleep(1)
                    continue
                
                # Capture frame
                ret, frame = self.camera.read()
                
                if not ret:
                    logger.warning("Failed to capture frame")
                    time.sleep(0.1)
                    continue
                
                # Calculate actual FPS
                current_time = time.time()
                dt = current_time - last_frame_time
                if dt > 0:
                    actual_fps = 1.0 / dt
                last_frame_time = current_time
                
                # Add timestamp and FPS to frame
                cv2.putText(
                    frame,
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} | FPS: {actual_fps:.1f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                
                # Encode frame to JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                # Convert to base64 for web streaming
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