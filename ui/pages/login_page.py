from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QThreadPool
from PyQt6.QtGui import QMouseEvent

from ui.theme import COLORS
from ui.components.loading_overlay import LoadingOverlay
from ui.components.toast import ToastManager
from utils.worker import Worker
import core.auth as auth

class LoginPage(QWidget):
    """The central login interface for returning users."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.pool = QThreadPool.globalInstance()
        
        # Center layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.card = QWidget()
        self.card.setFixedSize(420, 520)
        self.card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        self.layout_card = QVBoxLayout(self.card)
        self.layout_card.setContentsMargins(40, 40, 40, 40)
        self.layout_card.setSpacing(20)
        
        # Logo & Title
        logo_lbl = QLabel("CVify")
        logo_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {COLORS['accent']}; border: none;")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_lbl = QLabel("Welcome back")
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_primary']}; border: none;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.layout_card.addWidget(logo_lbl)
        self.layout_card.addWidget(title_lbl)
        self.layout_card.addSpacing(16)
        
        # Inputs
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("✉  Email Address")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("🔒  Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.layout_card.addWidget(self.email_input)
        self.layout_card.addWidget(self.password_input)
        
        # Options row (Remember me)
        opts_layout = QHBoxLayout()
        self.remember_cb = QCheckBox("Remember me")
        self.remember_cb.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        opts_layout.addWidget(self.remember_cb)
        opts_layout.addStretch()
        self.layout_card.addLayout(opts_layout)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #FF5C5C; border: none;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()
        self.layout_card.addWidget(self.error_label)
        
        # Login Button
        self.btn_login = QPushButton("Login")
        self.btn_login.clicked.connect(self._handle_login)
        self.layout_card.addWidget(self.btn_login)
        self.layout_card.addSpacing(16)
        
        # Sign up link
        signup_lbl = QLabel("Don't have an account? Sign Up")
        signup_lbl.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        signup_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signup_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        signup_lbl.mousePressEvent = lambda e: self.main_window.navigate('signup')
        self.layout_card.addWidget(signup_lbl)
        
        self.layout_card.addStretch()
        self.main_layout.addWidget(self.card)

        # Overlay reference
        self.overlay = LoadingOverlay(self)
        self.overlay.hide()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())
        
    def _handle_login(self):
        email = self.email_input.text().strip()
        pwd = self.password_input.text()
        
        self.error_label.hide()
        if not email or not pwd:
            self._show_error("Email and password are required.")
            return

        self.overlay.show_overlay("Authenticating...")
        
        worker = Worker(auth.authenticate, email, pwd)
        worker.signals.result.connect(self._on_login_result)
        worker.signals.error.connect(self._on_login_error)
        self.pool.start(worker)

    def _on_login_result(self, user):
        self.overlay.hide_overlay()
        if user is None:
            self._show_error("Invalid email or password.")
        else:
            if not user.is_verified:
                self.main_window.verify_email_context = user.email
                self.main_window.navigate('verify')
            else:
                self.main_window.current_user = user
                self.email_input.clear()
                self.password_input.clear()
                # Initialize main interface properly
                self.main_window.navigate('essentials')

    def _on_login_error(self, err_msg):
        self.overlay.hide_overlay()
        self._show_error("An error occurred during login. Please try again.")

    def _show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()
        self._shake_card()

    def _shake_card(self):
        from PyQt6.QtCore import QPoint
        self.anim = QPropertyAnimation(self.card, b"pos")
        self.anim.setDuration(400)
        
        base_pos = self.card.pos()
        self.anim.setKeyValueAt(0, base_pos)
        self.anim.setKeyValueAt(0.2, base_pos + QPoint(-15, 0))
        self.anim.setKeyValueAt(0.4, base_pos + QPoint(15, 0))
        self.anim.setKeyValueAt(0.6, base_pos + QPoint(-10, 0))
        self.anim.setKeyValueAt(0.8, base_pos + QPoint(10, 0))
        self.anim.setKeyValueAt(1.0, base_pos)
        
        self.anim.start()
