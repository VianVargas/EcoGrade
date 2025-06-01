from PyQt5.QtWidgets import QPushButton

class SidebarButton(QPushButton):
    def __init__(self, icon_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
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
        """)
        
        # Create icon (placeholder colored rectangles since we don't have actual icon files)
        if "recycle" in icon_path.lower():
            self.setText("♻")
        elif "home" in icon_path.lower():
            self.setText("🏠")
        elif "stats" in icon_path.lower():
            self.setText("📊")
        elif "power" in icon_path.lower():
            self.setText("⏻")
        elif "info" in icon_path.lower():
            self.setText("ℹ")
        else:
            self.setText("📄") 