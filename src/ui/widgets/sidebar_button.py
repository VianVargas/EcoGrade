from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon, QPalette, QPainter, QLinearGradient, QColor, QPen
from PyQt5.QtCore import QSize, Qt, QTimer
import os
import math

class SidebarButton(QPushButton):
    def __init__(self, icon_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self._wave_phase = 0.0
        self._hovered = False
        self.wave_timer = QTimer(self)
        self.wave_timer.timeout.connect(self.updateWave)
        self.setCursor(Qt.PointingHandCursor)
        self.icon_path = icon_path
        self.icon = None
        if (icon_path.lower().endswith('.svg')) and os.path.exists(icon_path):
            self.icon = QIcon(icon_path)
            self.setIconSize(QSize(25, 25))
        self.setText("")
        self.setStyleSheet("")  # Remove default stylesheet for custom painting

    def enterEvent(self, event):
        self._hovered = True
        self.wave_timer.start(16)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.wave_timer.stop()
        self.update()
        super().leaveEvent(event)

    def updateWave(self):
        self._wave_phase += 0.05
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        if self._hovered:
            # Draw animated wave gradient
            grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
            n_stops = 10
            phase = self._wave_phase
            for i in range(n_stops + 1):
                t = i / n_stops
                wave = 0.13 * math.sin(2 * math.pi * t * 2 + phase * 1.5)
                blend = min(max(t + wave, 0), 1)
                green = QColor("#10b981")
                blue = QColor("#004aad")
                r = int(green.red() * (1-blend) + blue.red() * blend)
                g = int(green.green() * (1-blend) + blue.green() * blend)
                b = int(green.blue() * (1-blend) + blue.blue() * blend)
                grad.setColorAt(t, QColor(r, g, b))
            painter.setBrush(grad)
        else:
            # Draw static gray background
            painter.setBrush(QColor("#374151"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
        # Draw icon or fallback text
        if self.icon:
            icon_rect = rect.adjusted(17, 17, -17, -17)
            self.icon.paint(painter, icon_rect, Qt.AlignCenter)
        else:
            painter.setPen(QColor("white"))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignCenter, "📄") 