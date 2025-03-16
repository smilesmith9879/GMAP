import time
import logging
import RPi.GPIO as GPIO
from backend.gpio_manager import get_gpio_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LOBOCamera:
    """
    LOBO机器人摄像头控制库，专门负责摄像头和云台的控制功能。
    从原始LOBOROBOT库中提取，避免与电机控制的GPIO冲突。
    """
    
    def __init__(self):
        """初始化摄像头控制模块"""
        # 确保GPIO管理器已初始化
        self.gpio_manager = get_gpio_manager()
        
        # 舵机控制引脚定义
        self.Servo_Pan_Pin = 23   # 水平方向舵机
        self.Servo_Tilt_Pin = 24  # 垂直方向舵机
        
        # 设置引脚为输出模式
        GPIO.setup(self.Servo_Pan_Pin, GPIO.OUT)
        GPIO.setup(self.Servo_Tilt_Pin, GPIO.OUT)
        
        # 设置PWM
        self.pwm_pan = GPIO.PWM(self.Servo_Pan_Pin, 50)  # 50Hz频率
        self.pwm_tilt = GPIO.PWM(self.Servo_Tilt_Pin, 50)
        
        # 启动PWM
        self.pwm_pan.start(0)
        self.pwm_tilt.start(0)
        
        # 舵机角度范围
        self.pan_min_angle = 35
        self.pan_max_angle = 125
        self.tilt_min_angle = 0
        self.tilt_max_angle = 85
        
        logger.info("LOBOCamera initialized")
    
    def __del__(self):
        """清理资源"""
        try:
            self.pwm_pan.stop()
            self.pwm_tilt.stop()
            logger.info("LOBOCamera resources released")
        except:
            pass
    
    def _angle_to_duty_cycle(self, angle):
        """
        将角度转换为PWM占空比
        
        Args:
            angle (int): 角度值 (0-180)
            
        Returns:
            float: PWM占空比值
        """
        # 舵机通常在0.5ms-2.5ms脉冲宽度下对应0-180度
        # 在50Hz下，0.5ms-2.5ms对应2.5%-12.5%占空比
        return 2.5 + (angle / 180.0) * 10.0
    
    def Servo(self, channel, angle):
        """
        控制舵机角度
        
        Args:
            channel (int): 舵机通道 (0=垂直, 1=水平)
            angle (int): 角度值
        """
        if channel == 0:  # 垂直方向舵机
            # 确保角度在有效范围内
            angle = max(self.tilt_min_angle, min(self.tilt_max_angle, angle))
            duty_cycle = self._angle_to_duty_cycle(angle)
            self.pwm_tilt.ChangeDutyCycle(duty_cycle)
            logger.debug(f"Tilt servo set to {angle} degrees")
        elif channel == 1:  # 水平方向舵机
            # 确保角度在有效范围内
            angle = max(self.pan_min_angle, min(self.pan_max_angle, angle))
            duty_cycle = self._angle_to_duty_cycle(angle)
            self.pwm_pan.ChangeDutyCycle(duty_cycle)
            logger.debug(f"Pan servo set to {angle} degrees")
    
    def set_servo_angle(self, channel, angle):
        """
        设置舵机角度（兼容原接口）
        
        Args:
            channel (int): 舵机通道 (0=水平, 1=垂直)
            angle (int): 角度值
        """
        # 注意：这里channel的定义与Servo方法相反，为了兼容原接口
        if channel == 0:  # 水平方向舵机
            self.Servo(1, angle)
        elif channel == 1:  # 垂直方向舵机
            self.Servo(0, angle)
    
    def center_servos(self):
        """将舵机居中"""
        self.Servo(0, 40)  # 垂直方向居中
        self.Servo(1, 80)  # 水平方向居中
        logger.info("Servos centered") 