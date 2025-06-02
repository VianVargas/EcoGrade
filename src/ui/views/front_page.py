import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty, QPoint, QRect, QEasingCurve
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QColor, QPainter, QPainterPath, QPen, QRadialGradient, QLinearGradient
import random

class LiquidButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._gradient_pos = 0.0
        self._flow_phase = 0.0
        self.anim = QPropertyAnimation(self, b"gradientPos")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("border: none; font-family: 'Segoe UI'; font-size: 24px; font-weight: bold; color: white;")
        self.setFixedSize(200, 60)
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
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        pos = self._gradient_pos
        phase = self._flow_phase
        # Create a wavy, blobby path for the button
        w, h = rect.width(), rect.height()
        path = QPainterPath()
        # Top left
        path.moveTo(20 + 4*math.sin(phase), 0)
        # Top edge
        path.cubicTo(w*0.5 + 8*math.sin(phase+1), 0 + 2*math.cos(phase+1),
                     w-20 + 4*math.sin(phase+2), 0,
                     w, 20 + 4*math.cos(phase+2))
        # Right edge
        path.cubicTo(w, h*0.5 + 8*math.sin(phase+2.5),
                     w, h-20 + 4*math.sin(phase+3),
                     w-20 + 4*math.cos(phase+3), h)
        # Bottom edge
        path.cubicTo(w*0.5 + 8*math.sin(phase+4), h + 2*math.cos(phase+4),
                     20 + 4*math.sin(phase+5), h,
                     0, h-20 + 4*math.cos(phase+5))
        # Left edge
        path.cubicTo(0, h*0.5 + 8*math.sin(phase+5.5),
                     0, 20 + 4*math.sin(phase+6),
                     20 + 4*math.cos(phase+6), 0)
        path.closeSubpath()
        # Gradient: top-to-bottom (horizontal split), with a wavy color boundary
        grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        n_stops = 12
        for i in range(n_stops + 1):
            t = i / n_stops
            # Sine wave for the color boundary
            wave = 0.12 * math.sin(2 * math.pi * t * 2 + phase * 1.5)
            blend = min(max(t + wave, 0), 1)
            # Blend between green and blue
            green = QColor("#10b981")
            blue = QColor("#004aad")
            r = int(green.red() * (1-blend) + blue.red() * blend)
            g = int(green.green() * (1-blend) + blue.green() * blend)
            b = int(green.blue() * (1-blend) + blue.blue() * blend)
            grad.setColorAt(t, QColor(r, g, b))
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        # Draw text
        painter.setPen(Qt.white)
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.text())

    def getGradientPos(self):
        return self._gradient_pos
    def setGradientPos(self, value):
        self._gradient_pos = value
        self.update()
    gradientPos = pyqtProperty(float, fget=getGradientPos, fset=setGradientPos)

class FrontPageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._wobble_phase = 0.0
        self.initUI()
        self.initAnimations()
        # --- Animated roaming trash shapes ---
        self.trash_types = [
            ('bottle', QColor(85, 119, 255)),   # Blue
            ('can', QColor(244, 63, 94)),      # Red
            ('cup', QColor(255, 193, 7)),      # Yellow
            ('bag', QColor(16, 185, 129)),     # Green
        ]
        self.trash_items = []
        for i in range(8):
            shape, color = self.trash_types[i % 4]
            size = random.randint(22, 38)
            x = random.randint(100, 400)
            y = random.randint(100, 400)
            vx = random.choice([-1, 1]) * random.uniform(0.2, 0.6)
            vy = random.choice([-1, 1]) * random.uniform(0.2, 0.6)
            self.trash_items.append({
                'shape': shape,
                'size': size,
                'x': x,
                'y': y,
                'vx': vx,
                'vy': vy,
                'color': color,
                'angle': random.uniform(0, 2 * 3.14159)
            })
    
    def initUI(self):
        # Set pure white background
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
            QLabel {
                background: transparent;
            }
        """)
        
        # Load Fredoka Medium font if available
        font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/fonts/static/Fredoka-Medium.ttf'))
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addStretch(1)

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

        # ECOGRADE title with solid colors (no animation)
        self.title = QLabel()
        title_font = QFont("Fredoka Medium", 96, QFont.Medium)
        self.title.setFont(title_font)
        self.title.setStyleSheet("margin-left: 2px;")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setText('<span style="color: #00bf63;">ECO</span><span style="color: #004aad;">GRADE</span>')
        row_layout.addWidget(self.title)

        layout.addLayout(row_layout)
        layout.addSpacing(24)

        # Start button
        start_btn = LiquidButton("START")
        start_btn.clicked.connect(self.go_to_main)
        layout.addWidget(start_btn, alignment=Qt.AlignHCenter)

        layout.addStretch(1)

    def initAnimations(self):
        # Blob animation timer
        self._wobble_phase = 0.0
        self.blob_timer = QTimer(self)
        self.blob_timer.timeout.connect(self.updateBlobAnimation)
        self.blob_timer.start(16)  # ~60 FPS

    def updateBlobAnimation(self):
        self._wobble_phase += 0.03
        # --- Animate trash items ---
        w, h = self.width(), self.height()
        for item in self.trash_items:
            item['x'] += item['vx']
            item['y'] += item['vy']
            item['angle'] += 0.01
            # Bounce off edges
            if item['x'] - item['size'] < 0 or item['x'] + item['size'] > w:
                item['vx'] *= -1
            if item['y'] - item['size'] < 0 or item['y'] + item['size'] > h:
                item['vy'] *= -1
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        phase = self._wobble_phase
        import math
        def wobble(val, freq, amp, offset=0):
            return val + math.sin(phase * freq + offset) * amp

        # --- Increased blob size ---
        blob_w = width * 0.35
        blob_h = height * 0.35

        # Helper to draw a blob at a given corner
        def draw_blob(corner_x, corner_y, color, glow_color, phase_offset):
            if corner_x == 0:
                base_x = 0
            else:
                base_x = width
            if corner_y == 0:
                base_y = 0
            else:
                base_y = height
            x_dir = 1 if corner_x == 0 else -1
            y_dir = 1 if corner_y == 0 else -1
            # Glow
            painter.setBrush(glow_color)
            painter.setPen(Qt.NoPen)
            glow_path = QPainterPath()
            glow_path.moveTo(base_x, base_y)
            glow_path.lineTo(base_x, base_y + y_dir * wobble(blob_h * 0.65, 1.1, 9, phase_offset))
            glow_path.cubicTo(
                base_x + x_dir * wobble(blob_w * 0.28, 1.2, 9, phase_offset+0.2), base_y + y_dir * wobble(blob_h * 0.48, 1.3, 9, phase_offset+0.3),
                base_x + x_dir * wobble(blob_w * 0.45, 1.4, 11, phase_offset+0.4), base_y + y_dir * wobble(blob_h * 0.58, 1.5, 9, phase_offset+0.5),
                base_x + x_dir * wobble(blob_w * 0.55, 1.6, 9, phase_offset+0.6), base_y + y_dir * wobble(blob_h * 0.43, 1.7, 9, phase_offset+0.7)
            )
            glow_path.cubicTo(
                base_x + x_dir * wobble(blob_w * 0.7, 1.8, 9, phase_offset+0.8), base_y + y_dir * wobble(blob_h * 0.21, 1.9, 9, phase_offset+0.9),
                base_x + x_dir * wobble(blob_w, 2.0, 9, phase_offset+1.0), base_y + y_dir * wobble(blob_h * 0.28, 2.1, 9, phase_offset+1.1),
                base_x + x_dir * wobble(blob_w, 2.2, 9, phase_offset+1.2), base_y + y_dir * wobble(blob_h * 0.13, 2.3, 9, phase_offset+1.3)
            )
            glow_path.lineTo(base_x + x_dir * blob_w, base_y)
            glow_path.lineTo(base_x, base_y)
            glow_path.closeSubpath()
            painter.drawPath(glow_path)
            # Main blob
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.moveTo(base_x, base_y)
            path.lineTo(base_x, base_y + y_dir * wobble(blob_h * 0.6, 1.1, 5, phase_offset))
            path.cubicTo(
                base_x + x_dir * wobble(blob_w * 0.22, 1.2, 5, phase_offset+0.2), base_y + y_dir * wobble(blob_h * 0.45, 1.3, 5, phase_offset+0.3),
                base_x + x_dir * wobble(blob_w * 0.36, 1.4, 6, phase_offset+0.4), base_y + y_dir * wobble(blob_h * 0.55, 1.5, 5, phase_offset+0.5),
                base_x + x_dir * wobble(blob_w * 0.44, 1.6, 5, phase_offset+0.6), base_y + y_dir * wobble(blob_h * 0.4, 1.7, 5, phase_offset+0.7)
            )
            path.cubicTo(
                base_x + x_dir * wobble(blob_w * 0.56, 1.8, 5, phase_offset+0.8), base_y + y_dir * wobble(blob_h * 0.18, 1.9, 5, phase_offset+0.9),
                base_x + x_dir * wobble(blob_w, 2.0, 5, phase_offset+1.0), base_y + y_dir * wobble(blob_h * 0.25, 2.1, 5, phase_offset+1.1),
                base_x + x_dir * wobble(blob_w, 2.2, 5, phase_offset+1.2), base_y + y_dir * wobble(blob_h * 0.1, 2.3, 5, phase_offset+1.3)
            )
            path.lineTo(base_x + x_dir * blob_w, base_y)
            path.lineTo(base_x, base_y)
            path.closeSubpath()
            painter.drawPath(path)

        # Colors
        blue = QColor(85, 119, 255)
        blue_glow = QColor(85, 119, 255, 60)
        green = QColor(16, 185, 129)
        green_glow = QColor(16, 185, 129, 60)

        # Draw blobs in all four corners with phase offsets
        draw_blob(0, height, blue, blue_glow, 0)           # Bottom-left (blue)
        draw_blob(width, height, blue, blue_glow, 1.0)     # Bottom-right (blue)
        draw_blob(0, 0, green, green_glow, 2.0)            # Top-left (green)
        draw_blob(width, 0, green, green_glow, 3.0)        # Top-right (green)

        # --- Draw roaming trash shapes as outlines only ---
        for item in self.trash_items:
            pen = QPen(item['color'], 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.save()
            painter.translate(item['x'], item['y'])
            painter.rotate(math.degrees(item['angle']))
            path = self.get_trash_path(item['shape'], item['size'])
            painter.drawPath(path)
            painter.restore()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def go_to_main(self):
        if self.parent_window:
            self.parent_window.switch_view("main")

    def get_trash_path(self, shape, size):
        path = QPainterPath()
        s = size / 2
        if shape == 'bottle':
            # Simple bottle silhouette
            path.moveTo(-s * 0.2, -s)
            path.lineTo(s * 0.2, -s)
            path.lineTo(s * 0.2, -s * 0.5)
            path.lineTo(s * 0.35, s * 0.7)
            path.quadTo(0, s, -s * 0.35, s * 0.7)
            path.lineTo(-s * 0.2, -s * 0.5)
            path.closeSubpath()
        elif shape == 'can':
            # Simple can (rectangle with rounded ends)
            path.moveTo(-s * 0.4, -s)
            path.lineTo(s * 0.4, -s)
            path.arcTo(-s * 0.4, -s, s * 0.8, s * 0.4, 0, 180)
            path.lineTo(-s * 0.4, s)
            path.arcTo(-s * 0.4, s - s * 0.4, s * 0.8, s * 0.4, 180, 180)
            path.closeSubpath()
        elif shape == 'cup':
            # Simple cup (trapezoid)
            path.moveTo(-s * 0.5, -s)
            path.lineTo(s * 0.5, -s)
            path.lineTo(s * 0.3, s)
            path.lineTo(-s * 0.3, s)
            path.closeSubpath()
        elif shape == 'bag':
            # Simple bag (rounded rectangle with handles)
            path.moveTo(-s * 0.4, -s * 0.2)
            path.quadTo(-s * 0.4, -s, 0, -s)
            path.quadTo(s * 0.4, -s, s * 0.4, -s * 0.2)
            path.lineTo(s * 0.4, s * 0.7)
            path.quadTo(0, s, -s * 0.4, s * 0.7)
            path.closeSubpath()
        return path 