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
        """Set up the main UI layout"""
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create camera layout
        self.camera_layout = QHBoxLayout()
        self.camera_layout.setSpacing(10)
        
        # Create camera widgets
        self.object_detection_camera = CameraWidget("object_detection", self.video_processor)
        self.residue_scan_camera = CameraWidget("residue_scan", self.video_processor)
        
        # Set fixed sizes for camera widgets
        self.object_detection_camera.setFixedSize(480, 360)
        self.residue_scan_camera.setFixedSize(480, 360)
        
        # Add cameras to layout
        self.camera_layout.addWidget(self.object_detection_camera)
        self.camera_layout.addWidget(self.residue_scan_camera)
        
        # Create control panel
        control_panel = QHBoxLayout()
        
        # Create buttons
        self.start_button = QPushButton("Start Detection")
        self.stop_button = QPushButton("Stop Detection")
        self.toggle_view_button = QPushButton("Toggle View")
        
        # Set fixed sizes for buttons
        button_width = 120
        button_height = 40
        self.start_button.setFixedSize(button_width, button_height)
        self.stop_button.setFixedSize(button_width, button_height)
        self.toggle_view_button.setFixedSize(button_width, button_height)
        
        # Add buttons to control panel
        control_panel.addWidget(self.start_button)
        control_panel.addWidget(self.stop_button)
        control_panel.addWidget(self.toggle_view_button)
        
        # Connect button signals
        self.start_button.clicked.connect(self.start_detection)
        self.stop_button.clicked.connect(self.stop_detection)
        self.toggle_view_button.clicked.connect(self.toggle_camera_view)
        
        # Add layouts to main layout
        main_layout.addLayout(self.camera_layout)
        main_layout.addLayout(control_panel)
        
        # Set the main layout
        self.setLayout(main_layout)
        
        # Initialize camera view state
        self.is_two_camera_layout = True
        self.update_camera_layout()

    def create_result_panel(self, title, value):
        """Create a result panel with analytics styling"""
        panel = QWidget()
        panel.setFixedHeight(80)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        panel.setStyleSheet("""
            QWidget {
                background-color: #1e293b;
                border-radius: 18px;
                border: 1px solid #334155;
                padding: 0px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)
        
        # Title label
        title_label = QLabel(title)
        title_label.setFont(QFont('Fredoka', 16, QFont.Normal))
        title_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                background-color: transparent;
                border: none;
                font-weight: 500;
            }
        """)
        
        # Value label
        value_label = QLabel(value)
        value_label.setFont(QFont('Inter', 16, QFont.DemiBold))
        
        # Set value color based on content
        if "No object detected" in value or value == "-":
            color = "#10b981"  # Green for no object/default state
        elif "Analyzing..." in value:
            color = "#f59e0b"  # Amber for analyzing
        elif "High Value" in value:
            color = "#10b981"  # Green for high value
        elif "Low Value" in value:
            color = "#f59e0b"  # Amber for low value
        elif "Rejected" in value:
            color = "#ef4444"  # Red for rejected
        elif "Mixed" in value:
            color = "#ef4444"  # Red for mixed
        else:
            color = "#10b981"  # Default green
            
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: transparent;
                border: none;
                font-weight: 600;
            }}
        """)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        # Store references for easy updating
        panel.title_label = title_label
        panel.value_label = value_label
        panel.update_value = lambda new_value: self.update_panel_value(panel, new_value)
        
        return panel
        
    def update_panel_value(self, panel, new_value):
        """Update panel value with appropriate styling"""
        panel.value_label.setText(str(new_value))
        
        # Update color based on content
        if "No object detected" in str(new_value) or str(new_value) == "-":
            color = "#10b981"  # Green
        elif "Analyzing..." in str(new_value):
            color = "#f59e0b"  # Yellow
        elif "High Value" in str(new_value):
            color = "#10b981"  # Green
        elif "Low Value" in str(new_value):
            color = "#3b82f6"  # Blue for low value
        elif "Rejected" in str(new_value):
            color = "#f59e0b"  # Yellow for rejected
        elif "Mixed" in str(new_value):
            color = "#ef4444"  # Red for mixed
        else:
            color = "#10b981"  # Default green
            
        panel.value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: transparent;
                border: none;
                font-weight: 600;
                font-size: 24px;
            }}
        """)

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
            camera_layout.setContentsMargins(20, 20, 20, 20)
            
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

    def _show_no_object_detected(self):
        self.waste_type_widget.update_value('No object detected')
        self.contamination_widget.update_value('0.00%')
        self.classification_widget.update_value('No object detected')
        self.confidence_widget.update_value('0.00%')

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

    def start_detection(self):
        """Start the detection process"""
        if not self.is_detecting:
            self.is_detecting = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            if hasattr(self, 'video_processor'):
                self.video_processor.start()

    def stop_detection(self):
        """Stop the detection process"""
        if self.is_detecting:
            self.is_detecting = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            if hasattr(self, 'video_processor'):
                self.video_processor.stop()

    def toggle_camera_view(self):
        """Toggle between single and dual camera views"""
        self.is_two_camera_layout = not self.is_two_camera_layout
        self.update_camera_layout()
        if self.is_two_camera_layout:
            self.toggle_view_button.setText("Single View")
        else:
            self.toggle_view_button.setText("Dual View")

    def update_camera_layout(self):
        """Update the camera layout based on current view mode"""
        # Clear existing layout
        for i in reversed(range(self.camera_layout.count())): 
            self.camera_layout.itemAt(i).widget().setParent(None)
        
        if self.is_two_camera_layout:
            # Add both cameras
            self.camera_layout.addWidget(self.object_detection_camera)
            self.camera_layout.addWidget(self.residue_scan_camera)
        else:
            # Add only object detection camera
            self.camera_layout.addWidget(self.object_detection_camera)
            self.residue_scan_camera.hide()