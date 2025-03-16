/**
 * Joystick Controls for AI Smart Four-Wheel Drive Car
 * Uses nipplejs library for joystick functionality
 */

// Joystick instances
let movementJoystick;
let cameraJoystick;

// Joystick values
let movementX = 0;
let movementY = 0;
let cameraX = 0;
let cameraY = 0;

// 摄像头云台默认位置
const DEFAULT_PAN = 80;
const DEFAULT_TILT = 40;

// 云台自动回中的延时器
let gimbalResetTimer = null;
const GIMBAL_RESET_DELAY = 5000; // 5秒后自动回中

// Throttle values
const movementThrottleInterval = 50; // 20Hz as per project requirements
const cameraThrottleInterval = 100; // 10Hz

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initJoysticks();
});

/**
 * Initialize joysticks
 */
function initJoysticks() {
    // Movement joystick
    const movementJoystickContainer = document.getElementById('movement-joystick');
    if (movementJoystickContainer) {
        movementJoystick = nipplejs.create({
            zone: movementJoystickContainer,
            mode: 'static',
            position: { left: '50%', top: '50%' },
            color: '#28a745',
            size: 100,
            lockX: false,
            lockY: false
        });

        // Movement joystick events
        movementJoystick.on('move', throttle((evt, data) => {
            // Calculate normalized values (-1 to 1)
            const distance = Math.min(data.distance, 50) / 50; // Normalize to 0-1
            const angle = data.angle.radian;
            
            // Convert to x, y coordinates
            movementX = distance * Math.cos(angle);
            movementY = distance * Math.sin(angle);
            
            // Apply deadzone
            if (Math.abs(movementX) < 0.05) movementX = 0;
            if (Math.abs(movementY) < 0.05) movementY = 0;
            
            // Send to server
            if (socket && isConnected) {
                socket.emit('joystick_movement', { x: movementX, y: movementY });
            }
        }, movementThrottleInterval));

        movementJoystick.on('end', () => {
            // Reset values
            movementX = 0;
            movementY = 0;
            
            // Send to server
            if (socket && isConnected) {
                socket.emit('joystick_movement', { x: 0, y: 0 });
            }
            
            console.log('Movement stopped');
        });
    }

    // Camera joystick
    const cameraJoystickContainer = document.getElementById('camera-joystick');
    if (cameraJoystickContainer) {
        cameraJoystick = nipplejs.create({
            zone: cameraJoystickContainer,
            mode: 'static',
            position: { left: '50%', top: '50%' },
            color: '#fd7e14',
            size: 100,
            lockX: false,
            lockY: false
        });

        // Camera joystick events
        cameraJoystick.on('move', throttle((evt, data) => {
            // 清除回中定时器
            if (gimbalResetTimer) {
                clearTimeout(gimbalResetTimer);
                gimbalResetTimer = null;
            }
            
            // Calculate normalized values (-1 to 1)
            const distance = Math.min(data.distance, 50) / 50; // Normalize to 0-1
            const angle = data.angle.radian;
            
            // Convert to x, y coordinates
            cameraX = distance * Math.cos(angle);
            cameraY = distance * Math.sin(angle);
            
            // Convert to pan/tilt angles
            // Pan: 35°-125°, default 80°
            // Tilt: 0°-85°, default 40°
            const pan = DEFAULT_PAN + (cameraX * 45); // 80° ± 45°
            const tilt = DEFAULT_TILT - (cameraY * 40); // 40° ± 40°
            
            // Send to server
            if (socket && isConnected) {
                socket.emit('gimbal_control', { 
                    pan: Math.round(pan), 
                    tilt: Math.round(tilt) 
                });
            }
            
            // Debug
            console.log('Camera:', { pan: Math.round(pan), tilt: Math.round(tilt) });
        }, cameraThrottleInterval));

        cameraJoystick.on('end', () => {
            // 设置回中定时器
            gimbalResetTimer = setTimeout(() => {
                // 发送回中命令
                if (socket && isConnected) {
                    socket.emit('gimbal_control', { 
                        pan: DEFAULT_PAN, 
                        tilt: DEFAULT_TILT 
                    });
                }
                // 重置变量
                cameraX = 0;
                cameraY = 0;
            }, GIMBAL_RESET_DELAY);
        });
    }
}

/**
 * Throttle function to limit the rate of function calls
 * @param {Function} func - Function to throttle
 * @param {number} limit - Throttle interval in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
    let lastCall = 0;
    return function(...args) {
        const now = Date.now();
        if (now - lastCall >= limit) {
            lastCall = now;
            return func.apply(this, args);
        }
    };
} 