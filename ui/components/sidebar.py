from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, pyqtProperty, QSize
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from ui.theme import COLORS
from ui.main_window import MainWindow

class AvatarWidget(QWidget):
    """Draws a circular user avatar with initials."""
    def __init__(self, initials: str, size: int = 40, parent=None):
        super().__init__(parent)
        self.initials = initials
        self._size = size
        self.setFixedSize(size, size)
        
        # Color based on hash of initials
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#F9CA24", "#6C5CE7", "#A55EEA"]
        idx = sum(ord(c) for c in initials) % len(colors) if initials else 0
        self.bg_color = colors[idx]

    def set_initials(self, initials: str):
        self.initials = initials
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addEllipse(0, 0, self._size, self._size)
        painter.fillPath(path, QColor(self.bg_color))
        
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(self._size // 3)
        painter.setFont(font)
        
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.initials)


class SidebarItem(QPushButton):
    """Animatable sidebar navigation button."""
    def __init__(self, icon: str, text: str, page_key: str, parent=None):
        super().__init__(parent)
        self.icon_text = icon
        self.label_text = text
        self.page_key = page_key
        self.is_active = False
        self.is_collapsed = False
        
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(text) # Useful when collapsed
        
        self._bg_opacity = 0.0
        
        self.anim = QPropertyAnimation(self, b"bg_opacity")
        self.anim.setDuration(120)

    @pyqtProperty(float)
    def bg_opacity(self):
        return self._bg_opacity

    @bg_opacity.setter
    def bg_opacity(self, value):
        self._bg_opacity = value
        self.update()

    def enterEvent(self, event):
        if not self.is_active:
            self.anim.setStartValue(self._bg_opacity)
            self.anim.setEndValue(1.0)
            self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_active:
            self.anim.setStartValue(self._bg_opacity)
            self.anim.setEndValue(0.0)
            self.anim.start()
        super().leaveEvent(event)

    def set_active(self, active: bool):
        self.is_active = active
        self._bg_opacity = 1.0 if active else 0.0
        self.update()

    def set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        if self._bg_opacity > 0:
            bg_color = QColor(COLORS['bg_elevated'])
            bg_color.setAlphaF(self._bg_opacity)
            path = QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
            painter.fillPath(path, bg_color)
            
        # Active left indicator
        if self.is_active:
            painter.fillRect(0, 8, 3, self.height() - 16, QColor(COLORS['accent']))
            
        # Text colors
        color = COLORS['accent'] if self.is_active else COLORS['text_secondary']
        
        # Draw Icon
        painter.setPen(QColor(color))
        font = painter.font()
        font.setPixelSize(16)
        painter.setFont(font)
        
        icon_rect = self.rect()
        icon_rect.setWidth(48)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, self.icon_text)
        
        # Draw Text
        if not self.is_collapsed:
            painter.setPen(QColor(COLORS['text_primary'] if self.is_active else COLORS['text_secondary']))
            font.setPixelSize(13)
            if self.is_active: font.setBold(True)
            painter.setFont(font)
            
            text_rect = self.rect()
            text_rect.setLeft(48)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.label_text)


class Sidebar(QWidget):
    """Collapsible sidebar integrating navigation items and user info."""
    def __init__(self, main_window: MainWindow, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.is_collapsed = False
        
        self.setFixedWidth(240)
        self.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border-right: 1px solid {COLORS['border']};")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 24, 12, 24)
        self.layout.setSpacing(8)
        
        # Top Header (Avatar + Details + Toggle Btn)
        self.header_widget = QWidget()
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(4, 0, 4, 0)
        
        self.avatar = AvatarWidget("U")
        self.header_layout.addWidget(self.avatar)
        
        self.user_info_widget = QWidget()
        self.user_info_layout = QVBoxLayout(self.user_info_widget)
        self.user_info_layout.setContentsMargins(8, 0, 0, 0)
        self.user_info_layout.setSpacing(2)
        
        self.lbl_name = QLabel("User Name")
        self.lbl_name.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 14px; border: none;")
        self.lbl_email = QLabel("user@example.com")
        self.lbl_email.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; border: none;")
        
        self.user_info_layout.addWidget(self.lbl_name)
        self.user_info_layout.addWidget(self.lbl_email)
        self.header_layout.addWidget(self.user_info_widget)
        
        self.header_layout.addStretch()
        
        self.btn_toggle = QPushButton("←")
        self.btn_toggle.setFixedSize(28, 28)
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_elevated']};
                color: {COLORS['text_primary']};
            }}
        """)
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        self.header_layout.addWidget(self.btn_toggle)
        
        self.layout.addWidget(self.header_widget)
        self.layout.addSpacing(24)
        
        # Navigation Items
        self.nav_items = []
        
        sections = [
            ("📋", "Essentials", "essentials"),
            ("⚡", "Power-Ups", "powerups"),
            ("🏆", "Differentiators", "differentiators"),
            ("✨", "Personal Touch", "personal_touch"),
            None, # Separator
            ("🤖", "Generate CV", "generate"),
            ("🗂️", "History", "history"),
            None, # Separator
            ("👤", "My Profile", "profile")
        ]
        
        for item in sections:
            if item is None:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet(f"background-color: {COLORS['border']}; margin: 8px 12px;")
                self.layout.addWidget(sep)
            else:
                icon, text, key = item
                nav_btn = SidebarItem(icon, text, key)
                nav_btn.clicked.connect(lambda checked, k=key: self._on_nav_clicked(k))
                self.layout.addWidget(nav_btn)
                self.nav_items.append(nav_btn)
                
        self.layout.addStretch()
        
        # Bottom controls
        self.bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(4, 0, 4, 0)
        
        self.lbl_version = QLabel("v1.0.0")
        self.lbl_version.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; border: none;")
        bottom_layout.addWidget(self.lbl_version)
        bottom_layout.addStretch()
        
        self.layout.addWidget(self.bottom_widget)

        # Animation Setup
        self.anim_width = QPropertyAnimation(self, b"minimumWidth")
        self.anim_width.setDuration(200)
        self.anim_width.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def refresh_user(self):
        user = self.main_window.current_user
        if user:
            name_parts = user.full_name.split() if user.full_name else []
            initials = "".join(p[0] for p in name_parts[:2]).upper() if name_parts else "U"
            self.avatar.set_initials(initials)
            self.lbl_name.setText(user.full_name)
            self.lbl_email.setText(user.email)

    def _on_nav_clicked(self, key: str):
        # Update active states
        for item in self.nav_items:
            item.set_active(item.page_key == key)
        # Navigate main wrapper
        self.main_window.navigate(key)

    def set_active_key(self, key: str):
        for item in self.nav_items:
            item.set_active(item.page_key == key)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        
        target_width = 80 if self.is_collapsed else 240
        self.btn_toggle.setText("→" if self.is_collapsed else "←")
        
        if self.is_collapsed:
            self.user_info_widget.hide()
            self.lbl_version.hide()
        else:
            self.user_info_widget.show()
            self.lbl_version.show()
            
        for item in self.nav_items:
            item.set_collapsed(self.is_collapsed)
            
        self.anim_width.setStartValue(self.width())
        self.anim_width.setEndValue(target_width)
        self.anim_width.start()
        
        # Parent layout container synchronization
        parent = self.parentWidget()
        if parent:
            anim_parent = QPropertyAnimation(parent, b"maximumWidth")
            anim_parent.setDuration(200)
            anim_parent.setStartValue(parent.width())
            anim_parent.setEndValue(target_width)
            anim_parent.start()
