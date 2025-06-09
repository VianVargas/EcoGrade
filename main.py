import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFontDatabase
from src.ui.main_window import MainWindow
from src.utils.app_client import app_client
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Enable high DPI scaling and use software OpenGL for smoother startup
        from PyQt5.QtGui import QGuiApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
        app = QApplication(sys.argv)
        app.setApplicationName("ECOGRADE")
        app.setStyle('Fusion')
        
        # Initialize the app client
        try:
            app_client.connect_to_pi()
        except Exception as e:
            print(f"Warning: Failed to connect to Raspberry Pi: {e}")
            print("The application will continue to run, but servo control will be disabled.")

        window = MainWindow()
        # Set the application window icon to LOGO.ico for best Windows compatibility
        logo_path = os.path.join(os.path.dirname(__file__), 'src', 'ui', 'assets', 'LOGO.ico')
        if os.path.exists(logo_path):
            window.setWindowIcon(QIcon(logo_path))
        window.show()
        
        # Clean up the client when the application exits
        app.aboutToQuit.connect(app_client.cleanup)
        
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()