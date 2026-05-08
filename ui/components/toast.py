from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from ui.theme import COLORS

class Toast(QWidget):
    """
    A single toast notification widget.
    """
    closed = pyqtSignal(object)  # Emits self when closed
    
    def __init__(self, message: str, type_str: str = 'info', duration: int = 3000, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.type_str = type_str
        
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._opacity = 1.0
        
        self.setup_ui(message)
        
        # Auto-dismiss timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)
        
    def setup_ui(self, message):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(12)
        
        # Map type to color
        color_map = {
            'success': COLORS['success'],
            'error': COLORS['error'],
            'warning': COLORS['warning'],
            'info': COLORS['info']
        }
        self.brand_color = color_map.get(self.type_str, COLORS['info'])
        
        # Type indicator (colored dot/icon placeholder)
        self.icon_label = QLabel("•")
        self.icon_label.setStyleSheet(f"color: {self.brand_color}; font-size: 24px; font-weight: bold; line-height: 1;")
        self.layout.addWidget(self.icon_label)
        
        # Message
        self.msg_label = QLabel(message)
        self.msg_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; background: transparent;")
        self.msg_label.setWordWrap(True)
        self.layout.addWidget(self.msg_label, stretch=1)
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['text_secondary']};
                background: transparent;
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {COLORS['text_primary']};
            }}
        """)
        self.close_btn.clicked.connect(self.hide_toast)
        self.layout.addWidget(self.close_btn)
        
        self.setFixedWidth(320)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        painter.fillPath(path, QColor(COLORS['bg_elevated']))
        
        # Draw left border accent
        path_accent = QPainterPath()
        path_accent.addRoundedRect(0, 0, 4, self.height(), 4, 4)
        painter.fillPath(path_accent, QColor(self.brand_color))

    @pyqtProperty(float)
    def windowOpacity(self):
        return self._opacity

    @windowOpacity.setter
    def windowOpacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)

    def show_toast(self):
        self.show()
        if self.duration > 0:
            self.timer.start(self.duration)

    def hide_toast(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(200)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self._on_hidden)
        self.anim.start()

    def _on_hidden(self):
        self.closed.emit(self)
        self.close()


class ToastManager:
    """
    Singleton-like manager to handle stacked toasts across the application.
    """
    _instance = None
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.toasts = []
        ToastManager._instance = self

    @classmethod
    def show_toast(cls, message: str, type_str: str = 'info', duration: int = 3000):
        if not cls._instance:
            return
        cls._instance._add_toast(message, type_str, duration)

    def _add_toast(self, message: str, type_str: str, duration: int):
        toast = Toast(message, type_str, duration, self.main_window)
        toast.closed.connect(self._remove_toast)
        
        self.toasts.append(toast)
        self._update_positions()
        
        # Slide in animation
        toast.show_toast()
        start_y = toast.y() + 50
        end_y = toast.y()
        
        toast.anim_pos = QPropertyAnimation(toast, b"pos")
        toast.anim_pos.setDuration(300)
        toast.anim_pos.setStartValue(QPoint(toast.x(), start_y))
        toast.anim_pos.setEndValue(QPoint(toast.x(), end_y))
        toast.anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)
        toast.anim_pos.start()

    def _remove_toast(self, toast: Toast):
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._update_positions()

    def _update_positions(self):
        if not self.main_window:
            return
            
        margin_right = 24
        margin_bottom = 24
        spacing = 8
        
        current_y = self.main_window.height() - margin_bottom
        
        # Iterate backwards to stack from bottom to top
        for toast in reversed(self.toasts):
            current_y -= toast.height()
            
            x = self.main_window.width() - toast.width() - margin_right
            toast.move(x, current_y)
            
            current_y -= spacing
