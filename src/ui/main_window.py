from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QDesktopWidget, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from .views.front_page import FrontPageWidget
from .views.main_view import MainView
from .analytics import AnalyticsWidget
from .widgets.sidebar_button import SidebarButton
from .views.about_view import AboutView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_view = "front"
        self.initUI()
        
    def initUI(self):
        self.setFixedSize(1280, 720)  # Set the window size
        self.center()         
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
        front_btn = SidebarButton("src/ui/assets/corner-up-left.svg")
        front_btn.clicked.connect(lambda: self.switch_view("front"))
        
        # Navigation buttons
        home_btn = SidebarButton("src/ui/assets/home.svg")
        home_btn.clicked.connect(lambda: self.switch_view("main"))
        
        analytics_btn = SidebarButton("src/ui/assets/bar-chart.svg")
        analytics_btn.clicked.connect(lambda: self.switch_view("analytics"))
        
        info_btn = SidebarButton("src/ui/assets/info.svg")
        info_btn.clicked.connect(lambda: self.switch_view("about"))
        power_btn = SidebarButton("src/ui/assets/power.svg")
        power_btn.clicked.connect(self.close)
        
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
    
    def create_about_view(self):
        self.about_view = AboutView()
        self.content_stack.addWidget(self.about_view)
    
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
        elif view_name == "about":
            self.content_stack.setCurrentIndex(3)
            self.sidebar.show()
        self.current_view = view_name 

    def show_about_dialog(self):
        about_text = (
            "<div style='font-family:Segoe UI,Arial,sans-serif; color:#222; background:#f9f9f9; padding:18px; border-radius:12px; max-width:520px;'>"
            "<h2 style='color:#10b981; margin-bottom:8px;'>EcoGrade</h2>"
            "<div style='font-size:15px; color:#222; margin-bottom:10px;'><b>LEVERAGING CONVOLUTIONAL NEURAL NETWORKS AND MULTI-DECISION ANALYSIS FOR ADVANCED REAL-TIME DETECTION AND QUALITY ASSESSMENT OF NON-BIODEGRADABLE WASTE MATERIALS</b></div>"
            "<div style='font-size:13px; color:#333; margin-bottom:16px;'>"
            "This study presents EcoGrade, an innovative system that enhances the assessment and classification of non-biodegradable waste through the integration of YOLOv8-based Convolutional Neural Networks (CNN) for real-time object detection and Multi-Criteria Decision Analysis (MCDA) for data-driven quality evaluation. Focusing on plastic types such as Polyethylene Terephthalate (PET), High-Density Polyethylene (HDPE), Low-Density Polyethylene (LDPE), and Polypropylene (PP), as well as Tin/Steel Cans, the system detects and analyzes waste materials based on material type, opacity, and contamination levels to determine their value. The YOLOv11s model was trained on a custom dataset to ensure precise classification, while the MCDA framework assigned weighted scores to evaluate material quality and guide decision-making. EcoGrade was tested under real-world conditions, specifically in partnership with the City Environmental Management Office (CEMO) of Marikina City, and its performance was benchmarked against ISO 25010 software quality standards, particularly in terms of functionality, reliability, and efficiency. Results demonstrated that the system achieved high detection accuracy and significantly improved classification performance compared to conventional models, offering a scalable, intelligent solution that supports sustainable waste management and promotes circular economy practices."
            "</div>"
            "<div style='font-size:14px; color:#222; margin-bottom:8px;'><b>Team Members</b></div>"
            "<ul style='font-size:13px; color:#333; margin:0 0 10px 18px; padding:0;'>"
            "<li><b>Villas, Rakee D.</b> – Fullstack Developer</li>"
            "<li><b>Vargas, Vian Andrei C.</b> – Hardware Engineer, Documentation</li>"
            "<li><b>Turingan, Fraizer Quinn R.</b> – Backend Developer, Documentation</li>"
            "<li><b>Santoceldez, Rogin R.</b> – Data Gatherer, Documentation</li>"
            "<li><b>Altiche, Adriane</b> – Frontend Developer, Documentation</li>"
            "</ul>"
            "<div style='font-size:12px; color:#666; margin-top:10px; border-top:1px solid #e0e0e0; padding-top:8px;'>"
            "&copy; 2024 EcoGrade Project. All rights reserved."
            "</div>"
            "</div>"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("About EcoGrade")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("QLabel{min-width:480px; font-size:13px;} QMessageBox{background:#f9f9f9;}")
        msg.exec_() 