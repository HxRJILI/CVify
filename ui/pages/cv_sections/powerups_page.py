from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt

from ui.theme import COLORS
from ui.pages.cv_sections.base import CVSectionPage, create_card_with_save_indicator, EntryCard
from ui.components.section_header import SectionHeader
from ui.components.tag_input import TagInput
from core.database import SessionLocal
from core.models import CVProfile

class SkillGroupEntry(EntryCard):
    def __init__(self, main_page, data=None):
        super().__init__()
        self.main_page = main_page
        
        self.category = QLineEdit()
        self.category.setPlaceholderText("Category (e.g., Programming Languages, Frameworks, Tools)")

        self.tags = TagInput()
        self.tags.set_placeholder("Add skills separated by comma...")

        self.layout.addWidget(QLabel("Skill Category:"))
        self.layout.addWidget(self.category)
        self.layout.addWidget(QLabel("Skills:"))
        self.layout.addWidget(self.tags)
        
        self.category.textChanged.connect(main_page.trigger_save)
        self.tags.tagsChanged.connect(main_page.trigger_save)

        if data:
            self.category.setText(data.get("category", ""))
            self.tags.set_tags(data.get("skills", []))

    def get_data(self):
        return {
            "category": self.category.text().strip(),
            "skills": self.tags.get_tags()
        }


class PowerUpsPage(CVSectionPage):
    """The Power-Ups page containing Skills."""
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        
        self.content_layout.addWidget(SectionHeader(
            "Power-Ups", 
            "Your technical and soft skills categorised for ATS systems to parse easily."
        ))

        self.setup_skills_card()
        
    def setup_skills_card(self):
        self.skills_card = create_card_with_save_indicator("Skill Configuration", self)
        
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(16)
        self.skills_card.content_layout.addLayout(self.list_layout)
        
        btn_add = QPushButton("+ Add Skill Category")
        btn_add.setProperty("class", "ghost")
        btn_add.clicked.connect(lambda: self.add_entry())
        self.skills_card.content_layout.addWidget(btn_add)
        
        self.content_layout.addWidget(self.skills_card)

    def add_entry(self, data=None):
        entry = SkillGroupEntry(self, data)
        entry.add_delete_button(lambda: self._remove_entry(self.list_layout, entry))
        self.list_layout.addWidget(entry)
        self.trigger_save()
        
    def _remove_entry(self, layout, widget):
        widget.deleteLater()
        self.trigger_save()

    def load_data(self):
        if not self.main_window.current_user: return
        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=self.main_window.current_user.id).first()
            if not profile: return
            
            while self.list_layout.count():
                w = self.list_layout.takeAt(0).widget()
                if w: w.deleteLater()
                
            for s in profile.skills_hard or []:
                self.add_entry(s)

    def save_data(self):
        if not self.main_window.current_user:
            return

        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=self.main_window.current_user.id).first()
            if not profile: return

            data = []
            for i in range(self.list_layout.count()):
                w = self.list_layout.itemAt(i).widget()
                if isinstance(w, SkillGroupEntry):
                    data.append(w.get_data())
            profile.skills_hard = data
            db.commit()
            
        self.skills_card.show_saved()
