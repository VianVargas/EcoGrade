from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QLabel, QSizePolicy, QPushButton, QComboBox)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPalette
import pyqtgraph as pg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import math
from src.ui.widgets.chart_widgets import PieChartWidget, BarChartWidget

# Color scheme
COLORS = {
    'background': '#111827',
    'panel': '#2D2D2D',
    'text': '#FFFFFF',
    'accent': '#4CAF50',
    'warning': '#2196F3',
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

class Panel(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.initUI(title)
        
    def initUI(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title label with improved styling
        title_label = QLabel(title)
        title_label.setFont(QFont('Segoe UI', 12, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: transparent;
                padding: 5px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add widgets to main layout
        layout.addWidget(title_label)
        layout.addWidget(self.content_widget)
        
        # Set panel style
        self.setStyleSheet("""
            QWidget {
                background-color: #111827;
                border-radius: 10px;
                border: 1px solid #16324b;
            }
        """)

class AnalyticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        
        # Add filter controls
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # Time filter dropdown
        time_filter_label = QLabel("Time Range:")
        time_filter_label.setStyleSheet("color: white; font-size: 12px; padding: 0; border: none;")
        self.time_filter = QComboBox()
        self.time_filter.addItems(["Past Hour", "Past Day", "Past Week", "Past Month"])
        
        # Style the dropdowns
        dropdown_style = """
            QComboBox {
                background-color: #111827;
                color: white;
                border: 1px solid #16324b;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 12px;
                min-width: 120px;
            }
            QComboBox:hover {
                border: 1px solid #3ac194;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(resources/icons/dropdown.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #111827;
                color: white;
                border: 1px solid #16324b;
                selection-background-color: #1e3a8a;
            }
        """
        
        self.time_filter.setStyleSheet(dropdown_style)
        
        # Add dropdown filters
        type_filter_label = QLabel("Type:")
        type_filter_label.setStyleSheet("color: white; font-size: 12px; padding: 0; border: none;")
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        self.type_filter.addItems([
            "PET Bottle", "HDPE Plastic", "PP", "LDPE", 
            "Tin-Steel Can", "Mixed Trash", "UHT Box", "Other"
        ])
        
        classification_filter_label = QLabel("Classification:")
        classification_filter_label.setStyleSheet("color: white; font-size: 12px; padding: 0; border: none;")
        self.classification_filter = QComboBox()
        self.classification_filter.addItem("All Classifications")
        self.classification_filter.addItems([
            "High Value Recyclable", "Low Value", "Rejects", "Mixed"
        ])
        
        # Apply dropdown style to all comboboxes
        self.type_filter.setStyleSheet(dropdown_style)
        self.classification_filter.setStyleSheet(dropdown_style)
        
        # Connect dropdown signals
        self.time_filter.currentTextChanged.connect(self.update_table)
        self.type_filter.currentTextChanged.connect(self.update_table)
        self.classification_filter.currentTextChanged.connect(self.update_table)
        
        # Add dropdowns to filter layout
        filter_layout.addWidget(time_filter_label)
        filter_layout.addWidget(self.time_filter)
        filter_layout.addWidget(type_filter_label)
        filter_layout.addWidget(self.type_filter)
        filter_layout.addWidget(classification_filter_label)
        filter_layout.addWidget(self.classification_filter)
        filter_layout.addStretch()
        
        # Add filter layout to panel
        table_panel.content_layout.addLayout(filter_layout)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Type', 'Opacity', 'Contamination', 'Classification', 'Timestamp'
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 50)  # ID column smaller
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # ID column fixed width
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Type
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Opacity
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # Contamination
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)  # Classification
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # Timestamp
        
        self.table.setMaximumHeight(300)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #111827;
                color: white;
                gridline-color: #16324b;
                border: none;
            }
            QHeaderView::section {
                background-color: #111827;
                color: white;
                padding: 5px;
                border: 1px solid #16324b;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #16324b;
            }
        """)
        table_panel.content_layout.addWidget(self.table)
        
        # Pie Chart Panel
        pie_panel = Panel("Distribution")  # Simplified title
        self.pie_chart = PieChartWidget()
        self.pie_chart.setMinimumSize(300, 300)
        self.pie_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pie_panel.content_layout.addWidget(self.pie_chart)
        
        # Add panels to top layout
        top_layout.addWidget(table_panel, 1)
        top_layout.addWidget(pie_panel, 1)
        
        # Bar Chart Panel
        bar_panel = Panel("Waste Types")
        
        # Add bar chart with reduced size
        self.bar_chart = BarChartWidget()
        self.bar_chart.setMinimumHeight(180)  # Reduced height
        self.bar_chart.setMaximumHeight(200)  # Reduced height
        bar_panel.content_layout.addWidget(self.bar_chart)
        
        # Add layouts to main layout
        main_layout.addLayout(top_layout)
        main_layout.addWidget(bar_panel)
        
        # Initialize charts
        self.update_charts()
        
    def setup_timer(self):
        # Update every 3 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(3000)  # Increased to 3 seconds to reduce flickering
        
    def update_time_filter(self, time_filter):
        # Update all charts with the new time filter
        self.bar_chart.set_time_filter(time_filter)
        self.update_charts()
        
    def update_data(self):
        self.update_table()
        self.update_charts()
        
    def update_table(self):
        try:
            db_path = Path('data/measurements.db')
            conn = sqlite3.connect(str(db_path))
            
            time_conditions = {
                'Past Hour': "datetime('now', '-1 hour')",
                'Past Day': "datetime('now', '-1 day')",
                'Past Week': "datetime('now', '-7 days')",
                'Past Month': "datetime('now', '-30 days')"
            }
            
            time_filter = self.time_filter.currentText()
            
            query = """
            SELECT id, waste_type, opacity, contamination, classification, timestamp
            FROM detections
            WHERE timestamp >= {time_condition}
            """.format(time_condition=time_conditions[time_filter])
            
            selected_type = self.type_filter.currentText()
            if selected_type != "All Types":
                query += f" AND waste_type = '{selected_type}'"
            
            selected_classification = self.classification_filter.currentText()
            if selected_classification != "All Classifications":
                query += f" AND classification = '{selected_classification}'"
            
            query += """
            ORDER BY timestamp DESC
            LIMIT 10
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            self.table.setRowCount(len(df))
            for i, row in df.iterrows():
                # ID
                item = QTableWidgetItem(str(row['id']))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, item)
                
                # Type
                item = QTableWidgetItem(str(row['waste_type']))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 1, item)
                
                # Opacity
                item = QTableWidgetItem(str(row['opacity']))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 2, item)
                
                # Contamination
                contamination = float(row['contamination'])
                item = QTableWidgetItem(f"{contamination:.2f}%")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, item)
                
                # Classification
                item = QTableWidgetItem(str(row['classification']))
                item.setTextAlignment(Qt.AlignCenter)
                if row['classification'] == 'High Value Recyclable':
                    item.setForeground(QColor(COLORS['accent']))
                elif row['classification'] == 'Low Value':
                    item.setForeground(QColor(COLORS['warning']))
                elif row['classification'] == 'Rejects':
                    item.setForeground(QColor(COLORS['error']))
                self.table.setItem(i, 4, item)
                
                # Timestamp
                item = QTableWidgetItem(str(row['timestamp']))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 5, item)
                    
        except Exception as e:
            print(f"Error updating table: {str(e)}")
            
    def update_charts(self):
        try:
            db_path = Path('data/measurements.db')
            conn = sqlite3.connect(str(db_path))
            conditions = []
            params = {}
            time_conditions = {
                'Past Hour': "datetime('now', '-1 hour')",
                'Past Day': "datetime('now', '-1 day')",
                'Past Week': "datetime('now', '-7 days')",
                'Past Month': "datetime('now', '-30 days')"
            }
            selected_time = self.time_filter.currentText()
            conditions.append(f"timestamp >= {time_conditions[selected_time]}")
            selected_type = self.type_filter.currentText()
            if selected_type != 'All Types':
                conditions.append("waste_type = :waste_type")
                params['waste_type'] = selected_type
            selected_class = self.classification_filter.currentText()
            if selected_class != 'All Classifications':
                conditions.append("classification = :classification")
                params['classification'] = selected_class
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Get data for both charts in a single query
            query = f"""
            SELECT waste_type, classification, COUNT(*) as count
            FROM detections
            WHERE {where_clause}
            GROUP BY waste_type, classification
            """
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if not df.empty:
                # Update pie chart
                pie_data = df.groupby('classification')['count'].sum()
                self.pie_chart.update_chart_with_data(
                    pie_data.index.tolist(),
                    pie_data.values.tolist()
                )
                
                # Update bar chart
                bar_data = df.groupby('waste_type')['count'].sum()
                num_items = len(bar_data)
                if num_items == 1:
                    self.bar_chart.set_bar_width(0.3)
                elif num_items <= 3:
                    self.bar_chart.set_bar_width(0.4)
                else:
                    self.bar_chart.set_bar_width(0.5)
                self.bar_chart.update_chart_with_data(
                    bar_data.index.tolist(),
                    bar_data.values.tolist()
                )
            else:
                self.pie_chart.update_chart_with_data([], [])
                self.bar_chart.update_chart_with_data([], [])
        except Exception as e:
            print(f"Error updating charts: {str(e)}")
            self.pie_chart.update_chart_with_data([], [])
            self.bar_chart.update_chart_with_data([], [])
            
    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event) 