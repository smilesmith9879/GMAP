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
    """Run background tasks for continuous updates with improved task scheduling."""
    global is_running
    frame_counter = 0
    last_log_time = time.time()
    
    # 任务执行时间追踪
    task_timestamps = {
        'sensor': 0,
        'status': 0,
        'video': 0,
        'slam': 0,
        'map': 0
    }
    
    # 创建专用线程
    status_thread = None
    video_thread = None
    slam_thread = None
    
    def status_monitor_task():
        """系统状态监控任务 - 在单独线程中运行"""
        while is_running:
            try:
                # 获取系统状态
                status = status_monitor.get_status()
                socketio.emit('status_update', status)
                
                # 1秒更新一次系统状态
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"状态监控任务错误: {e}", exc_info=True)
                time.sleep(0.5)
    
    def video_streaming_task():
        """视频流处理任务 - 在单独线程中运行"""
        nonlocal frame_counter
        last_fps_log = time.time()
        
        while is_running:
            try:
                # 获取最新视频帧
                latest_frame = camera_control.get_latest_frame()
                if latest_frame:
                    frame_counter += 1
                    
                    # 每200帧记录FPS
                    if frame_counter % 200 == 0:
                        current_time = time.time()
                        elapsed = current_time - last_fps_log
                        fps = 200 / elapsed if elapsed > 0 else 0
                        logger.info(f"视频流: 帧 #{frame_counter}, 大小: {len(latest_frame)} 字节, 平均 FPS: {fps:.2f}")
                        last_fps_log = current_time
                    
                    # 发送视频帧到前端
                    socketio.emit('video_frame', {'data': latest_frame})
                
                # 大约10帧每秒的速率
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"视频流任务错误: {e}", exc_info=True)
                time.sleep(0.5)
    
    # 启动专用线程
    logger.info("启动专用任务线程...")
    
    # 系统状态监控线程 - 高优先级
    status_thread = threading.Thread(target=status_monitor_task, daemon=True, name="StatusMonitor")
    status_thread.start()
    
    # 视频流线程 - 高优先级
    video_thread = threading.Thread(target=video_streaming_task, daemon=True, name="VideoStream")
    video_thread.start()
    
    # 主循环 - 处理传感器数据和SLAM
    while is_running:
        try:
            cycle_start = time.time()
            
            # 1. 传感器数据处理 (优先级高，每次循环)
            if cycle_start - task_timestamps['sensor'] >= 0.1:  # 10Hz
                sensor_data = sensor_fusion.get_sensor_data()
                socketio.emit('sensor_data', sensor_data)
                
                # 更新IMU数据到状态监控
                status_monitor.update_imu_data(sensor_data)
                
                task_timestamps['sensor'] = cycle_start
            
            # 2. SLAM处理 (优先级低，限制频率)
            latest_frame = camera_control.get_latest_frame()
            if latest_frame and cycle_start - task_timestamps['slam'] >= 0.5:  # 每0.5秒处理一次
                # 使用线程进行SLAM处理，避免阻塞主循环
                if slam_thread is None or not slam_thread.is_alive():
                    slam_thread = threading.Thread(
                        target=lambda: slam_processor.process_frame(latest_frame),
                        daemon=True,
                        name="SLAMProcessor"
                    )
                    slam_thread.start()
                    task_timestamps['slam'] = cycle_start
                    logger.debug(f"SLAM处理: 帧 #{frame_counter}")
            
            # 3. 地图更新 (优先级中，频率较低)
            if cycle_start - task_timestamps['map'] >= 2.0:  # 每2秒更新一次地图
                # 非阻塞方式获取地图数据
                def update_map():
                    try:
                        map_data = slam_processor.get_maps()
                        logger.info(f"地图状态: 2D={len(map_data['map_2d']) if map_data['map_2d'] else 0}字节, 3D点={len(map_data['map_3d'])}")
                        slam_processor.send_map_update()
                    except Exception as e:
                        logger.error(f"地图更新错误: {e}")
                
                threading.Thread(target=update_map, daemon=True, name="MapUpdate").start()
                task_timestamps['map'] = cycle_start
            
            # 计算循环耗时并调整睡眠时间
            cycle_time = time.time() - cycle_start
            
            # 目标循环频率50Hz (20ms)，确保响应及时
            sleep_time = max(0.02 - cycle_time, 0)
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif cycle_time > 0.1:  # 如果循环耗时超过100ms，记录警告
                logger.warning(f"主循环耗时过长: {cycle_time:.3f}s, 目标: 0.02s")
            
        except Exception as e:
            logger.error(f"主循环错误: {e}", exc_info=True)
            time.sleep(0.1)  # 出错时暂停，避免CPU占用过高
    
    logger.info("后台任务终止")

# 创建一个简单脚本测试系统信息获取
def test_system_info():
    try:
        # 测试CPU使用率
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        print(f"CPU: {cpu}%")
        
        # 测试内存使用率
        memory = psutil.virtual_memory().percent
        print(f"Memory: {memory}%")
        
        # 测试温度 (树莓派特有)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                print(f"Temperature: {temp}°C")
        except:
            print("Temperature reading failed")
            
    except Exception as e:
        print(f"Error: {e}")

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