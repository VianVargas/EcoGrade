from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QMessageBox, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, QSize, QRect
from PyQt5.QtGui import QFont, QPainter, QPainterPath, QIcon, QColor, QLinearGradient
from PyQt5.QtSvg import QSvgWidget
from src.ui.widgets.base_widgets import RoundedWidget
from src.ui.widgets.camera_widget import CameraWidget
from src.ui.widgets.detection_result_widget import DetectionResultWidget
from src.utils.video_processor import VideoProcessor
from src.utils.servo_controller import ServoController
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
import logging
import traceback
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_view.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SvgButton(QPushButton):
    def __init__(self, text, svg_path="src/ui/assets/camera-off.svg", parent=None):
        super().__init__(text, parent)
        self.svg_path = svg_path
        
        # Add gradient colors
        self.green = QColor("#10b981")
        self.blue = QColor("#004aad")
        
        # Set up gradient animation
        self._wave_phase = 0.0
        self._hovered = False
        self.wave_timer = QTimer(self)
        self.wave_timer.timeout.connect(self.updateWave)
        self.wave_timer.setInterval(16)
        
    def set_svg_path(self, svg_path):
        self.svg_path = svg_path
        self.update()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        
        # Draw gradient background
        if self.isDown() or self._hovered:
            grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
            n_stops = 10
            phase = self._wave_phase
            for i in range(n_stops + 1):
                t = i / n_stops
                wave = 0.13 * math.sin(2 * math.pi * t * 2 + phase * 1.5)
                blend = min(max(t + wave, 0), 1)
                
                r = int(self.green.red() * (1-blend) + self.blue.red() * blend)
                g = int(self.green.green() * (1-blend) + self.blue.green() * blend)
                b = int(self.green.blue() * (1-blend) + self.blue.blue() * blend)
                grad.setColorAt(t, QColor(r, g, b))
            painter.setBrush(grad)
        else:
            painter.setBrush(QColor("#374151"))  # Default state color
        
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
        
        # Draw text
        if self.text():
            painter.setPen(QColor("white"))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignCenter, self.text())
            
        # Draw icon if present
        if not self.icon().isNull():
            icon_size = self.iconSize()
            icon_rect = QRect(
                rect.center().x() - icon_size.width() // 2,
                rect.center().y() - icon_size.height() // 2,
                icon_size.width(),
                icon_size.height()
            )
            self.icon().paint(painter, icon_rect)
        
        # Draw text if no icon
        elif self.text():
            painter.setPen(QColor("white"))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignCenter, self.text())
            
    def enterEvent(self, event):
        self._hovered = True
        self.wave_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.wave_timer.stop()
        self.update()
        super().leaveEvent(event)

    def updateWave(self):
        self._wave_phase += 0.05
        self.update()

class MainView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_processor = VideoProcessor()
        self.last_classification = None
        self.last_valid_detection = None
        self.is_two_camera_layout = False  # Start with single camera layout
        self.is_detecting = False  # Track detection state
        self.frame_skip = 2  # Reduce from 3 to 2
        self.detection_interval = 0.1  # Reduce from 0.2 to 0.1
        self.processing_size = (416, 416)  # Increase from (320, 240)
        self.update_interval = 33  # Increase from 50ms to ~30 FPS
        
        # Add cooldown tracking
        self.last_servo_command_time = 0
        self.servo_cooldown = 2.0  # 2 seconds cooldown between servo commands
        
        # Initialize servo controller
        try:
            self.servo_controller = ServoController()
            logger.info("Servo controller initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize servo controller: {e}")
            self.servo_controller = None
        
        self.setup_ui()
        self._show_no_object_detected()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Camera view layout
        camera_layout = QHBoxLayout()
        camera_layout.setSpacing(20)
        
        # Create camera widgets
        self.object_detection_camera = CameraWidget(
            view_type="object_detection",
            video_processor=self.video_processor,
            parent=self
        )
        self.residue_scan_camera = CameraWidget(
            view_type="residue_scan",
            video_processor=self.video_processor,
            parent=self
        )
        
        # Add cameras to layout
        camera_layout.addWidget(self.object_detection_camera)
        camera_layout.addWidget(self.residue_scan_camera)
        
        # Initially hide residue scan camera
        self.residue_scan_camera.hide()
        
        # Add camera layout to main layout
        main_layout.addLayout(camera_layout)
        
        # Status and controls layout
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(20)
        
        # Status display
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #3ac194;
                font-size: 14px;
                padding: 5px;
                background-color: #2d2d2d;
                border-radius: 5px;
            }
        """)
        controls_layout.addWidget(self.status_label)
        
        # Classification display
        self.classification_label = QLabel("Classification: -")
        self.classification_label.setStyleSheet("""
            QLabel {
                color: #3ac194;
                font-size: 14px;
                padding: 5px;
                background-color: #2d2d2d;
                border-radius: 5px;
            }
        """)
        controls_layout.addWidget(self.classification_label)
        
        # Add controls layout to main layout
        main_layout.addLayout(controls_layout)
        
        # Set the main layout
        self.setLayout(main_layout)
        
        # Set up update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(self.update_interval)

    def toggle_camera_view(self):
        """Toggle between single and dual camera views"""
        self.is_two_camera_layout = not self.is_two_camera_layout
        if self.is_two_camera_layout:
            self.residue_scan_camera.show()
            self.object_detection_camera.setMinimumSize(480, 360)
            self.object_detection_camera.setMaximumSize(480, 360)
            self.residue_scan_camera.setMinimumSize(480, 360)
            self.residue_scan_camera.setMaximumSize(480, 360)
        else:
            self.residue_scan_camera.hide()
            self.object_detection_camera.setMinimumSize(640, 360)
            self.object_detection_camera.setMaximumSize(640, 360)

    def update_display(self):
        """Update the display with latest detection results"""
        if not self.video_processor.latest_result:
            return
            
        result = self.video_processor.latest_result
        
        # Update object detection camera
        if 'model' in result['frames']:
            self.object_detection_camera.update_frame(result['frames']['model'])
        
        # Update residue scan camera if visible
        if self.is_two_camera_layout and 'residue' in result['frames']:
            self.residue_scan_camera.update_frame(result['frames']['residue'])
        
        # Update status and classification
        if result['data']['classification'] not in ['-', 'No object detected']:
            self.status_label.setText(f"Status: Detecting")
            self.classification_label.setText(f"Classification: {result['data']['classification']}")
        else:
            self.status_label.setText(f"Status: Ready")
            self.classification_label.setText(f"Classification: -")

    def _show_no_object_detected(self):
        """Show no object detected state"""
        self.status_label.setText("Status: Ready")
        self.classification_label.setText("Classification: -")

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Stop video processing
            if self.video_processor:
                self.video_processor.stop()
                self.video_processor.release_camera()
            
            # Clean up servo controller
            if self.servo_controller:
                self.servo_controller.cleanup()
            
            event.accept()
        except Exception as e:
            logger.error(f"Error in closeEvent: {str(e)}")
            event.accept()