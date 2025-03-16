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
    console.log('DOM fully loaded and parsed, initializing video stream');
});

/**
 * Initialize video stream
 */
function initVideoStream() {
    if (!videoFeed) {
        console.error('Video feed element not found');
        return;
    }
    
    console.log('Setting up video stream with Socket.IO');
    // Set up Socket.IO event for video frames
    if (socket) {
        socket.on('video_frame', (data) => {
            console.log('Received video frame, type:', typeof data, 'length:', typeof data === 'string' ? data.length : (data.data ? data.data.length : 'N/A'));
            
            // 始终设置isStreaming为true并更新视频
            isStreaming = true;
            
            try {
                // 处理两种可能的数据格式
                if (typeof data === 'string') {
                    // 正确格式：不要在data URI中添加查询参数
                    videoFeed.src = `data:image/jpeg;base64,${data}`;
                    console.log('Updated video with string data');
                } else if (data && data.data) {
                    // 正确格式：不要在data URI中添加查询参数
                    videoFeed.src = `data:image/jpeg;base64,${data.data}`;
                    console.log('Updated video with object data');
                } else {
                    console.error('Invalid video data format:', data);
                }
                
                // 防止缓存的另一种方法 - 通过添加一个随机属性
                videoFeed.setAttribute('data-timestamp', new Date().getTime());
                
                // 强制重绘视频元素
                videoFeed.style.display = 'none';
                videoFeed.offsetHeight; // 触发重排
                videoFeed.style.display = 'block';
                
                updateFps();
            } catch (e) {
                console.error('Error updating video feed:', e);
                videoFeed.src = '/static/img/no-signal.png';
            }
        });
        
        socket.on('video_error', (data) => {
            isStreaming = false;
            console.error('Video error:', data.message);
            showNotification(`Video error: ${data.message}`, 'danger');
            
            // Show no-signal image
            videoFeed.src = '/static/img/no-signal.png';
        });

        // 添加断开连接处理
        socket.on('disconnect', () => {
            console.error('WebSocket disconnected!');
            isStreaming = false;
            videoFeed.src = '/static/img/no-signal.png';
            
            // 尝试重新连接
            setTimeout(() => {
                console.log('Attempting to reconnect...');
                socket.connect();
            }, 1000);
        });

        // 添加重连处理
        socket.on('reconnect', () => {
            console.log('WebSocket reconnected!');
        });
    } else {
        console.error('Socket.IO not initialized');
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