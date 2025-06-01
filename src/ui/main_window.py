from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from .views.front_page import FrontPageWidget
from .views.main_view import MainView
from .analytics import AnalyticsWidget
from .widgets.sidebar_button import SidebarButton

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_view = "front"
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Object Detection Dashboard')
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("QMainWindow { background-color: #111827; }")
        
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
        self.create_front_page()
        self.create_main_view()
        self.create_analytics_view()
        
        # Add widgets to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_stack, 1)
        
        # Initially hide sidebar and show front page
        self.show_front_page()
        
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(80)
        sidebar.setStyleSheet("QWidget { background-color: #1f2937; border-radius: 15px; }")
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        
        # Logo placeholder
        logo_btn = SidebarButton("logo.png")
        logo_btn.setText("🔄")
        logo_btn.setStyleSheet(logo_btn.styleSheet() + "QPushButton { background-color: #10b981; }")
        
        # Back to front page button
        front_btn = SidebarButton("front.png")
        front_btn.setText("◀")
        front_btn.clicked.connect(lambda: self.switch_view("front"))
        
        # Navigation buttons
        home_btn = SidebarButton("home.png")
        home_btn.clicked.connect(lambda: self.switch_view("main"))
        
        analytics_btn = SidebarButton("stats.png")
        analytics_btn.clicked.connect(lambda: self.switch_view("analytics"))
        
        info_btn = SidebarButton("info.png")
        power_btn = SidebarButton("power.png")
        power_btn.clicked.connect(self.close)
        
        sidebar_layout.addWidget(logo_btn)
        sidebar_layout.addWidget(front_btn)
        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(home_btn)
        sidebar_layout.addWidget(analytics_btn)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(info_btn)
        sidebar_layout.addWidget(power_btn)
        
        return sidebar
              
    def create_front_page(self):
        front_page = FrontPageWidget(self)
        self.content_stack.addWidget(front_page)
        
    def show_front_page(self):
        self.sidebar.hide()
        self.content_stack.setCurrentIndex(0)
        
    def show_main_content(self):
        self.sidebar.show()
        
    def create_main_view(self):
        main_view = MainView()
        self.content_stack.addWidget(main_view)
    
    def create_analytics_view(self):
        self.analytics_view = AnalyticsWidget()
        self.content_stack.addWidget(self.analytics_view)
    
    def switch_view(self, view_name):
        if view_name == "front":
            self.content_stack.setCurrentIndex(0)
            self.sidebar.hide()
        elif view_name == "main":
            self.content_stack.setCurrentIndex(1)
            self.sidebar.show()
        elif view_name == "analytics":
            self.content_stack.setCurrentIndex(2)
            self.sidebar.show()
            if hasattr(self, 'analytics_view'):
                self.analytics_view.update_data()
        self.current_view = view_name 