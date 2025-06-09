from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QDesktopWidget, QMessageBox, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from .views.front_page import FrontPageWidget
from .views.main_view import MainView
from .analytics import AnalyticsWidget
from .widgets.sidebar_button import SidebarButton
from .views.about_view import AboutView
import sys
import logging

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_view = "front"
        self.initUI()
        
    def initUI(self):
        self.setFixedSize(1280, 720)  # Set the window size
        self.center()         
        self.setStyleSheet("""
            QMainWindow {
                background-color: #111827;
                font-family: 'Fredoka';
            }
            QWidget {
                font-family: 'Fredoka';
            }
        """)
        self.setWindowTitle("ECOGRADE")
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create sidebar (hidden for front page)
        self.sidebar = self.create_sidebar()
        
        # Create main content area
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #111827;
                font-family: 'Fredoka';
            }
        """)
        self.create_front_page()
        self.create_main_view()
        self.create_analytics_view()
        self.create_about_view()
        
        # Add widgets to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_stack, 1)
        
        # Initially hide sidebar and show front page
        self.show_front_page()
        
    def center(self):
        # Get the screen geometry
        qr = self.frameGeometry()
        # Get the center point of the screen
        cp = QDesktopWidget().availableGeometry().center()
        # Move the rectangle's center to the screen center
        qr.moveCenter(cp)
        # Move the top-left point of the window to match the centered rectangle
        self.move(qr.topLeft())
        
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(80)
        sidebar.setStyleSheet("QWidget { background-color: #1f2937; border-radius: 15px; }")
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        
        # Back to front page button
        self.front_btn = SidebarButton("src/ui/assets/corner-up-left.svg")
        self.front_btn.clicked.connect(lambda: self.switch_view("front"))
        
        # Navigation buttons
        self.home_btn = SidebarButton("src/ui/assets/video.svg")
        self.home_btn.clicked.connect(lambda: self.switch_view("main"))
        
        self.analytics_btn = SidebarButton("src/ui/assets/bar-chart.svg")
        self.analytics_btn.clicked.connect(lambda: self.switch_view("analytics"))
        
        self.info_btn = SidebarButton("src/ui/assets/info.svg")
        self.info_btn.clicked.connect(lambda: self.switch_view("about"))
        
        self.power_btn = SidebarButton("src/ui/assets/power.svg")
        self.power_btn.clicked.connect(self.close)
        
        sidebar_layout.addWidget(self.front_btn)
        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(self.home_btn)
        sidebar_layout.addWidget(self.analytics_btn)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.info_btn)
        sidebar_layout.addWidget(self.power_btn)
        
        return sidebar
              
    def create_front_page(self):
        front_page = FrontPageWidget(self)
        self.content_stack.addWidget(front_page)
        
    def show_front_page(self):
        self.sidebar.hide()
        self.content_stack.setCurrentIndex(0)
        self.front_btn.setChecked(True)
        self.home_btn.setChecked(False)
        self.analytics_btn.setChecked(False)
        self.info_btn.setChecked(False)
        
    def show_main_content(self):
        self.sidebar.show()
        
    def create_main_view(self):
        main_view = MainView()
        self.content_stack.addWidget(main_view)
    
    def create_analytics_view(self):
        self.analytics_view = AnalyticsWidget()
        self.content_stack.addWidget(self.analytics_view)
    
    def create_about_view(self):
        self.about_view = AboutView()
        self.content_stack.addWidget(self.about_view)
    
    def switch_view(self, view_name):
        # Uncheck all buttons first
        self.front_btn.setChecked(False)
        self.home_btn.setChecked(False)
        self.analytics_btn.setChecked(False)
        self.info_btn.setChecked(False)
        
        if view_name == "front":
            self.content_stack.setCurrentIndex(0)
            self.sidebar.hide()
            self.front_btn.setChecked(True)
        elif view_name == "main":
            self.content_stack.setCurrentIndex(1)
            self.sidebar.show()
            self.home_btn.setChecked(True)
        elif view_name == "analytics":
            self.content_stack.setCurrentIndex(2)
            self.sidebar.show()
            self.analytics_btn.setChecked(True)
            if hasattr(self, 'analytics_view'):
                self.analytics_view.update_data()
        elif view_name == "about":
            self.content_stack.setCurrentIndex(3)
            self.sidebar.show()
            self.info_btn.setChecked(True)
        self.current_view = view_name 

    def closeEvent(self, event):
        """Handle window close event"""
        # The MainView's closeEvent will handle camera cleanup
        self.main_view.closeEvent(event)
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

