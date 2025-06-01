import os
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer

class PieChartWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 4), facecolor='#1e3a8a')
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, facecolor='#1e3a8a')
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
                wedges, texts, autotexts = self.ax.pie(
                    sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                    startangle=90, textprops={'color': 'white'})
                self.ax.set_title('Detection Results Distribution', color='white', fontsize=12, pad=20)
            else:
                self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
        else:
            self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
        self.fig.tight_layout()
        self.draw()

class BarChartWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 4), facecolor='#1e3a8a')
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, facecolor='#1e3a8a')
        self.update_chart()
        # Add timer for real-time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(2000)  # update every 2 seconds

    def update_chart(self, excel_path='detections.xlsx'):
        self.ax.clear()
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path)
            if 'waste_type' in df.columns:
                counts = df['waste_type'].value_counts()
                items = counts.index.tolist()
                values = counts.values.tolist()
                colors = ['#10b981', '#34d399', '#6ee7b7', '#f59e42', '#ef4444', '#6366f1', '#a3e635', '#f472b6'][:len(items)]
                bars = self.ax.bar(items, values, color=colors)
                self.ax.set_ylim(0, max(values + [1]))
                self.ax.set_facecolor('#1e3a8a')
                self.ax.tick_params(colors='white')
                for spine in self.ax.spines.values():
                    spine.set_color('white')
                self.ax.set_title('Detections per Object Type', color='white', fontsize=12, pad=20)
            else:
                self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
        else:
            self.ax.text(0.5, 0.5, 'No Data', color='white', ha='center', va='center')
        self.fig.tight_layout()
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