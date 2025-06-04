from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from src.ui.widgets.base_widgets import RoundedWidget
from src.ui.widgets.camera_widget import CameraWidget
from src.ui.widgets.detection_result_widget import DetectionResultWidget
from src.hardware.servo_controller import ServoController
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
from src.utils.video_processor import VideoProcessor

class MainView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_processor = VideoProcessor()  # Create one shared VideoProcessor
        self.servo_controller = ServoController()  # Initialize servo controller
        self.last_detection = {
            'waste_type': '-',
            'transparency': '-',
            'contamination_score': 0.0,
            'classification': '-'
        }
        self.initUI()
        
    def initUI(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)  # Make left and right panels closer
        
        # Left side - Camera feeds
        left_widget = RoundedWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(20, 40, 20, 20)  # Increased top margin to 40
        
        # Camera grid
        camera_grid = QGridLayout()
        camera_grid.setSpacing(15)  # Increase spacing between camera frames
        
        # Set fixed size for camera widgets
        CAMERA_WIDTH = 325
        CAMERA_HEIGHT = 260
        
        # Create camera widgets with the shared video processor
        self.object_detection_camera = CameraWidget(view_type="object_detection", video_processor=self.video_processor)
        self.opacity_scan_camera = CameraWidget(view_type="opacity_scan", video_processor=self.video_processor)
        self.residue_scan_camera = CameraWidget(view_type="residue_scan", video_processor=self.video_processor)
        self.mask_camera = CameraWidget(view_type="mask", video_processor=self.video_processor)
        
        # Set fixed size for all camera widgets
        for camera in [self.object_detection_camera, self.opacity_scan_camera, 
                      self.residue_scan_camera, self.mask_camera]:
            camera.setFixedSize(CAMERA_WIDTH, CAMERA_HEIGHT)
        
        # Add cameras to grid
        camera_grid.addWidget(self.object_detection_camera, 0, 0)  # Top left
        camera_grid.addWidget(self.opacity_scan_camera, 0, 1)      # Top right
        camera_grid.addWidget(self.residue_scan_camera, 1, 0)      # Bottom left
        camera_grid.addWidget(self.mask_camera, 1, 1)         # Bottom right
        
        # Connect signals
        self.object_detection_camera.result_updated.connect(self.update_detection_results)
        self.opacity_scan_camera.result_updated.connect(self.update_detection_results)
        self.residue_scan_camera.result_updated.connect(self.update_detection_results)
        self.mask_camera.result_updated.connect(self.update_detection_results)
        
        # Start/Stop button
        self.start_btn = QPushButton("START")
        self.start_btn.setFixedSize(120, 40)
        self.start_btn.setFont(QFont('Fredoka Medium', 14, QFont.DemiBold))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 20px;
                font-family: 'Fredoka Medium';
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        self.start_btn.clicked.connect(self.toggle_detection)
        
        left_layout.addLayout(camera_grid)
        left_layout.addSpacing(30)  # Add extra spacing before the button
        left_layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)
        left_layout.addStretch()
        
        # Right side - Detection results
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(20, 80, 20, 20)  # Increased top margin from 40 to 80
        
        # Detection result panels
        self.plastic_type_widget = DetectionResultWidget("WASTE TYPE:", "-")
        self.opacity_widget = DetectionResultWidget("OPACITY:", "-")
        self.contamination_widget = DetectionResultWidget("CONTAMINATION:", "0.00%")
        self.result_widget = DetectionResultWidget("RESULT:", "-")
        
        # Update font for all detection result widgets
        for widget in [self.plastic_type_widget, self.opacity_widget, 
                      self.contamination_widget, self.result_widget]:
            widget.set_font('Fredoka Medium')
        
        right_layout.addWidget(self.plastic_type_widget)
        right_layout.addWidget(self.opacity_widget)
        right_layout.addWidget(self.contamination_widget)
        right_layout.addWidget(self.result_widget)
        right_layout.addStretch()
        
        layout.addWidget(left_widget, 2)
        layout.addWidget(right_widget, 1)
        
        self.setLayout(layout)
    
    def update_detection_results(self, result_data):
        """Update the detection result widgets with new data"""
        classification = result_data.get('classification', '-')
        waste_type = result_data.get('waste_type', '-')
        transparency = result_data.get('transparency', '-')
        contamination = result_data.get('contamination_score', 0.0)

        # If a finalized result (not analyzing or waiting), update last_detection
        if classification not in ['No object detected', 'Waiting for: Type', 'Waiting for: Transparency', 'Waiting for: Type, Transparency', 'Analyzing...']:
            self.last_detection['waste_type'] = waste_type
            self.last_detection['transparency'] = transparency
            self.last_detection['contamination_score'] = contamination
            self.last_detection['classification'] = classification

        # If currently analyzing, show 'Analyzing...' only in the result field, but keep previous values for other fields
        if classification == 'Analyzing...':
            self.plastic_type_widget.update_value(self.last_detection['waste_type'])
            self.opacity_widget.update_value(self.last_detection['transparency'])
            contamination_text = f"{self.last_detection['contamination_score']:.2f}%"
            self.contamination_widget.update_value(contamination_text)
            self.result_widget.update_value('Analyzing...')
        else:
            # Always show the last valid detection
            self.plastic_type_widget.update_value(self.last_detection['waste_type'])
            self.opacity_widget.update_value(self.last_detection['transparency'])
            contamination_text = f"{self.last_detection['contamination_score']:.2f}%"
            self.contamination_widget.update_value(contamination_text)
            self.result_widget.update_value(self.last_detection['classification'])

        # Control servo based on classification
        if self.last_detection['classification'] in ['High Value', 'Low Value', 'Rejects']:
            if self.last_detection['classification'] == 'High Value':
                self.servo_controller.process_detection('high')
            elif self.last_detection['classification'] == 'Low Value':
                self.servo_controller.process_detection('low')
            elif self.last_detection['classification'] == 'Rejects':
                self.servo_controller.process_detection('reject')
    
    def toggle_detection(self):
        try:
            if self.start_btn.text() == "START":
                self.start_btn.setText("STOP")
                self.start_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #dc2626;
                        color: white;
                        border: none;
                        border-radius: 20px;
                        font-family: 'Fredoka Medium';
                        font-size: 16px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #b91c1c;
                    }
                """)
                # Show 'Analyzing...' in the results area
                self.plastic_type_widget.update_value("Analyzing...")
                self.opacity_widget.update_value("Analyzing...")
                self.contamination_widget.update_value("Analyzing...")
                self.result_widget.update_value("Analyzing...")
                # Initialize and start the video processor once
                self.video_processor.initialize()
                self.video_processor.start()
                # Animate camera widgets (faster fade-in)
                for cam in [self.object_detection_camera, self.opacity_scan_camera, self.residue_scan_camera, self.mask_camera]:
                    cam.setWindowOpacity(0.0)
                def fade_in_step(step=0):
                    if step <= 2:  # Reduce steps for even faster fade-in
                        for cam in [self.object_detection_camera, self.opacity_scan_camera, self.residue_scan_camera, self.mask_camera]:
                            cam.setWindowOpacity(step/2)
                        QTimer.singleShot(5, lambda: fade_in_step(step+1))  # Faster interval
                fade_in_step()
                # Start camera widgets (no delay)
                self.object_detection_camera.start_camera()
                self.opacity_scan_camera.start_camera()
                self.residue_scan_camera.start_camera()
                self.mask_camera.start_camera()
                # Set a timer to update results after 2 seconds
                QTimer.singleShot(2000, lambda: self.update_detection_results({
                    'waste_type': 'Analyzing...',
                    'transparency': 'Analyzing...',
                    'contamination_score': 0.0,
                    'classification': 'Analyzing...'
                }))
            else:
                # Stop the video processor and cameras as early as possible
                self.video_processor.stop()
                self.object_detection_camera.stop_camera()
                self.opacity_scan_camera.stop_camera()
                self.residue_scan_camera.stop_camera()
                self.mask_camera.stop_camera()
                self.start_btn.setText("START")
                self.start_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4f46e5;
                        color: white;
                        border: none;
                        border-radius: 20px;
                        font-family: 'Fredoka Medium';
                        font-size: 16px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #4338ca;
                    }
                """)
        except Exception as e:
            print(f"Error in toggle_detection: {str(e)}")
            self.start_btn.setText("START")
            # Ensure video processor is stopped
            self.video_processor.stop()
            # Stop all camera widgets
            self.object_detection_camera.stop_camera()
            self.opacity_scan_camera.stop_camera()
            self.residue_scan_camera.stop_camera()
            self.mask_camera.stop_camera()

    def update_charts(self):
        """Update the charts with new measurements."""
        if not hasattr(self, 'camera_widgets') or not self.camera_widgets['opacity'].video_processor:
            return
            
        # Get recent measurements
        measurements = self.camera_widgets['opacity'].video_processor.get_recent_measurements(limit=100)
        
        if not measurements:
            return
            
        # Update data arrays
        self.measurement_times = []
        self.opacity_values = []
        self.saturation_values = []
        
        for timestamp, mean, std_dev, brightness_percent, saturation in reversed(measurements):
            self.measurement_times.append(timestamp)
            self.opacity_values.append(mean)
            self.saturation_values.append(saturation)
            
        # Update plots
        self.opacity_curve.setData(self.opacity_values)
        self.saturation_curve.setData(self.saturation_values)
        
    def toggle_camera(self):
        try:
            if self.start_btn.text() == "START":
                self.start_btn.setText("STOP")
                self.object_detection_camera.start_camera()
                self.opacity_scan_camera.start_camera()
                self.residue_scan_camera.start_camera()
                self.mask_camera.start_camera()
            else:
                self.start_btn.setText("START")
                self.object_detection_camera.stop_camera()
                self.opacity_scan_camera.stop_camera()
                self.residue_scan_camera.stop_camera()
                self.mask_camera.stop_camera()
        except Exception as e:
            print(f"Error in toggle_camera: {str(e)}")
            self.start_btn.setText("START")
            self.object_detection_camera.stop_camera()
            self.opacity_scan_camera.stop_camera()
            self.residue_scan_camera.stop_camera()
            self.mask_camera.stop_camera()

    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up servo controller
        if hasattr(self, 'servo_controller'):
            self.servo_controller.cleanup()
        # Stop all camera widgets
        for widget in self.camera_widgets.values():
            widget.stop_camera()
        event.accept() 