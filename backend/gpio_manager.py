import logging
import atexit
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GPIOManager:
    """
    GPIO资源管理器，用于确保GPIO资源的正确初始化和清理。
    这个类使用单例模式，确保在整个应用程序中只有一个实例。
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPIOManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 设置GPIO模式
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        
        # 注册退出时的清理函数
        atexit.register(self.cleanup)
        
        logger.info("GPIO Manager initialized")
        self._initialized = True
    
    def cleanup(self):
        """清理所有GPIO资源"""
        try:
            GPIO.cleanup()
            logger.info("GPIO resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up GPIO resources: {e}")

# 创建全局实例
gpio_manager = GPIOManager()

# 导出全局实例，以便其他模块可以导入
def get_gpio_manager():
    return gpio_manager 