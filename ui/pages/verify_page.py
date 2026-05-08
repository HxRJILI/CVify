from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QThreadPool, pyqtSignal
from PyQt6.QtGui import QKeyEvent

from ui.theme import COLORS
from ui.components.loading_overlay import LoadingOverlay
from ui.components.toast import ToastManager
from utils.worker import Worker
import core.auth as auth
import core.email_service as email_service
from core.database import SessionLocal
from core.models import User

class SingleCharInput(QLineEdit):
    """A single character input box for OTPs."""
    backspace_pressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxLength(1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(48, 56)
        self.setStyleSheet(f"""
            QLineEdit {{
                font-size: 24px;
                font-weight: bold;
                background-color: {COLORS['bg_elevated']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Backspace and not self.text():
            self.backspace_pressed.emit()
        super().keyPressEvent(event)


class VerifyPage(QWidget):
    """Email verification interface."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.pool = QThreadPool.globalInstance()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.card = QWidget()
        self.card.setFixedSize(440, 400)
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
        
        # Envelope Icon
        self.icon_lbl = QLabel("✉")
        self.icon_lbl.setStyleSheet(f"font-size: 42px; color: {COLORS['accent']}; background: transparent; border: none;")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_card.addWidget(self.icon_lbl)
        
        title_lbl = QLabel("Check Your Email")
        title_lbl.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['text_primary']}; background: transparent; border: none;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_card.addWidget(title_lbl)
        
        self.desc_lbl = QLabel("We sent a 6-digit code to your email.\nEnter it below.")
        self.desc_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none;")
        self.desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_lbl.setWordWrap(True)
        self.layout_card.addWidget(self.desc_lbl)
        
        # OTP Boxes
        self.otp_container = QWidget()
        self.otp_container.setStyleSheet("background: transparent; border: none;")
        self.otp_layout = QHBoxLayout(self.otp_container)
        self.otp_layout.setContentsMargins(0, 0, 0, 0)
        self.otp_layout.setSpacing(12)
        
        self.boxes = []
        for i in range(6):
            box = SingleCharInput()
            box.textChanged.connect(lambda text, idx=i: self._on_box_text_changed(text, idx))
            box.backspace_pressed.connect(lambda idx=i: self._on_box_backspace(idx))
            self.otp_layout.addWidget(box)
            self.boxes.append(box)
            
        self.layout_card.addWidget(self.otp_container)
        
        # Error Label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #FF5C5C; background: transparent; border: none;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()
        self.layout_card.addWidget(self.error_label)
        
        # Resend Logic
        self.resend_lbl = QLabel("Resend in 60s")
        self.resend_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; background: transparent; border: none;")
        self.resend_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resend_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resend_lbl.mousePressEvent = self._handle_resend
        self.layout_card.addWidget(self.resend_lbl)
        
        self.layout_card.addStretch()
        self.main_layout.addWidget(self.card)
        
        self.overlay = LoadingOverlay(self)
        self.overlay.hide()
        
        self.countdown = 60
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        
        self.email_context = ""

    def showEvent(self, event):
        super().showEvent(event)
        # Grab context passed from signup
        self.email_context = getattr(self.main_window, 'verify_email_context', '')
        if self.email_context:
            self.desc_lbl.setText(f"We sent a 6-digit code to {self.email_context}.\nEnter it below.")
            
            # Start timer and optionally send the real email if it's a fresh signup
            self.start_timer()
            
            # Since signup creates the user with OTP, we trigger the first email now
            self._send_otp_email()
            
        if self.boxes:
            self.boxes[0].setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())

    def _on_box_text_changed(self, text: str, idx: int):
        self.error_label.hide()
        # Reset borders
        for box in self.boxes:
            box.setStyleSheet(box.styleSheet().replace(COLORS['error'], COLORS['border']))
            
        if text and idx < 5:
            self.boxes[idx + 1].setFocus()
        elif text and idx == 5:
            self._verify_code()

    def _on_box_backspace(self, idx: int):
        if idx > 0:
            self.boxes[idx - 1].setFocus()
            self.boxes[idx - 1].clear()

    def start_timer(self):
        self.countdown = 60
        self.resend_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; background: transparent; border: none;")
        self.resend_lbl.setText(f"Resend in {self.countdown}s")
        self.timer.start(1000)

    def _update_timer(self):
        self.countdown -= 1
        if self.countdown > 0:
            self.resend_lbl.setText(f"Resend in {self.countdown}s")
        else:
            self.timer.stop()
            self.resend_lbl.setText("Resend Code")
            self.resend_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; background: transparent; border: none;")

    def _handle_resend(self, event):
        if self.countdown <= 0 and self.email_context:
            self.start_timer()
            self._send_otp_email(regenerate=True)

    def _send_otp_email(self, regenerate=False):
        # We need the user's name and OTP
        def job():
            with SessionLocal() as db:
                user = db.query(User).filter(User.email == self.email_context).first()
                if not user:
                    raise Exception("User not found.")
                
                if regenerate:
                    user.verification_code = auth.generate_otp()
                    user.verification_expires_at = auth.datetime.utcnow() + auth.timedelta(minutes=15)
                    db.commit()
                    
                email_service.send_verification_email(user.email, user.full_name, user.verification_code)
                return True

        worker = Worker(job)
        worker.signals.error.connect(lambda e: ToastManager.show_toast("Failed to send email.", "error"))
        self.pool.start(worker)

    def _verify_code(self):
        code = "".join(b.text() for b in self.boxes)
        if len(code) < 6:
            return
            
        self.overlay.show_overlay("Verifying...")
        
        worker = Worker(auth.verify_user, self.email_context, code)
        worker.signals.result.connect(self._on_verify_success)
        worker.signals.error.connect(self._on_verify_error)
        self.pool.start(worker)

    def _on_verify_success(self, _):
        self.overlay.hide_overlay()
        ToastManager.show_toast("Account verified successfully!", "success")
        
        # Navigate to login layout to let them sign in normally
        # Or automatically authenticate. Design prefers auto-nav to login.
        QTimer.singleShot(1500, lambda: self.main_window.navigate('login'))

    def _on_verify_error(self, err_msg):
        self.overlay.hide_overlay()
        self.error_label.setText(err_msg)
        self.error_label.show()
        self._shake_and_flash()

    def _shake_and_flash(self):
        # Flash borders red
        for box in self.boxes:
            current_style = box.styleSheet()
            new_style = current_style.replace(COLORS['border'], COLORS['error'])
            box.setStyleSheet(new_style)
            box.clear()
            
        self.boxes[0].setFocus()
            
        # Shake container
        from PyQt6.QtCore import QPoint
        self.anim = QPropertyAnimation(self.otp_container, b"pos")
        self.anim.setDuration(400)
        
        base_pos = self.otp_container.pos()
        self.anim.setKeyValueAt(0, base_pos)
        self.anim.setKeyValueAt(0.2, base_pos + QPoint(-10, 0))
        self.anim.setKeyValueAt(0.4, base_pos + QPoint(10, 0))
        self.anim.setKeyValueAt(0.6, base_pos + QPoint(-5, 0))
        self.anim.setKeyValueAt(0.8, base_pos + QPoint(5, 0))
        self.anim.setKeyValueAt(1.0, base_pos)
        
        self.anim.start()
