from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QTextEdit,
    QPushButton, QDateEdit, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QDate

from ui.theme import COLORS
from ui.pages.cv_sections.base import CVSectionPage, create_card_with_save_indicator, EntryCard
from ui.components.section_header import SectionHeader
from core.database import SessionLocal
from core.models import CVProfile


class ProjectEntry(EntryCard):
    def __init__(self, main_page, data=None):
        super().__init__()
        self.main_page = main_page
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Project Name")
        self.link_edit = QLineEdit()
        self.link_edit.setPlaceholderText("Project Link / Repository")
        
        r1 = QHBoxLayout()
        r1.addWidget(self.name_edit)
        r1.addWidget(self.link_edit)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Description and tech stack used...")
        self.desc_edit.setFixedHeight(80)
        
        self.layout.addLayout(r1)
        self.layout.addWidget(QLabel("Description:"))
        self.layout.addWidget(self.desc_edit)
        
        self.name_edit.textChanged.connect(main_page.trigger_save)
        self.link_edit.textChanged.connect(main_page.trigger_save)
        self.desc_edit.textChanged.connect(main_page.trigger_save)

        if data:
            self.name_edit.setText(data.get("name", ""))
            self.link_edit.setText(data.get("link", ""))
            self.desc_edit.setPlainText(data.get("description", ""))

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "link": self.link_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip()
        }


class CertEntry(EntryCard):
    def __init__(self, main_page, data=None):
        super().__init__()
        self.main_page = main_page
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Certification Name")
        self.issuer_edit = QLineEdit()
        self.issuer_edit.setPlaceholderText("Issuer")
        
        r1 = QHBoxLayout()
        r1.addWidget(self.name_edit)
        r1.addWidget(self.issuer_edit)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("MM/yyyy")
        self.date_edit.setDate(QDate.currentDate())
        
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Date Issued:"))
        r2.addWidget(self.date_edit)
        r2.addStretch()
        
        self.layout.addLayout(r1)
        self.layout.addLayout(r2)
        
        self.name_edit.textChanged.connect(main_page.trigger_save)
        self.issuer_edit.textChanged.connect(main_page.trigger_save)
        self.date_edit.dateChanged.connect(lambda _: main_page.trigger_save())

        if data:
            self.name_edit.setText(data.get("name", ""))
            self.issuer_edit.setText(data.get("issuer", ""))
            try:
                if data.get("date"):
                    self.date_edit.setDate(QDate.fromString(data.get("date"), "MM/yyyy"))
            except: pass

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "issuer": self.issuer_edit.text().strip(),
            "date": self.date_edit.date().toString("MM/yyyy")
        }


class DifferentiatorsPage(CVSectionPage):
    """The Differentiators page containing Projects and Certifications."""
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        
        self.content_layout.addWidget(SectionHeader(
            "Differentiators", 
            "Stand out from the crowd with personal projects and certifications."
        ))

        self.setup_projects_card()
        self.setup_certs_card()
        
    def setup_projects_card(self):
        self.projects_card = create_card_with_save_indicator("Projects", self)
        
        self.proj_layout = QVBoxLayout()
        self.proj_layout.setSpacing(16)
        self.projects_card.content_layout.addLayout(self.proj_layout)
        
        btn_add = QPushButton("+ Add Project")
        btn_add.setProperty("class", "ghost")
        btn_add.clicked.connect(lambda: self.add_entry(self.proj_layout, ProjectEntry))
        self.projects_card.content_layout.addWidget(btn_add)
        
        self.content_layout.addWidget(self.projects_card)

    def setup_certs_card(self):
        self.certs_card = create_card_with_save_indicator("Certifications", self)
        
        self.certs_layout = QVBoxLayout()
        self.certs_layout.setSpacing(16)
        self.certs_card.content_layout.addLayout(self.certs_layout)
        
        btn_add = QPushButton("+ Add Certification")
        btn_add.setProperty("class", "ghost")
        btn_add.clicked.connect(lambda: self.add_entry(self.certs_layout, CertEntry))
        self.certs_card.content_layout.addWidget(btn_add)
        
        self.content_layout.addWidget(self.certs_card)

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
            
            while self.proj_layout.count():
                w = self.proj_layout.takeAt(0).widget()
                if w: w.deleteLater()
                
            for p in profile.projects or []:
                self.add_entry(self.proj_layout, ProjectEntry, p)
                
            while self.certs_layout.count():
                w = self.certs_layout.takeAt(0).widget()
                if w: w.deleteLater()
                
            for c in profile.certifications or []:
                self.add_entry(self.certs_layout, CertEntry, c)

    def save_data(self):
        if not self.main_window.current_user:
            return
            
        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=self.main_window.current_user.id).first()
            if not profile: return
            
            proj_data = []
            for i in range(self.proj_layout.count()):
                w = self.proj_layout.itemAt(i).widget()
                if isinstance(w, ProjectEntry):
                    proj_data.append(w.get_data())
            profile.projects = proj_data
            
            cert_data = []
            for i in range(self.certs_layout.count()):
                w = self.certs_layout.itemAt(i).widget()
                if isinstance(w, CertEntry):
                    cert_data.append(w.get_data())
            profile.certifications = cert_data
            
            db.commit()
            
        self.projects_card.show_saved()
        self.certs_card.show_saved()
