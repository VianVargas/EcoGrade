from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QLabel, QSizePolicy, QPushButton, QComboBox, QScrollArea,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QRect, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPalette, QIcon
import pyqtgraph as pg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import math
from src.ui.widgets.chart_widgets import PieChartWidget, BarChartWidget

# Enhanced color scheme with better contrast
COLORS = {
    'background': '#111827',      # Darker background for better contrast
    'panel': '#1e293b',           # Lighter panels for better separation
    'text': '#f8fafc',            # Brighter white for better readability
    'text_secondary': '#cbd5e1',  # Secondary text color
    'accent': '#22c55e',          # Brighter green for High Value
    'warning': '#f59e0b',         # Better yellow for Rejects
    'error': '#ef4444',           # Red for Mixed
    'border': '#475569',          # More visible borders
    'grid': '#334155',            # More visible grid lines
    'hover': '#3b82f6'            # Blue for hovers
}

# Pie chart color mapping
PIE_LABELS = ["High Value", "Low Value", "Rejected", "Mixed"]
PIE_COLORS = ['#22c55e', '#3b82f6', '#ef4444', '#f59e0b']  # Green, Blue, Yellow, Red
PIE_COLOR_MAP = dict(zip(PIE_LABELS, PIE_COLORS))
PIE_OTHER_COLOR = '#ef4444'  # Red for Mixed

# Bar chart color mapping for waste types
BAR_TYPE_COLORS = {
    'PET Bottle': '#3b82f6',
    'HDPE Plastic': '#22c55e',
    'PP': '#f59e0b',
    'LDPE': '#a855f7',
    'Tin Can': '#6b7280',
    'Mixed': '#ef4444',
}

def get_bar_color(waste_type):
    return BAR_TYPE_COLORS.get(waste_type, '#6b7280')

class Panel(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['panel']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)  # Increased margins for better spacing
        layout.setSpacing(15)  # Increased spacing
        
        # Enhanced title label
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-family: 'Fredoka';
                font-size: 20px;
                font-weight: 700;
                background-color: transparent;
                border: none;
                padding: 5px 0px;
                letter-spacing: 0.5px;
            }}
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        layout.addWidget(self.content_widget)

class AnalyticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_timer()
        
    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Enhanced background
        self.setStyleSheet(f"background-color: {COLORS['background']};")

        # Create content widget without scroll area for fixed layout
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {COLORS['background']};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)  # Reduced spacing
        content_layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins

        # Top section (Table and Pie Chart)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)  # Reduced spacing
        
        # Enhanced Table Panel
        table_panel = Panel("Recent Detections")
        table_panel.content_layout.setContentsMargins(5, 0, 5, 0)
        table_panel.content_layout.setSpacing(0)
        
        # Enhanced filter controls - more compact
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)  # Reduced spacing
        filter_layout.setContentsMargins(10, 8, 10, 8)  # Reduced margins
        
        # Enhanced filter labels and dropdowns
        filter_style = f"""
            QLabel {{
                color: {COLORS['text']};
                font-family: 'Fredoka';
                font-size: 13px;
                font-weight: 600;
                padding: 0;
                border: none;
                margin-right: 5px;
            }}
        """
        
        # Enhanced dropdown style
        dropdown_style = f"""
            QComboBox {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-family: 'Fredoka';
                font-size: 12px;
                font-weight: 500;
                min-width: 100px;
            }}
            QComboBox:hover {{
                border: 2px solid {COLORS['hover']};
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox::down-arrow {{
                image: url(resources/icons/dropdown.png);
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                selection-background-color: {COLORS['hover']};
                font-family: 'Fredoka';
                font-size: 12px;
                padding: 5px;
            }}
        """
        
        # Time filter
        time_filter_label = QLabel("Time Range:")
        time_filter_label.setStyleSheet(filter_style)
        self.time_filter = QComboBox()
        self.time_filter.addItems(["Past Hour", "Past Day", "Past Week", "Past Month"])
        self.time_filter.setStyleSheet(dropdown_style)
        
        # Type filter
        type_filter_label = QLabel("Type:")
        type_filter_label.setStyleSheet(filter_style)
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        self.type_filter.addItems([
            "PET Bottle", "HDPE Plastic", "PP", "LDPE", 
            "Tin Can", "UHT Box"
        ])
        self.type_filter.setStyleSheet(dropdown_style)
        
        # Classification filter
        classification_filter_label = QLabel("Classification:")
        classification_filter_label.setStyleSheet(filter_style)
        self.classification_filter = QComboBox()
        self.classification_filter.addItem("All Classifications")
        self.classification_filter.addItems([
            "High Value", "Low Value", "Rejected", "Mixed Trash"
        ])
        self.classification_filter.setStyleSheet(dropdown_style)
        
        # Connect dropdown signals
        self.time_filter.currentTextChanged.connect(self.update_data)
        self.type_filter.currentTextChanged.connect(self.update_data)
        self.classification_filter.currentTextChanged.connect(self.update_data)
        
        # Add filters to layout
        filter_layout.addWidget(time_filter_label)
        filter_layout.addWidget(self.time_filter)
        filter_layout.addWidget(type_filter_label)
        filter_layout.addWidget(self.type_filter)
        filter_layout.addWidget(classification_filter_label)
        filter_layout.addWidget(self.classification_filter)
        filter_layout.addStretch()
        
        # Enhanced action buttons
        button_style = f"""
            QPushButton {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                min-width: 35px;
                min-height: 35px;
            }}
            QPushButton:hover {{
                border: 2px solid {COLORS['hover']};
                background-color: {COLORS['panel']};
            }}
        """
        
        delete_button_style = f"""
            QPushButton {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                min-width: 35px;
                min-height: 35px;
            }}
            QPushButton:hover {{
                border: 2px solid {COLORS['error']};
                background-color: rgba(239, 68, 68, 0.1);
            }}
        """
        
        # Delete button
        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon("src/ui/assets/trash-2.svg"))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.setStyleSheet(delete_button_style)
        delete_btn.setToolTip("Delete selected items")
        delete_btn.clicked.connect(self.delete_selected)
        filter_layout.addWidget(delete_btn)
        
        # Export button
        export_btn = QPushButton()
        export_btn.setIcon(QIcon("src/ui/assets/download.svg"))
        export_btn.setIconSize(QSize(16, 16))
        export_btn.setStyleSheet(button_style)
        export_btn.setToolTip("Export to Excel")
        export_btn.clicked.connect(self.export_to_excel)
        filter_layout.addWidget(export_btn)
        
        # Add filter layout to panel
        table_panel.content_layout.addLayout(filter_layout)
        
        # Enhanced table - more compact
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Type', 'Confidence', 'Contamination', 'Classification', 'Timestamp'
        ])
        
        # Set column widths - optimized for smaller space
        self.table.setColumnWidth(0, 40)   # ID column
        self.table.setColumnWidth(1, 90)   # Type column
        self.table.setColumnWidth(2, 70)   # Confidence column
        
        # Set header and column behavior
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        
        # Enhanced table properties - more compact
        self.table.setShowGrid(True)
        self.table.setGridStyle(Qt.SolidLine)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setFrameShadow(QFrame.Plain)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setMaximumHeight(250)  # Reduced height to fit better
        self.table.setAlternatingRowColors(True)
        
        # Enhanced table style
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['background']};
                alternate-background-color: {COLORS['panel']};
                color: {COLORS['text']};
                gridline-color: {COLORS['grid']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                font-family: 'Fredoka';
                font-size: 13px;
                outline: none;
                selection-background-color: {COLORS['hover']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                padding: 10px 5px;
                border: none;
                border-bottom: 2px solid {COLORS['border']};
                border-right: 1px solid {COLORS['grid']};
                font-family: 'Fredoka';
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QTableWidget::item {{
                padding: 8px 5px;
                border-bottom: 1px solid {COLORS['grid']};
                border-right: 1px solid {COLORS['grid']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['hover']};
                color: white;
            }}
            QHeaderView {{
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {COLORS['background']};
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        table_panel.content_layout.addWidget(self.table)
        
        # Enhanced Pie Chart Panel - more compact
        pie_panel = Panel("Waste Distribution")  
        self.pie_chart = PieChartWidget()
        self.pie_chart.setMinimumSize(280, 280)  # Increased from 200x200
        self.pie_chart.setMaximumSize(320, 320)  # Increased from 220x220
        self.pie_chart.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        pie_panel.content_layout.addWidget(self.pie_chart)
        
        # Add panels to top layout
        top_layout.addWidget(table_panel, 2)  # Reduced from 3 to give more space to pie chart
        top_layout.addWidget(pie_panel, 1)    # Pie chart gets more space
        
        # Enhanced Bar Chart Panel - more compact
        bar_panel = Panel("Waste Generation by Type")
        
        # Add bar chart with better sizing
        self.bar_chart = BarChartWidget()
        self.bar_chart.setMinimumHeight(180)  # Reduced height
        self.bar_chart.setMaximumHeight(220)  # Maximum height constraint
        bar_panel.content_layout.addWidget(self.bar_chart)
        
        # Add layouts to main layout
        content_layout.addLayout(top_layout)
        content_layout.addWidget(bar_panel)
        
        # Add content widget directly (no scroll area)
        main_layout.addWidget(content_widget)
        
        # Schedule initial updates after UI is set up for smoother startup
        QTimer.singleShot(0, self.update_data)
        QTimer.singleShot(0, self.update_charts)
        
    def setup_timer(self):
        # Update every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)  # 1 second interval
        
    def update_time_filter(self, time_filter):
        # Update all charts with the new time filter
        self.bar_chart.set_time_filter(time_filter)
        self.update_charts()
        
    def update_data(self):
        """Update both table and charts with current filter settings"""
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
            conditions = [f"timestamp >= {time_conditions[time_filter]}"]
            params = {}
            
            selected_type = self.type_filter.currentText()
            if selected_type != "All Types":
                conditions.append("waste_type = :waste_type")
                params['waste_type'] = selected_type
            
            selected_classification = self.classification_filter.currentText()
            if selected_classification != "All Classifications":
                conditions.append("classification = :classification")
                params['classification'] = selected_classification
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
            SELECT id, waste_type, confidence_level, contamination, classification, timestamp
            FROM detections
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT 100
            """
            
            df = pd.read_sql_query(query, conn, params=params)
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
                
                # Confidence
                item = QTableWidgetItem(str(row['confidence_level']))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 2, item)
                
                # Contamination
                contamination = float(row['contamination'])
                item = QTableWidgetItem(f"{contamination:.2f}%")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, item)
                
                # Classification with enhanced colors
                item = QTableWidgetItem(str(row['classification']))
                item.setTextAlignment(Qt.AlignCenter)
                if row['classification'] == 'High Value':
                    item.setForeground(QColor(COLORS['accent']))  # Green
                elif row['classification'] == 'Low Value':
                    item.setForeground(QColor('#3b82f6'))  # Blue
                elif row['classification'] == 'Rejected':
                    item.setForeground(QColor(COLORS['warning']))  # Yellow
                elif row['classification'] == 'Mixed':
                    item.setForeground(QColor(COLORS['error']))  # Red
                self.table.setItem(i, 4, item)
                
                # Timestamp
                timestamp = datetime.strptime(str(row['timestamp']), '%Y-%m-%d %H:%M:%S')
                formatted_timestamp = timestamp.strftime('%m-%d %H:%M:%S')
                item = QTableWidgetItem(formatted_timestamp)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 5, item)
                    
        except Exception as e:
            print(f"Error updating table: {str(e)}")
            
    def update_charts(self):
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
            conditions = [f"timestamp >= {time_conditions[time_filter]}"]
            params = {}
            
            selected_type = self.type_filter.currentText()
            if selected_type != "All Types":
                conditions.append("waste_type = :waste_type")
                params['waste_type'] = selected_type
            
            selected_classification = self.classification_filter.currentText()
            if selected_classification != "All Classifications":
                conditions.append("classification = :classification")
                params['classification'] = selected_classification
            
            where_clause = " AND ".join(conditions)
            
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

    def export_to_excel(self):
        try:
            # Get the current filtered data
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
            SELECT id, waste_type, confidence_level, contamination, classification, timestamp
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
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                raise Exception("No data to export")
            
            # Format timestamp to remove year
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%m-%d %H:%M:%S')
            
            # Generate default filename with current timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f'ecograde_export_{timestamp}.xlsx'
            
            # Show file dialog for saving
            file_dialog = QFileDialog()
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            file_dialog.setNameFilter("Excel Files (*.xlsx)")
            file_dialog.setDefaultSuffix("xlsx")
            file_dialog.selectFile(default_filename)
            
            if file_dialog.exec_():
                filename = file_dialog.selectedFiles()[0]
                
                # Export to Excel
                df.to_excel(filename, index=False, engine='openpyxl')
                
                # Show success message
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(f"Data exported successfully to {filename}")
                msg.setWindowTitle("Export Successful")
                msg.setStyleSheet(f"""
                    QMessageBox {{
                        background-color: {COLORS['panel']};
                        color: {COLORS['text']};
                        border: 2px solid {COLORS['border']};
                        border-radius: 10px;
                    }}
                    QMessageBox QLabel {{
                        color: {COLORS['text']};
                        font-family: 'Fredoka';
                        font-size: 13px;
                    }}
                    QPushButton {{
                        background-color: {COLORS['background']};
                        color: {COLORS['text']};
                        border: 2px solid {COLORS['border']};
                        padding: 8px 20px;
                        border-radius: 8px;
                        font-family: 'Fredoka';
                        font-weight: 600;
                        min-width: 80px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid {COLORS['accent']};
                    }}
                """)
                msg.exec_()
            
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(f"Error exporting data: {str(e)}")
            msg.setWindowTitle("Export Error")
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {COLORS['panel']};
                    color: {COLORS['text']};
                    border: 2px solid {COLORS['error']};
                    border-radius: 10px;
                }}
                QMessageBox QLabel {{
                    color: {COLORS['text']};
                    font-family: 'Fredoka';
                    font-size: 13px;
                }}
                QPushButton {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text']};
                    border: 2px solid {COLORS['border']};
                    padding: 8px 20px;
                    border-radius: 8px;
                    font-family: 'Fredoka';
                    font-weight: 600;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    border: 2px solid {COLORS['error']};
                }}
            """)
            msg.exec_() 

    def delete_selected(self):
        """Delete selected rows from the database."""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select rows to delete.")
            return
        
        # Get unique row indices
        row_indices = set(item.row() for item in selected_rows)
        
        # Enhanced confirmation dialog
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(f"Are you sure you want to delete {len(row_indices)} selected items?")
        msg.setInformativeText("This action cannot be undone.")
        msg.setWindowTitle("Confirm Deletion")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
            }}
            QMessageBox QLabel {{
                color: {COLORS['text']};
                font-family: 'Fredoka';
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 20px;
                font-family: 'Fredoka';
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                border: 2px solid {COLORS['error']};
            }}
        """)
        
        if msg.exec_() == QMessageBox.Yes:
            try:
                conn = sqlite3.connect('data/measurements.db')
                cursor = conn.cursor()
                
                # Get IDs of selected rows
                ids_to_delete = []
                for row in row_indices:
                    id_item = self.table.item(row, 0)
                    if id_item:
                        ids_to_delete.append(int(id_item.text()))
                
                # Delete rows from database
                placeholders = ','.join('?' * len(ids_to_delete))
                cursor.execute(f"DELETE FROM detections WHERE id IN ({placeholders})", ids_to_delete)
                conn.commit()
                conn.close()
                
                # Update the table and charts
                self.update_data()
                
                # Show success message
                QMessageBox.information(self, "Success", "Selected items have been deleted.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete items: {str(e)}")
                if 'conn' in locals():
                    conn.close() 