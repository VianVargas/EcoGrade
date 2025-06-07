import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFontDatabase
from src.ui.main_window import MainWindow
import os
from pathlib import Path

if __name__ == '__main__':
    # Enable high DPI scaling and use software OpenGL for smoother startup
    from PyQt5.QtGui import QGuiApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    app = QApplication(sys.argv)
    app.setApplicationName("ECOGRADE")
    app.setStyle('Fusion')
    

    window = MainWindow()
    # Set the application window icon to LOGO.ico for best Windows compatibility
    logo_path = os.path.join(os.path.dirname(__file__), 'src', 'ui', 'assets', 'LOGO.ico')
    if os.path.exists(logo_path):
        window.setWindowIcon(QIcon(logo_path))
    window.show()
    sys.exit(app.exec_()) 