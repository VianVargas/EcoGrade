from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont
import numpy as np
import time

class CameraWidget(QLabel):
    result_updated = pyqtSignal(dict)
    
    def __init__(self, view_type="object_detection", video_processor=None, parent=None):
        super().__init__(parent)
        self.view_type = view_type
        self.setMinimumSize(640, 360)  # 16:9 aspect ratio
        self.setMaximumSize(640, 360)
        
        self.setStyleSheet("""
            QLabel {
                color: #3ac194;
                background-color: black;
                border-radius: 10px;
                border: 1px solid #3ac194;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont('Fredoka', 12, QFont.Bold))
        self.setText(f"{view_type.replace('_', ' ').title()} View")

        self.video_processor = video_processor
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)
        self.camera_started = False
        self.last_update_time = 0
        self.update_interval = 33  # ~30 FPS
        self.frame_buffer = None
        self.frame_count = 0
        self.fps = 0
        self.fps_update_time = time.time()
    
    def start_camera(self):
        if self.camera_started:
            return
        try:
            if self.video_processor:
                self.clear()
                self.setText("")
                self.update_timer.start(self.update_interval)
                self.camera_started = True
            else:
                self.setText("No VideoProcessor")
        except Exception as e:
            self.setText(f"Camera Error\n{str(e)}")
            self.camera_started = False
            self.update_timer.stop()
    
    def update_frame(self):
        if not self.camera_started:
            self.setText(f"{self.view_type.replace('_', ' ').title()} View")
            return

        current_time = time.time() * 1000  # Convert to milliseconds
        if current_time - self.last_update_time < self.update_interval:
            return

        if self.video_processor and self.video_processor.latest_result is not None:
            result = self.video_processor.latest_result
            frames = result['frames']
            
            # Select frame based on view type
            frame = frames.get(self.view_type, frames['model'])

            if frame is not None and frame.size > 0:
                # Convert to QImage efficiently
                height, width = frame.shape[:2]
                bytes_per_line = 3 * width
                q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                
                # Scale pixmap efficiently
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
                self.setPixmap(scaled_pixmap)
                
                # Update FPS
                self.frame_count += 1
                if time.time() - self.fps_update_time >= 1.0:
                    self.fps = self.frame_count
                    self.frame_count = 0
                    self.fps_update_time = time.time()
                
                # Emit result
                self.result_updated.emit(result['data'])
                self.last_update_time = current_time
            else:
                self.handle_empty_frame()
        else:
            self.handle_empty_frame()

    def handle_empty_frame(self):
        self.setText(f"{self.view_type.replace('_', ' ').title()} View")
    
    def stop_camera(self):
        self.update_timer.stop()
        self.camera_started = False
        self.clear()
        self.setText(f"{self.view_type.replace('_', ' ').title()} View")
        self.update() 