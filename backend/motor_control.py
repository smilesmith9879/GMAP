import time
import logging
import threading
from LOBOROBOT import LOBOROBOT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MotorControl:
    """
    Controls the movement of the 4WD car using the LOBOROBOT library.
    Handles differential drive based on joystick input.
    """
    
    def __init__(self, robot=None):
        """
        Initialize the motor control module.
        
        Args:
            robot (LOBOROBOT, optional): An instance of LOBOROBOT. If None, a new instance will be created.
        """
        if robot is None:
            self.robot = LOBOROBOT()
            logger.info("Created new LOBOROBOT instance in MotorControl")
        else:
            self.robot = robot
            logger.info("Using shared LOBOROBOT instance in MotorControl")
            
        self.max_speed = 60  # Maximum speed as per project requirements
        self.turn_speed_factor = 0.7  # Turn speed is 70% of max speed
        self.x = 0  # Joystick x-axis (-1 to 1)
        self.y = 0  # Joystick y-axis (-1 to 1)
        self.is_running = True
        self.control_thread = None
        self.lock = threading.Lock()
        
        # Start the control thread
        self.start()
        
        logger.info("Motor control initialized")
        
    def start(self):
        """Start the motor control thread."""
        if self.control_thread is None:
            self.is_running = True
            self.control_thread = threading.Thread(target=self._control_loop)
            self.control_thread.daemon = True
            self.control_thread.start()
            logger.info("Motor control thread started")
    
    def stop(self):
        """Stop the motor control thread and motors."""
        self.is_running = False
        if self.control_thread:
            self.control_thread.join(timeout=1.0)
            self.control_thread = None
        
        # Stop all motors
        self.robot.MotorStop()
        logger.info("Motor control stopped")
    
    def set_movement(self, x, y):
        """
        Set the movement direction and speed based on joystick input.
        
        Args:
            x (float): Joystick x-axis value (-1 to 1)
            y (float): Joystick y-axis value (-1 to 1)
        """
        with self.lock:
            self.x = x
            self.y = y
    
    def _control_loop(self):
        """Main control loop for motor movement."""
        last_update_time = time.time()
        
        while self.is_running:
            current_time = time.time()
            dt = current_time - last_update_time
            
            # Update at 20Hz
            if dt >= 0.05:
                with self.lock:
                    x = self.x
                    y = self.y
                
                self._calculate_and_set_motor_speeds(x, y)
                
                last_update_time = current_time
            
            # Sleep to reduce CPU usage
            time.sleep(0.01)
    
    def _calculate_and_set_motor_speeds(self, x, y):
        """
        Calculate and set motor speeds based on joystick position.
        
        Args:
            x (float): Joystick x-axis value (-1 to 1)
            y (float): Joystick y-axis value (-1 to 1)
        """
        # If both inputs are very small, stop the motors
        if abs(x) < 0.05 and abs(y) < 0.05:
            self.robot.MotorStop()
            return
        
        # Calculate left and right motor speeds
        left_speed = int(y * self.max_speed - x * self.max_speed * self.turn_speed_factor)
        right_speed = int(y * self.max_speed + x * self.max_speed * self.turn_speed_factor)
        
        # Ensure speeds are within range
        left_speed = max(-self.max_speed, min(self.max_speed, left_speed))
        right_speed = max(-self.max_speed, min(self.max_speed, right_speed))
        
        # Set motor speeds
        if left_speed >= 0 and right_speed >= 0:
            # Forward
            self.robot.MotorRun(0, 'forward', abs(left_speed))
            self.robot.MotorRun(1, 'forward', abs(right_speed))
        elif left_speed < 0 and right_speed < 0:
            # Backward
            self.robot.MotorRun(0, 'backward', abs(left_speed))
            self.robot.MotorRun(1, 'backward', abs(right_speed))
        elif left_speed >= 0 and right_speed < 0:
            # Turn right
            self.robot.MotorRun(0, 'forward', abs(left_speed))
            self.robot.MotorRun(1, 'backward', abs(right_speed))
        elif left_speed < 0 and right_speed >= 0:
            # Turn left
            self.robot.MotorRun(0, 'backward', abs(left_speed))
            self.robot.MotorRun(1, 'forward', abs(right_speed)) 