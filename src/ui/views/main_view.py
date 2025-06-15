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
        # Create main layout
        main_layout = QHBoxLayout()  # Changed to horizontal layout
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Left side - Camera feeds
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        # Create camera layout
        camera_layout = QHBoxLayout()
        camera_layout.setSpacing(20)
        
        # Create camera widgets
        self.object_detection_camera = CameraWidget("object_detection", self.video_processor)
        self.residue_scan_camera = CameraWidget("residue_scan", self.video_processor)
        
        # Add cameras to layout
        camera_layout.addWidget(self.object_detection_camera)
        camera_layout.addWidget(self.residue_scan_camera)
        
        # Add camera layout to left layout
        left_layout.addLayout(camera_layout)
        
        # Create status layout
        status_layout = QHBoxLayout()
        status_layout.setSpacing(20)
        
        # Create status labels
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #3ac194;
                font-size: 14px;
                padding: 5px;
            }
        """)
        
        self.classification_label = QLabel("Classification: -")
        self.classification_label.setStyleSheet("""
            QLabel {
                color: #3ac194;
                font-size: 14px;
                padding: 5px;
            }
        """)
        
        # Add status labels to layout
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.classification_label)
        
        # Add status layout to left layout
        left_layout.addLayout(status_layout)
        
        # Right side - Detection results
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create result panels
        self.waste_type_widget = self.create_result_panel("WASTE TYPE:", "No object detected")
        self.confidence_widget = self.create_result_panel("CONFIDENCE LEVEL:", "0.00%")
        self.contamination_widget = self.create_result_panel("CONTAMINATION:", "0.00%")
        self.classification_widget = self.create_result_panel("RESULT:", "No object detected")
        
        # Add result panels to right layout
        right_layout.addWidget(self.waste_type_widget)
        right_layout.addWidget(self.confidence_widget)
        right_layout.addWidget(self.contamination_widget)
        right_layout.addWidget(self.classification_widget)
        right_layout.addStretch()
        
        # Add left and right widgets to main layout
        main_layout.addWidget(left_widget, 3)  # Camera section takes more space
        main_layout.addWidget(right_widget, 1)  # Results section
        
        # Set the main layout
        self.setLayout(main_layout)
        
        # Start video processing
        self.video_processor.start()
        
        # Initialize with no object detected
        self._show_no_object_detected()

    def create_result_panel(self, title, value):
        """Create a result panel with title and value"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
                padding: 10px;
            }
            QLabel {
                color: #3ac194;
                font-size: 14px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #3ac194; font-size: 16px; font-weight: bold;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        # Store the value label for later updates
        panel.value_label = value_label
        
        return panel

    def update_result_panel(self, panel, value):
        """Update the value of a result panel"""
        if hasattr(panel, 'value_label'):
            panel.value_label.setText(value)

    def _show_no_object_detected(self):
        """Show no object detected state"""
        self.update_result_panel(self.waste_type_widget, 'No object detected')
        self.update_result_panel(self.confidence_widget, '0.00%')
        self.update_result_panel(self.contamination_widget, '0.00%')
        self.update_result_panel(self.classification_widget, 'No object detected')
        self.status_label.setText("Status: Ready")
        self.classification_label.setText("Classification: -")

    def setup_camera_layout(self):
        """Setup the camera layout based on current state"""
        # Store current detection state
        is_detecting = hasattr(self, 'start_btn') and self.start_btn.icon() == self.camera_on_icon
        
        # Stop all cameras before changing layout
        if hasattr(self, 'object_detection_camera'):
            self.object_detection_camera.stop_camera()
        if hasattr(self, 'residue_scan_camera'):
            self.residue_scan_camera.stop_camera()
        
        # Clear existing layout
        if self.camera_container.layout():
            # First remove all widgets from the layout
            while self.camera_container.layout().count():
                item = self.camera_container.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            # Then delete the layout itself
            QWidget().setLayout(self.camera_container.layout())
        
        # Calculate camera sizes based on container size
        container_width = self.camera_container.width() - 40  # Account for padding
        container_height = self.camera_container.height() - 40  # Account for padding
        
        # Create camera widgets if they don't exist
        if not hasattr(self, 'object_detection_camera'):
            self.object_detection_camera = CameraWidget(view_type="object_detection", video_processor=self.video_processor)
            self.residue_scan_camera = CameraWidget(view_type="residue_scan", video_processor=self.video_processor)
            
            # Connect signals
            self.object_detection_camera.result_updated.connect(self.update_detection_results)
            self.residue_scan_camera.result_updated.connect(self.update_detection_results)
        
        # Ensure cameras are children of the container
        self.object_detection_camera.setParent(self.camera_container)
        self.residue_scan_camera.setParent(self.camera_container)
        
        if self.is_two_camera_layout:
            # Two camera layout - HORIZONTAL (left and right)
            camera_layout = QHBoxLayout()
            camera_layout.setSpacing(15)
            camera_layout.setContentsMargins(20, 20, 20, 20)
            
            # Set sizes for two camera horizontal layout
            camera_width = 510  # Half of 680
            camera_height = 600
            self.object_detection_camera.setFixedSize(camera_width, camera_height)
            self.residue_scan_camera.setFixedSize(camera_width, camera_height)
            
            # Set size policies
            self.object_detection_camera.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.residue_scan_camera.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            
            # Place cameras side by side horizontally
            camera_layout.addWidget(self.object_detection_camera)
            camera_layout.addWidget(self.residue_scan_camera)
            
            # Set the new layout
            self.camera_container.setLayout(camera_layout)
            
            # Show both cameras
            self.object_detection_camera.show()
            self.residue_scan_camera.show()
            
            # Start both cameras if detection is active
            if is_detecting:
                self.object_detection_camera.start_camera()
                self.residue_scan_camera.start_camera()
        else:
            # Single camera layout
            camera_layout = QVBoxLayout()
            camera_layout.setSpacing(5)
            camera_layout.setContentsMargins(100, 20, 20, 20)
            
            # Set size for single camera layout
            self.object_detection_camera.setFixedSize(1000, 700)  # Set specific size for main camera
            self.object_detection_camera.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Prevent resizing
            
            # Add only the main camera
            camera_layout.addWidget(self.object_detection_camera)
            
            # Set the new layout
            self.camera_container.setLayout(camera_layout)
            
            # Show only the main camera
            self.object_detection_camera.show()
            self.residue_scan_camera.hide()
            
            # Start the main camera if detection is active
            if is_detecting:
                self.object_detection_camera.start_camera()
        
        # Force layout update
        self.camera_container.updateGeometry()
        self.camera_container.update()

    def toggle_camera_layout(self):
        """Toggle between single and two camera layouts"""
        try:
            # Stop cameras and reset button state if detection is active
            if self.is_detecting:
                self.is_detecting = False
                self.start_btn.setIcon(self.camera_off_icon)
                self.start_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #374151;
                        color: white;
                        border: 1px solid #4b5563;
                        border-radius: 30px;
                        font-family: 'Inter';
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #4b5563;
                        border: 1px solid #10b981;
                    }
                    QPushButton:pressed {
                        background-color: #374151;
                        border: 1px solid #10b981;
                    }
                    QPushButton QIcon {
                        color: white;
                    }
                """)
                
                # Stop all cameras
                if hasattr(self, 'object_detection_camera'):
                    self.object_detection_camera.stop_camera()
                if hasattr(self, 'residue_scan_camera'):
                    self.residue_scan_camera.stop_camera()
            
            # Toggle layout state
            self.is_two_camera_layout = not self.is_two_camera_layout
            
            # Update button text
            self.layout_btn.setText("Split View" if self.is_two_camera_layout else "Single View")
            
            # Update camera layout
            self.setup_camera_layout()
            
        except Exception as e:
            logging.error(f"Error toggling camera layout: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Failed to change camera layout: {str(e)}")

    def update_detection_results(self, results):
        """Update detection results and control servos"""
        try:
            if not results:
                return

            # Update last detection time
            self.last_detection_time = datetime.now()
            
            # Store the results
            self.last_valid_detection = results
            
            # Update UI widgets
            self.waste_type_widget.update_value(results.get('waste_type', '-'))
            self.contamination_widget.update_value(f"{results.get('contamination_score', 0.0):.2f}%")
            self.classification_widget.update_value(results.get('classification', '-'))
            self.confidence_widget.update_value(f"{results.get('confidence_level', 0.0):.2f}%")
            
            # Control servos based on classification
            if self.servo_controller:
                classification = results.get('classification', '').lower()
                try:
                    if 'high' in classification:
                        self.servo_controller.process_command('high')
                    elif 'mix' in classification:
                        self.servo_controller.process_command('mix')
                    elif 'low' in classification:
                        self.servo_controller.process_command('low')
                    elif 'reject' in classification:
                        self.servo_controller.process_command('reject')
                except Exception as e:
                    logger.error(f"Error controlling servos: {e}")
            
        except Exception as e:
            logger.error(f"Error updating detection results: {e}")
            traceback.print_exc()

    def toggle_detection(self):
        """Toggle detection on/off"""
        try:
            if not self.is_detecting:
                # Start detection
                self.is_detecting = True
                self.start_btn.setIcon(self.camera_on_icon)
                self.start_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #dc2626;
                        color: white;
                        border: 1px solid #ef4444;
                        border-radius: 30px;
                        font-family: 'Inter';
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #b91c1c;
                        border: 1px solid #10b981;
                    }
                    QPushButton:pressed {
                        background-color: #991b1b;
                        border: 1px solid #10b981;
                    }
                    QPushButton QIcon {
                        color: white;
                    }
                """)
                
                # Show 'Analyzing...' in the results area
                self.waste_type_widget.update_value("Analyzing...")
                self.contamination_widget.update_value("Analyzing...")
                self.classification_widget.update_value("Analyzing...")
                self.confidence_widget.update_value("Analyzing...")
                
                # Initialize and start the video processor
                self.video_processor.initialize()
                self.video_processor.start()
                
                # Start camera widgets without animation
                self.object_detection_camera.start_camera()
                if self.is_two_camera_layout:
                    self.residue_scan_camera.start_camera()
                
                # Set a timer to update results
                QTimer.singleShot(500, lambda: self.update_detection_results({
                    'waste_type': 'Analyzing...',
                    'contamination_score': 0.0,
                    'classification': 'Analyzing...',
                    'confidence_level': 0.0
                }))
            else:
                # Stop detection
                self.is_detecting = False
                self.start_btn.setIcon(self.camera_off_icon)
                self.start_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #374151;
                        color: white;
                        border: 1px solid #4b5563;
                        border-radius: 30px;
                        font-family: 'Inter';
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #4b5563;
                        border: 1px solid #10b981;
                    }
                    QPushButton:pressed {
                        background-color: #374151;
                        border: 1px solid #10b981;
                    }
                    QPushButton QIcon {
                        color: white;
                    }
                """)
                
                # Stop the video processor and cameras
                self.video_processor.stop()
                self.object_detection_camera.stop_camera()
                self.residue_scan_camera.stop_camera()
                
                # Reset results
                self.waste_type_widget.update_value("-")
                self.contamination_widget.update_value("0.00%")
                self.classification_widget.update_value("-")
                self.confidence_widget.update_value("0.00%")
        except Exception as e:
            print(f"Error in toggle_detection: {str(e)}")
            self.is_detecting = False
            self.start_btn.setIcon(self.camera_off_icon)
            self.video_processor.stop()
            self.object_detection_camera.stop_camera()
            self.residue_scan_camera.stop_camera()
            
            # Reset results on error
            self.waste_type_widget.update_value("-")
            self.contamination_widget.update_value("0.00%")
            self.classification_widget.update_value("-")
            self.confidence_widget.update_value("0.00%")

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