from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QGridLayout
from .base_widgets import RoundedWidget

class GridWidget(RoundedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Filter section
        filter_layout = QHBoxLayout()
        filter_label = QLabel("FILTER")
        filter_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        filter_dropdown = QComboBox()
        filter_dropdown.addItems(["All", "Type 1", "Type 2", "Type 3"])
        filter_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #1e40af;
                color: white;
                border: 1px solid white;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
            }
        """)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addStretch()
        filter_layout.addWidget(filter_dropdown)
        
        # Grid
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(2)
        
        for i in range(7):
            for j in range(5):
                cell = QLabel()
                cell.setMinimumSize(60, 40)
                cell.setStyleSheet("""
                    QLabel {
                        background-color: #1e40af;
                        border: 1px solid white;
                        border-radius: 3px;
                    }
                """)
                grid_layout.addWidget(cell, i, j)
        
        layout.addLayout(filter_layout)
        layout.addWidget(grid_widget)
        layout.setSpacing(15)
        self.setLayout(layout) 