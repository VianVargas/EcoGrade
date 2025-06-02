import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

class FrontPageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.initUI()
    
    def initUI(self):
        # Background setup
        self.background = QLabel(self)
        self.load_background_image()
        
        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)
        self.setLayout(layout)
        
        # ECOGRADE title
        title = QLabel("ECOGRADE")
        title_font = QFont("Intro Rust", 48, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignCenter)
        

        # Start button
        start_btn = QPushButton("START")
        start_btn.setFixedSize(200, 60)
        start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #1e40af);
                color: white;
                font-family: 'Intro Rust';
                font-size: 24px;
                font-weight: bold;
                border: none;
                border-radius: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #059669, stop:1 #1e3a8a);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #047857, stop:1 #1e3a8a);
            }
        """)
        start_btn.clicked.connect(self.go_to_main)
        
        # Add widgets to layout
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        layout.addStretch(1)
    
    def load_background_image(self):
        """Loads the image centered at original size (no scaling)."""
        image_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'START.jpg'))
        print(f"Loading image from: {image_path}")  # Debug print
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                print(f"Image loaded successfully. Size: {pixmap.width()}x{pixmap.height()}")  # Debug print
                self.background.setPixmap(pixmap)
                self.background.setScaledContents(True)  # Enable scaling
                self.background.setAlignment(Qt.AlignCenter)
                self.background.raise_()  # Ensure background is behind other widgets
                self.background.show()
                self.setStyleSheet("")
            else:
                print("Warning: Failed to load image - pixmap is null")
                self.background.hide()
                self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111827, stop:1 #1e3a8a);")
        else:
            print(f"Warning: Image not found at {image_path}")
            self.background.hide()
            self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111827, stop:1 #1e3a8a);")
    
    def go_to_main(self):
        """Switch to main view when start button is clicked"""
        if self.parent_window:
            self.parent_window.switch_view("main")

    def resizeEvent(self, event):
        """Handles window resize - re-centers image and button."""
        super().resizeEvent(event)
        if hasattr(self, 'background') and self.background.pixmap():
            # Resize the background label to fill the widget
            self.background.setGeometry(0, 0, self.width(), self.height()) 