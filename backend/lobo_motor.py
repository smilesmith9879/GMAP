import time
import logging
import RPi.GPIO as GPIO
from backend.gpio_manager import get_gpio_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LOBOMotor:
    """
    LOBO机器人电机控制库，专门负责车辆的运动控制功能。
    从原始LOBOROBOT库中提取，避免与摄像头控制的GPIO冲突。
    """
    
    def __init__(self):
        """初始化电机控制模块"""
        # 确保GPIO管理器已初始化
        self.gpio_manager = get_gpio_manager()
        
        # 电机控制引脚定义
        self.Motor_A_EN = 4
        self.Motor_B_EN = 17
        
        self.Motor_A_Pin1 = 14
        self.Motor_A_Pin2 = 15
        self.Motor_B_Pin1 = 27
        self.Motor_B_Pin2 = 18
        
        # 设置引脚为输出模式
        GPIO.setup(self.Motor_A_EN, GPIO.OUT)
        GPIO.setup(self.Motor_B_EN, GPIO.OUT)
        GPIO.setup(self.Motor_A_Pin1, GPIO.OUT)
        GPIO.setup(self.Motor_A_Pin2, GPIO.OUT)
        GPIO.setup(self.Motor_B_Pin1, GPIO.OUT)
        GPIO.setup(self.Motor_B_Pin2, GPIO.OUT)
        
        # 设置PWM
        self.pwm_A = GPIO.PWM(self.Motor_A_EN, 1000)
        self.pwm_B = GPIO.PWM(self.Motor_B_EN, 1000)
        
        # 启动PWM
        self.pwm_A.start(0)
        self.pwm_B.start(0)
        
        logger.info("LOBOMotor initialized")
    
    def __del__(self):
        """清理资源"""
        try:
            self.pwm_A.stop()
            self.pwm_B.stop()
            logger.info("LOBOMotor resources released")
        except:
            pass
    
    def MotorStop(self):
        """停止所有电机"""
        self.pwm_A.ChangeDutyCycle(0)
        self.pwm_B.ChangeDutyCycle(0)
        GPIO.output(self.Motor_A_Pin1, GPIO.LOW)
        GPIO.output(self.Motor_A_Pin2, GPIO.LOW)
        GPIO.output(self.Motor_B_Pin1, GPIO.LOW)
        GPIO.output(self.Motor_B_Pin2, GPIO.LOW)
        logger.debug("All motors stopped")
    
    def MotorRun(self, motor, direction, speed):
        """
        控制指定电机的运行
        
        Args:
            motor (int): 电机编号 (0=左侧, 1=右侧)
            direction (str): 方向 ('forward' 或 'backward')
            speed (int): 速度 (0-100)
        """
        if speed > 100:
            speed = 100
        if motor == 0:  # 左侧电机
            if direction == 'forward':
                GPIO.output(self.Motor_A_Pin1, GPIO.HIGH)
                GPIO.output(self.Motor_A_Pin2, GPIO.LOW)
                self.pwm_A.ChangeDutyCycle(speed)
            else:  # backward
                GPIO.output(self.Motor_A_Pin1, GPIO.LOW)
                GPIO.output(self.Motor_A_Pin2, GPIO.HIGH)
                self.pwm_A.ChangeDutyCycle(speed)
        else:  # 右侧电机
            if direction == 'forward':
                GPIO.output(self.Motor_B_Pin1, GPIO.HIGH)
                GPIO.output(self.Motor_B_Pin2, GPIO.LOW)
                self.pwm_B.ChangeDutyCycle(speed)
            else:  # backward
                GPIO.output(self.Motor_B_Pin1, GPIO.LOW)
                GPIO.output(self.Motor_B_Pin2, GPIO.HIGH)
                self.pwm_B.ChangeDutyCycle(speed)
        
        logger.debug(f"Motor {motor} running {direction} at speed {speed}")
    
    # 以下是原LOBOROBOT库中的运动控制函数
    def t_up(self, speed, t_time):
        """前进"""
        self.MotorRun(0, 'forward', speed)
        self.MotorRun(1, 'forward', speed)
        if t_time > 0:
            time.sleep(t_time)
            self.MotorStop()
    
    def t_down(self, speed, t_time):
        """后退"""
        self.MotorRun(0, 'backward', speed)
        self.MotorRun(1, 'backward', speed)
        if t_time > 0:
            time.sleep(t_time)
            self.MotorStop()
    
    def turnLeft(self, speed, t_time):
        """左转"""
        self.MotorRun(0, 'backward', speed)
        self.MotorRun(1, 'forward', speed)
        if t_time > 0:
            time.sleep(t_time)
            self.MotorStop()
    
    def turnRight(self, speed, t_time):
        """右转"""
        self.MotorRun(0, 'forward', speed)
        self.MotorRun(1, 'backward', speed)
        if t_time > 0:
            time.sleep(t_time)
            self.MotorStop()
    
    def t_stop(self, t_time):
        """停止"""
        self.MotorStop()
        if t_time > 0:
            time.sleep(t_time) 