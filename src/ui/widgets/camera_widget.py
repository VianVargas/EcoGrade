from PyQt5.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont
import cv2
import numpy as np
from src.utils.video_processor import VideoProcessor
import time

class CameraWidget(QLabel):
    result_updated = pyqtSignal(dict)  # Signal to emit detection results
    
    def __init__(self, view_type="object_detection", video_processor=None, parent=None):
        super().__init__(parent)
        self.view_type = view_type
        self.setFixedSize(640, 360)  # Fixed size at 640x360
        
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
        self.update_interval = 50  # Increased from 33ms to 50ms (20 FPS)
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
        if not self.camera_started:
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
            return

        current_time = time.time() * 1000  # Convert to milliseconds
        if current_time - self.last_update_time < self.update_interval:
            return

        if self.video_processor and self.video_processor.latest_result is not None:
            result = self.video_processor.latest_result
            frames = result['frames']
            
            # Select frame based on view type
            if self.view_type == "object_detection":
                frame = frames['model']
            elif self.view_type == "residue_scan":
                frame = frames['residue']
            elif self.view_type == "mask":
                frame = frames['mask']
            else:
                frame = frames['model']

            if frame is not None and frame.size > 0:
                # Cache the frame buffer
                if self.frame_buffer is None or self.frame_buffer.shape != frame.shape:
                    self.frame_buffer = np.zeros_like(frame)
                
                # Update frame buffer
                np.copyto(self.frame_buffer, frame)
                
                # Convert to QImage only when needed
                height, width, channel = self.frame_buffer.shape
                bytes_per_line = 3 * width
                q_image = QImage(self.frame_buffer.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
                
                # Scale pixmap efficiently to 80% of container size
                pixmap = QPixmap.fromImage(q_image)
                target_size = QSize(int(self.width() * 0.9), int(self.height() * 0.9))
                scaled_pixmap = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.FastTransformation)
                self.setPixmap(scaled_pixmap)
                
                # Emit result
                self.result_updated.emit(result['data'])
                self.last_update_time = current_time
            else:
                self.handle_empty_frame()
        else:
            self.handle_empty_frame()

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