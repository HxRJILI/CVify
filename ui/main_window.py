from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QLabel, QPushButton, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QMouseEvent

from ui.theme import COLORS

class TitleBar(QWidget):
    """Custom frameless title bar for the application."""
    
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(40)
        self.setStyleSheet(f"background-color: {COLORS['bg_surface']};")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(16, 0, 8, 0)
        self.layout.setSpacing(8)
        
        # Logo / Title
        self.title_label = QLabel("CVify")
        self.title_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.title_label)
        
        self.layout.addStretch()
        
        # Window Controls
        self.btn_min = self._create_control_button("—", self._minimize)
        self.btn_max = self._create_control_button("□", self._maximize)
        self.btn_close = self._create_control_button("✕", self._close, is_close=True)
        
        self.layout.addWidget(self.btn_min)
        self.layout.addWidget(self.btn_max)
        self.layout.addWidget(self.btn_close)
        
        self._drag_pos = None

    def _create_control_button(self, text, handler, is_close=False):
        btn = QPushButton(text)
        btn.setFixedSize(32, 24)
        btn.clicked.connect(handler)
        
        hover_color = COLORS['error'] if is_close else COLORS['bg_elevated']
        border_radius = "4px"
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: {border_radius};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                color: {COLORS['text_primary']};
            }}
        """)
        return btn

    def _minimize(self):
        self.parent_window.showMinimized()

    def _maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    def _close(self):
        self.parent_window.close()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and not self.parent_window.isMaximized():
            new_pos = event.globalPosition().toPoint()
            diff = new_pos - self._drag_pos
            self.parent_window.move(self.parent_window.pos() + diff)
            self._drag_pos = new_pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None


class MainWindow(QMainWindow):
    """
    Root window containing custom title bar, sidebar (when logged in),
    and a stacked widget for view routing.
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("CVify")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.current_user = None
        
        # Central widget and main layout
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("central_widget")
        self.central_widget.setStyleSheet(f"""
            QWidget#central_widget {{
                background-color: {COLORS["bg_primary"]};
                border-radius: 12px;
                border: 1px solid {COLORS["border"]};
            }}
        """)
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Title bar
        self.title_bar = TitleBar(self)
        self.main_layout.addWidget(self.title_bar)
        
        # Content area (Sidebar + Stacked Widget)
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Navigation Sidebar
        from ui.components.sidebar import Sidebar
        
        self.sidebar_container = QWidget()
        self.sidebar_container.setFixedWidth(240)
        self.sidebar_container.setStyleSheet("border: none; background: transparent;")
        self.sidebar_layout = QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.sidebar = Sidebar(self)
        self.sidebar_layout.addWidget(self.sidebar)
        self.sidebar_container.hide() # Hidden until logged in
        
        self.content_layout.insertWidget(0, self.sidebar_container)
        
        # Router container (Stacked Widget)
        self.router = QStackedWidget()
        self.content_layout.addWidget(self.router, stretch=1)
        
        self.main_layout.addWidget(self.content_widget, stretch=1)
        
        # Pages dictionary map
        self.pages = {}
        
        self._target_page_key = None
        
        # Initialize placeholder pages for testing routing
        self._init_placeholder_pages()
        
        # Navigate to home initially
        self.router.setCurrentWidget(self.pages["home"])

    def _init_placeholder_pages(self):
        from ui.pages.home_page import HomePage
        from ui.pages.login_page import LoginPage
        from ui.pages.signup_page import SignupPage
        from ui.pages.verify_page import VerifyPage
        
        from ui.pages.cv_sections.essentials_page import EssentialsPage
        from ui.pages.cv_sections.powerups_page import PowerUpsPage
        from ui.pages.cv_sections.differentiators_page import DifferentiatorsPage
        from ui.pages.cv_sections.personal_touch_page import PersonalTouchPage
        
        from ui.pages.generate_page import GeneratePage
        from ui.pages.history_page import HistoryPage
        from ui.pages.profile_page import ProfilePage
        
        self.pages['home'] = HomePage(self)
        self.router.addWidget(self.pages['home'])
        
        self.pages['login'] = LoginPage(self)
        self.router.addWidget(self.pages['login'])
        
        self.pages['signup'] = SignupPage(self)
        self.router.addWidget(self.pages['signup'])
        
        self.pages['verify'] = VerifyPage(self)
        self.router.addWidget(self.pages['verify'])

        self.pages['essentials'] = EssentialsPage(self)
        self.router.addWidget(self.pages['essentials'])

        self.pages['powerups'] = PowerUpsPage(self)
        self.router.addWidget(self.pages['powerups'])

        self.pages['differentiators'] = DifferentiatorsPage(self)
        self.router.addWidget(self.pages['differentiators'])

        self.pages['personal_touch'] = PersonalTouchPage(self)
        self.router.addWidget(self.pages['personal_touch'])

        self.pages['generate'] = GeneratePage(self)
        self.router.addWidget(self.pages['generate'])

        self.pages['history'] = HistoryPage(self)
        self.router.addWidget(self.pages['history'])

        self.pages['profile'] = ProfilePage(self)
        self.router.addWidget(self.pages['profile'])

    def navigate(self, page_key: str):
        """
        Navigates to the given page key.
        """
        if page_key not in self.pages:
            print(f"Error: Page '{page_key}' not found.")
            return
            
        target_widget = self.pages[page_key]
        if self.router.currentWidget() == target_widget:
            return
            
        self._target_page_key = page_key
        
        self.router.setCurrentWidget(target_widget)
        
        # Manage sidebar visibility
        auth_pages = ['home', 'login', 'signup', 'verify']
        if self._target_page_key in auth_pages or self.current_user is None:
            self.sidebar_container.hide()
        else:
            self.sidebar_container.show()
            self.sidebar.refresh_user()
            self.sidebar.set_active_key(self._target_page_key)
            
        self._target_page_key = None
