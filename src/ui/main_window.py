from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QDesktopWidget, QMessageBox, QApplication, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from .views.front_page import FrontPageWidget
from .views.main_view import MainView
from .analytics import AnalyticsWidget
from .widgets.sidebar_button import SidebarButton
from .views.about_view import AboutView
import sys
import logging
import traceback

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_view = "front"
        self.initUI()
        
    def initUI(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle('EcoGrade')
        self.setWindowIcon(QIcon('src/ui/assets/LOGO.ico'))
        
        # Set minimum and maximum window size
        self.setMinimumSize(1024, 768)  # Reduced minimum size for smaller screens
        self.setMaximumSize(3840, 2160)  # Support for 4K displays
        
        # Create main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = self.create_sidebar()
        self.sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        main_layout.addWidget(self.sidebar)
        
        # Create content stack
        self.content_stack = QStackedWidget()
        self.content_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #0f172a;
            }
        """)
        self.create_front_page()
        self.create_main_view()
        self.create_analytics_view()
        self.create_about_view()
        
        main_layout.addWidget(self.content_stack)
        
        # Set main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Center the window on screen
        self.center()
        
        # Start in maximized state
        self.showMaximized()
        self.setWindowState(Qt.WindowMaximized)
        
        # Show front page and hide sidebar initially
        self.show_front_page()
        
    def center(self):
        # Center the window when not maximized
        if not self.isMaximized():
            qr = self.frameGeometry()
            cp = QDesktopWidget().availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())
        
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(80)
        sidebar.setStyleSheet("""
            QWidget { 
                background-color: #1f2937; 
                border-top-right-radius: 15px; 
                border-bottom-left-radius: 0px;
                border-top-left-radius: 0px;
                border-bottom-right-radius: 15px;
                border: 1px solid #475569;
            }
        """)
        
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
        try:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self,
                'Confirm Exit',
                'Are you sure you want to exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Stop the video processor
                if hasattr(self, 'main_view') and hasattr(self.main_view, 'video_processor'):
                    self.main_view.video_processor.stop()
                
                # Stop any running cameras
                if hasattr(self, 'main_view'):
                    if hasattr(self.main_view, 'object_detection_camera'):
                        self.main_view.object_detection_camera.stop_camera()
                    if hasattr(self.main_view, 'residue_scan_camera'):
                        self.main_view.residue_scan_camera.stop_camera()
                
                # Accept the close event
                event.accept()
            else:
                # Reject the close event
                event.ignore()
            
        except Exception as e:
            logging.error(f"Error during window close: {str(e)}")
            logging.error(traceback.format_exc())
            # Still accept the close event even if there's an error
            event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())