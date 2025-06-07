from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from src.ui.widgets.base_widgets import RoundedWidget

class DetectionResultWidget(RoundedWidget):
    def __init__(self, title, value, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 60)
        layout = QVBoxLayout()
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont('Fredoka', 16, QFont.DemiBold))
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-family: 'Fredoka';
                font-size: 16px;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # Value widget
        self.value_widget = QWidget()
        self.value_widget.setStyleSheet("""
            QWidget {
                background-color: #10b981;
                border-radius: 20px;
                border: none;
            }
        """)
        self.value_widget.setMinimumHeight(40)
        
        # Value layout
        value_layout = QVBoxLayout(self.value_widget)
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont('Fredoka', 18, QFont.DemiBold))
        self.value_label.setStyleSheet("""
            QLabel {
                color: white;
                font-family: 'Fredoka';
                font-size: 18px;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }
        """)
        self.value_label.setAlignment(Qt.AlignCenter)
        value_layout.addWidget(self.value_label)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_widget)
        layout.setSpacing(10)
        self.setLayout(layout)
    
    def update_value(self, new_value):
        """Update the displayed value"""
        self.value_label.setText(str(new_value))
    
    def set_font(self, font_family):
        """Update the font for both title and value labels"""
        self.title_label.setFont(QFont(font_family, 16, QFont.DemiBold))
        self.value_label.setFont(QFont(font_family, 18, QFont.DemiBold))
        # Update stylesheets to include font family
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-family: '{font_family}';
                font-size: 16px;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }}
        """)
        self.value_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-family: '{font_family}';
                font-size: 18px;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }}
        """) 