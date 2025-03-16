/**
 * Map Visualization for AI Smart Four-Wheel Drive Car
 * Handles 2D and 3D map rendering
 */

// Map state
let map2dCanvas;
let map3dScene, map3dCamera, map3dRenderer;
let map3dControls;
let map3dPoints = [];
let robotModel;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initMaps();
});

/**
 * Initialize maps
 */
function initMaps() {
    // Initialize 2D map
    initMap2D();
    
    // Initialize 3D map
    initMap3D();
    
    // Set up Socket.IO event for map updates
    if (socket) {
        socket.on('map_update', (data) => {
            updateMaps(data);
        });
    }
}

/**
 * Initialize 2D map
 */
function initMap2D() {
    const map2dContainer = document.getElementById('map-2d');
    if (!map2dContainer) return;
    
    // Create canvas for 2D map
    map2dCanvas = document.createElement('canvas');
    map2dCanvas.width = map2dContainer.clientWidth;
    map2dCanvas.height = map2dContainer.clientHeight;
    map2dCanvas.style.width = '100%';
    map2dCanvas.style.height = '100%';
    map2dContainer.appendChild(map2dCanvas);
    
    // Draw empty map
    const ctx = map2dCanvas.getContext('2d');
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, map2dCanvas.width, map2dCanvas.height);
    
    // Draw grid
    ctx.strokeStyle = '#ddd';
    ctx.lineWidth = 1;
    
    const gridSize = 20;
    for (let x = 0; x < map2dCanvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, map2dCanvas.height);
        ctx.stroke();
    }
    
    for (let y = 0; y < map2dCanvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(map2dCanvas.width, y);
        ctx.stroke();
    }
    
    // Draw center point
    ctx.fillStyle = '#007bff';
    ctx.beginPath();
    ctx.arc(map2dCanvas.width / 2, map2dCanvas.height / 2, 5, 0, Math.PI * 2);
    ctx.fill();
}

/**
 * Initialize 3D map
 */
function initMap3D() {
    const map3dContainer = document.getElementById('map-3d');
    if (!map3dContainer) return;
    
    // Create Three.js scene
    map3dScene = new THREE.Scene();
    map3dScene.background = new THREE.Color(0xf0f0f0);
    
    // Create camera
    map3dCamera = new THREE.PerspectiveCamera(
        75,
        map3dContainer.clientWidth / map3dContainer.clientHeight,
        0.1,
        1000
    );
    map3dCamera.position.set(0, 5, 10);
    
    // Create renderer
    map3dRenderer = new THREE.WebGLRenderer({ antialias: true });
    map3dRenderer.setSize(map3dContainer.clientWidth, map3dContainer.clientHeight);
    map3dContainer.appendChild(map3dRenderer.domElement);
    
    // Add orbit controls
    map3dControls = new THREE.OrbitControls(map3dCamera, map3dRenderer.domElement);
    map3dControls.enableDamping = true;
    map3dControls.dampingFactor = 0.25;
    
    // Add grid
    const gridHelper = new THREE.GridHelper(20, 20);
    map3dScene.add(gridHelper);
    
    // Add axes
    const axesHelper = new THREE.AxesHelper(5);
    map3dScene.add(axesHelper);
    
    // Add lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    map3dScene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
    directionalLight.position.set(0, 10, 0);
    map3dScene.add(directionalLight);
    
    // Add robot model (simple box for now)
    const robotGeometry = new THREE.BoxGeometry(1, 0.5, 1.5);
    const robotMaterial = new THREE.MeshStandardMaterial({ color: 0x007bff });
    robotModel = new THREE.Mesh(robotGeometry, robotMaterial);
    robotModel.position.y = 0.25;
    map3dScene.add(robotModel);
    
    // Start animation loop
    animate3D();
}

/**
 * Animate 3D map
 */
function animate3D() {
    requestAnimationFrame(animate3D);
    
    // Update controls
    if (map3dControls) {
        map3dControls.update();
    }
    
    // Render scene
    if (map3dRenderer && map3dScene && map3dCamera) {
        map3dRenderer.render(map3dScene, map3dCamera);
    }
}

/**
 * Update maps with new data
 * @param {Object} data - Map data
 */
function updateMaps(data) {
    console.log("收到地图数据更新:", {
        "有2D数据": !!data.map_2d, 
        "2D数据长度": data.map_2d ? data.map_2d.length : 0,
        "有3D数据": !!data.map_3d, 
        "3D点数": data.map_3d ? data.map_3d.length : 0,
        "位置": data.position,
        "方向": data.orientation
    });
    
    // Update 2D map
    if (data.map_2d && map2dCanvas) {
        console.log("正在更新2D地图，数据长度:", data.map_2d.length);
        updateMap2D(data.map_2d);
    } else {
        console.warn("跳过2D地图更新 - 无数据或无canvas元素", 
            "有数据:", !!data.map_2d, 
            "有canvas:", !!map2dCanvas);
    }
    
    // Update 3D map
    if (data.map_3d && map3dScene) {
        updateMap3D(data.map_3d);
    }
    
    // Update robot position
    if (data.position && data.orientation) {
        updateRobotPosition(data.position, data.orientation);
    }
}

/**
 * Update 2D map
 * @param {string} mapData - Base64 encoded map image
 */
function updateMap2D(mapData) {
    console.log("开始更新2D地图...", "数据长度:", mapData.length);
    
    const ctx = map2dCanvas.getContext('2d');
    
    // 首先绘制清晰的背景
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, map2dCanvas.width, map2dCanvas.height);
    
    // 检查数据是否为空
    if (!mapData || mapData.length < 100) {
        console.error("地图数据太短或为空:", mapData);
        ctx.fillStyle = 'red';
        ctx.font = '16px Arial';
        ctx.fillText('地图数据无效', 10, 30);
        return;
    }
    
    // 创建图像对象
    const img = new Image();
    
    // 添加错误处理
    img.onerror = (err) => {
        console.error("2D地图图像加载失败:", err);
        // 输出base64数据的前100个字符，帮助调试
        console.error("Base64数据前缀:", mapData.substring(0, 100) + "...");
        
        // 在出错时绘制红色边框以指示问题
        ctx.strokeStyle = 'red';
        ctx.lineWidth = 5;
        ctx.strokeRect(0, 0, map2dCanvas.width, map2dCanvas.height);
        
        // 绘制文本说明
        ctx.fillStyle = 'red';
        ctx.font = '16px Arial';
        ctx.fillText('地图加载失败', 10, 30);
        ctx.fillText('检查后端日志', 10, 50);
        
        // 尝试直接绘制一个简单的地图
        drawFallbackMap(ctx);
    };
    
    img.onload = () => {
        console.log("2D地图图像加载成功，尺寸:", img.width, "x", img.height);
        ctx.drawImage(img, 0, 0, map2dCanvas.width, map2dCanvas.height);
        
        // 在成功加载后添加时间戳
        ctx.fillStyle = 'blue';
        ctx.font = '10px Arial';
        ctx.fillText('更新: ' + new Date().toLocaleTimeString(), 5, map2dCanvas.height - 5);
    };
    
    try {
        // 确保正确的数据URL格式
        const dataUrl = `data:image/png;base64,${mapData}`;
        console.log("设置图像源...", "URL前缀:", dataUrl.substring(0, 30) + "...");
        img.src = dataUrl;
        console.log("图像源已设置");
    } catch (e) {
        console.error("设置2D地图图像源时出错:", e);
    }
}

// 添加一个后备地图绘制函数
function drawFallbackMap(ctx) {
    const width = ctx.canvas.width;
    const height = ctx.canvas.height;
    
    // 绘制网格
    ctx.strokeStyle = '#ddd';
    ctx.lineWidth = 1;
    
    const gridSize = 20;
    for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }
    
    for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }
    
    // 绘制中心点
    const centerX = width / 2;
    const centerY = height / 2;
    
    ctx.fillStyle = '#007bff';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 5, 0, Math.PI * 2);
    ctx.fill();
    
    // 绘制十字线
    ctx.strokeStyle = '#007bff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(centerX - 10, centerY);
    ctx.lineTo(centerX + 10, centerY);
    ctx.moveTo(centerX, centerY - 10);
    ctx.lineTo(centerX, centerY + 10);
    ctx.stroke();
    
    // 添加文本说明
    ctx.fillStyle = 'orange';
    ctx.font = '14px Arial';
    ctx.fillText('使用后备地图 - 图像加载失败', 10, height - 20);
}

/**
 * Update 3D map
 * @param {Array} pointsData - 3D point cloud data
 */
function updateMap3D(pointsData) {
    // Remove old points
    map3dPoints.forEach(point => {
        map3dScene.remove(point);
    });
    map3dPoints = [];
    
    // Add new points
    const pointGeometry = new THREE.SphereGeometry(0.05, 8, 8);
    
    pointsData.forEach(point => {
        const pointMaterial = new THREE.MeshBasicMaterial({
            color: new THREE.Color(
                point.r / 255,
                point.g / 255,
                point.b / 255
            )
        });
        
        const pointMesh = new THREE.Mesh(pointGeometry, pointMaterial);
        pointMesh.position.set(point.x, point.z, -point.y); // Adjust for Three.js coordinate system
        
        map3dScene.add(pointMesh);
        map3dPoints.push(pointMesh);
    });
}

/**
 * Update robot position
 * @param {Object} position - Position data
 * @param {Object} orientation - Orientation data
 */
function updateRobotPosition(position, orientation) {
    if (!robotModel) return;
    
    // Update position
    robotModel.position.x = position.x;
    robotModel.position.z = -position.y; // Adjust for Three.js coordinate system
    
    // Update orientation
    robotModel.rotation.x = THREE.MathUtils.degToRad(orientation.pitch);
    robotModel.rotation.y = THREE.MathUtils.degToRad(orientation.yaw);
    robotModel.rotation.z = THREE.MathUtils.degToRad(orientation.roll);
    
    // Update 2D map robot indicator
    if (map2dCanvas) {
        const ctx = map2dCanvas.getContext('2d');
        const centerX = map2dCanvas.width / 2 + position.x * 20; // Scale position
        const centerY = map2dCanvas.height / 2 - position.y * 20; // Scale position
        
        // Draw robot position
        ctx.fillStyle = '#007bff';
        ctx.beginPath();
        ctx.arc(centerX, centerY, 5, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw direction indicator
        const yawRad = THREE.MathUtils.degToRad(orientation.yaw);
        const dirX = centerX + Math.cos(yawRad) * 10;
        const dirY = centerY - Math.sin(yawRad) * 10;
        
        ctx.strokeStyle = '#007bff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(dirX, dirY);
        ctx.stroke();
    }
} 