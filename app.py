from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import time
import threading
import logging
from LOBOROBOT import LOBOROBOT

# Import backend modules
from backend.motor_control import MotorControl
from backend.camera_control import CameraControl
from backend.slam_processor import SLAMProcessor
from backend.sensor_fusion import SensorFusion
from backend.websocket_manager import WebSocketManager
from backend.status_monitor import StatusMonitor

# Configure logging - 设置为DEBUG级别以获取更详细的信息
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG以获取更详细的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('robot_debug.log')  # 同时将日志保存到文件
    ]
)
logger = logging.getLogger(__name__)

# 设置第三方库的日志级别较高，避免过多无关日志
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ai-smart-four-wheel-drive-car'
# 使用已验证有效的SocketIO配置
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',  # 使用threading模式增强性能
    ping_timeout=60,         # 增加ping超时到60秒
    ping_interval=25,        # 增加ping间隔到25秒
    max_http_buffer_size=10 * 1024 * 1024  # 增加HTTP缓冲区大小到10MB
)

# Initialize LOBOROBOT once to avoid GPIO conflicts
robot = LOBOROBOT()
logger.info("LOBOROBOT initialized once")

# Initialize backend modules
motor_control = MotorControl(robot=robot)
camera_control = CameraControl(robot=robot)
slam_processor = SLAMProcessor(socketio)
sensor_fusion = SensorFusion()
websocket_manager = WebSocketManager(socketio)
status_monitor = StatusMonitor()

# Global variables
connected_clients = 0
is_running = True

@app.route('/')
def index():
    """Render the main control interface."""
    return render_template('index.html')

@app.route('/mobile')
def mobile():
    """Render the mobile-optimized interface."""
    return render_template('mobile.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get the current status of the system."""
    status = status_monitor.get_status()
    return jsonify(status)

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    global connected_clients
    connected_clients += 1
    logger.info(f"Client connected. Total clients: {connected_clients}")
    # 记录连接类型
    transport = request.environ.get('HTTP_UPGRADE', '').lower() == 'websocket'
    logger.info(f"Client connection type: {'WebSocket' if transport else 'HTTP polling'}")
    emit('status', {'message': 'Connected to server', 'clients': connected_clients})
    
    # 发送一个测试帧
    latest_frame = camera_control.get_latest_frame()
    if latest_frame:
        logger.info(f"Sending initial test frame on connection, size: {len(latest_frame)} bytes")
        emit('video_frame', {'data': latest_frame})  # 使用对象格式，与background_tasks一致

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    global connected_clients
    connected_clients -= 1
    logger.info(f"Client disconnected. Total clients: {connected_clients}")

@socketio.on('joystick_movement')
def handle_joystick_movement(data):
    """Handle joystick movement for motor control."""
    x = data.get('x', 0)
    y = data.get('y', 0)
    
    # Apply deadzone
    if abs(x) < 0.05:
        x = 0
    if abs(y) < 0.05:
        y = 0
        
    motor_control.set_movement(x, y)
    
@socketio.on('gimbal_control')
def handle_gimbal_control(data):
    """Handle gimbal control for camera positioning."""
    pan = data.get('pan', 80)  # Default 80°
    tilt = data.get('tilt', 40)  # Default 40°
    
    # Ensure values are within range
    pan = max(35, min(125, pan))  # 35°-125°
    tilt = max(0, min(85, tilt))  # 0°-85°
    
    camera_control.set_gimbal_position(pan, tilt)

@socketio.on('calibrate_imu')
def handle_calibrate_imu():
    """Handle IMU calibration request."""
    sensor_fusion.calibrate_imu()
    emit('notification', {'message': 'IMU Calibration Complete'})

@socketio.on('error')
def handle_error(error):
    """Handle WebSocket errors."""
    logger.error(f"WebSocket error: {error}")

def background_tasks():
    """Run background tasks for continuous updates."""
    global is_running
    frame_counter = 0
    last_log_time = time.time()
    
    while is_running:
        try:
            cycle_start = time.time()
            
            # Update sensor data (10Hz)
            sensor_data = sensor_fusion.get_sensor_data()
            socketio.emit('sensor_data', sensor_data)
            
            # Update status
            status = status_monitor.get_status()
            socketio.emit('status_update', status)
            
            # 获取并发送视频帧
            latest_frame = camera_control.get_latest_frame()
            if latest_frame:
                frame_counter += 1
                # 每20帧记录一次日志，避免日志过多
                if frame_counter % 200 == 0:
                    current_time = time.time()
                    elapsed = current_time - last_log_time
                    fps = 200 / elapsed if elapsed > 0 else 0
                    logger.info(f"Sending video frame #{frame_counter} to clients, size: {len(latest_frame)} bytes, avg FPS: {fps:.2f}")
                    last_log_time = current_time
                
                # 发送格式保持一致 - 使用对象格式
                try:
                    socketio.emit('video_frame', {'data': latest_frame})
                except Exception as e:
                    logger.error(f"Error sending video frame: {e}")
            
            # 计算并等待剩余时间以维持10Hz频率
            cycle_time = time.time() - cycle_start
            remaining = 0.1 - cycle_time  # 目标10Hz
            
            if remaining > 0:
                time.sleep(remaining)
            else:
                # 如果循环耗时超过0.1秒，记录警告
                if cycle_time > 0.2:  # 如果延迟超过0.2秒则警告
                    logger.warning(f"Background task cycle taking too long: {cycle_time:.3f}s, target: 0.1s")
                
        except Exception as e:
            logger.error(f"Error in background tasks: {e}", exc_info=True)
            time.sleep(0.1)  # 出错时暂停一小段时间避免CPU占用过高

if __name__ == '__main__':
    # Start background thread for continuous updates
    background_thread = threading.Thread(target=background_tasks)
    background_thread.daemon = True
    background_thread.start()
    
    try:
        # Start the Flask-SocketIO server
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        is_running = False
        logger.info("Server shutting down...")
    finally:
        # Clean up resources
        motor_control.stop()
        camera_control.stop()
        slam_processor.stop()
        sensor_fusion.stop()

# 创建简单脚本测试摄像头
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print("Camera working:", ret) 