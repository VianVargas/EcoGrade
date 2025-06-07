from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QPainterPath, QPen

class AboutDesignWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self._wobble_phase = 0.0
        self.blob_timer = QTimer(self)
        self.blob_timer.timeout.connect(self.updateBlobAnimation)
        self.blob_timer.start(16)  # ~60 FPS

    def updateBlobAnimation(self):
        self._wobble_phase += 0.03
        self.update()

    def paintEvent(self, event):
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

        # Helper to draw a blob at a given corner (copied from front page)
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

        # Colors (copied from front page)
        blue = QColor(85, 119, 255)
        blue_glow = QColor(85, 119, 255, 60)
        green = QColor(16, 185, 129)
        green_glow = QColor(16, 185, 129, 60)

        # Draw blobs in all four corners (using the same draw_blob calls as in the front page, but with -1 offset for right/bottom)
        draw_blob(0, height-1, blue, blue_glow, 0)           # Bottom–left (blue)
        draw_blob(width-1, height-1, blue, blue_glow, 1.0)   # Bottom–right (blue)
        draw_blob(0, 0, green, green_glow, 2.0)              # Top–left (green)
        draw_blob(width-1, 0, green, green_glow, 3.0)        # Top–right (green)

        # Soft vertical gradient overlay (keep) (using QPainter.CompositionMode_SourceOver so that the blobs are visible)
        grad = QLinearGradient(0, 0, 0, height)
        grad.setColorAt(0, QColor(17, 24, 39, 120))
        grad.setColorAt(1, QColor(17, 24, 39, 60))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.fillRect(self.rect(), grad)

class AboutView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: transparent;")
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Add animated design background
        self.design_widget = AboutDesignWidget(self)
        self.design_widget.lower()
        self.design_widget.setGeometry(self.rect())
        self.design_widget.show()

        # Ensure design widget resizes with AboutView
        self.resizeEvent = self._resizeEvent

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner_widget = QWidget()
        inner_layout = QVBoxLayout(inner_widget)
        inner_layout.setContentsMargins(60, 40, 60, 40)
        inner_layout.setSpacing(24)

        # Title (split color ECOGRADE, similar to front page)
        title = QLabel("<span style='color: #00bf63;'>ECO</span><span style='color: #004aad;'>GRADE</span>")
        title.setTextFormat(Qt.RichText)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-family: 'Fredoka'; font-size: 56px; font-weight: bold; letter-spacing: 2px;")
        inner_layout.addWidget(title)

        # Tagline (using Fredoka Medium)
        tagline = QLabel("LEVERAGING CONVOLUTIONAL NEURAL NETWORKS AND MULTI-DECISION ANALYSIS FOR ADVANCED REAL-TIME DETECTION AND QUALITY ASSESSMENT OF NON-BIODEGRADABLE WASTE MATERIALS")
        tagline.setWordWrap(True)
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet("color: white; font-family: 'Fredoka'; font-size: 18px; font-weight: 600; margin-bottom: 8px;")
        inner_layout.addWidget(tagline)

        # Description (using Fredoka Medium)
        desc = QLabel(
            "This study presents EcoGrade, an innovative system that enhances the assessment and classification of non-biodegradable waste through the integration of YOLOv11-based Convolutional Neural Networks (CNN) for real-time object detection and Multi-Criteria Decision Analysis (MCDA) for data-driven quality evaluation. Focusing on plastic types such as Polyethylene Terephthalate (PET), High-Density Polyethylene (HDPE), Low-Density Polyethylene (LDPE), and Polypropylene (PP), as well as Tin/Steel Cans, the system detects and analyzes waste materials based on material type, opacity, and contamination levels to determine their value. The YOLOv11n model was trained on a custom dataset to ensure precise classification, while the MCDA framework assigned weighted scores to evaluate material quality and guide decision-making. EcoGrade was tested under real-world conditions, specifically in partnership with the City Environmental Management Office (CEMO) of Marikina City, and its performance was benchmarked against ISO 25010 software quality standards, particularly in terms of functionality, reliability, and efficiency. Results demonstrated that the system achieved high detection accuracy and significantly improved classification performance compared to conventional models, offering a scalable, intelligent solution that supports sustainable waste management and promotes circular economy practices."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: white; font-family: 'Fredoka'; font-size: 14px; line-height: 1.6; margin-bottom: 16px;")
        inner_layout.addWidget(desc)

        # Team Members Title (renamed to QuadPals, using Fredoka Medium) (split color QUADPALS)
        team_title = QLabel("<span style='color: #00bf63;'>QUAD</span><span style='color: #004aad;'>PALS</span>")
        team_title.setTextFormat(Qt.RichText)
        team_title.setAlignment(Qt.AlignCenter)
        team_title.setStyleSheet("font-family: 'Fredoka'; font-size: 32px; font-weight: bold; margin-top: 16px; margin-bottom: 8px;")
        inner_layout.addWidget(team_title)

        # Team Members List (centered, no bullets, names in Fredoka Medium, roles in Fredoka Medium)
        team_members = [
            ("Villas, Rakee D.", "Fullstack Developer"),
            ("Vargas, Vian Andrei C.", "Hardware Engineer, Documentation"),
            ("Turingan, Fraizer Quinn R.", "Backend Developer, Documentation"),
            ("Santoceldez, Rogin R.", "Data Gatherer, Documentation"),
            ("Altiche, Adriane", "Frontend Developer, Documentation"),
        ]
        for name, role in team_members:
            member_label = QLabel(f"<span style='font-size:16px; color:white; font-family:Fredoka; font-weight:600;'>{name}</span><br><span style='font-size:13px; color:#bdbdbd; font-family:Fredoka;'>{role}</span>")
            member_label.setTextFormat(Qt.RichText)
            member_label.setAlignment(Qt.AlignCenter)
            member_label.setStyleSheet("margin-bottom: 10px;")
            inner_layout.addWidget(member_label)

        # Copyright (using Fredoka Medium)
        copyright = QLabel("© 2025 EcoGrade Project. All rights reserved.")
        copyright.setAlignment(Qt.AlignCenter)
        copyright.setStyleSheet("color: #bdbdbd; font-family: 'Fredoka'; font-size: 12px; margin-top: 24px;")
        inner_layout.addWidget(copyright)

        scroll.setWidget(inner_widget)
        outer_layout.addWidget(scroll)

        # (Store inner_widget as an instance variable so that showEvent and hideEvent can animate it.)
        self.inner_widget = inner_widget

    def _resizeEvent(self, event):
        self.design_widget.setGeometry(self.rect())
        QWidget.resizeEvent(self, event)

    def showEvent(self, event):
        self.inner_widget.setGraphicsEffect(QGraphicsOpacityEffect(self.inner_widget))
        anim = QPropertyAnimation(self.inner_widget.graphicsEffect(), b"opacity", self.inner_widget)
        anim.setDuration(500)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        super().showEvent(event)

    def hideEvent(self, event):
        if self.inner_widget.graphicsEffect() is None:
            self.inner_widget.setGraphicsEffect(QGraphicsOpacityEffect(self.inner_widget))
        anim_out = QPropertyAnimation(self.inner_widget.graphicsEffect(), b"opacity", self.inner_widget)
        anim_out.setDuration(500)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.InOutQuad)
        anim_out.start(QPropertyAnimation.DeleteWhenStopped)
        QTimer.singleShot(500, lambda: (self.inner_widget.graphicsEffect().setOpacity(1.0) if (self.inner_widget.graphicsEffect() is not None) else None))
        super().hideEvent(event) 