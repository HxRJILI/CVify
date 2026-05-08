from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.theme import COLORS

class CardWidget(QWidget):
    """
    A generic elevated card widget used for grouping related fields.
    """
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card_widget")
        self.setStyleSheet(f"""
            QWidget#card_widget {{
                background-color: {COLORS["bg_surface"]};
                border-radius: 12px;
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)
        
        if title:
            header_layout = QVBoxLayout()
            header_layout.setSpacing(4)
            
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 16px; font-weight: bold;")
            header_layout.addWidget(self.title_label)
            
            self.main_layout.addLayout(header_layout)
            
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(16)
        self.main_layout.addLayout(self.content_layout)

    def add_widget(self, widget: QWidget):
        """Helper to add widget to the card's content layout."""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Helper to add layout to the card's content layout."""
        self.content_layout.addLayout(layout)
