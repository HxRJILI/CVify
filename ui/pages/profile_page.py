from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt

from ui.theme import COLORS
from ui.components.section_header import SectionHeader
from ui.components.card_widget import CardWidget
from core.database import SessionLocal
from core.models import User, CVProfile


class StatBox(QFrame):
    def __init__(self, label, value):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        val_lbl = QLabel(str(value))
        val_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 28px; font-weight: bold; border: none; background: transparent;")
        
        txt_lbl = QLabel(label)
        txt_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        
        layout.addWidget(val_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(txt_lbl, alignment=Qt.AlignmentFlag.AlignCenter)


class ProfilePage(QWidget):
    """The overview / settings page for the user's account."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(24)
        
        # Header
        self.content_layout.addWidget(SectionHeader(
            "Account Profile", 
            "Overview of your CVify account and profile completeness."
        ))

        # Stats Row
        stats_layout = QHBoxLayout()
        self.stat_docs = StatBox("Total CVs Generated", "0")
        self.stat_completeness = StatBox("Profile Completion", "0%")
        self.stat_skills = StatBox("Skills Logged", "0")
        
        stats_layout.addWidget(self.stat_docs)
        stats_layout.addWidget(self.stat_completeness)
        stats_layout.addWidget(self.stat_skills)
        
        self.content_layout.addLayout(stats_layout)
        
        # Account Info Card
        self.account_card = CardWidget()
        acc_layout = self.account_card.content_layout
        
        self.email_lbl = QLabel("Email: ...")
        self.email_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px;")
        
        self.verified_lbl = QLabel("Status: Verified")
        self.verified_lbl.setStyleSheet(f"color: {COLORS['success']}; font-size: 14px; font-weight: bold;")
        
        btn_logout = QPushButton("Logout")
        btn_logout.setProperty("class", "danger")
        btn_logout.clicked.connect(self._logout)
        
        acc_layout.addWidget(QLabel("<b>Account Information</b>"))
        acc_layout.addSpacing(8)
        acc_layout.addWidget(self.email_lbl)
        acc_layout.addWidget(self.verified_lbl)
        acc_layout.addSpacing(16)
        acc_layout.addWidget(btn_logout, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.content_layout.addWidget(self.account_card)
        self.content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        self.layout.addWidget(scroll)
        
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_data()
        
    def refresh_data(self):
        user = self.main_window.current_user
        if not user:
            return
            
        self.email_lbl.setText(f"Email: {user.email}")
        status = "Verified ✅" if user.is_verified else "Unverified ⚠️"
        color = COLORS['success'] if user.is_verified else COLORS['warning']
        self.verified_lbl.setText(f"Status: {status}")
        self.verified_lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        
        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=user.id).first()
            if profile:
                skill_count = 0
                for group in (profile.skills_hard or []):
                    skill_count += len(group.get("skills", []))

                # Update stat boxes manually by swapping widgets or simple update
                # Since we stored the values inside layout, let's just make it simple:
                self.stat_skills.layout().itemAt(0).widget().setText(str(skill_count))

                # Mock completeness
                score = 0
                if profile.contact: score += 20
                if profile.summary: score += 20
                if profile.work_experience: score += 20
                if profile.education: score += 20
                if profile.skills_hard: score += 20
                self.stat_completeness.layout().itemAt(0).widget().setText(f"{score}%")

    def _logout(self):
        self.main_window.current_user = None
        self.main_window.navigate('login')
