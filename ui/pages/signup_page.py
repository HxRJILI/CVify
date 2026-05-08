from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from ui.theme import COLORS
from ui.components.loading_overlay import LoadingOverlay
from ui.components.toast import ToastManager
from utils.worker import Worker
from utils.validators import is_valid_email
import core.auth as auth

class PasswordStrengthWidget(QWidget):
    """4-segment progressive bar indicating password strength."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self.strength = 0 # 0 to 4
        
    def set_strength(self, val):
        self.strength = max(0, min(4, val))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        segment_w = (w - 12) / 4
        
        colors = [
            "#FF5C5C", # Weak Red
            "#FFB547", # Fair Orange
            "#FFD166", # Good Yellow
            "#3DD68C"  # Strong Green
        ]
        
        for i in range(4):
            path = QPainterPath()
            rx = i * (segment_w + 4)
            path.addRoundedRect(rx, 0, segment_w, self.height(), 3, 3)
            
            if i < self.strength:
                painter.fillPath(path, QColor(colors[self.strength - 1]))
            else:
                painter.fillPath(path, QColor(COLORS['bg_elevated']))


class SignupPage(QWidget):
    """Account creation interface."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.pool = QThreadPool.globalInstance()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.card = QWidget()
        self.card.setFixedSize(420, 600)
        self.card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        self.layout_card = QVBoxLayout(self.card)
        self.layout_card.setContentsMargins(40, 40, 40, 40)
        self.layout_card.setSpacing(16)
        
        # Logo & Title
        logo_lbl = QLabel("CVify")
        logo_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {COLORS['accent']}; border: none;")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_lbl = QLabel("Create an account")
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_primary']}; border: none;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.layout_card.addWidget(logo_lbl)
        self.layout_card.addWidget(title_lbl)
        self.layout_card.addSpacing(8)
        
        # Inputs
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("👤  Full Name")
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("✉  Email Address")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("🔒  Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self._evaluate_password)
        
        self.pwd_strength = PasswordStrengthWidget()
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("🔒  Confirm Password")
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.textChanged.connect(self._check_match)
        
        self.layout_card.addWidget(self.name_input)
        self.layout_card.addWidget(self.email_input)
        self.layout_card.addWidget(self.password_input)
        self.layout_card.addWidget(self.pwd_strength)
        self.layout_card.addWidget(self.confirm_input)
        
        # Inline error
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #FF5C5C; border: none; font-size: 12px;")
        self.error_label.hide()
        self.layout_card.addWidget(self.error_label)
        
        self.layout_card.addSpacing(8)
        
        # Signup Button
        self.btn_signup = QPushButton("Sign Up")
        self.btn_signup.clicked.connect(self._handle_signup)
        self.layout_card.addWidget(self.btn_signup)
        self.layout_card.addSpacing(8)
        
        # Login link
        login_lbl = QLabel("Already have an account? Login")
        login_lbl.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        login_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        login_lbl.mousePressEvent = lambda e: self.main_window.navigate('login')
        self.layout_card.addWidget(login_lbl)
        
        self.layout_card.addStretch()
        self.main_layout.addWidget(self.card)

        self.overlay = LoadingOverlay(self)
        self.overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())

    def _evaluate_password(self, pwd: str):
        score = 0
        if len(pwd) >= 8: score += 1
        if any(c.isupper() for c in pwd): score += 1
        if any(c.isdigit() for c in pwd): score += 1
        if any(not c.isalnum() for c in pwd): score += 1
        
        self.pwd_strength.set_strength(score)
        self._check_match()

    def _check_match(self, _=None):
        pwd = self.password_input.text()
        conf = self.confirm_input.text()
        
        if conf and pwd != conf:
            self.confirm_input.setStyleSheet(f"border: 1px solid {COLORS['error']};")
        else:
            self.confirm_input.setStyleSheet("")

    def _handle_signup(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        pwd = self.password_input.text()
        conf = self.confirm_input.text()
        
        self.error_label.hide()
        
        if not all([name, email, pwd, conf]):
            self._show_error("All fields are required.")
            return
            
        if not is_valid_email(email):
            self._show_error("Please enter a valid email address.")
            return
            
        if pwd != conf:
            self._show_error("Passwords do not match.")
            return
            
        if self.pwd_strength.strength < 3:
            self._show_error("Password is too weak.")
            return

        self.overlay.show_overlay("Creating account...")
        
        worker = Worker(auth.create_user, email, pwd, name)
        worker.signals.result.connect(self._on_signup_success)
        worker.signals.error.connect(self._on_signup_error)
        self.pool.start(worker)

    def _on_signup_success(self, user):
        # We will trigger the email logic in Step 7.
        # For now, pass context and jump to verify.
        self.overlay.hide_overlay()
        self.main_window.verify_email_context = user.email
        
        # Send Email happens in background here typically via email_service
        # (Mocked out till Step 7 where we fill in the actual email call)
        
        # Navigate
        self.main_window.navigate('verify')

    def _on_signup_error(self, err_msg):
        self.overlay.hide_overlay()
        if "already exists" in err_msg.lower():
            self._show_error("An account with this email already exists.")
        else:
            self._show_error("Error creating account. Please try again.")

    def _show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()
