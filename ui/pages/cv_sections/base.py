from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer

from ui.theme import COLORS

class CVSectionPage(QWidget):
    """
    Base class for all CV section pages. 
    Provides auto-save debouncing and layout structure.
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.is_loading = True
        
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._perform_save)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 40, 40, 64)
        self.content_layout.setSpacing(24)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        # Indicator Label for saves (global to page for simplicity)
        self.save_indicator = QLabel("Saved ✓")
        self.save_indicator.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        self.save_indicator.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.save_indicator.hide()
        
        # Add inside a fixed top header layout if needed, or floating.
        # For simplicity, we can let individual cards show their own or just use a global page one.
        # The prompt says "A subtle 'Saved ✓' indicator appears in the top-right of each card".
        # We will handle it at the card level.
        
    def trigger_save(self):
        """Called by UI elements when changed to debounce the database save."""
        if self.is_loading:
            return
        # Start or reset the 500ms timer
        self.save_timer.start(500)

    def _perform_save(self):
        try:
            self.save_data()
        except Exception as e:
            print(f"Error saving data: {e}")

    def save_data(self):
        """Override this in subclasses to collect child widget data and save to DB."""
        pass

    def load_data(self):
        """Override this in subclasses to populate child widgets from DB."""
        pass

    def showEvent(self, event):
        super().showEvent(event)
        self.is_loading = True
        self.load_data()
        self.is_loading = False

def create_card_with_save_indicator(title: str, parent_page: CVSectionPage):
    """Helper to create a CardWidget with an embedded save indicator."""
    from ui.components.card_widget import CardWidget
    from PyQt6.QtWidgets import QHBoxLayout, QLabel
    
    card = CardWidget()
    
    header_layout = QHBoxLayout()
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 16px; font-weight: bold; background: transparent;")
    
    ind_lbl = QLabel("Saved ✓")
    ind_lbl.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; font-size: 12px; background: transparent;")
    ind_lbl.hide()
    
    header_layout.addWidget(title_lbl)
    header_layout.addStretch()
    header_layout.addWidget(ind_lbl)
    
    # Insert header as first item in the card's main_layout
    card.main_layout.insertLayout(0, header_layout)
    
    card.save_indicator = ind_lbl
    
    def on_saved():
        ind_lbl.show()
        QTimer.singleShot(2000, ind_lbl.hide)
        
    card.show_saved = on_saved
    
    return card

class EntryCard(QFrame):
    """A sub-card for list entries with a delete button."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_elevated']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        
    def add_delete_button(self, callback):
        from PyQt6.QtWidgets import QPushButton, QHBoxLayout
        btn = QPushButton("✕ Remove")
        btn.setProperty("class", "destructive")
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['error']};
                border: 1px solid {COLORS['error']};
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #2A1111;
            }}
        """)
        btn.setFixedSize(80, 28)
        btn.clicked.connect(callback)
        
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn)
        self.layout.addLayout(row)
