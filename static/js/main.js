/**
 * Main JavaScript for AI Smart Four-Wheel Drive Car
 * Handles Socket.IO connection and common functionality
 */

// Socket.IO connection
let socket;
let isConnected = false;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;

// DOM Elements
const connectionStatus = document.getElementById('connection-status');
const connectionStatusMobile = document.getElementById('connection-status-mobile');

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initSocketIO();
    setupEventListeners();
});

/**
 * Initialize Socket.IO connection
 */
function initSocketIO() {
    // Connect to Socket.IO server
    socket = io({
        reconnection: true,
        reconnectionAttempts: maxReconnectAttempts,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 60000
    });

    // Connection events
    socket.on('connect', () => {
        console.log('Connected to server');
        isConnected = true;
        reconnectAttempts = 0;
        updateConnectionStatus(true);
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        isConnected = false;
        updateConnectionStatus(false);
    });

    socket.on('reconnect_attempt', (attemptNumber) => {
        console.log(`Reconnect attempt ${attemptNumber}/${maxReconnectAttempts}`);
        reconnectAttempts = attemptNumber;
    });

    socket.on('reconnect_failed', () => {
        console.log('Failed to reconnect to server');
        showNotification('Connection failed. Please refresh the page.', 'danger');
    });

    // Server events
    socket.on('status', (data) => {
        console.log('Status update:', data);
        if (data.message) {
            showNotification(data.message, 'info');
        }
    });

    socket.on('notification', (data) => {
        console.log('Notification:', data);
        showNotification(data.message, 'warning');
    });

    socket.on('ping', () => {
        // Respond to ping with pong
        socket.emit('pong');
    });
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Calibrate IMU button
    const calibrateImuBtn = document.getElementById('calibrate-imu-btn');
    if (calibrateImuBtn) {
        calibrateImuBtn.addEventListener('click', () => {
            if (!isConnected) {
                showNotification('Not connected to server', 'danger');
                return;
            }
            
            socket.emit('calibrate_imu');
            showNotification('Calibrating IMU...', 'info');
        });
    }

    // Stop button
    const stopBtn = document.getElementById('stop-btn');
    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            if (!isConnected) {
                showNotification('Not connected to server', 'danger');
                return;
            }
            
            socket.emit('joystick_movement', { x: 0, y: 0 });
            showNotification('Stopped', 'info');
        });
    }

    // Center camera button
    const centerCameraBtn = document.getElementById('center-camera-btn');
    if (centerCameraBtn) {
        centerCameraBtn.addEventListener('click', () => {
            if (!isConnected) {
                showNotification('Not connected to server', 'danger');
                return;
            }
            
            socket.emit('gimbal_control', { pan: 80, tilt: 40 });
            showNotification('Camera centered', 'info');
        });
    }

    // Map toggle buttons
    const map2dBtn = document.getElementById('map-2d-btn');
    const map3dBtn = document.getElementById('map-3d-btn');
    const map2d = document.getElementById('map-2d');
    const map3d = document.getElementById('map-3d');

    if (map2dBtn && map3dBtn && map2d && map3d) {
        map2dBtn.addEventListener('click', () => {
            map2dBtn.classList.add('active');
            map2dBtn.classList.remove('btn-outline-primary');
            map2dBtn.classList.add('btn-primary');
            
            map3dBtn.classList.remove('active');
            map3dBtn.classList.remove('btn-primary');
            map3dBtn.classList.add('btn-outline-primary');
            
            map2d.style.display = 'block';
            map3d.style.display = 'none';
        });

        map3dBtn.addEventListener('click', () => {
            map3dBtn.classList.add('active');
            map3dBtn.classList.remove('btn-outline-primary');
            map3dBtn.classList.add('btn-primary');
            
            map2dBtn.classList.remove('active');
            map2dBtn.classList.remove('btn-primary');
            map2dBtn.classList.add('btn-outline-primary');
            
            map3d.style.display = 'block';
            map2d.style.display = 'none';
        });
    }

    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            // Page is visible, check connection
            if (socket && !isConnected) {
                socket.connect();
            }
        }
    });

    // Handle before unload
    window.addEventListener('beforeunload', () => {
        // Stop motors before leaving page
        if (socket && isConnected) {
            socket.emit('joystick_movement', { x: 0, y: 0 });
        }
    });
}

/**
 * Update connection status UI
 * @param {boolean} connected - Whether connected to server
 */
function updateConnectionStatus(connected) {
    if (connectionStatus) {
        if (connected) {
            connectionStatus.innerHTML = '<i class="fas fa-circle text-success"></i> Connected';
        } else {
            connectionStatus.innerHTML = '<i class="fas fa-circle text-danger"></i> Disconnected';
        }
    }

    if (connectionStatusMobile) {
        if (connected) {
            connectionStatusMobile.innerHTML = '<i class="fas fa-circle text-success"></i> Connected';
        } else {
            connectionStatusMobile.innerHTML = '<i class="fas fa-circle text-danger"></i> Disconnected';
        }
    }
}

/**
 * Show a notification
 * @param {string} message - Notification message
 * @param {string} type - Notification type (info, success, warning, danger)
 */
function showNotification(message, type = 'info') {
    // Desktop notifications
    const notificationsContainer = document.getElementById('notifications');
    if (notificationsContainer) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        notificationsContainer.prepend(notification);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 150);
        }, 5000);
    }
    
    // Mobile notifications
    const notificationContainer = document.getElementById('notification-container');
    if (notificationContainer) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0 mb-2`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        notificationContainer.appendChild(toast);
        
        // Initialize and show toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 5000
        });
        bsToast.show();
        
        // Remove after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    // Console log
    console.log(`Notification (${type}):`, message);
} 