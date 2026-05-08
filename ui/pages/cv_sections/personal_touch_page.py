from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QTextEdit,
    QPushButton, QComboBox, QFrame
)
from PyQt6.QtCore import Qt

from ui.theme import COLORS
from ui.pages.cv_sections.base import CVSectionPage, create_card_with_save_indicator, EntryCard
from ui.components.section_header import SectionHeader
from core.database import SessionLocal
from core.models import CVProfile

class LanguageEntry(EntryCard):
    def __init__(self, main_page, data=None):
        super().__init__()
        self.main_page = main_page
        
        self.language_edit = QLineEdit()
        self.language_edit.setPlaceholderText("Language (e.g., English)")
        
        self.proficiency_combo = QComboBox()
        self.proficiency_combo.addItems([
            "Native/Bilingual",
            "Fluent",
            "Conversational",
            "Basic"
        ])
        
        r1 = QHBoxLayout()
        r1.addWidget(self.language_edit)
        r1.addWidget(self.proficiency_combo)
        
        self.layout.addLayout(r1)
        
        self.language_edit.textChanged.connect(main_page.trigger_save)
        self.proficiency_combo.currentIndexChanged.connect(lambda _: main_page.trigger_save())

        if data:
            self.language_edit.setText(data.get("language", ""))
            idx = self.proficiency_combo.findText(data.get("proficiency", ""))
            if idx >= 0: self.proficiency_combo.setCurrentIndex(idx)

    def get_data(self):
        return {
            "language": self.language_edit.text().strip(),
            "proficiency": self.proficiency_combo.currentText()
        }

class VolunteeringEntry(EntryCard):
    def __init__(self, main_page, data=None):
        super().__init__()
        self.main_page = main_page
        
        self.role_edit = QLineEdit()
        self.role_edit.setPlaceholderText("Role/Title")
        self.org_edit = QLineEdit()
        self.org_edit.setPlaceholderText("Organization")
        
        r1 = QHBoxLayout()
        r1.addWidget(self.role_edit)
        r1.addWidget(self.org_edit)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Brief description of your involvement...")
        self.desc_edit.setFixedHeight(60)
        
        self.layout.addLayout(r1)
        self.layout.addWidget(QLabel("Description:"))
        self.layout.addWidget(self.desc_edit)
        
        self.role_edit.textChanged.connect(main_page.trigger_save)
        self.org_edit.textChanged.connect(main_page.trigger_save)
        self.desc_edit.textChanged.connect(main_page.trigger_save)

        if data:
            self.role_edit.setText(data.get("role", ""))
            self.org_edit.setText(data.get("organization", ""))
            self.desc_edit.setPlainText(data.get("description", ""))

    def get_data(self):
        return {
            "role": self.role_edit.text().strip(),
            "organization": self.org_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip()
        }


class PersonalTouchPage(CVSectionPage):
    """The Personal Touch page containing Languages and Volunteering."""
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        
        self.content_layout.addWidget(SectionHeader(
            "Personal Touch", 
            "Languages and volunteering experience that complete your profile."
        ))

        self.setup_languages_card()
        self.setup_volunteering_card()
        
    def setup_languages_card(self):
        self.languages_card = create_card_with_save_indicator("Languages", self)
        
        self.lang_layout = QVBoxLayout()
        self.lang_layout.setSpacing(16)
        self.languages_card.content_layout.addLayout(self.lang_layout)
        
        btn_add = QPushButton("+ Add Language")
        btn_add.setProperty("class", "ghost")
        btn_add.clicked.connect(lambda: self.add_entry(self.lang_layout, LanguageEntry))
        self.languages_card.content_layout.addWidget(btn_add)
        
        self.content_layout.addWidget(self.languages_card)

    def setup_volunteering_card(self):
        self.volunteer_card = create_card_with_save_indicator("Volunteering Experience", self)
        
        self.vol_layout = QVBoxLayout()
        self.vol_layout.setSpacing(16)
        self.volunteer_card.content_layout.addLayout(self.vol_layout)
        
        btn_add = QPushButton("+ Add Volunteering")
        btn_add.setProperty("class", "ghost")
        btn_add.clicked.connect(lambda: self.add_entry(self.vol_layout, VolunteeringEntry))
        self.volunteer_card.content_layout.addWidget(btn_add)
        
        self.content_layout.addWidget(self.volunteer_card)

    def add_entry(self, layout, entry_class, data=None):
        entry = entry_class(self, data)
        entry.add_delete_button(lambda: self._remove_entry(entry))
        layout.addWidget(entry)
        self.trigger_save()
        
    def _remove_entry(self, widget):
        widget.deleteLater()
        self.trigger_save()

    def load_data(self):
        if not self.main_window.current_user: return
        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=self.main_window.current_user.id).first()
            if not profile: return
            
            while self.lang_layout.count():
                w = self.lang_layout.takeAt(0).widget()
                if w: w.deleteLater()
                
            for p in profile.languages or []:
                self.add_entry(self.lang_layout, LanguageEntry, p)
                
            while self.vol_layout.count():
                w = self.vol_layout.takeAt(0).widget()
                if w: w.deleteLater()
                
            for c in profile.volunteer or []:
                self.add_entry(self.vol_layout, VolunteeringEntry, c)

    def save_data(self):
        if not self.main_window.current_user:
            return
            
        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=self.main_window.current_user.id).first()
            if not profile: return
            
            lang_data = []
            for i in range(self.lang_layout.count()):
                w = self.lang_layout.itemAt(i).widget()
                if isinstance(w, LanguageEntry):
                    lang_data.append(w.get_data())
            profile.languages = lang_data
            
            vol_data = []
            for i in range(self.vol_layout.count()):
                w = self.vol_layout.itemAt(i).widget()
                if isinstance(w, VolunteeringEntry):
                    vol_data.append(w.get_data())
            profile.volunteer = vol_data
            
        self.languages_card.show_saved()
        self.volunteer_card.show_saved()
