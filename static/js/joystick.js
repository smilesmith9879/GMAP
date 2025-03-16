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
            
            // Debug
            console.log('Movement:', { x: movementX.toFixed(2), y: movementY.toFixed(2) });
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
            // Calculate normalized values (-1 to 1)
            const distance = Math.min(data.distance, 50) / 50; // Normalize to 0-1
            const angle = data.angle.radian;
            
            // Convert to x, y coordinates
            cameraX = distance * Math.cos(angle);
            cameraY = distance * Math.sin(angle);
            
            // Convert to pan/tilt angles
            // Pan: 35°-125°, default 80°
            // Tilt: 0°-85°, default 40°
            const pan = 80 + (cameraX * 45); // 80° ± 45°
            const tilt = 40 - (cameraY * 40); // 40° ± 40°
            
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
            // Keep last position, don't reset
            console.log('Camera joystick released');
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