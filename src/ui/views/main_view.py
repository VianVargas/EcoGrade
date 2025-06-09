from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QPainter, QPainterPath, QIcon
from PyQt5.QtSvg import QSvgWidget
from src.ui.widgets.base_widgets import RoundedWidget
from src.ui.widgets.camera_widget import CameraWidget
from src.ui.widgets.detection_result_widget import DetectionResultWidget
from src.utils.video_processor import VideoProcessor
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
from src.utils.app_client import app_client
import logging
import traceback

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
        
    def set_svg_path(self, svg_path):
        self.svg_path = svg_path
        self.update()

class MainView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_processor = VideoProcessor()
        self.last_classification = None
        self.last_valid_detection = None
        self.is_two_camera_layout = True  # Track current layout state
        self.is_detecting = False  # Track detection state
        self.setup_ui()
        self._show_no_object_detected()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # Left side - Camera feeds
        self.left_widget = RoundedWidget()
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(15, 35, 15, 15)
        
        # Create camera layout container with smaller size
        self.camera_container = QWidget()
        self.camera_container.setMinimumSize(700, 550)  # Reduced from 800x700 to 650x500
        self.camera_container.setMaximumSize(700, 550)  # Added maximum size constraint
        self.camera_container.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;  /* Dark gray background */
                border-radius: 10px;
            }
        """)
        self.setup_camera_layout()
        
        # Button container for Start/Stop and Change Layout buttons
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(5, 5, 5, 5)

        # Start/Stop button with icon
        self.start_btn = QPushButton()
        self.start_btn.setFixedSize(50, 50)  # Make it square for icon
        self.start_btn.setFont(QFont('Fredoka', 18, QFont.DemiBold))
        
        # Create icons
        self.camera_on_icon = QIcon("src/ui/assets/camera-off.svg")
        self.camera_off_icon = QIcon("src/ui/assets/camera.svg")
        
        # Set initial state
        self.start_btn.setIcon(self.camera_off_icon)
        self.start_btn.setIconSize(QSize(32, 32))  # Larger icon size
        
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 25px;
                font-family: 'Fredoka';
                font-size: 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        self.start_btn.clicked.connect(self.toggle_detection)
        
        # Camera layout change button
        self.layout_btn = QPushButton("Change Layout")
        self.layout_btn.setFixedSize(120, 40)
        self.layout_btn.setFont(QFont('Fredoka', 12, QFont.DemiBold))
        self.layout_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 20px;
                font-family: 'Fredoka';
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        self.layout_btn.clicked.connect(self.toggle_camera_layout)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.layout_btn)
        
        self.left_layout.addWidget(self.camera_container)
        self.left_layout.addSpacing(20)  # Reduced spacing from 30 to 20
        self.left_layout.addWidget(button_container, alignment=Qt.AlignCenter)
        self.left_layout.addStretch()
        
        # Right side - Detection results
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(20, 80, 20, 20)
        
        # Detection result panels
        self.waste_type_widget = DetectionResultWidget("WASTE TYPE:", "-")
        self.confidence_widget = DetectionResultWidget("CONFIDENCE LEVEL:", "0.00%")
        self.contamination_widget = DetectionResultWidget("CONTAMINATION:", "0.00%")
        self.classification_widget = DetectionResultWidget("RESULT:", "-")
        
        # Update font for all detection result widgets
        for widget in [self.waste_type_widget, self.confidence_widget,
                      self.contamination_widget, self.classification_widget]:
            widget.set_font('Fredoka')
            widget.title_label.setFont(QFont('Fredoka', 16, QFont.DemiBold))
            widget.value_label.setFont(QFont('Fredoka', 18, QFont.DemiBold))
        
        # Add widgets in the new sequence
        right_layout.addWidget(self.waste_type_widget)
        right_layout.addWidget(self.confidence_widget)
        right_layout.addWidget(self.contamination_widget)
        right_layout.addWidget(self.classification_widget)
        
        right_layout.addStretch()
        
        layout.addWidget(self.left_widget, 2)
        layout.addWidget(right_widget, 1)
        
        self.setLayout(layout)

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
        
        # Set smaller fixed size for camera widgets
        CAMERA_WIDTH = 300  # Reduced from 325
        CAMERA_HEIGHT = 225  # Reduced from 260
        LARGE_CAMERA_WIDTH = 600  # Reduced from 670 (2 * 280 + 20 spacing)
        SINGLE_CAMERA_SIZE = 450  # Reduced from 500
        
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
            # Two camera layout
            camera_layout = QVBoxLayout()
            camera_layout.setSpacing(2)  # Reduced from 15 to 5
            camera_layout.setContentsMargins(0, 0, 0, 0)
            
            # Set sizes for two camera layout
            self.object_detection_camera.setFixedSize(LARGE_CAMERA_WIDTH, CAMERA_HEIGHT)
            self.residue_scan_camera.setFixedSize(LARGE_CAMERA_WIDTH, CAMERA_HEIGHT)
            
            # Stack cameras vertically
            camera_layout.addWidget(self.object_detection_camera, alignment=Qt.AlignCenter)
            camera_layout.addWidget(self.residue_scan_camera, alignment=Qt.AlignCenter)
            
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
            camera_layout.setSpacing(5)  # Reduced from 15 to 5
            camera_layout.setContentsMargins(0, 0, 0, 0)
            
            # Set size for single camera layout
            self.object_detection_camera.setFixedSize(SINGLE_CAMERA_SIZE, SINGLE_CAMERA_SIZE)
            
            # Add only the main camera
            camera_layout.addWidget(self.object_detection_camera, alignment=Qt.AlignCenter)
            
            # Set the new layout
            self.camera_container.setLayout(camera_layout)
            
            # Hide other camera
            self.residue_scan_camera.hide()
            self.object_detection_camera.show()
            
            # Start only the main camera if detection is active
            if is_detecting:
                self.object_detection_camera.start_camera()
        
        # Force layout update
        self.camera_container.updateGeometry()
        self.camera_container.update()

    def toggle_camera_layout(self):
        self.is_two_camera_layout = not self.is_two_camera_layout
        self.setup_camera_layout()

    def update_detection_results(self, result_data):
        """Update the detection result widgets with new data"""
        if not result_data:
            return

        # Get current detection data
        current_waste_type = result_data.get('waste_type', 'No object detected')
        current_classification = result_data.get('classification', 'Analyzing...')
        current_contamination = result_data.get('contamination_score', 0.0)
        current_confidence = result_data.get('confidence_level', 0.0)

        # Check if this is a valid detection
        is_valid_detection = current_classification not in [
            'Analyzing...', 'No object detected',
            'Waiting for: Type', 'Waiting for: Transparency',
            'Waiting for: Type, Transparency', 'Unknown', '-'
        ]

        # If we get a valid detection, store and display it
        if is_valid_detection:
            self.last_valid_detection = {
                'waste_type': current_waste_type,
                'classification': current_classification,
                'contamination_score': current_contamination,
                'confidence_level': current_confidence
            }
            # Show the new valid detection
            self.waste_type_widget.update_value(current_waste_type)
            self.classification_widget.update_value(current_classification)
            if isinstance(current_contamination, (int, float)):
                self.contamination_widget.update_value(f"{current_contamination:.2f}%")
            else:
                self.contamination_widget.update_value("0.00%")
            # Update confidence
            if isinstance(current_confidence, (int, float)):
                self.confidence_widget.update_value(f"{current_confidence:.2f}%")
            else:
                self.confidence_widget.update_value("0.00%")
        # For all other states, show the last valid detection if it exists
        elif self.last_valid_detection:
            self.waste_type_widget.update_value(self.last_valid_detection['waste_type'])
            self.classification_widget.update_value(self.last_valid_detection['classification'])
            contamination = self.last_valid_detection['contamination_score']
            confidence = self.last_valid_detection.get('confidence_level', 0.0)
            if isinstance(contamination, (int, float)):
                self.contamination_widget.update_value(f"{contamination:.2f}%")
            else:
                self.contamination_widget.update_value("0.00%")
            # Update confidence
            if isinstance(confidence, (int, float)):
                self.confidence_widget.update_value(f"{confidence:.2f}%")
            else:
                self.confidence_widget.update_value("0.00%")
        # Only show 'No object detected' if we have no last valid detection
        else:
            self._show_no_object_detected()

        # Force immediate update of all widgets
        self.waste_type_widget.update()
        self.classification_widget.update()
        self.contamination_widget.update()
        self.confidence_widget.update()

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
                        border: none;
                        border-radius: 25px;
                        font-family: 'Fredoka';
                        font-size: 18px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #b91c1c;
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
                        background-color: #4f46e5;
                        color: white;
                        border: none;
                        border-radius: 25px;
                        font-family: 'Fredoka';
                        font-size: 16px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #4338ca;
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
        """Handle window close event."""
        # Stop all camera widgets
        self.object_detection_camera.stop_camera()
        self.residue_scan_camera.stop_camera()
        # Clean up app client
        try:
            logging.info("Cleaning up app client connection...")
            app_client.cleanup()
            logging.info("Successfully cleaned up app client connection")
        except Exception as e:
            logging.error(f"Error during app client cleanup: {str(e)}")
        event.accept()