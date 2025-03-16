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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ai-smart-four-wheel-drive-car'
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Initialize LOBOROBOT once
robot = LOBOROBOT()
logger.info("LOBOROBOT initialized once for all modules")

# Initialize backend modules with shared robot instance
motor_control = MotorControl(robot=robot)
camera_control = CameraControl(robot=robot)
slam_processor = SLAMProcessor()
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
    emit('status', {'message': 'Connected to server', 'clients': connected_clients})

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

def background_tasks():
    """Run background tasks for continuous updates."""
    global is_running
    
    while is_running:
        # Update sensor data (10Hz)
        sensor_data = sensor_fusion.get_sensor_data()
        socketio.emit('sensor_data', sensor_data)
        
        # Update status
        status = status_monitor.get_status()
        socketio.emit('status_update', status)
        
        # Sleep to maintain update rate
        time.sleep(0.1)  # 10Hz

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
        # No need to explicitly stop the robot as it's handled by the modules 