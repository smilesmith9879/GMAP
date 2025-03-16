import time
import threading
import logging
import numpy as np
import math
try:
    import smbus2 as smbus
except ImportError:
    import smbus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MPU6050 registers and addresses
MPU6050_ADDR = 0x68
PWR_MGMT_1 = 0x6B
SMPLRT_DIV = 0x19
CONFIG = 0x1A
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
INT_ENABLE = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H = 0x43
GYRO_YOUT_H = 0x45
GYRO_ZOUT_H = 0x47

class SensorFusion:
    """
    Handles sensor data collection, processing, and fusion.
    Primarily works with the MPU6050 IMU sensor.
    """
    
    def __init__(self):
        """Initialize the sensor fusion module."""
        self.bus = smbus.SMBus(1)  # I2C bus
        self.is_running = True
        self.is_calibrated = False
        self.sensor_thread = None
        self.lock = threading.Lock()
        
        # Sensor data
        self.accel_data = {'x': 0, 'y': 0, 'z': 0}
        self.gyro_data = {'x': 0, 'y': 0, 'z': 0}
        self.orientation = {'roll': 0, 'pitch': 0, 'yaw': 0}
        
        # Calibration values
        self.accel_bias = {'x': 0, 'y': 0, 'z': 0}
        self.gyro_bias = {'x': 0, 'y': 0, 'z': 0}
        
        # Initialize the IMU
        self._init_imu()
        
        # Start sensor thread
        self.start()
        
        logger.info("Sensor fusion initialized")
    
    def _init_imu(self):
        """Initialize the MPU6050 IMU sensor."""
        try:
            # Wake up the MPU6050
            self.bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0)
            
            # Configure the accelerometer and gyroscope
            self.bus.write_byte_data(MPU6050_ADDR, SMPLRT_DIV, 9)  # 100Hz sample rate
            self.bus.write_byte_data(MPU6050_ADDR, CONFIG, 0)  # No DLPF
            self.bus.write_byte_data(MPU6050_ADDR, GYRO_CONFIG, 0)  # 250 deg/s
            self.bus.write_byte_data(MPU6050_ADDR, ACCEL_CONFIG, 0)  # 2g
            self.bus.write_byte_data(MPU6050_ADDR, INT_ENABLE, 1)  # Enable data ready interrupt
            
            logger.info("IMU initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing IMU: {e}")
            return False
    
    def start(self):
        """Start the sensor fusion thread."""
        self.is_running = True
        self.sensor_thread = threading.Thread(target=self._sensor_loop)
        self.sensor_thread.daemon = True
        self.sensor_thread.start()
        logger.info("Sensor fusion thread started")
    
    def stop(self):
        """Stop the sensor fusion thread."""
        self.is_running = False
        if self.sensor_thread:
            self.sensor_thread.join(timeout=1.0)
        logger.info("Sensor fusion stopped")
    
    def calibrate_imu(self):
        """
        Calibrate the IMU by collecting samples and calculating bias.
        Takes 5 seconds (50 samples at 10Hz) as per project requirements.
        """
        logger.info("Starting IMU calibration...")
        
        # Reset calibration values
        accel_samples = {'x': [], 'y': [], 'z': []}
        gyro_samples = {'x': [], 'y': [], 'z': []}
        
        # Collect 50 samples (5 seconds at 10Hz)
        for _ in range(50):
            # Read raw sensor data
            accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = self._read_raw_data()
            
            # Store samples
            accel_samples['x'].append(accel_x)
            accel_samples['y'].append(accel_y)
            accel_samples['z'].append(accel_z)
            gyro_samples['x'].append(gyro_x)
            gyro_samples['y'].append(gyro_y)
            gyro_samples['z'].append(gyro_z)
            
            time.sleep(0.1)  # 10Hz
        
        # Calculate average bias
        with self.lock:
            self.accel_bias['x'] = sum(accel_samples['x']) / len(accel_samples['x'])
            self.accel_bias['y'] = sum(accel_samples['y']) / len(accel_samples['y'])
            self.accel_bias['z'] = sum(accel_samples['z']) / len(accel_samples['z']) - 16384  # Remove gravity (1g)
            
            self.gyro_bias['x'] = sum(gyro_samples['x']) / len(gyro_samples['x'])
            self.gyro_bias['y'] = sum(gyro_samples['y']) / len(gyro_samples['y'])
            self.gyro_bias['z'] = sum(gyro_samples['z']) / len(gyro_samples['z'])
            
            self.is_calibrated = True
        
        logger.info("IMU calibration complete")
        return True
    
    def get_sensor_data(self):
        """
        Get the latest processed sensor data.
        
        Returns:
            dict: Dictionary containing accelerometer, gyroscope, and orientation data
        """
        with self.lock:
            return {
                'accelerometer': self.accel_data.copy(),
                'gyroscope': self.gyro_data.copy(),
                'orientation': self.orientation.copy(),
                'is_calibrated': self.is_calibrated
            }
    
    def _read_raw_data(self):
        """
        Read raw data from the MPU6050.
        
        Returns:
            tuple: (accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z)
        """
        try:
            # Read accelerometer data
            accel_x = self._read_word_2c(ACCEL_XOUT_H)
            accel_y = self._read_word_2c(ACCEL_YOUT_H)
            accel_z = self._read_word_2c(ACCEL_ZOUT_H)
            
            # Read gyroscope data
            gyro_x = self._read_word_2c(GYRO_XOUT_H)
            gyro_y = self._read_word_2c(GYRO_YOUT_H)
            gyro_z = self._read_word_2c(GYRO_ZOUT_H)
            
            return accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z
        except Exception as e:
            logger.error(f"Error reading IMU data: {e}")
            return 0, 0, 0, 0, 0, 0
    
    def _read_word_2c(self, reg):
        """
        Read a word from the IMU and convert to 2's complement.
        
        Args:
            reg (int): Register address
            
        Returns:
            int: Signed 16-bit value
        """
        high = self.bus.read_byte_data(MPU6050_ADDR, reg)
        low = self.bus.read_byte_data(MPU6050_ADDR, reg + 1)
        val = (high << 8) + low
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val
    
    def _sensor_loop(self):
        """Sensor loop that runs at 10Hz to update sensor data."""
        update_interval = 0.1  # 10Hz
        last_update_time = time.time()
        
        while self.is_running:
            try:
                current_time = time.time()
                elapsed = current_time - last_update_time
                
                # Maintain update rate
                if elapsed < update_interval:
                    time.sleep(update_interval - elapsed)
                    continue
                
                last_update_time = current_time
                
                # Read raw sensor data
                accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = self._read_raw_data()
                
                # Apply calibration if available
                if self.is_calibrated:
                    accel_x -= self.accel_bias['x']
                    accel_y -= self.accel_bias['y']
                    accel_z -= self.accel_bias['z']
                    
                    gyro_x -= self.gyro_bias['x']
                    gyro_y -= self.gyro_bias['y']
                    gyro_z -= self.gyro_bias['z']
                
                # Convert to physical units
                accel_x_g = accel_x / 16384.0  # Convert to g (1g = 16384)
                accel_y_g = accel_y / 16384.0
                accel_z_g = accel_z / 16384.0
                
                gyro_x_deg = gyro_x / 131.0  # Convert to deg/s (1 deg/s = 131)
                gyro_y_deg = gyro_y / 131.0
                gyro_z_deg = gyro_z / 131.0
                
                # Calculate orientation (simple complementary filter)
                roll = math.atan2(accel_y_g, accel_z_g) * 180.0 / math.pi
                pitch = math.atan2(-accel_x_g, math.sqrt(accel_y_g * accel_y_g + accel_z_g * accel_z_g)) * 180.0 / math.pi
                
                # Update sensor data
                with self.lock:
                    self.accel_data = {
                        'x': accel_x_g,
                        'y': accel_y_g,
                        'z': accel_z_g
                    }
                    
                    self.gyro_data = {
                        'x': gyro_x_deg,
                        'y': gyro_y_deg,
                        'z': gyro_z_deg
                    }
                    
                    self.orientation = {
                        'roll': roll,
                        'pitch': pitch,
                        'yaw': self.orientation.get('yaw', 0) + gyro_z_deg * update_interval
                    }
                
            except Exception as e:
                logger.error(f"Error in sensor loop: {e}")
                time.sleep(update_interval)

    def _read_imu_data(self):
        """Read raw data from the IMU."""
        try:
            logger.debug("Attempting to read IMU data")
            
            # Check if I2C bus is available
            if self.bus is None:
                logger.warning("I2C bus not initialized")
                return None
            
            # Log I2C device address
            logger.debug(f"Reading from IMU at I2C address: 0x{MPU6050_ADDR:x}")
            
            # Read accelerometer data
            try:
                acc_x = self._read_word_2c(ACCEL_XOUT_H)
                acc_y = self._read_word_2c(ACCEL_YOUT_H)
                acc_z = self._read_word_2c(ACCEL_ZOUT_H)
                logger.debug(f"Raw accelerometer data: x={acc_x}, y={acc_y}, z={acc_z}")
            except Exception as e:
                logger.error(f"Failed to read accelerometer data: {e}", exc_info=True)
                return None
            
            # Read gyroscope data
            try:
                gyro_x = self._read_word_2c(GYRO_XOUT_H)
                gyro_y = self._read_word_2c(GYRO_YOUT_H)
                gyro_z = self._read_word_2c(GYRO_ZOUT_H)
                logger.debug(f"Raw gyroscope data: x={gyro_x}, y={gyro_y}, z={gyro_z}")
            except Exception as e:
                logger.error(f"Failed to read gyroscope data: {e}", exc_info=True)
                return None
            
            # Scale the values
            acc_x_scaled = acc_x / 16384.0
            acc_y_scaled = acc_y / 16384.0
            acc_z_scaled = acc_z / 16384.0
            
            gyro_x_scaled = gyro_x / 131.0
            gyro_y_scaled = gyro_y / 131.0
            gyro_z_scaled = gyro_z / 131.0
            
            logger.debug(f"Scaled accelerometer: x={acc_x_scaled:.4f}, y={acc_y_scaled:.4f}, z={acc_z_scaled:.4f}")
            logger.debug(f"Scaled gyroscope: x={gyro_x_scaled:.4f}, y={gyro_y_scaled:.4f}, z={gyro_z_scaled:.4f}")
            
            return {
                'acc': (acc_x_scaled, acc_y_scaled, acc_z_scaled),
                'gyro': (gyro_x_scaled, gyro_y_scaled, gyro_z_scaled)
            }
            
        except Exception as e:
            logger.error(f"Error reading IMU data: {e}", exc_info=True)
            return None

    def calibrate_imu(self):
        """Calibrate the IMU by calculating offsets."""
        logger.info("Starting IMU calibration")
        
        if not self.is_calibrated:
            logger.warning("IMU not calibrated, cannot calibrate")
            return False
        
        try:
            # Take multiple samples to get stable offsets
            samples = 100
            logger.info(f"Collecting {samples} samples for calibration")
            
            gyro_x_sum = 0
            gyro_y_sum = 0
            gyro_z_sum = 0
            
            for i in range(samples):
                data = self._read_imu_data()
                if data:
                    gyro_x_sum += data['gyro'][0]
                    gyro_y_sum += data['gyro'][1]
                    gyro_z_sum += data['gyro'][2]
                    
                    if i % 10 == 0:
                        logger.debug(f"Calibration progress: {i}/{samples}")
                else:
                    logger.warning("Failed to read IMU data during calibration")
                    return False
                
                time.sleep(0.01)
            
            # Calculate average offsets
            self.gyro_offsets = (
                gyro_x_sum / samples,
                gyro_y_sum / samples,
                gyro_z_sum / samples
            )
            
            logger.info(f"IMU calibration complete. Gyro offsets: x={self.gyro_offsets[0]:.4f}, y={self.gyro_offsets[1]:.4f}, z={self.gyro_offsets[2]:.4f}")
            
            # Set IMU as calibrated
            self.is_calibrated = True
            return True
            
        except Exception as e:
            logger.error(f"Error during IMU calibration: {e}", exc_info=True)
            return False 