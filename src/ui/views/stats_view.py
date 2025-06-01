from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from ..widgets.base_widgets import RoundedWidget
from ..widgets.chart_widgets import PieChartWidget, BarChartWidget, DetectionTableWidget
from ..widgets.grid_widget import GridWidget

class StatsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        self.stats_layout = QVBoxLayout(self)
        self.stats_layout.setSpacing(20)
        
        # Top row
        top_layout = QHBoxLayout()
        
        # Grid widget (optional, can be replaced with table)
        # grid_widget = GridWidget()
        
        # Pie chart
        pie_widget = RoundedWidget()
        pie_layout = QVBoxLayout(pie_widget)
        self.pie_chart = PieChartWidget()
        pie_layout.addWidget(self.pie_chart)
        
        top_layout.addWidget(pie_widget, 1)
        
        # Bar chart
        bar_widget = RoundedWidget()
        bar_layout = QVBoxLayout(bar_widget)
        self.bar_chart = BarChartWidget()
        bar_layout.addWidget(self.bar_chart)
        
        top_layout.addWidget(bar_widget, 1)
        
        # Table
        table_widget = RoundedWidget()
        table_layout = QVBoxLayout(table_widget)
        self.detection_table = DetectionTableWidget()
        table_layout.addWidget(self.detection_table)
        
        self.stats_layout.addLayout(top_layout)
        self.stats_layout.addWidget(table_widget)
    
    def refresh_analytics(self):
        self.pie_chart.update_chart()
        self.bar_chart.update_chart()
        self.detection_table.update_table() 