import time
import logging
import threading
from backend.lobo_motor import LOBOMotor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MotorControl:
    """
    Controls the movement of the 4WD car using the LOBOMotor library.
    Handles differential drive based on joystick input.
    """
    
    def __init__(self):
        """Initialize the motor control module."""
        self.robot = LOBOMotor()
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
        self.robot.t_stop(0)  # Stop all motors
        logger.info("Motor control stopped")
    
    def set_movement(self, x, y):
        """
        Set the movement based on joystick input.
        
        Args:
            x (float): Joystick x-axis value (-1 to 1)
            y (float): Joystick y-axis value (-1 to 1)
        """
        with self.lock:
            self.x = x
            self.y = y
    
    def _control_loop(self):
        """Control loop that runs at 20Hz to update motor speeds."""
        update_interval = 0.05  # 20Hz
        
        while self.is_running:
            try:
                with self.lock:
                    x = self.x
                    y = self.y
                
                # If both values are near zero, stop the motors
                if abs(x) < 0.05 and abs(y) < 0.05:
                    self.robot.t_stop(0)
                    time.sleep(update_interval)
                    continue
                
                # Calculate motor speeds based on joystick position
                self._calculate_and_set_motor_speeds(x, y)
                
                # Sleep to maintain update rate
                time.sleep(update_interval)
            
            except Exception as e:
                logger.error(f"Error in motor control loop: {e}")
                time.sleep(update_interval)
    
    def _calculate_and_set_motor_speeds(self, x, y):
        """
        Calculate and set motor speeds based on joystick position.
        
        Args:
            x (float): Joystick x-axis value (-1 to 1)
            y (float): Joystick y-axis value (-1 to 1)
        """
        # Scale joystick values to motor speeds
        forward_speed = int(abs(y) * self.max_speed)
        turn_speed = int(abs(x) * self.max_speed * self.turn_speed_factor)
        
        # Determine movement type based on joystick position
        if abs(y) > abs(x):
            # Forward/backward movement dominates
            if y > 0:
                self.robot.t_up(forward_speed, 0)
            else:
                self.robot.t_down(forward_speed, 0)
        else:
            # Left/right movement dominates
            if x > 0:
                self.robot.turnRight(turn_speed, 0)
            else:
                self.robot.turnLeft(turn_speed, 0) 