from PyQt5.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont, QPainter
import cv2
import numpy as np
from src.utils.video_processor import VideoProcessor
import time

class CameraWidget(QLabel):
    result_updated = pyqtSignal(dict)  # Signal to emit detection results
    
    def __init__(self, view_type="object_detection", video_processor=None, parent=None):
        super().__init__(parent)
        self.view_type = view_type
        self.setMinimumSize(640, 360)  # 16:9 aspect ratio
        self.setMaximumSize(640, 360)  # Fixed size
        
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

        self.video_processor = video_processor
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)
        self.camera_started = False
        self.error_message = None
        self.last_update_time = 0
        self.update_interval = 33  # ~30 FPS
        self.frame_buffer = None
        self.processing_frame = False
    
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
        if self.camera_started:
            return
        try:
            if self.video_processor:
                self.clear()
                self.setText("")
                self.update()
                
                # Start camera with reduced update frequency
                self.update_timer.start(self.update_interval)
                self.camera_started = True
                self.glow_effect.setEnabled(True)
            else:
                self.setText("No VideoProcessor")
        except Exception as e:
            self.error_message = str(e)
            print(f"Error starting camera widget: {self.error_message}")
            self.setText(f"Camera Error\n{self.error_message}")
            self.camera_started = False
            self.update_timer.stop()
    
    def update_frame(self):
        """Update the camera frame"""
        if not self.video_processor or not self.video_processor.latest_result:
            return

        try:
            result = self.video_processor.latest_result
            frame = result['frames'].get(self.view_type)
            
            if frame is not None:
                # Convert frame to QImage
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                q_image = q_image.rgbSwapped()
                
                # Scale image to fit widget while maintaining aspect ratio
                scaled_pixmap = QPixmap.fromImage(q_image).scaled(
                    self.width(), self.height(),
                    Qt.KeepAspectRatio,
                    Qt.FastTransformation  # Use fast transformation instead of smooth
                )
                
                # Center the image
                x = (self.width() - scaled_pixmap.width()) // 2
                y = (self.height() - scaled_pixmap.height()) // 2
                
                # Create a new pixmap with the widget size
                final_pixmap = QPixmap(self.width(), self.height())
                final_pixmap.fill(Qt.black)
                
                # Draw the scaled image centered
                painter = QPainter(final_pixmap)
                painter.drawPixmap(x, y, scaled_pixmap)
                painter.end()
                
                self.setPixmap(final_pixmap)
                
                # Update last update time
                self.last_update_time = time.time()
                
                # Emit result if available
                if 'data' in result:
                    self.result_updated.emit(result['data'])
                    
        except Exception as e:
            print(f"Error updating frame: {str(e)}")
            self.error_message = str(e)

    def handle_empty_frame(self):
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
        self.setText(f"{self.view_type.replace('_', ' ').title()} View")
        self.update()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap():
            self.setPixmap(self.pixmap().scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation))
    
    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)
    
    def stop_camera(self):
        self.update_timer.stop()
        self.camera_started = False
        # Force text to be visible
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
        # Clear any displayed frame
        self.clear()
        # Set text after clearing
        self.setText(f"{self.view_type.replace('_', ' ').title()} View")
        # Disable glow effect when camera stops
        self.glow_effect.setEnabled(False)
        # Force update
        self.update()
        # No need to call stop_camera on video_processor as it's managed by the main view 