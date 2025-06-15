import os
import math
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                            QHBoxLayout)
from PyQt5.QtCore import (Qt, QTimer, QPropertyAnimation, pyqtProperty, 
                         QEasingCurve)
from PyQt5.QtGui import (QFont, QPixmap, QFontDatabase, QColor, QPainter, 
                        QPainterPath, QPen, QLinearGradient)

class FrontPageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._wobble_phase = 0.0
        
        # Rain effect: initialize raindrops
        self.num_raindrops = 50
        self.raindrops = self._init_raindrops()
        
        # Initialize UI first
        self.initUI()
        
        # Then initialize animations
        self.initAnimations()

    def initUI(self):
        # Set background and basic styling
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
            QLabel {
                background: transparent;
            }
        """)
        
        # Load fonts
        self.loadFonts()
        
        # Create main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Add top spacer
        layout.addStretch(1)

        # Create title row with logo and text
        self.createTitleRow(layout)

        # Add spacing
        layout.addSpacing(24)

        # Add start button
        self.createStartButton(layout)

        # Add bottom spacer
        layout.addStretch(1)

    def loadFonts(self):
        """Load custom fonts from assets folder"""
        font_dir = os.path.join(os.path.dirname(__file__), '../assets/fonts')
        font_path_semibold = os.path.join(font_dir, 'Fredoka-SemiBold.ttf')
        font_path_medium = os.path.join(font_dir, 'Fredoka-Medium.ttf')

        # Load fonts and store their IDs
        if os.path.exists(font_path_semibold):
            QFontDatabase.addApplicationFont(font_path_semibold)
        if os.path.exists(font_path_medium):
            QFontDatabase.addApplicationFont(font_path_medium)

    def createTitleRow(self, parent_layout):
        """Create the logo and title row"""
        row_layout = QHBoxLayout()
        row_layout.setAlignment(Qt.AlignCenter)
        row_layout.setSpacing(40)
        
        # Add logo
        self.addLogo(row_layout)
        
        # Add title
        self.addTitle(row_layout)
        
        parent_layout.addLayout(row_layout)

    def addLogo(self, layout):
        """Add the application logo"""
        logo_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../assets/LOGO.png'))
        
        logo_label = QLabel()
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            logo_label.setPixmap(logo_pixmap.scaledToHeight(
                180, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)

    def addTitle(self, layout):
        """Add the ECOGRADE title"""
        self.title = QLabel()
        # Use Fredoka with SemiBold weight instead of Medium
        title_font = QFont("Fredoka", 96)
        title_font.setWeight(QFont.DemiBold)
        self.title.setFont(title_font)
        self.title.setStyleSheet("""
            margin-left: 2px;
            font-family: 'Fredoka';
            font-weight: 600;
        """)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setText(
            '<span style="color: #00bf63;">ECO</span>'
            '<span style="color: #004aad;">GRADE</span>')
        layout.addWidget(self.title)

    def createStartButton(self, layout):
        """Create and add the DEMO button"""
        start_btn = LiquidButton("BEGIN DEMO")
        start_btn.clicked.connect(self.go_to_main)
        layout.addWidget(start_btn, alignment=Qt.AlignHCenter)

    def _init_raindrops(self):
        import random
        width = self.width() if self.width() > 0 else 1280
        height = self.height() if self.height() > 0 else 720
        return [
            {
                'x': random.randint(0, width),
                'y': random.randint(-height, 0),
                'length': random.randint(10, 24),
                'speed': random.uniform(1.5, 3.0),  # Slower speed
                'thickness': random.uniform(1.2, 2.2),
                'alpha': random.randint(80, 160)
            }
            for _ in range(self.num_raindrops)
        ]

    def initAnimations(self):
        """Initialize animation timers"""
        self._wobble_phase = 0.0
        self.blob_timer = QTimer(self)
        self.blob_timer.timeout.connect(self.updateBlobAnimation)
        self.blob_timer.start(16)  # ~60 FPS

    def updateBlobAnimation(self):
        """Update animation state for each frame"""
        self._wobble_phase += 0.03
        self._update_raindrops()
        self.update()

    def _update_raindrops(self):
        import random
        width = self.width()
        height = self.height()
        for drop in self.raindrops:
            drop['y'] += drop['speed']
            if drop['y'] > height:
                drop['x'] = random.randint(0, width)
                drop['y'] = random.randint(-40, 0)
                drop['length'] = random.randint(8, 21)
                drop['speed'] = random.uniform(2.0, 4.0)  # Slower speed
                drop['thickness'] = random.uniform(1.5, 2.5)
                drop['alpha'] = random.randint(80, 160)

    def paintEvent(self, event):
        """Custom painting for the widget"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background blobs
        self.drawBackgroundBlobs(painter)

        # Draw rain effect
        self.drawRain(painter)

    def drawBackgroundBlobs(self, painter):
        """Draw the animated background blobs"""
        width = self.width()
        height = self.height()
        phase = self._wobble_phase
        
        # Helper function for wobbly values
        def wobble(val, freq, amp, offset=0):
            return val + math.sin(phase * freq + offset) * amp

        # Colors
        blue = QColor(85, 119, 255)
        blue_glow = QColor(85, 119, 255, 40)
        green = QColor(16, 185, 129)
        green_glow = QColor(16, 185, 129, 40)

        # Draw blobs in all four corners
        self.drawBlob(painter, 0, height, blue, blue_glow, 0, wobble)      # Bottom-left
        self.drawBlob(painter, width, height, blue, blue_glow, 1.0, wobble) # Bottom-right
        self.drawBlob(painter, 0, 0, green, green_glow, 2.0, wobble)       # Top-left
        self.drawBlob(painter, width, 0, green, green_glow, 3.0, wobble)    # Top-right

    def drawBlob(self, painter, corner_x, corner_y, color, glow_color, phase_offset, wobble_func):
        """Draw a single blob at a corner"""
        width = self.width()
        height = self.height()
        blob_w = width * 0.35
        blob_h = height * 0.35

        base_x = 0 if corner_x == 0 else width
        base_y = 0 if corner_y == 0 else height
        x_dir = 1 if corner_x == 0 else -1
        y_dir = 1 if corner_y == 0 else -1

        # Draw glow effect
        painter.setBrush(glow_color)
        painter.setPen(Qt.NoPen)
        glow_path = self.createBlobPath(base_x, base_y, x_dir, y_dir, blob_w, blob_h, 
                                       phase_offset, wobble_func, scale=0.75, amp=12)
        painter.drawPath(glow_path)

        # Draw main blob
        painter.setBrush(color)
        path = self.createBlobPath(base_x, base_y, x_dir, y_dir, blob_w, blob_h,
                                 phase_offset, wobble_func, scale=0.6, amp=5)
        painter.drawPath(path)

    def createBlobPath(self, base_x, base_y, x_dir, y_dir, blob_w, blob_h, 
                      phase_offset, wobble_func, scale=0.6, amp=5):
        """Create a blob path with wobbly edges"""
        path = QPainterPath()
        path.moveTo(base_x, base_y)
        
        # Top edge
        path.lineTo(base_x, base_y + y_dir * wobble_func(blob_h * scale, 1.1, amp, phase_offset))
        
        # Right curve
        path.cubicTo(
            base_x + x_dir * wobble_func(blob_w * 0.22, 1.2, amp, phase_offset+0.2),
            base_y + y_dir * wobble_func(blob_h * 0.45, 1.3, amp, phase_offset+0.3),
            base_x + x_dir * wobble_func(blob_w * 0.36, 1.4, amp+1, phase_offset+0.4),
            base_y + y_dir * wobble_func(blob_h * 0.55, 1.5, amp, phase_offset+0.5),
            base_x + x_dir * wobble_func(blob_w * 0.44, 1.6, amp, phase_offset+0.6),
            base_y + y_dir * wobble_func(blob_h * 0.4, 1.7, amp, phase_offset+0.7)
        )
        
        # Bottom curve
        path.cubicTo(
            base_x + x_dir * wobble_func(blob_w * 0.56, 1.8, amp, phase_offset+0.8),
            base_y + y_dir * wobble_func(blob_h * 0.18, 1.9, amp, phase_offset+0.9),
            base_x + x_dir * wobble_func(blob_w, 2.0, amp, phase_offset+1.0),
            base_y + y_dir * wobble_func(blob_h * 0.25, 2.1, amp, phase_offset+1.1),
            base_x + x_dir * wobble_func(blob_w, 2.2, amp, phase_offset+1.2),
            base_y + y_dir * wobble_func(blob_h * 0.1, 2.3, amp, phase_offset+1.3)
        )
        
        # Close path
        path.lineTo(base_x + x_dir * blob_w, base_y)
        path.lineTo(base_x, base_y)
        path.closeSubpath()
        
        return path

    def drawRain(self, painter):
        painter.save()
        for drop in self.raindrops:
            # Gradient effect: darker at the top, lighter at the bottom
            alpha = int(drop['alpha'] * (1 - drop['y'] / self.height()))
            color = QColor(120, 180, 255, alpha)
            pen = QPen(color, drop['thickness'])
            painter.setPen(pen)
            # Round positions for a pixelated effect
            x = round(drop['x'])
            y = round(drop['y'])
            painter.drawLine(x, y, x, y + drop['length'])
        painter.restore()

    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        # Re-initialize raindrops to fit new size
        self.raindrops = self._init_raindrops()
        self.update()
    
    def go_to_main(self):
        """Handle start button click"""
        if self.parent_window:
            self.parent_window.switch_view("main")


class LiquidButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._gradient_pos = 0.0
        self._flow_phase = 0.0
        
        # Setup animations
        self.anim = QPropertyAnimation(self, b"gradientPos")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)
        
        # Setup appearance
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            border: none; 
            font-family: 'Fredoka';
            font-size: 20px;
            font-weight: 500;
            color: white;
        """)
        self.setFixedSize(200, 60)
        
        # Setup flow animation timer
        self.flow_timer = QTimer(self)
        self.flow_timer.timeout.connect(self.updateFlow)
        self._flowing = False

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setEndValue(1.0)
        self.anim.start()
        self._flowing = True
        self.flow_timer.start(16)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setEndValue(0.0)
        self.anim.start()
        self._flowing = False
        self.flow_timer.stop()
        super().leaveEvent(event)

    def updateFlow(self):
        self._flow_phase += 0.04
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        pos = self._gradient_pos
        phase = self._flow_phase
        
        # Create wavy button shape
        path = self.createButtonPath(rect, phase)
        
        # Create gradient with wave effect
        grad = self.createButtonGradient(rect, phase)
        
        # Draw button
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        
        # Draw text
        painter.setPen(Qt.white)
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.text())

    def createButtonPath(self, rect, phase):
        """Create the wavy button shape"""
        w, h = rect.width(), rect.height()
        path = QPainterPath()
        
        # Top left
        path.moveTo(20 + 4*math.sin(phase), 0)
        
        # Top edge
        path.cubicTo(
            w*0.5 + 8*math.sin(phase+1), 0 + 2*math.cos(phase+1),
            w-20 + 4*math.sin(phase+2), 0,
            w, 20 + 4*math.cos(phase+2)
        )
        
        # Right edge
        path.cubicTo(
            w, h*0.5 + 8*math.sin(phase+2.5),
            w, h-20 + 4*math.sin(phase+3),
            w-20 + 4*math.cos(phase+3), h
        )
        
        # Bottom edge
        path.cubicTo(
            w*0.5 + 8*math.sin(phase+4), h + 2*math.cos(phase+4),
            20 + 4*math.sin(phase+5), h,
            0, h-20 + 4*math.cos(phase+5)
        )
        
        # Left edge
        path.cubicTo(
            0, h*0.5 + 8*math.sin(phase+5.5),
            0, 20 + 4*math.sin(phase+6),
            20 + 4*math.cos(phase+6), 0
        )
        
        path.closeSubpath()
        return path

    def createButtonGradient(self, rect, phase):
        """Create the animated gradient"""
        grad = QLinearGradient(rect.left(), rect.top(), 
                              rect.left(), rect.bottom())
        
        green = QColor("#10b981")
        blue = QColor("#004aad")
        
        # Create 12 color stops with wave effect
        n_stops = 12
        for i in range(n_stops + 1):
            t = i / n_stops
            wave = 0.12 * math.sin(2 * math.pi * t * 2 + phase * 1.5)
            blend = min(max(t + wave, 0), 1)
            
            # Blend between green and blue
            r = int(green.red() * (1-blend) + blue.red() * blend)
            g = int(green.green() * (1-blend) + blue.green() * blend)
            b = int(green.blue() * (1-blend) + blue.blue() * blend)
            
            grad.setColorAt(t, QColor(r, g, b))
            
        return grad

    def getGradientPos(self):
        return self._gradient_pos
        
    def setGradientPos(self, value):
        self._gradient_pos = value
        self.update()
        
    gradientPos = pyqtProperty(float, fget=getGradientPos, fset=setGradientPos)