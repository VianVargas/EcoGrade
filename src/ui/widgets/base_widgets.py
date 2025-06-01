from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt

class RoundedWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e3a8a;
                border-radius: 15px;
            }
        """)

class CameraWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self.setStyleSheet("""
            QLabel {
                background-color: black;
                border-radius: 10px;
                border: 2px solid #1e40af;
                color: white;
                font-size: 14px;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Camera Feed")

class DetectionResultWidget(RoundedWidget):
    def __init__(self, title, value, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 60)
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        value_widget = QWidget()
        value_widget.setStyleSheet("""
            QWidget {
                background-color: #10b981;
                border-radius: 20px;
                border: none;
            }
        """)
        value_widget.setMinimumHeight(40)
        
        value_layout = QVBoxLayout(value_widget)
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        value_label.setAlignment(Qt.AlignCenter)
        value_layout.addWidget(value_label)
        
        layout.addWidget(title_label)
        layout.addWidget(value_widget)
        layout.setSpacing(10)
        self.setLayout(layout) 