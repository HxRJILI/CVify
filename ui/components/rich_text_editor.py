from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton, QButtonGroup
from PyQt6.QtGui import QTextListFormat, QTextCursor

from ui.theme import COLORS

class RichTextEditor(QWidget):
    """
    A simple rich text editor built around QTextEdit with a basic formatting toolbar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        # Toolbar
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(4)
        
        self.btn_bold = self._create_btn("B")
        self.btn_bold.clicked.connect(self._toggle_bold)
        
        self.btn_italic = self._create_btn("I")
        self.btn_italic.clicked.connect(self._toggle_italic)
        
        self.btn_bullet = self._create_btn("•")
        self.btn_bullet.clicked.connect(self._insert_bullet)
        
        self.toolbar_layout.addWidget(self.btn_bold)
        self.toolbar_layout.addWidget(self.btn_italic)
        self.toolbar_layout.addWidget(self.btn_bullet)
        self.toolbar_layout.addStretch()
        
        self.layout.addLayout(self.toolbar_layout)
        
        # Text Edit
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.layout.addWidget(self.editor)

    def _create_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text_primary']};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_elevated']};
            }}
        """)
        return btn

    def _toggle_bold(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontWeight(700 if fmt.fontWeight() != 700 else 400)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _toggle_italic(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _insert_bullet(self):
        cursor = self.editor.textCursor()
        cursor.insertList(QTextListFormat.Style.ListDisc)
        self.editor.setFocus()

    def toPlainText(self) -> str:
        return self.editor.toPlainText()

    def toHtml(self) -> str:
        return self.editor.toHtml()

    def setHtml(self, text: str):
        self.editor.setHtml(text)

    def setPlainText(self, text: str):
        self.editor.setPlainText(text)
