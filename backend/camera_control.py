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
            robot (LOBOROBOT, optional): An existing LOBOROBOT instance to use.
                                         If None, a new instance will be created.
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
        logger.info(f"Setting gimbal position - requested: pan={pan}°, tilt={tilt}°")
        
        # Ensure values are within range
        original_pan, original_tilt = pan, tilt
        pan = max(35, min(125, pan))
        tilt = max(0, min(85, tilt))
        
        if original_pan != pan or original_tilt != tilt:
            logger.info(f"Adjusted gimbal position to valid range: pan={pan}°, tilt={tilt}°")
        
        # Check if position actually changed
        if abs(self.pan - pan) < 1 and abs(self.tilt - tilt) < 1:
            logger.debug("Gimbal position unchanged, skipping update")
            return
        
        # Update stored values
        self.pan = pan
        self.tilt = tilt
        
        # Set servo angles
        try:
            logger.info(f"About to call set_servo_angle with channel=0, pan={pan}")
            self.robot.set_servo_angle(9, pan)
            logger.info(f"set_servo_angle for pan completed")
            
            logger.info(f"About to call set_servo_angle with channel=1, tilt={tilt}")
            self.robot.set_servo_angle(10, tilt)
            logger.info(f"set_servo_angle for tilt completed")
            
            logger.info(f"Gimbal position successfully set to pan={pan}°, tilt={tilt}°")
        except Exception as e:
            logger.error(f"Error setting gimbal position: {e}", exc_info=True)
            logger.error(f"LOBOROBOT object details: {type(self.robot)}")
    
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
        frame_count = 0
        error_count = 0
        
        logger.info("Camera loop started")
        
        while self.is_running:
            try:
                current_time = time.time()
                elapsed = current_time - last_frame_time
                
                # Maintain frame rate
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                    continue
                
                logger.debug(f"Attempting to capture frame after {elapsed:.3f}s")
                
                # Check camera status
                if not self.camera or not self.camera.isOpened():
                    logger.warning("Camera not opened or not available, attempting to reinitialize")
                    self._init_camera()
                    time.sleep(1)
                    continue
                
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    error_count += 1
                    logger.warning(f"Failed to capture frame (error {error_count}/10)")
                    if error_count >= 10:  # Reinitialize after 10 consecutive errors
                        logger.error("Too many capture errors, reinitializing camera")
                        self._init_camera()
                        error_count = 0
                    time.sleep(0.1)
                    continue
                
                # Reset error counter on successful capture
                error_count = 0
                frame_count += 1
                
                # Log frame size and type
                logger.debug(f"Frame captured: {frame.shape}, type: {frame.dtype}")
                
                # Check if frame is empty or invalid
                if frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0:
                    logger.warning("Captured empty or invalid frame")
                    time.sleep(0.1)
                    continue
                
                # Calculate actual FPS
                actual_fps = 1.0 / elapsed
                logger.debug(f"Current FPS: {actual_fps:.2f}")
                
                # Encode frame to JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                encode_start = time.time()
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                encode_time = time.time() - encode_start
                
                # Convert to base64 for transmission
                b64_start = time.time()
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                b64_time = time.time() - b64_start
                
                logger.debug(f"Frame {frame_count}: encoding time: {encode_time:.3f}s, base64 time: {b64_time:.3f}s, size: {len(jpg_as_text)} bytes")
                
                # Update frame buffer
                with self.lock:
                    self.frame_buffer.append(jpg_as_text)
                    # Keep buffer size limited
                    while len(self.frame_buffer) > self.max_buffer_size:
                        self.frame_buffer.pop(0)
                    
                    logger.debug(f"Frame buffer size: {len(self.frame_buffer)}")
                
                last_frame_time = current_time
                
                # Log every 100 frames
                if frame_count % 100 == 0:
                    logger.info(f"Processed {frame_count} frames, current buffer size: {len(self.frame_buffer)}")
                
            except Exception as e:
                logger.error(f"Error in camera loop: {e}", exc_info=True)
                time.sleep(0.1) 