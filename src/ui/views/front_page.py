import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QColor, QPalette, QLinearGradient, QBrush
from PyQt5.QtSvg import QSvgWidget

class FrontPageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._bg_phase = 0.0  # For background animation
        self.initUI()
        self.initAnimations()
    
    def initUI(self):
        
        # Load Fredoka Medium font if available
        font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/fonts/static/Fredoka-Medium.ttf'))
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)
        
        # Background setup
        self.background = QLabel(self)
        self.load_background_image()
        
        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addStretch(1)  # Top stretch for vertical centering

        # Centered logo and ECOGRADE title
        row_layout = QHBoxLayout()
        row_layout.setAlignment(Qt.AlignCenter)
        row_layout.setSpacing(40)

        # Logo (LOGO.png)
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LOGO.png'))
        logo_label = QLabel()
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            logo_label.setPixmap(logo_pixmap.scaledToHeight(180, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
            row_layout.addWidget(logo_label)

        # ECOGRADE colored title
        self.title = QLabel()
        title_font = QFont("Fredoka Medium", 96, QFont.Medium)
        self.title.setFont(title_font)
        self.title.setStyleSheet("margin-left: 2px;")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setText('<span style="color: #00bf63;">ECO</span><span style="color: #004aad;">GRADE</span>')
        row_layout.addWidget(self.title)

        layout.addLayout(row_layout)
        layout.addSpacing(24)  # Small gap between group and button

        # Start button just below the group
        start_btn = QPushButton("START")
        start_btn.setFixedSize(200, 60)
        start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #1e40af);
                color: white;
                font-family: 'Fredoka Medium';
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
        layout.addWidget(start_btn, alignment=Qt.AlignHCenter)

        layout.addStretch(1)  # Bottom stretch for vertical centering
    
    def initAnimations(self):
        # Fade-in animation for the title
        self.title.setGraphicsEffect(None)
        self.title.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self.title, b"windowOpacity")
        self.fade_anim.setDuration(1200)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

        # Color pulse animation for the text
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.animateTextColor)
        self.pulse_timer.start(40)
        self._pulse_phase = 0.0

        # Background gradient animation
        self.bg_timer = QTimer(self)
        self.bg_timer.timeout.connect(self.animateBackground)
        self.bg_timer.start(40)

    def animateTextColor(self):
        # Pulse between two greens and two blues
        import math
        self._pulse_phase += 0.04
        green1 = QColor("#00bf63")
        green2 = QColor("#10b981")
        blue1 = QColor("#004aad")
        blue2 = QColor("#1e40af")
        t = (math.sin(self._pulse_phase) + 1) / 2
        g = QColor(
            int(green1.red() * (1-t) + green2.red() * t),
            int(green1.green() * (1-t) + green2.green() * t),
            int(green1.blue() * (1-t) + green2.blue() * t)
        )
        b = QColor(
            int(blue1.red() * (1-t) + blue2.red() * t),
            int(blue1.green() * (1-t) + blue2.green() * t),
            int(blue1.blue() * (1-t) + blue2.blue() * t)
        )
        self.title.setText(f'<span style="color: {g.name()};">ECO</span><span style="color: {b.name()};">GRADE</span>')

    def animateBackground(self):
        # Animate a vertical gradient between two color sets
        import math
        self._bg_phase += 0.01
        t = (math.sin(self._bg_phase) + 1) / 2
        color1 = QColor(17, 24, 39)  # #111827
        color2 = QColor(30, 185, 99)  # #1eb963
        color3 = QColor(0, 74, 173)  # #004aad
        color4 = QColor(16, 185, 129)  # #10b981
        ctop = QColor(
            int(color1.red() * (1-t) + color2.red() * t),
            int(color1.green() * (1-t) + color2.green() * t),
            int(color1.blue() * (1-t) + color2.blue() * t)
        )
        cbottom = QColor(
            int(color3.red() * (1-t) + color4.red() * t),
            int(color3.green() * (1-t) + color4.green() * t),
            int(color3.blue() * (1-t) + color4.blue() * t)
        )
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, ctop)
        grad.setColorAt(1, cbottom)
        pal = self.palette()
        pal.setBrush(QPalette.Window, QBrush(grad))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def load_background_image(self):
        """Loads the SVG image centered at original size (no scaling)."""
        svg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/start.svg'))
        if hasattr(self, 'background') and isinstance(self.background, QSvgWidget):
            self.background.load(svg_path)
            self.background.setGeometry(0, 0, self.width(), self.height())
            self.background.show()
            self.setStyleSheet("")
        else:
            # Replace QLabel with QSvgWidget for SVG backgrounds
            if hasattr(self, 'background'):
                self.background.deleteLater()
            self.background = QSvgWidget(svg_path, self)
            self.background.setGeometry(0, 0, self.width(), self.height())
            self.background.show()
            self.setStyleSheet("")
    
    def go_to_main(self):
        """Switch to main view when start button is clicked"""
        if self.parent_window:
            self.parent_window.switch_view("main")

    def resizeEvent(self, event):
        """Handles window resize - re-centers image and button."""
        super().resizeEvent(event)
        if hasattr(self, 'background'):
            self.background.setGeometry(0, 0, self.width(), self.height()) 