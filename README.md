# AI Smart Four-Wheel Drive Car

An intelligent 4WD robotic car with real-time control, visual SLAM, sensor fusion, and web/mobile interfaces for remote operation, mapping, and tracking.

## Features

- **Real-time Control**: Control the car's movement and camera gimbal using joystick interfaces
- **Visual SLAM**: Generate 2D and 3D maps of the environment using RTAB-Map
- **Sensor Fusion**: Combine data from IMU and camera for accurate positioning
- **Web Interface**: Responsive web interface for desktop and mobile devices
- **Diagnostics**: Monitor system status, CPU usage, memory usage, and temperature

## Architecture

### Backend (Flask, Python, Raspberry Pi 5)

- **MotorControl**: Controls the 4WD chassis using differential drive
- **CameraControl**: Handles video streaming and gimbal control
- **SLAMProcessor**: Processes visual SLAM data using RTAB-Map
- **SensorFusion**: Processes IMU data and performs sensor fusion
- **WebSocketManager**: Manages real-time communication with clients
- **StatusMonitor**: Monitors system status and performance

### Frontend

- **Desktop Interface**: Full-featured control panel with video, controls, and diagnostics
- **Mobile Interface**: Touch-optimized interface for mobile devices

### Hardware

- 4WD chassis
- USB Camera (320×240, 10 FPS)
- MPU6050 IMU
- 2-axis gimbal
- Raspberry Pi 5

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ai-smart-4wd-car.git
   cd ai-smart-4wd-car
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app.py
   ```

4. Open a web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

### Desktop Interface

- Use the left joystick to control the car's movement
- Use the right joystick to control the camera gimbal
- Click the "Stop" button to stop the car
- Click the "Center" button to center the camera
- Click the "Calibrate IMU" button to calibrate the IMU
- Toggle between 2D and 3D maps using the buttons

### Mobile Interface

- Use the left joystick to control the car's movement
- Use the right joystick to control the camera gimbal
- Use the action buttons for quick access to common functions

## Configuration

The following parameters can be configured:

- **Motion**:
  - Max speed: 60
  - Turn speed: 70% of max speed
  - Control rate: 20Hz
  - Joystick deadzone: 0.05

- **Gimbal**:
  - Pan range: 35°-125° (default 80°)
  - Tilt range: 0°-85° (default 40°)

- **Camera**:
  - Resolution: 320×240
  - Frame rate: 10 FPS
  - JPEG quality: 70%
  - Buffer size: 3 frames

- **WebSocket**:
  - Ping interval: 25s
  - Timeout: 60s
  - Max retries: 10

## License

This project is licensed under the MIT License - see the LICENSE file for details. 