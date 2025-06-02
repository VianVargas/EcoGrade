from PyQt5.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont
import cv2
import numpy as np
from src.utils.video_processor import VideoProcessor

class CameraWidget(QLabel):
    result_updated = pyqtSignal(dict)  # Signal to emit detection results
    
    def __init__(self, view_type="object_detection", video_processor=None, parent=None):
        super().__init__(parent)
        self.view_type = view_type
        self.setMinimumSize(200, 150)
        
        # Create glow effect
        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setBlurRadius(15)
        self.glow_effect.setColor(QColor("#14e7a1"))
        self.glow_effect.setOffset(0, 0)
        self.glow_effect.setEnabled(False)  # Initially disabled
        self.setGraphicsEffect(self.glow_effect)
        
        self.setStyleSheet("""
            QLabel {
                background-color: black;
                border-radius: 10px;
                border: 1px solid #3ac194;
            }
            QLabel:hover {
                border: 2px solid #14e7a1;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont('Segoe UI', 12, QFont.Bold))
        self.setText(f"{view_type.replace('_', ' ').title()} View")
        
        self.video_processor = video_processor  # Use the shared VideoProcessor
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)
        self.camera_started = False
        self.error_message = None
    
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
            return  # Prevent double start
        try:
            if self.video_processor:
                self.update_timer.start(33)  # ~30 FPS
                self.camera_started = True
                self.setText("")
                # Enable glow effect when camera starts
                self.glow_effect.setEnabled(True)
                # No need to call start_camera on video_processor as it's already started
            else:
                self.setText("No VideoProcessor")
        except Exception as e:
            self.error_message = str(e)
            print(f"Error starting camera widget: {self.error_message}")
            self.setText(f"Camera Error\n{self.error_message}")
    
    def update_frame(self):
        if self.video_processor and self.video_processor.latest_result is not None:
            result = self.video_processor.latest_result
            frames = result['frames']
            # Select the appropriate frame based on view type
            if self.view_type == "object_detection":
                frame = frames['model']
            elif self.view_type == "opacity_scan":
                frame = frames['opacity']
            elif self.view_type == "residue_scan":
                frame = frames['residue']
            elif self.view_type == "mask_view":
                frame = frames['mask']
            else:
                frame = frames['model']  # Default to model view
            if frame is not None and frame.size > 0:
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
                pixmap = QPixmap.fromImage(q_image)
                self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.result_updated.emit(result['data'])
            else:
                print(f"Warning: Empty frame received for {self.view_type}")
                self.setText(f"{self.view_type.replace('_', ' ').title()} View")
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap():
            self.setPixmap(self.pixmap().scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)
    
    def stop_camera(self):
        self.update_timer.stop()
        self.camera_started = False
        self.setText(f"{self.view_type.replace('_', ' ').title()} View")
        # Disable glow effect when camera stops
        self.glow_effect.setEnabled(False)
        # Clear any displayed frame
        self.clear()
        # No need to call stop_camera on video_processor as it's managed by the main view 