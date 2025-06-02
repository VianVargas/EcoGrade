from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtCore import QSize, Qt
import os

class SidebarButton(QPushButton):
    def __init__(self, icon_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        
        # Set up the palette for white icons
        palette = self.palette()
        palette.setColor(QPalette.ButtonText, Qt.white)
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                border: none;
                border-radius: 10px;
                margin: 5px;
                font-size: 24px;
                color: white;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:pressed {
                background-color: #1f2937;
            }
            QPushButton::icon {
                color: white;
            }
        """)
        
        # If the icon_path is a PNG or SVG file, use it as an icon
        if (icon_path.lower().endswith('.png') or icon_path.lower().endswith('.svg')) and os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setIcon(icon)
            self.setIconSize(QSize(25, 25))  # Adjust icon size to fit within the button
        else:
            self.setText("📄")  # Fallback to a file icon if no valid image is found 