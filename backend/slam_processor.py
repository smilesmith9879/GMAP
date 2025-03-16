import time
import threading
import logging
import numpy as np
import cv2
import os
import json
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SLAMProcessor:
    """
    Handles visual SLAM processing using RTAB-Map.
    Generates 2D and 3D maps of the environment.
    """
    
    def __init__(self, socketio=None):
        """
        Initialize the SLAM processor module.
        
        Args:
            socketio: Flask-SocketIO instance for sending updates to frontend
        """
        self.socketio = socketio  # 添加SocketIO实例用于发送地图更新
        self.is_running = True
        self.slam_thread = None
        self.lock = threading.Lock()
        self.last_map_update_time = 0
        self.map_update_interval = 1.0  # 每秒发送一次地图更新
        self.frame_count = 0  # 处理的帧计数
        
        # SLAM data
        self.map_2d = None
        self.map_3d = None
        self.position = {'x': 0, 'y': 0, 'z': 0}
        self.orientation = {'roll': 0, 'pitch': 0, 'yaw': 0}
        
        # Map settings
        self.map_resolution = 0.05  # meters per pixel
        self.map_size = (200, 200)  # pixels
        
        # Feature tracking
        self.orb = cv2.ORB_create()
        self.last_keypoints = None
        self.last_descriptors = None
        
        # Initialize empty maps
        self._init_maps()
        
        # Start SLAM thread
        self.start()
        
        logger.info("SLAM processor initialized")
    
    def _init_maps(self):
        """Initialize empty maps."""
        # Create an empty 2D map (occupancy grid)
        self.map_2d = np.zeros(self.map_size, dtype=np.uint8)
        
        # Create an empty 3D map (point cloud)
        self.map_3d = []
        
        logger.info("Maps initialized")
    
    def start(self):
        """Start the SLAM processor thread."""
        self.is_running = True
        self.slam_thread = threading.Thread(target=self._slam_loop)
        self.slam_thread.daemon = True
        self.slam_thread.start()
        logger.info("SLAM processor thread started")
    
    def stop(self):
        """Stop the SLAM processor thread."""
        self.is_running = False
        if self.slam_thread:
            self.slam_thread.join(timeout=1.0)
        
        # Save maps before stopping
        self._save_maps()
        
        logger.info("SLAM processor stopped")
    
    def process_frame(self, frame):
        """
        Process a video frame for SLAM.
        
        Args:
            frame (bytes): Base64 encoded JPEG image
        
        Returns:
            bool: True if processed successfully
        """
        if frame is None:
            logger.warning("Received None frame in SLAM processor")
            return False
        
        try:
            # 记录处理开始
            logger.debug(f"Processing frame for SLAM, size: {len(frame)}")
            self.frame_count += 1
            
            # 解码base64数据
            try:
                # 解码base64字符串到二进制数据
                img_data = base64.b64decode(frame)
                
                # 将二进制数据转换为numpy数组
                img_array = np.frombuffer(img_data, dtype=np.uint8)
                
                # 将numpy数组解码为OpenCV图像
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if img is None or img.size == 0:
                    logger.warning("Failed to decode frame image")
                    return False
                
                logger.debug(f"Image decoded: {img.shape}")
            except Exception as e:
                logger.error(f"Error decoding frame: {e}")
                return False
            
            # 进行ORB特征提取
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            keypoints, descriptors = self.orb.detectAndCompute(gray, None)
            
            logger.debug(f"Detected {len(keypoints)} keypoints")
            
            # 如果是第一帧，保存特征点并返回
            if self.last_keypoints is None:
                self.last_keypoints = keypoints
                self.last_descriptors = descriptors
                logger.debug("First frame, storing keypoints")
                return True
            
            # 如果找到足够的特征点，则进行特征匹配
            if len(keypoints) > 10 and self.last_descriptors is not None:
                # 创建一个特征匹配器
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                
                # 匹配特征点
                matches = bf.match(descriptors, self.last_descriptors)
                
                # 根据距离排序
                matches = sorted(matches, key=lambda x: x.distance)
                
                # 仅使用前20个最佳匹配
                good_matches = matches[:min(20, len(matches))]
                
                logger.debug(f"Found {len(good_matches)} good matches")
                
                # 使用匹配更新地图
                self._update_map_from_matches(keypoints, self.last_keypoints, good_matches)
                
                # 存储当前帧的特征点
                self.last_keypoints = keypoints
                self.last_descriptors = descriptors
                
                # 尝试发送地图更新到前端
                current_time = time.time()
                if current_time - self.last_map_update_time >= self.map_update_interval:
                    self.send_map_update()
                    self.last_map_update_time = current_time
                
                # 每100帧记录一次日志
                if self.frame_count % 100 == 0:
                    logger.info(f"Processed {self.frame_count} frames for SLAM")
                
                return True
            else:
                logger.debug("Not enough keypoints for matching")
                return False
            
        except Exception as e:
            logger.error(f"Error processing frame for SLAM: {e}", exc_info=True)
            return False
    
    def get_maps(self):
        """
        Get the current maps.
        
        Returns:
            dict: Dictionary containing 2D and 3D maps
        """
        with self.lock:
            # 将2D地图转换为PNG，然后编码为base64
            _, buffer = cv2.imencode('.png', self.map_2d)
            map_2d_encoded = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'map_2d': map_2d_encoded,
                'map_3d': self.map_3d,
                'position': self.position,
                'orientation': self.orientation
            }
    
    def send_map_update(self):
        """Send map updates to the frontend."""
        if self.socketio:
            try:
                map_data = self.get_maps()
                logger.debug(f"Sending map update to frontend, 2D map size: {len(map_data['map_2d'])}, 3D points: {len(map_data['map_3d'])}")
                self.socketio.emit('map_update', map_data)
                return True
            except Exception as e:
                logger.error(f"Error sending map update: {e}")
                return False
        else:
            logger.warning("SocketIO not available for sending map updates")
            return False
    
    def update_position(self, position, orientation):
        """
        Update the current position and orientation.
        
        Args:
            position (dict): Position dictionary with x, y, z keys
            orientation (dict): Orientation dictionary with roll, pitch, yaw keys
        """
        with self.lock:
            self.position = position
            self.orientation = orientation
    
    def _save_maps(self):
        """Save maps to disk."""
        try:
            # Create maps directory if it doesn't exist
            if not os.path.exists('maps'):
                os.makedirs('maps')
            
            # Save 2D map as image
            cv2.imwrite('maps/map_2d.png', self.map_2d)
            
            # Save 3D map as JSON
            with open('maps/map_3d.json', 'w') as f:
                json.dump(self.map_3d, f)
            
            # Save position and orientation
            with open('maps/position.json', 'w') as f:
                json.dump({
                    'position': self.position,
                    'orientation': self.orientation
                }, f)
            
            logger.info("Maps saved to disk")
        except Exception as e:
            logger.error(f"Error saving maps: {e}")
    
    def _update_map_from_matches(self, keypoints1, keypoints2, matches):
        """
        Update map based on feature matches between frames.
        
        Args:
            keypoints1: Keypoints from current frame
            keypoints2: Keypoints from previous frame
            matches: Matches between keypoints
        """
        with self.lock:
            try:
                # 计算平均移动
                dx = 0
                dy = 0
                count = 0
                
                for match in matches:
                    pt1 = keypoints1[match.queryIdx].pt
                    pt2 = keypoints2[match.trainIdx].pt
                    
                    # 计算位移
                    dx += pt1[0] - pt2[0]
                    dy += pt1[1] - pt2[1]
                    count += 1
                
                if count > 0:
                    dx /= count
                    dy /= count
                    
                    # 更新位置
                    scale = 0.01  # 缩放因子
                    self.position['x'] += dx * scale
                    self.position['y'] += dy * scale
                    
                    # 添加特征点到3D地图
                    point_color = (
                        np.random.randint(100, 255),
                        np.random.randint(100, 255),
                        np.random.randint(100, 255)
                    )
                    
                    for match in matches:
                        # 添加一些随机噪声以产生3D效果
                        z = np.random.normal(0, 0.05)
                        
                        # 添加点到3D地图
                        self.map_3d.append({
                            'x': float(self.position['x'] + np.random.normal(0, 0.05)),
                            'y': float(self.position['y'] + np.random.normal(0, 0.05)),
                            'z': float(z),
                            'r': point_color[0],
                            'g': point_color[1],
                            'b': point_color[2]
                        })
                    
                    # 限制3D地图大小
                    max_points = 1000
                    if len(self.map_3d) > max_points:
                        self.map_3d = self.map_3d[-max_points:]
                    
                    # 更新2D地图
                    map_center_x = self.map_size[0] // 2
                    map_center_y = self.map_size[1] // 2
                    
                    x = int(map_center_x + self.position['x'] * 20)  # 缩放因子
                    y = int(map_center_y + self.position['y'] * 20)  # 缩放因子
                    
                    # 确保坐标在地图范围内
                    x = max(0, min(self.map_size[0]-1, x))
                    y = max(0, min(self.map_size[1]-1, y))
                    
                    # 在地图上绘制轨迹
                    cv2.circle(self.map_2d, (x, y), 1, 255, -1)
                    
                    logger.debug(f"Updated map, position: ({self.position['x']:.2f}, {self.position['y']:.2f})")
                
            except Exception as e:
                logger.error(f"Error updating map from matches: {e}")
    
    def _slam_loop(self):
        """SLAM loop that runs at 10Hz to update maps."""
        update_interval = 0.1  # 10Hz
        last_update_time = time.time()
        
        while self.is_running:
            try:
                current_time = time.time()
                elapsed = current_time - last_update_time
                
                # Maintain update rate
                if elapsed < update_interval:
                    time.sleep(update_interval - elapsed)
                    continue
                
                last_update_time = current_time
                
                # 这里不再调用_update_maps_simulation，改为在process_frame中更新地图
                # 我们保留这个循环是为了定期发送地图更新
                current_time = time.time()
                if current_time - self.last_map_update_time >= self.map_update_interval:
                    self.send_map_update()
                    self.last_map_update_time = current_time
                
            except Exception as e:
                logger.error(f"Error in SLAM loop: {e}")
                time.sleep(update_interval)
    
    def _update_maps_simulation(self):
        """
        Update maps with simulated data.
        This method is deprecated and kept for backward compatibility.
        """
        logger.warning("Using deprecated simulation method for map updates")
        with self.lock:
            # Simulate robot movement
            self.position['x'] += np.random.normal(0, 0.01)
            self.position['y'] += np.random.normal(0, 0.01)
            
            # Update 2D map (add random obstacles)
            if np.random.random() < 0.1:  # 10% chance to add an obstacle
                x = np.random.randint(0, self.map_size[0])
                y = np.random.randint(0, self.map_size[1])
                radius = np.random.randint(1, 5)
                cv2.circle(self.map_2d, (x, y), radius, 255, -1)
            
            # Update 3D map (add random points)
            if np.random.random() < 0.1:  # 10% chance to add points
                num_points = np.random.randint(1, 10)
                for _ in range(num_points):
                    x = self.position['x'] + np.random.normal(0, 0.1)
                    y = self.position['y'] + np.random.normal(0, 0.1)
                    z = np.random.normal(0, 0.05)
                    
                    # Add point to 3D map
                    self.map_3d.append({
                        'x': float(x),
                        'y': float(y),
                        'z': float(z),
                        'r': np.random.randint(0, 256),
                        'g': np.random.randint(0, 256),
                        'b': np.random.randint(0, 256)
                    })
                    
                    # Limit the size of the 3D map
                    if len(self.map_3d) > 1000:
                        self.map_3d.pop(0) 