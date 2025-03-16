/**
 * Status Monitoring for AI Smart Four-Wheel Drive Car
 * Handles status updates and display
 */

// DOM Elements
const cpuUsage = document.getElementById('cpu-usage');
const memoryUsage = document.getElementById('memory-usage');
const temperature = document.getElementById('temperature');
const uptime = document.getElementById('uptime');
const imuStatus = document.getElementById('imu-status');

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initStatusMonitoring();
});

/**
 * Initialize status monitoring
 */
function initStatusMonitoring() {
    // Set up Socket.IO event for status updates
    if (socket) {
        socket.on('status_update', (data) => {
            updateStatusDisplay(data);
        });
        
        socket.on('sensor_data', (data) => {
            updateSensorDisplay(data);
        });
        
        // Request initial status
        socket.on('connect', () => {
            setTimeout(() => {
                fetch('/api/status')
                    .then(response => response.json())
                    .then(data => {
                        updateStatusDisplay(data);
                    })
                    .catch(error => {
                        console.error('Error fetching status:', error);
                    });
            }, 1000);
        });
    }
    
    // Start uptime timer
    setInterval(updateUptimeDisplay, 1000);
}

/**
 * Update status display
 * @param {Object} data - Status data
 */
function updateStatusDisplay(data) {
    // 记录收到的状态数据
    console.log("收到状态更新:", {
        "CPU": data.cpu_usage, 
        "内存": data.memory_usage, 
        "温度": data.temperature, 
        "FPS": data.fps
    });
    
    // 确保数据有效
    if (!data) {
        console.error("收到无效的状态数据");
        return;
    }
    
    // 处理CPU使用率
    if (cpuUsage) {
        // 确保有有效值
        const cpu = typeof data.cpu_usage === 'number' ? data.cpu_usage : 0;
        cpuUsage.textContent = `${Math.round(cpu)}%`;
        
        // 添加警告类样式
        if (cpu > 80) {
            cpuUsage.classList.add('text-danger');
            cpuUsage.classList.remove('text-warning');
        } else if (cpu > 60) {
            cpuUsage.classList.add('text-warning');
            cpuUsage.classList.remove('text-danger');
        } else {
            cpuUsage.classList.remove('text-warning', 'text-danger');
        }
    }
    
    // 处理内存使用率
    if (memoryUsage) {
        // 确保有有效值
        const memory = typeof data.memory_usage === 'number' ? data.memory_usage : 0;
        memoryUsage.textContent = `${Math.round(memory)}%`;
        
        // 添加警告类样式
        if (memory > 80) {
            memoryUsage.classList.add('text-danger');
            memoryUsage.classList.remove('text-warning');
        } else if (memory > 60) {
            memoryUsage.classList.add('text-warning');
            memoryUsage.classList.remove('text-danger');
        } else {
            memoryUsage.classList.remove('text-warning', 'text-danger');
        }
    }
    
    // 处理温度
    if (temperature) {
        // 确保有有效值
        const temp = typeof data.temperature === 'number' ? data.temperature : 0;
        temperature.textContent = `${Math.round(temp)}°C`;
        
        // 添加警告类样式
        if (temp > 70) {
            temperature.classList.add('text-danger');
            temperature.classList.remove('text-warning');
        } else if (temp > 60) {
            temperature.classList.add('text-warning');
            temperature.classList.remove('text-danger');
        } else {
            temperature.classList.remove('text-warning', 'text-danger');
        }
    }
    
    // 更新FPS
    const fpsElement = document.getElementById('fps');
    if (fpsElement && typeof data.fps === 'number') {
        fpsElement.textContent = Math.round(data.fps);
    }
    
    // 更新通知
    if (data.notifications && Array.isArray(data.notifications) && data.notifications.length > 0) {
        const notificationsContainer = document.getElementById('notifications');
        if (notificationsContainer) {
            // Clear existing notifications
            notificationsContainer.innerHTML = '';
            
            // Add new notifications
            data.notifications.forEach(notification => {
                const notificationElement = document.createElement('div');
                notificationElement.className = 'alert alert-info alert-dismissible fade show';
                notificationElement.innerHTML = `
                    ${notification.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                
                notificationsContainer.appendChild(notificationElement);
            });
        }
    }
}

/**
 * Update sensor display
 * @param {Object} data - Sensor data
 */
function updateSensorDisplay(data) {
    // Update IMU status
    if (imuStatus && data.is_calibrated !== undefined) {
        imuStatus.textContent = data.is_calibrated ? 'Calibrated' : 'Not Calibrated';
        imuStatus.className = data.is_calibrated ? 'sensor-value text-success' : 'sensor-value text-warning';
    }
    
    // Update accelerometer data
    if (data.accelerometer) {
        const accelX = document.getElementById('accel-x');
        const accelY = document.getElementById('accel-y');
        const accelZ = document.getElementById('accel-z');
        
        if (accelX) accelX.textContent = data.accelerometer.x.toFixed(2);
        if (accelY) accelY.textContent = data.accelerometer.y.toFixed(2);
        if (accelZ) accelZ.textContent = data.accelerometer.z.toFixed(2);
    }
    
    // Update gyroscope data
    if (data.gyroscope) {
        const gyroX = document.getElementById('gyro-x');
        const gyroY = document.getElementById('gyro-y');
        const gyroZ = document.getElementById('gyro-z');
        
        if (gyroX) gyroX.textContent = data.gyroscope.x.toFixed(2);
        if (gyroY) gyroY.textContent = data.gyroscope.y.toFixed(2);
        if (gyroZ) gyroZ.textContent = data.gyroscope.z.toFixed(2);
    }
    
    // Update orientation data
    if (data.orientation) {
        const orientationRoll = document.getElementById('orientation-roll');
        const orientationPitch = document.getElementById('orientation-pitch');
        const orientationYaw = document.getElementById('orientation-yaw');
        
        if (orientationRoll) orientationRoll.textContent = data.orientation.roll.toFixed(2);
        if (orientationPitch) orientationPitch.textContent = data.orientation.pitch.toFixed(2);
        if (orientationYaw) orientationYaw.textContent = data.orientation.yaw.toFixed(2);
    }
}

/**
 * Update uptime display
 */
function updateUptimeDisplay() {
    if (!uptime) return;
    
    // Get current uptime from server or use client-side timer
    const currentTime = new Date().getTime();
    const startTime = window.startTime || currentTime;
    const elapsedSeconds = Math.floor((currentTime - startTime) / 1000);
    
    // Format uptime
    const hours = Math.floor(elapsedSeconds / 3600);
    const minutes = Math.floor((elapsedSeconds % 3600) / 60);
    const seconds = elapsedSeconds % 60;
    
    uptime.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
} 