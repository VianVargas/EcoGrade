from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QTimer
from src.ui.widgets.base_widgets import RoundedWidget
from src.ui.widgets.camera_widget import CameraWidget
from src.ui.widgets.detection_result_widget import DetectionResultWidget
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
from src.utils.video_processor import VideoProcessor

class MainView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_processor = VideoProcessor()  # Create one shared VideoProcessor
        self.initUI()
        
    def initUI(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)  # Make left and right panels closer
        
        # Left side - Camera feeds
        left_widget = RoundedWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Camera grid
        camera_grid = QGridLayout()
        camera_grid.setSpacing(5)
        
        # Set fixed size for camera widgets
        CAMERA_WIDTH = 320
        CAMERA_HEIGHT = 280
        
        # Create camera widgets with the shared video processor
        self.object_detection_camera = CameraWidget(view_type="object_detection", video_processor=self.video_processor)
        self.opacity_scan_camera = CameraWidget(view_type="opacity_scan", video_processor=self.video_processor)
        self.residue_scan_camera = CameraWidget(view_type="residue_scan", video_processor=self.video_processor)
        self.mask_view_camera = CameraWidget(view_type="mask_view", video_processor=self.video_processor)
        
        # Set fixed size for all camera widgets
        for camera in [self.object_detection_camera, self.opacity_scan_camera, 
                      self.residue_scan_camera, self.mask_view_camera]:
            camera.setFixedSize(CAMERA_WIDTH, CAMERA_HEIGHT)
        
        # Add cameras to grid
        camera_grid.addWidget(self.object_detection_camera, 0, 0)  # Top left
        camera_grid.addWidget(self.opacity_scan_camera, 0, 1)      # Top right
        camera_grid.addWidget(self.residue_scan_camera, 1, 0)      # Bottom left
        camera_grid.addWidget(self.mask_view_camera, 1, 1)         # Bottom right
        
        # Connect signals
        self.object_detection_camera.result_updated.connect(self.update_detection_results)
        self.opacity_scan_camera.result_updated.connect(self.update_detection_results)
        self.residue_scan_camera.result_updated.connect(self.update_detection_results)
        self.mask_view_camera.result_updated.connect(self.update_detection_results)
        
        # Start/Stop button
        self.start_btn = QPushButton("START")
        self.start_btn.setFixedSize(120, 40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        self.start_btn.clicked.connect(self.toggle_detection)
        
        left_layout.addLayout(camera_grid)
        left_layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)
        left_layout.addStretch()
        
        # Right side - Detection results
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # Detection result panels
        self.plastic_type_widget = DetectionResultWidget("WASTE TYPE:", "-")
        self.opacity_widget = DetectionResultWidget("OPACITY:", "-")
        self.contamination_widget = DetectionResultWidget("CONTAMINATION:", "0.00%")
        self.result_widget = DetectionResultWidget("RESULT:", "-")
        
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
        # Update plastic type
        waste_type = result_data.get('waste_type', '-')
        self.plastic_type_widget.update_value(waste_type)
        
        # Update opacity
        transparency = result_data.get('transparency', '-')
        self.opacity_widget.update_value(transparency)
        
        # Update contamination
        contamination = result_data.get('contamination_score', 0.0)
        contamination_text = f"{contamination:.2f}%"
        self.contamination_widget.update_value(contamination_text)
        
        # Update result
        classification = result_data.get('classification', '-')
        self.result_widget.update_value(classification)
    
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
                        font-size: 16px;
                        font-weight: bold;
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
                for cam in [self.object_detection_camera, self.opacity_scan_camera, self.residue_scan_camera, self.mask_view_camera]:
                    cam.setWindowOpacity(0.0)
                def fade_in_step(step=0):
                    if step <= 5:  # Reduce steps for faster fade-in
                        for cam in [self.object_detection_camera, self.opacity_scan_camera, self.residue_scan_camera, self.mask_view_camera]:
                            cam.setWindowOpacity(step/5)
                        QTimer.singleShot(10, lambda: fade_in_step(step+1))  # Faster interval
                fade_in_step()
                # Start camera widgets (no delay)
                self.object_detection_camera.start_camera()
                self.opacity_scan_camera.start_camera()
                self.residue_scan_camera.start_camera()
                self.mask_view_camera.start_camera()
                # Set a timer to update results after 2 seconds
                QTimer.singleShot(2000, lambda: self.update_detection_results({
                    'waste_type': 'Analyzing...',
                    'transparency': 'Analyzing...',
                    'contamination_score': 0.0,
                    'classification': 'Analyzing...'
                }))
            else:
                self.start_btn.setText("START")
                self.start_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4f46e5;
                        color: white;
                        border: none;
                        border-radius: 20px;
                        font-size: 16px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #4338ca;
                    }
                """)
                # Stop the video processor
                self.video_processor.stop()
                # Stop camera widgets (no delay)
                self.object_detection_camera.stop_camera()
                self.opacity_scan_camera.stop_camera()
                self.residue_scan_camera.stop_camera()
                self.mask_view_camera.stop_camera()
        except Exception as e:
            print(f"Error in toggle_detection: {str(e)}")
            self.start_btn.setText("START")
            # Ensure video processor is stopped
            self.video_processor.stop()
            # Stop all camera widgets
            self.object_detection_camera.stop_camera()
            self.opacity_scan_camera.stop_camera()
            self.residue_scan_camera.stop_camera()
            self.mask_view_camera.stop_camera()

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
                self.mask_view_camera.start_camera()
            else:
                self.start_btn.setText("START")
                self.object_detection_camera.stop_camera()
                self.opacity_scan_camera.stop_camera()
                self.residue_scan_camera.stop_camera()
                self.mask_view_camera.stop_camera()
        except Exception as e:
            print(f"Error in toggle_camera: {str(e)}")
            self.start_btn.setText("START")
            self.object_detection_camera.stop_camera()
            self.opacity_scan_camera.stop_camera()
            self.residue_scan_camera.stop_camera()
            self.mask_view_camera.stop_camera()

    def closeEvent(self, event):
        """Handle window close event."""
        for widget in self.camera_widgets.values():
            widget.stop_camera()
        event.accept() 