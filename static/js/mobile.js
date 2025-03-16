/**
 * Mobile-specific JavaScript for AI Smart Four-Wheel Drive Car
 * Handles mobile interface functionality
 */

// DOM Elements
const mapToggleBtn = document.getElementById('map-toggle-btn');
const mapModal = document.getElementById('mapModal');

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initMobileInterface();
});

/**
 * Initialize mobile interface
 */
function initMobileInterface() {
    // Set up map toggle button
    if (mapToggleBtn && mapModal) {
        mapToggleBtn.addEventListener('click', () => {
            const bsModal = new bootstrap.Modal(mapModal);
            bsModal.show();
        });
    }
    
    // Handle orientation changes
    window.addEventListener('orientationchange', () => {
        setTimeout(() => {
            // Resize joysticks
            if (typeof movementJoystick !== 'undefined' && movementJoystick) {
                movementJoystick.destroy();
            }
            
            if (typeof cameraJoystick !== 'undefined' && cameraJoystick) {
                cameraJoystick.destroy();
            }
            
            // Reinitialize joysticks
            initJoysticks();
            
            // Resize map if visible
            if (map3dRenderer) {
                const map3dContainer = document.getElementById('map-3d');
                if (map3dContainer) {
                    map3dCamera.aspect = map3dContainer.clientWidth / map3dContainer.clientHeight;
                    map3dCamera.updateProjectionMatrix();
                    map3dRenderer.setSize(map3dContainer.clientWidth, map3dContainer.clientHeight);
                }
            }
        }, 300);
    });
    
    // Handle touch events
    document.addEventListener('touchmove', (e) => {
        // Prevent default touch behavior to avoid scrolling
        if (e.target.closest('.joystick-container')) {
            e.preventDefault();
        }
    }, { passive: false });
    
    // Handle modal events
    if (mapModal) {
        mapModal.addEventListener('shown.bs.modal', () => {
            // Resize map when modal is shown
            if (map3dRenderer) {
                const map3dContainer = document.getElementById('map-3d');
                if (map3dContainer) {
                    map3dCamera.aspect = map3dContainer.clientWidth / map3dContainer.clientHeight;
                    map3dCamera.updateProjectionMatrix();
                    map3dRenderer.setSize(map3dContainer.clientWidth, map3dContainer.clientHeight);
                }
            }
            
            // Redraw 2D map
            if (map2dCanvas) {
                const map2dContainer = document.getElementById('map-2d');
                if (map2dContainer) {
                    map2dCanvas.width = map2dContainer.clientWidth;
                    map2dCanvas.height = map2dContainer.clientHeight;
                    
                    // Redraw map
                    const ctx = map2dCanvas.getContext('2d');
                    ctx.fillStyle = '#f0f0f0';
                    ctx.fillRect(0, 0, map2dCanvas.width, map2dCanvas.height);
                }
            }
        });
    }
    
    // Disable pull-to-refresh
    document.body.addEventListener('touchstart', (e) => {
        if (e.touches.length > 1) {
            e.preventDefault();
        }
    }, { passive: false });
} 