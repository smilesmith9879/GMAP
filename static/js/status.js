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
    if (cpuUsage) {
        cpuUsage.textContent = `${Math.round(data.cpu_usage)}%`;
        
        // Add warning class if CPU usage is high
        if (data.cpu_usage > 80) {
            cpuUsage.classList.add('text-danger');
        } else if (data.cpu_usage > 60) {
            cpuUsage.classList.add('text-warning');
            cpuUsage.classList.remove('text-danger');
        } else {
            cpuUsage.classList.remove('text-warning', 'text-danger');
        }
    }
    
    if (memoryUsage) {
        memoryUsage.textContent = `${Math.round(data.memory_usage)}%`;
        
        // Add warning class if memory usage is high
        if (data.memory_usage > 80) {
            memoryUsage.classList.add('text-danger');
        } else if (data.memory_usage > 60) {
            memoryUsage.classList.add('text-warning');
            memoryUsage.classList.remove('text-danger');
        } else {
            memoryUsage.classList.remove('text-warning', 'text-danger');
        }
    }
    
    if (temperature) {
        temperature.textContent = `${Math.round(data.temperature)}°C`;
        
        // Add warning class if temperature is high
        if (data.temperature > 70) {
            temperature.classList.add('text-danger');
        } else if (data.temperature > 60) {
            temperature.classList.add('text-warning');
            temperature.classList.remove('text-danger');
        } else {
            temperature.classList.remove('text-warning', 'text-danger');
        }
    }
    
    // Update notifications
    if (data.notifications && data.notifications.length > 0) {
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