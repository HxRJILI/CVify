from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen

from ui.theme import COLORS

class SpinnerWidget(QWidget):
    """A custom animated arc spinner."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(16)  # ~60fps

    def rotate(self):
        self.angle = (self.angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(COLORS['accent']))
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        rect = self.rect().adjusted(4, 4, -4, -4)
        painter.drawArc(rect, -self.angle * 16, 270 * 16)


class LoadingOverlay(QWidget):
    """
    Full-window translucent overlay blocking interactions, showing a spinner,
    a label, and an optional progress bar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if parent:
            self.resize(parent.size())
            
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Center card
        self.card = QWidget()
        self.card.setFixedSize(300, 200)
        self.card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_layout.setSpacing(20)
        
        # Spinner
        self.spinner = SpinnerWidget()
        self.card_layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Label
        self.status_label = QLabel("Loading...")
        self.status_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; background: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_layout.addWidget(self.status_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_elevated']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
        """)
        self.progress_bar.hide()  # hidden by default
        self.card_layout.addWidget(self.progress_bar)
        
        self.layout.addWidget(self.card)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))  # 60% opacity black

    def mousePressEvent(self, event):
        event.accept()  # Block clicks

    def mouseReleaseEvent(self, event):
        event.accept()

    def show_overlay(self, message: str = "Loading..."):
        self.status_label.setText(message)
        self.progress_bar.hide()
        self.spinner.show()
        self.raise_()
        self.show()

    def show_progress(self, message: str = "Loading...", indeterminate: bool = True, value: int = 0, maximum: int = 100):
        self.status_label.setText(message)
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, maximum)
            self.progress_bar.setValue(value)
        self.progress_bar.show()
        self.spinner.hide()
        self.raise_()
        self.show()

    def hide_overlay(self):
        self.hide()

    def set_progress(self, message: str, value: int):
        if not self.progress_bar.isVisible():
            self.progress_bar.show()
        self.progress_bar.setRange(0, 100)
        self.status_label.setText(message)
        self.progress_bar.setValue(value)
        self.spinner.hide()
