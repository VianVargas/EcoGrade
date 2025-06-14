import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFontDatabase
from src.ui.main_window import MainWindow
from src.utils.video_processor import VideoProcessor
from src.utils.database import init_db
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
        # Enable high DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("ECOGRADE")
        app.setStyle('Fusion')
        
        # Initialize database
        init_db()
        
        # Create and show main window
        window = MainWindow()
        # Set the application window icon to LOGO.ico for best Windows compatibility
        logo_path = os.path.join(os.path.dirname(__file__), 'src', 'ui', 'assets', 'LOGO.ico')
        if os.path.exists(logo_path):
            window.setWindowIcon(QIcon(logo_path))
        window.show()
        
        # Start application
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == '__main__':
    main()