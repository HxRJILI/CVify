import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QIcon
from PyQt6.QtCore import Qt

from ui.theme import get_stylesheet
from ui.main_window import MainWindow
from ui.components.toast import ToastManager

def run_app():
    """
    Initializes the QApplication, loads fonts, applies the global stylesheet,
    and starts the main event loop.
    """
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    # Load custom fonts (assumes fonts exist, gracefully falls back to system defaults if missing)
    QFontDatabase.addApplicationFont("assets/fonts/Inter-Regular.ttf")
    QFontDatabase.addApplicationFont("assets/fonts/Inter-SemiBold.ttf")
    QFontDatabase.addApplicationFont("assets/fonts/Inter-Bold.ttf")
    QFontDatabase.addApplicationFont("assets/fonts/JetBrainsMono-Regular.ttf")
    
    # Apply global stylesheet
    app.setStyleSheet(get_stylesheet())
    
    # Instantiate and show main window
    window = MainWindow()
    ToastManager(window)
    window.show()
    
    sys.exit(app.exec())
