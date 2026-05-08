from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from ui.theme import COLORS

class ProgressStep(QWidget):
    """
    Onboarding tooltip bubble pointing left at a sidebar item.
    """
    next_clicked = pyqtSignal()

    def __init__(self, title: str, description: str, step: int, total_steps: int, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        
        self.card = QWidget()
        self.card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['accent']};
                border-radius: 8px;
            }}
        """)
        
        card_layout = QVBoxLayout(self.card)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        card_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet("color: white; background: transparent;")
        lbl_desc.setWordWrap(True)
        card_layout.addWidget(lbl_desc)
        
        foot_layout = QHBoxLayout()
        lbl_step = QLabel(f"{step}/{total_steps}")
        lbl_step.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px; background: transparent;")
        
        self.btn_next = QPushButton("Next" if step < total_steps else "Got it")
        self.btn_next.setStyleSheet(f"""
            QPushButton {{
                background-color: white; 
                color: {COLORS['accent']}; 
                padding: 4px 12px; 
                border-radius: 4px; 
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #F0F0F8;
            }}
        """)
        self.btn_next.clicked.connect(self.next_clicked.emit)
        
        foot_layout.addWidget(lbl_step)
        foot_layout.addStretch()
        foot_layout.addWidget(self.btn_next)
        
        card_layout.addLayout(foot_layout)
        self.layout.addWidget(self.card)
        self.setFixedSize(260, 140)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.moveTo(12, self.height() / 2)
        path.lineTo(24, self.height() / 2 - 8)
        path.lineTo(24, self.height() / 2 + 8)
        path.closeSubpath()
        
        painter.fillPath(path, QColor(COLORS['accent']))
