from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QMessageBox, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, QSize, QRect
from PyQt5.QtGui import QFont, QPainter, QPainterPath, QIcon, QColor, QLinearGradient
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
        self.setup_ui()
        self._show_no_object_detected()
        
    def setup_ui(self):
        # Set main background color to match analytics
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: white;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Left side - Camera feeds (matches analytics layout)
        self.left_widget = QWidget()
        self.left_widget.setStyleSheet("""
            QWidget {
                background-color: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
            }
        """)
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(20, 20, 20, 20)
        self.left_layout.setSpacing(15)
        
        # Create camera layout container with analytics styling //0f172a, border: 2px solid #10b981;
        self.camera_container = QWidget()
        self.camera_container.setMinimumSize(500, 400)  # Reduced from 700, 500
        self.camera_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_container.setStyleSheet("""
            QWidget {
                background-color: #0f172a;  
                border-radius: 12px;
            }
        """)
        self.setup_camera_layout()
        
        # Button container with analytics styling
        button_container = QWidget()
        button_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button_container.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                margin: 0;
                padding: 0;
            }
        """)
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(0, 10, 0, 10)

        # Start/Stop button with analytics styling
        self.start_btn = SvgButton("")
        self.start_btn.setFixedSize(60, 60)
        self.start_btn.setFont(QFont('Inter', 14, QFont.DemiBold))
        
        # Create icons
        self.camera_off_icon = QIcon("src/ui/assets/camera-off.svg")
        self.camera_on_icon = QIcon("src/ui/assets/camera.svg")
        
        # Set initial state with analytics styling
        self.start_btn.setIcon(self.camera_off_icon)
        self.start_btn.setIconSize(QSize(32, 32))
        
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
        """)
        self.start_btn.clicked.connect(self.toggle_detection)
        
        # Camera layout change button with analytics styling
        self.layout_btn = SvgButton("Single View")
        self.layout_btn.setFixedSize(140, 60)
        self.layout_btn.setFont(QFont('Inter', 12, QFont.DemiBold))
        self.layout_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                border: 1px solid #4b5563;
                border-radius: 20px;
                font-family: 'Inter';
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4b5563;
                border: 1px solid #10b981;
            }
            QPushButton:pressed {
                background-color: #374151;
                border: 1px solid #10b981;
            }
        """)
        self.layout_btn.clicked.connect(self.toggle_camera_layout)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.layout_btn)
        button_layout.addStretch()
        
        self.left_layout.addWidget(self.camera_container, 1)
        self.left_layout.addWidget(button_container)
        
        # Right side - Detection results with analytics styling
        right_widget = QWidget()
        right_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(0, 250, 0, 200)
        
        # Detection result panels with analytics design
        self.waste_type_widget = self.create_result_panel("WASTE TYPE:", "No object detected")
        self.confidence_widget = self.create_result_panel("CONFIDENCE LEVEL:", "0.00%")
        self.contamination_widget = self.create_result_panel("CONTAMINATION:", "0.00%")
        self.classification_widget = self.create_result_panel("RESULT:", "No object detected")
        
        # Add widgets to right layout
        right_layout.addWidget(self.waste_type_widget)
        right_layout.addWidget(self.confidence_widget)
        right_layout.addWidget(self.contamination_widget)
        right_layout.addWidget(self.classification_widget)
        right_layout.addStretch()
        
        # Set layout proportions to match analytics
        layout.addWidget(self.left_widget, 3)  # Camera section takes more space
        layout.addWidget(right_widget, 1)      # Results section
        
        self.setLayout(layout)

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