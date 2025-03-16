import time
import threading
import logging
import psutil
import os
import platform
import subprocess

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
        
        # IMU data
        self.imu_data = {
            'accelerometer': {'x': 0, 'y': 0, 'z': 0},
            'gyroscope': {'x': 0, 'y': 0, 'z': 0},
            'orientation': {'roll': 0, 'pitch': 0, 'yaw': 0},
            'is_calibrated': False,
            'is_available': False
        }
        
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
                'notifications': self.notifications.copy(),
                'imu_data': self.imu_data.copy()  # Add IMU data to status
            }
    
    def update_imu_data(self, imu_data):
        """
        Update IMU sensor data.
        
        Args:
            imu_data (dict): Dictionary containing IMU sensor data
        """
        with self.lock:
            self.imu_data.update(imu_data)
            
            # Add notification if IMU calibration status changes
            if imu_data.get('is_calibrated', False) and not self.imu_data.get('is_calibrated', False):
                self.add_notification("IMU calibration completed")
            elif not imu_data.get('is_calibrated', False) and self.imu_data.get('is_calibrated', False):
                self.add_notification("IMU needs calibration")
                
            # Add notification if IMU availability changes
            if imu_data.get('is_imu_available', False) and not self.imu_data.get('is_available', False):
                self.add_notification("IMU connected")
            elif not imu_data.get('is_imu_available', False) and self.imu_data.get('is_available', False):
                self.add_notification("IMU disconnected")
            
            # Update availability flag
            self.imu_data['is_available'] = imu_data.get('is_imu_available', False)
    
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
        """更新系统状态信息并记录详细日志"""
        try:
            logger.debug("开始更新系统状态")
            
            # 获取CPU使用率
            cpu_usage = self._get_cpu_usage()
            
            # 获取内存使用率
            memory_usage = self._get_memory_usage()
            
            # 获取磁盘使用率
            try:
                disk_usage = psutil.disk_usage('/').percent
                logger.debug(f"获取到磁盘使用率: {disk_usage}%")
            except Exception as e:
                logger.error(f"获取磁盘使用率失败: {e}")
                disk_usage = 0
            
            # 获取温度
            temperature = self._get_temperature()
            
            # 更新状态数据
            with self.lock:
                self.cpu_usage = cpu_usage
                self.memory_usage = memory_usage
                self.temperature = temperature
                self.disk_usage = disk_usage
            
            logger.debug(f"系统状态已更新: CPU={cpu_usage}%, 内存={memory_usage}%, 温度={temperature}°C, 磁盘={disk_usage}%")
            
        except Exception as e:
            logger.error(f"更新系统状态过程中出错: {e}", exc_info=True)
            # 确保不会因为错误而停止监控
    
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
    
    def _get_cpu_usage(self):
        """获取CPU使用率"""
        try:
            # 使用psutil获取CPU使用率
            cpu = psutil.cpu_percent(interval=0.1)
            logger.debug(f"获取到CPU使用率: {cpu}%")
            return cpu
        except Exception as e:
            logger.error(f"获取CPU使用率失败: {e}")
            return 0  # 返回0而不是None，确保前端显示有效值
    
    def _get_memory_usage(self):
        """获取内存使用率"""
        try:
            # 使用psutil获取内存使用率
            memory = psutil.virtual_memory().percent
            logger.debug(f"获取到内存使用率: {memory}%")
            return memory
        except Exception as e:
            logger.error(f"获取内存使用率失败: {e}")
            return 0  # 返回0而不是None
    
    def _get_temperature(self):
        """获取系统温度"""
        try:
            # 首先尝试通过psutil获取温度
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    # 检查不同的可能温度源
                    for name, entries in temps.items():
                        if entries:
                            # 取第一个温度值
                            temp = entries[0].current
                            logger.debug(f"通过psutil获取到温度 ({name}): {temp}°C")
                            return temp
            
            # 回退到直接读取树莓派温度文件
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read()) / 1000.0
                    logger.debug(f"通过thermal_zone0获取到温度: {temp}°C")
                    return temp
            
            # 最后尝试树莓派命令
            try:
                output = subprocess.check_output(['vcgencmd', 'measure_temp'], stderr=subprocess.STDOUT)
                temp_str = output.decode('utf-8')
                temp = float(temp_str.replace('temp=', '').replace('\'C', ''))
                logger.debug(f"通过vcgencmd获取到温度: {temp}°C")
                return temp
            except:
                logger.warning("温度获取方法都失败了，返回默认值0")
                return 0
        except Exception as e:
            logger.error(f"获取温度过程中出错: {e}")
            return 0  # 返回0而不是None 