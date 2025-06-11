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

# Color scheme
COLORS = {
    'background': '#111827',
    'panel': '#2D2D2D',
    'text': '#FFFFFF',
    'accent': '#4CAF50',  # Green for High Value
    'warning': '#FFC107',  # Yellow for Rejects
    'error': '#F44336',   # Red for Mixed
    'border': '#3D3D3D',
    'grid': '#3D3D3D'
}

# Pie chart color mapping
PIE_LABELS = ["High Value", "Low Value", "Rejects", "Mixed"]
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
    'Mixed': '#ff7043',
    
}

def get_bar_color(waste_type):
    return BAR_TYPE_COLORS.get(waste_type, '#bdbdbd')

class Panel(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border-radius: 10px;
                border: 1px solid #16324b;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title label with centered text and adjusted styling
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-family: 'Fredoka';
                font-size: 14px;
                font-weight: 600;
                background-color: transparent;
                border: none;
                padding: 2px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
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

        # Set background color for analytics view and scroll area
        self.setStyleSheet("background-color: #111827;")

        # Add a scroll area for the analytics content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: #111827; }")

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #111827;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(16, 16, 16, 16)

        # Top section (Table and Pie Chart)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)
        
        # Table Panel
        table_panel = Panel("Recent Detections")
        table_panel.content_layout.setContentsMargins(0, 0, 0, 0)  # Remove panel content margins
        table_panel.content_layout.setSpacing(0)  # Remove spacing between panel elements
        
        # Add filter controls
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        filter_layout.setContentsMargins(16, 16, 16, 16)  # Add consistent margins
        filter_layout.addSpacing(0)  # Remove extra spacing
        
        # Time filter dropdown
        time_filter_label = QLabel("Time Range:")
        time_filter_label.setFont(QFont('Fredoka', 12))
        time_filter_label.setStyleSheet("color: white; padding: 0; border: none;")
        self.time_filter = QComboBox()
        self.time_filter.addItems(["Past Hour", "Past Day", "Past Week", "Past Month"])
        
        # Style the dropdowns with Fredoka Medium
        dropdown_style = """
            QComboBox {
                background-color: #111827;
                color: white;
                border: 1px solid #16324b;
                border-radius: 5px;
                padding: 1px 3px;
                font-family: 'Fredoka';
                font-size: 11px;
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
                font-family: 'Fredoka';
                font-size: 12px;
            }
        """
        
        self.time_filter.setStyleSheet(dropdown_style)
        
        # Add dropdown filters with Fredoka Medium
        type_filter_label = QLabel("Type:")
        type_filter_label.setFont(QFont('Fredoka', 12))
        type_filter_label.setStyleSheet("color: white; padding: 0; border: none;")
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        self.type_filter.addItems([
            "PET Bottle", "HDPE Plastic", "PP", "LDPE", 
            "Tin-Steel Can", "UHT Box"
        ])
        
        classification_filter_label = QLabel("Classification:")
        classification_filter_label.setFont(QFont('Fredoka', 12))
        classification_filter_label.setStyleSheet("color: white; padding: 0; border: none;")
        self.classification_filter = QComboBox()
        self.classification_filter.addItem("All Classifications")
        self.classification_filter.addItems([
            "High Value", "Low Value", "Rejects", "Mixed Trash"
        ])
        
        # Apply dropdown style to all comboboxes
        self.type_filter.setStyleSheet(dropdown_style)
        self.classification_filter.setStyleSheet(dropdown_style)
        
        # Connect dropdown signals
        self.time_filter.currentTextChanged.connect(self.update_data)
        self.type_filter.currentTextChanged.connect(self.update_data)
        self.classification_filter.currentTextChanged.connect(self.update_data)
        
        # Add dropdowns to filter layout
        filter_layout.addWidget(time_filter_label)
        filter_layout.addWidget(self.time_filter)
        filter_layout.addWidget(type_filter_label)
        filter_layout.addWidget(self.type_filter)
        filter_layout.addWidget(classification_filter_label)
        filter_layout.addWidget(self.classification_filter)
        
        # Add stretch to push export button to the right
        filter_layout.addStretch()
        
        # Add spacing before export button
        filter_layout.addSpacing(200)  # Add 20 pixels of spacing
        
        # Add delete button
        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon("src/ui/assets/trash-2.svg"))
        delete_btn.setIconSize(QSize(15, 15))
        delete_btn.setFixedSize(26, 26)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #111827;
                border: 1px solid #16324b;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected)
        filter_layout.addWidget(delete_btn)
        
        # Add export button
        export_btn = QPushButton()
        export_btn.setIcon(QIcon("src/ui/assets/download.svg"))
        export_btn.setIconSize(QSize(15, 15))  # Reduced from 20,20 to 16,16
        export_btn.setFixedSize(26, 26)  # Reduced from 32,32 to 28,28
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #111827;
                border: 1px solid #16324b;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                border: 1px solid #3ac194;
            }
        """)
        export_btn.clicked.connect(self.export_to_excel)
        filter_layout.addWidget(export_btn)
        
        filter_layout.addStretch()
        
        # Add filter layout to panel
        table_panel.content_layout.addLayout(filter_layout)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Type', 'Confidence', 'Contamination', 'Classification', 'Timestamp'
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 54)  # ID column
        self.table.setColumnWidth(1, 110)  # Type column
        self.table.setColumnWidth(2, 80)   # Confidence column
        
        # Set header and column behavior
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        
        # Set table properties
        self.table.setShowGrid(True)
        self.table.setGridStyle(Qt.SolidLine)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setFrameShadow(QFrame.Plain)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setMaximumHeight(300)
        
        # Set table style
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #111827;
                color: white;
                gridline-color: #16324b;
                border: 1px solid #16324b;
                border-radius: 0px;
                font-family: 'Fredoka';
                font-size: 12px;
                outline: none;
            }
            QHeaderView::section {
                background-color: #111827;
                color: white;
                padding: 5px;
                border: 1px solid #16324b;
                border-top: 1px solid #16324b;
                border-bottom: 1px solid #16324b;
                font-family: 'Fredoka';
                font-size: 11px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #16324b;
            }
            QHeaderView {
                border: none;
                border-bottom: 1px solid #16324b;
            }
            QScrollBar:vertical {
                border: none;
                background: #111827;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #16324b;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        table_panel.content_layout.addWidget(self.table)
        
        # Pie Chart Panel
        pie_panel = Panel("Waste Distribution")  
        self.pie_chart = PieChartWidget()
        self.pie_chart.setMinimumSize(250, 250)
        self.pie_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pie_panel.content_layout.addWidget(self.pie_chart)
        
        # Add panels to top layout
        top_layout.addWidget(table_panel, 2)
        top_layout.addWidget(pie_panel, 1)
        
        # Bar Chart Panel
        bar_panel = Panel("Waste Generation by Type")
        
        # Add bar chart with adjusted size
        self.bar_chart = BarChartWidget()
        self.bar_chart.setMinimumHeight(250)  # Increased from 200
        self.bar_chart.setMaximumHeight(270)  # Increased from 220
        bar_panel.content_layout.addWidget(self.bar_chart)
        
        # Add layouts to main layout
        content_layout.addLayout(top_layout)
        content_layout.addWidget(bar_panel)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
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
                
                # Classification
                item = QTableWidgetItem(str(row['classification']))
                item.setTextAlignment(Qt.AlignCenter)
                if row['classification'] == 'High Value':
                    item.setForeground(QColor(COLORS['accent']))  # Green
                elif row['classification'] == 'Low Value':
                    item.setForeground(QColor('#2196F3'))  # Blue
                elif row['classification'] == 'Rejects':
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
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #111827;
                        color: white;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QPushButton {
                        background-color: #16324b;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #1e3a8a;
                    }
                """)
                msg.exec_()
            
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(f"Error exporting data: {str(e)}")
            msg.setWindowTitle("Export Error")
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #111827;
                    color: white;
                }
                QMessageBox QLabel {
                    color: white;
                }
                QPushButton {
                    background-color: #16324b;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #1e3a8a;
                }
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
        
        # Confirm deletion
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(f"Are you sure you want to delete {len(row_indices)} selected items?")
        msg.setWindowTitle("Confirm Deletion")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #111827;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
            }
            QPushButton {
                background-color: #111827;
                color: white;
                border: 1px solid #16324b;
                border-radius: 5px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                border: 1px solid #3ac194;
            }
        """)
        
        if msg.exec_() == QMessageBox.Yes:
            try:
                # Get IDs of selected rows
                ids_to_delete = []
                for row in row_indices:
                    id_item = self.table.item(row, 0)
                    if id_item:
                        ids_to_delete.append(id_item.text())
                
                # Delete from database
                db_path = Path('data/measurements.db')
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                
                # Delete each selected row
                for id_to_delete in ids_to_delete:
                    c.execute('DELETE FROM detections WHERE id = ?', (id_to_delete,))
                
                conn.commit()
                conn.close()
                
                # Update the table
                self.update_data()
                
                # Show success message
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(f"Successfully deleted {len(ids_to_delete)} items.")
                msg.setWindowTitle("Success")
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #111827;
                        color: white;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QPushButton {
                        background-color: #111827;
                        color: white;
                        border: 1px solid #16324b;
                        border-radius: 5px;
                        padding: 5px 15px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        border: 1px solid #3ac194;
                    }
                """)
                msg.exec_()
                
            except Exception as e:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText(f"Failed to delete items: {str(e)}")
                msg.setWindowTitle("Error")
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #111827;
                        color: white;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QPushButton {
                        background-color: #111827;
                        color: white;
                        border: 1px solid #16324b;
                        border-radius: 5px;
                        padding: 5px 15px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        border: 1px solid #3ac194;
                    }
                """)
                msg.exec_() 