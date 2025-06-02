from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QLabel, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPalette
import pyqtgraph as pg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import math

# Color scheme
COLORS = {
    'background': '#1E1E1E',
    'panel': '#2D2D2D',
    'text': '#FFFFFF',
    'accent': '#4CAF50',
    'warning': '#FFC107',
    'error': '#F44336',
    'border': '#3D3D3D',
    'grid': '#3D3D3D'
}

# Pie chart color mapping
PIE_LABELS = ["High Value Recyclable", "Low Value", "Rejects", "Mixed"]
PIE_COLORS = ['#4CAF50', '#2196F3', '#FFC107', '#F44336']  # Green, Blue, Yellow, Red
PIE_COLOR_MAP = dict(zip(PIE_LABELS, PIE_COLORS))
PIE_OTHER_COLOR = '#F44336'  # Red for Mixed

# Bar chart color mapping for waste types
BAR_TYPE_COLORS = {
    'PET Bottle': '#42a5f5',
    'HDPE Plastic': '#66bb6a',
    'PP': '#ffa726',
    'LDPE': '#ab47bc',
    'Tin-Steel Can': '#bdbdbd',
    'Mixed Trash': '#8d6e63',
    'UHT Box': '#ff7043',
    'Other': '#789262',
}

def get_bar_color(waste_type):
    return BAR_TYPE_COLORS.get(waste_type, '#bdbdbd')

class Panel(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['panel']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                padding: 4px;
            }}
        """)
        layout.addWidget(title_label)
        
        # Content container
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

class PieChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.colors = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def set_data(self, labels, values):
        # Only keep PIE_LABELS, group others as 'Mixed'
        filtered = {label: 0 for label in PIE_LABELS}
        mixed = 0
        for label, value in zip(labels, values):
            if label in PIE_LABELS:
                filtered[label] += value
            else:
                mixed += value
        self.data = [(label, filtered[label]) for label in PIE_LABELS]
        if mixed > 0:
            self.data.append(('Mixed', mixed))
        self.colors = [PIE_COLOR_MAP.get(label, PIE_OTHER_COLOR) for label, _ in self.data]
        self.update()
        
    def paintEvent(self, event):
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        total = sum(value for _, value in self.data)
        if total == 0:
            return
        margin = 40
        rect = self.rect()
        chart_rect = QRect(
            rect.left() + margin,
            rect.top() + margin,
            rect.width() - 2 * margin,
            rect.height() - 2 * margin
        )
        size = min(chart_rect.width(), chart_rect.height())
        chart_rect.setWidth(size)
        chart_rect.setHeight(size)
        chart_rect.moveCenter(rect.center())
        painter.setPen(QPen(QColor(COLORS['text'])))
        painter.setFont(QFont('Open Sans', 12, QFont.Bold))
        painter.drawText(rect, Qt.AlignTop | Qt.AlignHCenter, "Classification Distribution")
        start_angle = 0
        for i, (label, value) in enumerate(self.data):
            angle = 360 * (value / total)
            painter.setPen(QPen(QColor(COLORS['border']), 1))
            painter.setBrush(QColor(self.colors[i % len(self.colors)]))
            painter.drawPie(chart_rect, int(start_angle * 16), int(angle * 16))
            mid_angle = math.radians(start_angle + angle/2)
            radius = size / 2
            percentage = (value / total) * 100
            # Only show percentage if angle is large enough
            if angle > 30:
                label_radius = radius * 0.65
                font = QFont('Open Sans', 10)
                text_box = (-30, -10, 60, 20)
            elif angle > 15:
                label_radius = radius * 0.75
                font = QFont('Open Sans', 8)
                text_box = (-20, -8, 40, 16)
            else:
                label_radius = radius * 0.85
                font = QFont('Open Sans', 7)
                text_box = (-15, -6, 30, 12)
            if angle > 15:
                label_x = chart_rect.center().x() + label_radius * math.cos(mid_angle)
                label_y = chart_rect.center().y() + label_radius * math.sin(mid_angle)
                painter.setPen(QPen(QColor(COLORS['text'])))
                painter.setFont(font)
                painter.save()
                painter.translate(int(label_x), int(label_y))
                painter.rotate(math.degrees(mid_angle) + 90)
                painter.drawText(*text_box, Qt.AlignCenter, f"{percentage:.1f}%")
                painter.restore()
            start_angle += angle
        # Draw legend on the left side
        legend_y = rect.top() + 20
        legend_x = rect.left() + 20
        for i, (label, _) in enumerate(self.data):
            painter.setBrush(QColor(self.colors[i % len(self.colors)]))
            painter.setPen(Qt.NoPen)
            painter.drawRect(legend_x, legend_y, 18, 18)
            painter.setPen(QPen(QColor(COLORS['text'])))
            painter.setFont(QFont('Open Sans', 9))
            painter.drawText(legend_x + 24, legend_y + 15, label)
            legend_y += 30

class AnalyticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
            }}
            QTableWidget {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: none;
                border-radius: 4px;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                padding: 5px;
                border: none;
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        self.init_ui()
        self.setup_timer()
        
    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Top section (Table and Pie Chart)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)
        
        # Table Panel
        table_panel = Panel("Recent Detections")
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Timestamp', 'Transparency', 
            'Contamination', 'Classification', 'Type'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMaximumHeight(300)
        table_panel.content_layout.addWidget(self.table)
        
        # Pie Chart Panel
        pie_panel = Panel("Classification Distribution")
        self.pie_chart = PieChartWidget()
        self.pie_chart.setMinimumSize(300, 300)
        self.pie_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pie_panel.content_layout.addWidget(self.pie_chart)
        
        # Add panels to top layout
        top_layout.addWidget(table_panel, 1)
        top_layout.addWidget(pie_panel, 1)
        
        # Bar Chart Panel
        bar_panel = Panel("Waste Types Distribution (Last Hour)")
        self.bar_chart = pg.PlotWidget()
        self.bar_chart.setBackground(COLORS['panel'])
        self.bar_chart.setMinimumHeight(200)
        self.bar_chart.setMaximumHeight(250)
        self.bar_chart.getAxis('bottom').setTextPen(COLORS['text'])
        self.bar_chart.getAxis('left').setTextPen(COLORS['text'])
        self.bar_chart.getAxis('bottom').setPen(COLORS['border'])
        self.bar_chart.getAxis('left').setPen(COLORS['border'])
        self.bar_chart.showGrid(x=True, y=True, alpha=0.3)
        self.bar_chart.getPlotItem().getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.bar_chart.getPlotItem().getViewBox().setAspectLocked(False)
        self.bar_chart.getPlotItem().getViewBox().setRange(xRange=[-0.5, 4.5], yRange=[0, 10], padding=0.1)
        bar_panel.content_layout.addWidget(self.bar_chart)
        
        # Add layouts to main layout
        main_layout.addLayout(top_layout)
        main_layout.addWidget(bar_panel)
        
        # Initialize charts
        self.update_charts()
        
    def setup_timer(self):
        # Update every 2 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(2000)
        
    def update_data(self):
        self.update_table()
        self.update_charts()
        
    def update_table(self):
        try:
            # Connect to SQLite database
            db_path = Path('data/measurements.db')
            conn = sqlite3.connect(str(db_path))
            
            # Get last 10 records
            query = """
            SELECT id, timestamp, waste_type, opacity, contamination, classification
            FROM detections
            ORDER BY timestamp DESC
            LIMIT 10
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Update table
            self.table.setRowCount(len(df))
            for i, row in df.iterrows():
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    # Color coding for classification
                    if j == 5:  # Classification column
                        if value == 'High Value Recyclable':
                            item.setForeground(QColor(COLORS['accent']))
                        elif value == 'Low Value':
                            item.setForeground(QColor(COLORS['warning']))
                        elif value == 'Rejects':
                            item.setForeground(QColor(COLORS['error']))
                    
                    self.table.setItem(i, j, item)
                    
        except Exception as e:
            print(f"Error updating table: {str(e)}")
            
    def update_charts(self):
        try:
            # Connect to SQLite database
            db_path = Path('data/measurements.db')
            conn = sqlite3.connect(str(db_path))
            
            # Get data for pie chart (classification distribution)
            pie_query = """
            SELECT classification, COUNT(*) as count
            FROM detections
            GROUP BY classification
            """
            pie_df = pd.read_sql_query(pie_query, conn)
            
            # Get data for bar chart (waste types over time)
            bar_query = """
            SELECT waste_type, COUNT(*) as count
            FROM detections
            WHERE timestamp >= datetime('now', '-1 hour')
            GROUP BY waste_type
            """
            bar_df = pd.read_sql_query(bar_query, conn)
            
            conn.close()
            
            # Update pie chart
            if not pie_df.empty:
                self.pie_chart.set_data(
                    pie_df['classification'].values,
                    pie_df['count'].values
                )
                
            # Update bar chart
            self.bar_chart.clear()
            if not bar_df.empty:
                x = np.arange(len(bar_df))
                brushes = [pg.mkBrush(get_bar_color(wt)) for wt in bar_df['waste_type']]
                bargraph = pg.BarGraphItem(
                    x=x,
                    height=bar_df['count'].values,
                    width=0.6,
                    brushes=brushes
                )
                self.bar_chart.addItem(bargraph)
                ax = self.bar_chart.getAxis('bottom')
                ax.setTicks([[(i, label) for i, label in enumerate(bar_df['waste_type'])]])
                max_count = bar_df['count'].max()
                self.bar_chart.setYRange(0, max_count * 1.2)
                ax.setStyle(showValues=True)
                ax.setHeight(50)
                
        except Exception as e:
            print(f"Error updating charts: {str(e)}")
            
    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event) 