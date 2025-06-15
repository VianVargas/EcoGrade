from PyQt5.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont
import cv2
import numpy as np
from src.utils.video_processor import VideoProcessor
import time
import logging

logger = logging.getLogger(__name__)

class CameraWidget(QLabel):
    result_updated = pyqtSignal(dict)  # Signal to emit detection results
    
    def __init__(self, view_type="object_detection", video_processor=None, parent=None):
        super().__init__(parent)
        self.view_type = view_type
        self.setMinimumSize(640, 360)  # 16:9 aspect ratio
        self.setMaximumSize(640, 360)
        
        # Create glow effect
        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setBlurRadius(15)
        self.glow_effect.setColor(QColor("#14e7a1"))
        self.glow_effect.setOffset(0, 0)
        self.glow_effect.setEnabled(False)  # Initially disabled
        self.setGraphicsEffect(self.glow_effect)
        
        self.setStyleSheet("""
            QLabel {
                color: #3ac194;
                background-color: black;
                border-radius: 10px;
                border: 1px solid #3ac194;
            }
            QLabel:hover {
                border: 2px solid #14e7a1;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont('Fredoka', 12, QFont.Bold))
        self.setText(f"{view_type.replace('_', ' ').title()} View")
        
        # Initialize video processor
        self.video_processor = video_processor
        self.is_running = False
        self.frame_count = 0
        self.last_detection_time = None
        self.last_valid_detection = None
        self.detection_cooldown = 1.0  # 1 second cooldown between detections
        
        # Initialize timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)
        self.update_timer.setInterval(33)  # ~30 FPS
        
        # Start camera
        self.start_camera()

    def enterEvent(self, event):
        # Increase glow on hover
        self.glow_effect.setBlurRadius(25)
        self.glow_effect.setColor(QColor("#14e7a1"))
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        # Reset glow on leave
        self.glow_effect.setBlurRadius(15)
        self.glow_effect.setColor(QColor("#3ac194"))
        super().leaveEvent(event)
    
    def start_camera(self):
        """Start the camera and processing"""
        try:
            if not self.is_running:
                self.is_running = True
                self.update_timer.start()
                logger.info(f"{self.view_type} camera started")
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            self.is_running = False

    def stop_camera(self):
        """Stop the camera and processing"""
        try:
            if self.is_running:
                self.is_running = False
                self.update_timer.stop()
                logger.info(f"{self.view_type} camera stopped")
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")

    def update_frame(self):
        """Update the camera frame"""
        try:
            if not self.is_running or not self.video_processor:
                return
                
            # Get frame from video processor
            frame = self.video_processor.get_frame()
            if frame is None:
                return
                
            # Convert frame to QImage
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Scale image to fit widget while maintaining aspect ratio
            scaled_pixmap = QPixmap.fromImage(q_image).scaled(
                self.width(), self.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Update the label with the new frame
            self.setPixmap(scaled_pixmap)
            
            # Process frame for detection
            self.frame_count += 1
            if self.frame_count % 2 == 0:  # Process every other frame
                self.process_frame(frame)
                
        except Exception as e:
            logger.error(f"Error updating frame: {e}")

    def process_frame(self, frame):
        """Process frame for object detection"""
        try:
            if not self.is_running or not self.video_processor:
                return
                
            # Check cooldown
            current_time = time.time()
            if (self.last_detection_time and 
                current_time - self.last_detection_time < self.detection_cooldown):
                return
                
            # Process frame
            results = self.video_processor.process_frame(frame)
            if results:
                self.last_detection_time = current_time
                self.last_valid_detection = results
                self.result_updated.emit(results)
                
        except Exception as e:
            logger.error(f"Error processing frame: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap():
            self.setPixmap(self.pixmap().scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation))
    
    def closeEvent(self, event):
        """Handle widget close event"""
        try:
            self.stop_camera()
            event.accept()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            event.accept() 