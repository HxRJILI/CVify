from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from ui.theme import COLORS

class SectionHeader(QWidget):
    """
    Standard header for CV section pages, providing consistent title and description.
    """
    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 16)
        self.layout.setSpacing(4)
        
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "heading")
        self.title_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 24px; font-weight: bold;")
        
        self.desc_label = QLabel(description)
        self.desc_label.setProperty("class", "subheading")
        self.desc_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.desc_label.setWordWrap(True)
        
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.desc_label)
