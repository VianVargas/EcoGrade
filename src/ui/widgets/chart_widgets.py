import os
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
import matplotlib.pyplot as plt
import sqlite3
from pathlib import Path

class PieChartWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 4), facecolor='#111827')
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, facecolor='#111827')
        self.update_chart()
        # Add timer for real-time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(2000)  # update every 2 seconds

    def update_chart(self, excel_path='detections.xlsx'):
        self.ax.clear()
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path)
            if 'result' in df.columns:
                counts = df['result'].value_counts()
                labels = counts.index.tolist()
                sizes = counts.values.tolist()
                colors = ['#10b981', '#f59e42', '#ef4444', '#6366f1', '#6ee7b7'][:len(labels)]
                
                # Calculate percentages for better label display
                total = sum(sizes)
                percentages = [f'{size/total*100:.1f}%' for size in sizes]
                
                # Create pie chart with improved labels
                wedges, texts, autotexts = self.ax.pie(
                    sizes, 
                    labels=labels,
                    colors=colors,
                    autopct='%1.1f%%',
                    startangle=90,
                    textprops={'color': 'white', 'fontsize': 10},
                    pctdistance=0.85,  # Move percentage labels further out
                    labeldistance=1.1   # Move labels further out
                )
                
                # Make the percentage labels more visible
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(10)
                    autotext.set_fontweight('bold')
                
                # Add a white circle in the middle to create a donut chart
                centre_circle = plt.Circle((0,0), 0.70, fc='#1e3a8a')
                self.ax.add_artist(centre_circle)
                
                # Equal aspect ratio ensures that pie is drawn as a circle
                self.ax.axis('equal')
            else:
                self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
        else:
            self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
        self.fig.tight_layout()
        self.draw()

class BarChartWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 2.5), facecolor='#111827')  # Made figure smaller
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, facecolor='#111827')
        self.time_filter = 'Past Hour'  # Default to hour
        self.update_chart()
        # Add timer for real-time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(2000)  # update every 2 seconds

    def set_time_filter(self, time_filter):
        self.time_filter = time_filter
        self.update_chart()

    def update_chart(self):
        self.ax.clear()
        try:
            # Connect to SQLite database
            db_path = Path('data/measurements.db')
            conn = sqlite3.connect(str(db_path))
            
            # Determine time filter
            time_conditions = {
                'Past Hour': "datetime('now', '-1 hour')",
                'Past Day': "datetime('now', '-1 day')",
                'Past Week': "datetime('now', '-7 days')",
                'Past Month': "datetime('now', '-30 days')"
            }
            
            # Get data for bar chart based on time filter
            query = f"""
            SELECT waste_type, COUNT(*) as count
            FROM detections
            WHERE timestamp >= {time_conditions[self.time_filter]}
            GROUP BY waste_type
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                items = df['waste_type'].tolist()
                values = df['count'].tolist()
                
                # Define colors for each waste type
                waste_type_colors = {
                    'PET Bottle': '#10b981',      # Green
                    'HDPE Plastic': '#34d399',    # Light Green
                    'PP': '#f59e42',              # Orange
                    'LDPE': '#ab47bc',            # Purple
                    'Tin-Steel Can': '#bdbdbd',   # Gray
                    'Mixed Trash': '#8d6e63',     # Brown
                    'UHT Box': '#ff7043',         # Deep Orange
                    'Other': '#789262'            # Olive
                }
                
                # Get colors for each waste type, default to gray if not found
                colors = [waste_type_colors.get(wt, '#bdbdbd') for wt in items]
                
                # Calculate bar width based on number of items
                num_items = len(items)
                if num_items == 1:
                    bar_width = 0.2  # Very narrow bar for single item
                    x_positions = [0.5]  # Center the single bar
                elif num_items <= 3:
                    bar_width = 0.3  # Narrower bars for few items
                    x_positions = range(len(items))
                else:
                    bar_width = 0.5  # Default width for many items
                    x_positions = range(len(items))
                
                # Create bars with proper positioning
                bars = self.ax.bar(x_positions, values, color=colors, width=bar_width)
                
                # Customize the appearance
                self.ax.set_ylim(0, max(values + [1]))
                self.ax.set_facecolor('#111827')
                self.fig.set_facecolor('#111827')
                
                # Set x-axis ticks and labels
                if num_items == 1:
                    self.ax.set_xticks([0.5])
                    self.ax.set_xticklabels(items, rotation=45, ha='right', color='white', fontsize=9)
                else:
                    self.ax.set_xticks(range(len(items)))
                    self.ax.set_xticklabels(items, rotation=45, ha='right', color='white', fontsize=9)
                
                # Style the ticks and labels
                self.ax.tick_params(colors='white', labelsize=9)  # Smaller font
                for spine in self.ax.spines.values():
                    spine.set_color('white')
                    spine.set_linewidth(1)
                
                # Add value labels on top of bars
                for bar in bars:
                    height = bar.get_height()
                    self.ax.text(bar.get_x() + bar.get_width()/2., height,
                                f'{int(height)}',
                                ha='center', va='bottom', color='white', fontsize=9)  # Smaller font
                
                # Add border
                for spine in self.ax.spines.values():
                    spine.set_visible(True)
                    spine.set_color('white')
                    spine.set_linewidth(1)
                
                # Adjust layout to prevent label cutoff
                self.fig.tight_layout()
            else:
                self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
                
        except Exception as e:
            print(f"Error updating bar chart: {str(e)}")
            self.ax.text(0.5, 0.5, 'Error Loading Data', color='white', ha='center', va='center')
            
        self.draw()

class DetectionTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.label = QLabel('Detections Table')
        self.label.setStyleSheet('color: white; font-size: 16px; font-weight: bold;')
        self.layout.addWidget(self.label)
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        self.update_table()
        # Add timer for real-time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_table)
        self.timer.start(2000)  # update every 2 seconds

    def update_table(self, excel_path='detections.xlsx'):
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path)
            self.table.setRowCount(len(df))
            self.table.setColumnCount(len(df.columns))
            self.table.setHorizontalHeaderLabels(df.columns)
            for i, row in df.iterrows():
                for j, col in enumerate(df.columns):
                    self.table.setItem(i, j, QTableWidgetItem(str(row[col])))
        else:
            self.table.setRowCount(0)
            self.table.setColumnCount(0) 