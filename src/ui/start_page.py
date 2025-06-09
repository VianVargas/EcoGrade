from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPixmap, QPainter, QLinearGradient, QColor

class StartPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.initUI()
    
    def initUI(self):
        # Set background gradient
        self.setAutoFillBackground(True)
        p = self.palette()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(30, 58, 138))  # Dark blue
        gradient.setColorAt(1, QColor(16, 185, 129))  # Teal
        p.setBrush(self.backgroundRole(), gradient)
        self.setPalette(p)
        
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
        
        # Subtitle lines
        subtitle_lines = [
            "LEVERAGING CONVOLUTIONAL NEURAL NETWORKS AND",
            "MULTI-DECISION ANALYSIS FOR ADVANCED REAL-TIME",
            "DETECTION AND QUALITY ASSESSMENT OF",
            "NON-BIODEGRADABLE WASTE MATERIALS"
        ]
        
        # Subtitle layout
        subtitle_layout = QVBoxLayout()
        subtitle_layout.setSpacing(10)
        
        subtitle_font = QFont("Intro Rust", 14)
        for line in subtitle_lines:
            label = QLabel(line)
            label.setFont(subtitle_font)
            label.setStyleSheet("color: white;")
            label.setAlignment(Qt.AlignCenter)
            subtitle_layout.addWidget(label)
        
        # Start button
        start_btn = QPushButton("START")
        start_btn.setFixedSize(200, 60)
        start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #16324b);
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
        layout.addLayout(subtitle_layout)
        layout.addStretch(1)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        layout.addStretch(1)
    
    def go_to_main(self):
        """Switch to main view when start button is clicked"""
        if self.parent_window:
            self.parent_window.switch_view("main")

    def paintEvent(self, event):
        """Ensure gradient background scales with window"""
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(30, 58, 138))
        gradient.setColorAt(1, QColor(16, 185, 129))
        painter.fillRect(self.rect(), gradient)
        super().paintEvent(event) 