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
import time

class PieChartWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 2.5), facecolor='#111827')
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, facecolor='#111827')
        self.classification_colors = {
            'High Value Recyclable': '#4CAF50',   # Green
            'Low Value': '#2196F3',    # Blue
            'Rejects': '#FFC107',      # Yellow
            'Mixed': '#F44336'         # Red
        }
        self.update_chart()

    def update_chart_with_data(self, items, values):
        self.ax.clear()
        if not items or not values:
            self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
            self.draw()
            return

        # Get colors for each classification
        colors = [self.classification_colors.get(c, '#bdbdbd') for c in items]
        
        # Create pie chart
        wedges, texts, autotexts = self.ax.pie(
            values,
            labels=None,
            colors=colors,
            autopct='%1.1f%%',
            textprops={'color': 'white', 'fontsize': 8},
            wedgeprops={'linewidth': 1, 'edgecolor': '#16324b'}
        )

        # Style percentage labels
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(8)

        # Add border
        for spine in self.ax.spines.values():
            spine.set_visible(True)
            spine.set_color('#16324b')
            spine.set_linewidth(1)

        # Create legend with all classifications
        legend_handles = []
        legend_labels = []
        for classification in self.classification_colors.keys():
            if classification in items:
                legend_handles.append(plt.Rectangle((0, 0), 1, 1, 
                    facecolor=self.classification_colors[classification]))
                legend_labels.append(classification.replace(' Recyclable', ''))

        if legend_handles:
            legend = self.ax.legend(
                handles=legend_handles,
                labels=legend_labels,
                loc='upper left',
                bbox_to_anchor=(-0.25, 0.9),
                frameon=False,
                fontsize=8
            )
            for text in legend.get_texts():
                text.set_color('white')

        self.fig.tight_layout()
        self.draw()

    def update_chart(self):
        try:
            db_path = Path('data/measurements.db')
            conn = sqlite3.connect(str(db_path))
            
            query = """
            SELECT classification, COUNT(*) as count
            FROM detections
            WHERE timestamp >= datetime('now', '-1 hour')
            GROUP BY classification
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                self.update_chart_with_data(
                    df['classification'].tolist(),
                    df['count'].tolist()
                )
            else:
                self.ax.clear()
                self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
                self.draw()
                
        except Exception as e:
            print(f"Error updating pie chart: {str(e)}")
            self.ax.clear()
            self.ax.text(0.5, 0.5, 'Error Loading Data', color='white', ha='center', va='center')
            self.draw()

class BarChartWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 2.5), facecolor='#111827')
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, facecolor='#111827')
        self.time_filter = 'hour'  # Default to hour
        self.bar_width = 0.5  # Default bar width
        self.update_chart()

    def set_time_filter(self, time_filter):
        self.time_filter = time_filter
        self.update_chart()
        
    def set_bar_width(self, width):
        self.bar_width = width
        
    def update_chart_with_data(self, items, values):
        self.ax.clear()
        
        if not items or not values:
            self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
            self.draw()
            return
            
        # Define colors for each waste type
        waste_type_colors = {
            'PET Bottle': '#10b981',      # Green
            'HDPE Plastic': '#34d399',    # Light Green
            'PP': '#f59e42',              # Orange
            'LDPE': '#ab47bc',            # Purple
            'Tin-Steel Can': '#bdbdbd',   # Gray
            'UHT Box': '#ff7043',         # Deep Orange
        }
        
        # Get colors for each waste type, default to gray if not found
        colors = [waste_type_colors.get(wt, '#bdbdbd') for wt in items]
        
        # Calculate bar positions based on number of items
        num_items = len(items)
        if num_items == 1:
            x_positions = [0.5]  # Center the single bar
        else:
            x_positions = range(len(items))
        
        # Create bars with proper positioning and width
        bars = self.ax.bar(x_positions, values, color=colors, width=self.bar_width)
        
        # Set x-axis limits to prevent single bar from stretching
        if num_items == 1:
            self.ax.set_xlim(-0.5, 1.5)  # Center the single bar with padding
        else:
            self.ax.set_xlim(-0.5, len(items) - 0.5)  # Add padding for multiple bars
        
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
        self.ax.tick_params(colors='white', labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color('white')
            spine.set_linewidth(1)
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            self.ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', color='white', fontsize=9)
        
        # Add border
        for spine in self.ax.spines.values():
            spine.set_visible(True)
            spine.set_color('white')
            spine.set_linewidth(1)
        
        # Adjust layout to prevent label cutoff
        self.fig.tight_layout()
        self.draw()

    def update_chart(self):
        try:
            db_path = Path('data/measurements.db')
            conn = sqlite3.connect(str(db_path))
            
            time_conditions = {
                'hour': "datetime('now', '-1 hour')",
                'day': "datetime('now', '-1 day')",
                'week': "datetime('now', '-7 days')",
                'month': "datetime('now', '-30 days')"
            }
            
            query = f"""
            SELECT waste_type, COUNT(*) as count
            FROM detections
            WHERE timestamp >= {time_conditions[self.time_filter]}
            GROUP BY waste_type
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                self.update_chart_with_data(
                    df['waste_type'].tolist(),
                    df['count'].tolist()
                )
            else:
                self.ax.clear()
                self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
                self.draw()
                
        except Exception as e:
            print(f"Error updating bar chart: {str(e)}")
            self.ax.clear()
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