/**
 * Video Streaming for AI Smart Four-Wheel Drive Car
 * Handles video feed display and updates
 */

// DOM Elements
const videoFeed = document.getElementById('video-feed');

// Video state
let isStreaming = false;
let frameCount = 0;
let lastFpsUpdateTime = 0;
let fps = 0;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initVideoStream();
});

/**
 * Initialize video stream
 */
function initVideoStream() {
    if (!videoFeed) return;
    
    // Set up Socket.IO event for video frames
    if (socket) {
        socket.on('video_frame', (data) => {
            if (!isStreaming) {
                isStreaming = true;
                console.log('Video streaming started');
                showNotification('Video streaming started', 'success');
            }
            
            // Update video feed
            videoFeed.src = `data:image/jpeg;base64,${data}`;
            
            // Update FPS counter
            updateFps();
        });
        
        socket.on('video_error', (data) => {
            isStreaming = false;
            console.error('Video error:', data.message);
            showNotification(`Video error: ${data.message}`, 'danger');
            
            // Show no-signal image
            videoFeed.src = '/static/img/no-signal.png';
        });
    }
}

/**
 * Update FPS counter
 */
function updateFps() {
    frameCount++;
    
    const now = performance.now();
    const elapsed = now - lastFpsUpdateTime;
    
    // Update FPS every second
    if (elapsed >= 1000) {
        fps = Math.round((frameCount * 1000) / elapsed);
        
        // Update FPS display
        const fpsElement = document.getElementById('fps');
        if (fpsElement) {
            fpsElement.textContent = fps;
        }
        
        // Reset counters
        frameCount = 0;
        lastFpsUpdateTime = now;
        
        // Send FPS to server for monitoring
        if (socket && isConnected) {
            socket.emit('update_fps', { fps });
        }
    }
} 