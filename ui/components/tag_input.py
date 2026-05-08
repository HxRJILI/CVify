from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, 
    QScrollArea, QCompleter
)
from PyQt6.QtCore import Qt, QStringListModel, pyqtSignal
from PyQt6.QtGui import QMouseEvent

from ui.theme import COLORS

class FlowLayout(QVBoxLayout):
    """Simple placeholder for flow layout logic to be used with tags."""
    # Note: A real FlowLayout requires calculating widths dynamically.
    # For simplicity, we use wrapped QHBoxLayouts inside a QVBoxLayout.
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(8)
        self.rows = []
        self.add_row()

    def add_row(self):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.addLayout(row)
        self.rows.append(row)

    def add_widget(self, widget: QWidget):
        # A true flow layout would check width; this is a simplified approach
        # attaching to the last row. If we wanted correct wrapping, we'd need
        # the official Qt FlowLayout implementation. For now, this serves the MVP.
        # Actually doing a basic width check wrapping here:
        if not self.parentWidget():
            self.rows[-1].addWidget(widget)
            return

        parent_width = self.parentWidget().width()
        current_row = self.rows[-1]
        
        # very rudimentary tracking
        current_width = sum(current_row.itemAt(i).widget().width() + self.spacing() for i in range(current_row.count()))
        
        if current_width + widget.width() > parent_width - 40 and current_row.count() > 0:
            self.add_row()
            
        self.rows[-1].addWidget(widget)

    def clear(self):
        while self.count():
            item = self.takeAt(0)
            if item.layout():
                # clear row
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                item.layout().deleteLater()
        self.rows = []
        self.add_row()


class TagWidget(QWidget):
    """Individual tag/chip widget with a close button."""
    removed = pyqtSignal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text_val = text
        self.setFixedHeight(30)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_elevated']};
                border: 1px solid {COLORS['border']};
                border-radius: 15px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(6)
        
        lbl = QLabel(text)
        lbl.setStyleSheet("border: none; background: transparent;")
        
        close_btn = QLabel("✕")
        close_btn.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-weight: bold;
            border: none;
            background: transparent;
        """)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = self._on_close
        
        layout.addWidget(lbl)
        layout.addWidget(close_btn)
        
    def _on_close(self, event: QMouseEvent):
        self.removed.emit(self.text_val)


class TagInput(QWidget):
    """
    Input field that turns comma-separated text or Enter presses into tags.
    """
    tagsChanged = pyqtSignal(list)
    
    def __init__(self, suggestions: list[str] = None, parent=None):
        super().__init__(parent)
        self.tags = []
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type and press Enter or comma...")
        self.input_field.returnPressed.connect(self._add_pending_tag)
        self.input_field.textChanged.connect(self._check_comma)
        
        if suggestions:
            completer = QCompleter(suggestions)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.input_field.setCompleter(completer)
            
        self.main_layout.addWidget(self.input_field)
        
        self.tags_container = QWidget()
        self.tags_layout = FlowLayout(self.tags_container)
        self.main_layout.addWidget(self.tags_container)

    def _check_comma(self, text: str):
        if ',' in text:
            parts = text.split(',')
            for part in parts[:-1]:
                self.add_tag(part.strip())
            self.input_field.setText(parts[-1].lstrip())

    def _add_pending_tag(self):
        text = self.input_field.text().strip()
        if text:
            self.add_tag(text)
            self.input_field.clear()

    def add_tag(self, text: str):
        if not text or text in self.tags:
            return
            
        self.tags.append(text)
        self._render_tags()
        self.tagsChanged.emit(self.tags)
        
    def _remove_tag(self, text: str):
        if text in self.tags:
            self.tags.remove(text)
            self._render_tags()
            self.tagsChanged.emit(self.tags)

    def _render_tags(self):
        self.tags_layout.clear()
        for tag in self.tags:
            tag_widget = TagWidget(tag)
            tag_widget.removed.connect(self._remove_tag)
            self.tags_layout.add_widget(tag_widget)

    def set_placeholder(self, text: str):
        self.input_field.setPlaceholderText(text)

    def set_tags(self, tags: list[str]):
        self.tags = tags.copy()
        self._render_tags()

    def get_tags(self) -> list[str]:
        return self.tags
