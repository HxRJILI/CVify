import json
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QTextEdit,
    QPushButton, QDateEdit, QCheckBox, QComboBox, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QIcon, QPixmap

from ui.theme import COLORS
from ui.pages.cv_sections.base import CVSectionPage, create_card_with_save_indicator, EntryCard
from ui.components.section_header import SectionHeader
from ui.components.toast import ToastManager
from core.database import SessionLocal
from core.models import CVProfile
from utils.validators import is_valid_url
from utils.worker import Worker
import core.llm_service as llm_service
from PyQt6.QtCore import QThreadPool

class BulletRow(QWidget):
    def __init__(self, main_page: CVSectionPage, text=""):
        super().__init__()
        self.main_page = main_page
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        
        self.handle = QLabel("↕")
        self.handle.setStyleSheet("color: " + COLORS['text_muted'] + ";")
        self.handle.setCursor(Qt.CursorShape.OpenHandCursor)
        
        self.input = QLineEdit(text)
        self.input.setPlaceholderText("Describe your achievement...")
        self.input.textChanged.connect(self.main_page.trigger_save)
        
        self.btn_ai = QPushButton("✧ AI Enhance")
        self.btn_ai.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {COLORS['accent']};
                color: {COLORS['accent']}; border-radius: 4px; padding: 4px 8px;
            }}
            QPushButton:hover {{ background: {COLORS['bg_elevated']}; }}
        """)
        
        self.btn_del = QPushButton("✕")
        self.btn_del.setFixedSize(28, 28)
        self.btn_del.setStyleSheet(f"color: {COLORS['error']}; background: transparent; border: none;")
        
        self.layout.addWidget(self.handle)
        self.layout.addWidget(self.input, stretch=1)
        self.layout.addWidget(self.btn_ai)
        self.layout.addWidget(self.btn_del)
        
        self.btn_ai.clicked.connect(self._enhance_text)
        
    def _enhance_text(self):
        text = self.input.text().strip()
        if not text or len(text) < 5:
            ToastManager.show_toast("Text is too short to enhance.", "warning")
            return
            
        self.btn_ai.setText("⌛...")
        self.btn_ai.setEnabled(False)
        self.input.setEnabled(False)
        
        self._worker = Worker(llm_service.enhance_text, text)
        self._worker.signals.result.connect(self._on_enhance_result)
        self._worker.signals.error.connect(self._on_enhance_error)
        QThreadPool.globalInstance().start(self._worker)
        
    def _on_enhance_result(self, new_text):
        self.btn_ai.setText("✧ AI Enhance")
        self.btn_ai.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setText(new_text)
        ToastManager.show_toast("Text enhanced successfully!", "success")
        
    def _on_enhance_error(self, error):
        self.btn_ai.setText("✧ AI Enhance")
        self.btn_ai.setEnabled(True)
        self.input.setEnabled(True)
        ToastManager.show_toast("Error enhancing text.", "error")

class BulletListEditor(QWidget):
    def __init__(self, main_page: CVSectionPage):
        super().__init__()
        self.main_page = main_page
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        
        self.rows_layout = QVBoxLayout()
        self.layout.addLayout(self.rows_layout)
        
        self.btn_add = QPushButton("+ Add Bullet")
        self.btn_add.setProperty("class", "ghost")
        self.btn_add.clicked.connect(lambda: self.add_bullet())
        self.layout.addWidget(self.btn_add, alignment=Qt.AlignmentFlag.AlignLeft)
        
    def add_bullet(self, text=""):
        row = BulletRow(self.main_page, text)
        row.btn_del.clicked.connect(lambda: self.remove_bullet(row))
        self.rows_layout.addWidget(row)
        if hasattr(self.main_page, "trigger_save"):
            self.main_page.trigger_save()
            
    def remove_bullet(self, row):
        row.deleteLater()
        if hasattr(self.main_page, "trigger_save"):
            self.main_page.trigger_save()
            
    def get_bullets(self):
        bullets = []
        for i in range(self.rows_layout.count()):
            w = self.rows_layout.itemAt(i).widget()
            if isinstance(w, BulletRow):
                txt = w.input.text().strip()
                if txt: bullets.append(txt)
        return bullets

    def clear(self):
        while self.rows_layout.count():
            w = self.rows_layout.takeAt(0).widget()
            if w: w.deleteLater()


class WorkExperienceEntry(EntryCard):
    def __init__(self, main_page, data=None):
        super().__init__()
        self.main_page = main_page
        
        # Fields
        self.company = QLineEdit()
        self.company.setPlaceholderText("Company Name")
        self.title = QLineEdit()
        self.title.setPlaceholderText("Job Title")
        self.location = QLineEdit()
        self.location.setPlaceholderText("Location")
        
        r1 = QHBoxLayout()
        r1.addWidget(self.company)
        r1.addWidget(self.title)
        
        r2 = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDisplayFormat("MM/yyyy")
        self.end_date = QDateEdit()
        self.end_date.setDisplayFormat("MM/yyyy")
        self.present_cb = QCheckBox("Present")
        self.present_cb.toggled.connect(self._toggle_end_date)
        
        r2.addWidget(QLabel("Start:"))
        r2.addWidget(self.start_date)
        r2.addWidget(QLabel("End:"))
        r2.addWidget(self.end_date)
        r2.addWidget(self.present_cb)
        r2.addStretch()
        
        self.bullets = BulletListEditor(main_page)
        
        self.layout.addLayout(r1)
        self.layout.addLayout(r2)
        self.layout.addWidget(self.location)
        self.layout.addWidget(QLabel("Achievements/Responsibilities:"))
        self.layout.addWidget(self.bullets)
        
        # Connect signals
        for w in [self.company, self.title, self.location]:
            w.textChanged.connect(main_page.trigger_save)
        self.start_date.dateChanged.connect(lambda _: main_page.trigger_save())
        self.end_date.dateChanged.connect(lambda _: main_page.trigger_save())
        self.present_cb.toggled.connect(lambda _: main_page.trigger_save())

        if data:
            self._load_data(data)
        else:
            self.start_date.setDate(QDate.currentDate())
            self.end_date.setDate(QDate.currentDate())
            self.bullets.add_bullet()
            
    def _toggle_end_date(self, checked):
        self.end_date.setEnabled(not checked)
        
    def _load_data(self, data):
        self.company.setText(data.get("company", ""))
        self.title.setText(data.get("title", ""))
        self.location.setText(data.get("location", ""))
        
        start = data.get("start", "")
        if start:
            try:
                self.start_date.setDate(QDate.fromString(start, "MM/yyyy"))
            except: pass
            
        end = data.get("end", "")
        if end.lower() == "present":
            self.present_cb.setChecked(True)
        elif end:
            try:
                self.end_date.setDate(QDate.fromString(end, "MM/yyyy"))
            except: pass
            
        for b in data.get("bullets", []):
            self.bullets.add_bullet(b)

    def get_data(self):
        end = "Present" if self.present_cb.isChecked() else self.end_date.date().toString("MM/yyyy")
        return {
            "company": self.company.text().strip(),
            "title": self.title.text().strip(),
            "location": self.location.text().strip(),
            "start": self.start_date.date().toString("MM/yyyy"),
            "end": end,
            "bullets": self.bullets.get_bullets()
        }

class EducationEntry(EntryCard):
    def __init__(self, main_page, data=None):
        super().__init__()
        self.main_page = main_page
        
        self.school = QLineEdit()
        self.school.setPlaceholderText("Institution Name")
        
        self.degree = QComboBox()
        self.degree.addItems(["Bachelor's", "Master's", "PhD", "Associate's", "Certificate", "High School", "Other"])
        
        self.field = QLineEdit()
        self.field.setPlaceholderText("Field of Study")
        
        self.gpa = QLineEdit()
        self.gpa.setPlaceholderText("GPA (Optional)")
        
        r1 = QHBoxLayout()
        r1.addWidget(self.school)
        r1.addWidget(self.degree)
        
        r2 = QHBoxLayout()
        r2.addWidget(self.field)
        r2.addWidget(self.gpa)
        
        r3 = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDisplayFormat("MM/yyyy")
        self.end_date = QDateEdit()
        self.end_date.setDisplayFormat("MM/yyyy")
        self.expected_cb = QCheckBox("Expected")
        
        r3.addWidget(QLabel("Start:"))
        r3.addWidget(self.start_date)
        r3.addWidget(QLabel("End:"))
        r3.addWidget(self.end_date)
        r3.addWidget(self.expected_cb)
        r3.addStretch()
        
        self.layout.addLayout(r1)
        self.layout.addLayout(r2)
        self.layout.addLayout(r3)
        
        # Connect
        for w in [self.school, self.field, self.gpa]:
            w.textChanged.connect(main_page.trigger_save)
        self.degree.currentIndexChanged.connect(lambda _: main_page.trigger_save())
        self.start_date.dateChanged.connect(lambda _: main_page.trigger_save())
        self.end_date.dateChanged.connect(lambda _: main_page.trigger_save())
        self.expected_cb.toggled.connect(lambda _: main_page.trigger_save())

        if data:
            self._load_data(data)
        else:
            self.start_date.setDate(QDate.currentDate())
            self.end_date.setDate(QDate.currentDate())

    def _load_data(self, data):
        self.school.setText(data.get("institution", ""))
        self.field.setText(data.get("field", ""))
        self.gpa.setText(data.get("gpa", ""))
        idx = self.degree.findText(data.get("degree", ""))
        if idx >= 0: self.degree.setCurrentIndex(idx)
        
        if data.get("start"): self.start_date.setDate(QDate.fromString(data.get("start"), "MM/yyyy"))
        if "Expected" in data.get("end", ""):
            self.expected_cb.setChecked(True)
            try:
                date_str = data.get("end").replace(" (Expected)", "")
                self.end_date.setDate(QDate.fromString(date_str, "MM/yyyy"))
            except: pass
        elif data.get("end"):
            self.end_date.setDate(QDate.fromString(data.get("end"), "MM/yyyy"))
            
    def get_data(self):
        end = self.end_date.date().toString("MM/yyyy")
        if self.expected_cb.isChecked(): end += " (Expected)"
        return {
            "institution": self.school.text().strip(),
            "degree": self.degree.currentText(),
            "field": self.field.text().strip(),
            "start": self.start_date.date().toString("MM/yyyy"),
            "end": end,
            "gpa": self.gpa.text().strip()
        }


class EssentialsPage(CVSectionPage):
    """The Essentials page containing Contact, Summary, Work, and Education."""
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        
        self.content_layout.addWidget(SectionHeader(
            "The Essentials", 
            "Your core information. This is the foundation of every professional CV."
        ))

        self.setup_contact_card()
        self.setup_summary_card()
        self.setup_work_card()
        self.setup_education_card()
        
    def setup_contact_card(self):
        self.contact_card = create_card_with_save_indicator("Contact Information", self)

        self.photo_path = ""
        self.photo_preview = QLabel("No image uploaded")
        self.photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_preview.setFixedSize(120, 150)
        self.photo_preview.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['bg_elevated']};
                border: 1px dashed {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text_secondary']};
            }}
        """)

        self.photo_label = QLabel("Upload a headshot to place it in the CV header.")
        self.photo_label.setWordWrap(True)
        self.photo_label.setStyleSheet(f"color: {COLORS['text_secondary']};")

        self.btn_upload_photo = QPushButton("Upload Photo")
        self.btn_upload_photo.setProperty("class", "ghost")
        self.btn_upload_photo.clicked.connect(self._upload_photo)

        photo_controls = QVBoxLayout()
        photo_controls.addWidget(self.photo_label)
        photo_controls.addSpacing(8)
        photo_controls.addWidget(self.btn_upload_photo, alignment=Qt.AlignmentFlag.AlignLeft)
        photo_controls.addStretch()

        photo_row = QHBoxLayout()
        photo_row.addWidget(self.photo_preview)
        photo_row.addSpacing(16)
        photo_row.addLayout(photo_controls)

        self.contact_card.content_layout.addLayout(photo_row)
        self.contact_card.content_layout.addSpacing(8)
        
        self.cf_name = QLineEdit()
        self.cf_name.setPlaceholderText("Full Name")
        self.cf_phone = QLineEdit()
        self.cf_phone.setPlaceholderText("Professional Phone (eg. +1 555-000-0000)")
        self.cf_email = QLineEdit()
        self.cf_email.setPlaceholderText("Email Address")
        self.cf_location = QLineEdit()
        self.cf_location.setPlaceholderText("Location (City, State)")
        self.cf_linkedin = QLineEdit()
        self.cf_linkedin.setPlaceholderText("LinkedIn URL")
        self.cf_portfolio = QLineEdit()
        self.cf_portfolio.setPlaceholderText("Portfolio / Website URL")
        
        # Add to Card
        for row in [(self.cf_name, self.cf_phone), (self.cf_email, self.cf_location), (self.cf_linkedin, self.cf_portfolio)]:
            h = QHBoxLayout()
            h.addWidget(row[0])
            h.addWidget(row[1])
            self.contact_card.content_layout.addLayout(h)
            
        # Hook up
        for w in [self.cf_name, self.cf_phone, self.cf_email, self.cf_location, self.cf_linkedin, self.cf_portfolio]:
            w.textChanged.connect(self.trigger_save)
            
        self.content_layout.addWidget(self.contact_card)

    def _upload_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Photo",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not file_path:
            return

        source_path = Path(file_path)
        target_dir = Path.home() / "Documents" / "CVify" / "photos"
        target_dir.mkdir(parents=True, exist_ok=True)

        user_token = str(self.main_window.current_user.id if self.main_window.current_user else "user")
        target_path = target_dir / f"cv_photo_{user_token}{source_path.suffix.lower() or '.jpg'}"
        if source_path.resolve() != target_path.resolve():
            shutil.copy2(source_path, target_path)

        self.photo_path = str(target_path)
        self._refresh_photo_preview(self.photo_path)
        self.trigger_save()

    def _refresh_photo_preview(self, photo_path: str):
        if photo_path and Path(photo_path).exists():
            pixmap = QPixmap(photo_path)
            if not pixmap.isNull():
                self.photo_preview.setPixmap(
                    pixmap.scaled(
                        self.photo_preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.photo_label.setText(Path(photo_path).name)
                return

        self.photo_preview.clear()
        self.photo_preview.setText("No image uploaded")
        self.photo_label.setText("Upload a headshot to place it in the CV header.")

    def setup_summary_card(self):
        self.summary_card = create_card_with_save_indicator("Professional Summary", self)
        
        self.summary_edit = QTextEdit()
        self.summary_edit.setFixedHeight(100)
        self.summary_edit.setPlaceholderText("A brief overview of your professional background and key strengths...")
        self.summary_edit.textChanged.connect(self._on_summary_changed)
        
        self.char_counter = QLabel("0 / 600")
        self.char_counter.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.char_counter.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.btn_ai_summary = QPushButton("✧ AI Enhance")
        self.btn_ai_summary.setProperty("class", "ghost")
        self.btn_ai_summary.clicked.connect(self._enhance_summary)
        
        bot_layout = QHBoxLayout()
        bot_layout.addWidget(self.btn_ai_summary)
        bot_layout.addStretch()
        bot_layout.addWidget(self.char_counter)

        self.summary_card.content_layout.addWidget(self.summary_edit)
        self.summary_card.content_layout.addLayout(bot_layout)

        self.content_layout.addWidget(self.summary_card)

    def _enhance_summary(self):
        text = self.summary_edit.toPlainText().strip()
        if not text or len(text) < 10:
            ToastManager.show_toast("Text is too short to enhance.", "warning")
            return
            
        self.btn_ai_summary.setText("⌛...")
        self.btn_ai_summary.setEnabled(False)
        self.summary_edit.setEnabled(False)
        
        self._worker = Worker(llm_service.enhance_text, text)
        self._worker.signals.result.connect(self._on_enhance_summary_result)
        self._worker.signals.error.connect(self._on_enhance_summary_error)
        QThreadPool.globalInstance().start(self._worker)

    def _on_enhance_summary_result(self, new_text):
        self.btn_ai_summary.setText("✧ AI Enhance")
        self.btn_ai_summary.setEnabled(True)
        self.summary_edit.setEnabled(True)
        self.summary_edit.setPlainText(new_text)
        ToastManager.show_toast("Summary enhanced successfully!", "success")
        
    def _on_enhance_summary_error(self, error):
        self.btn_ai_summary.setText("✧ AI Enhance")
        self.btn_ai_summary.setEnabled(True)
        self.summary_edit.setEnabled(True)
        ToastManager.show_toast("Error enhancing text.", "error")

    def _on_summary_changed(self):
        text = self.summary_edit.toPlainText()
        length = len(text)
        self.char_counter.setText(f"{length} / 600")
        
        if length >= 590:
            self.char_counter.setStyleSheet(f"color: {COLORS['error']};")
        elif length >= 500:
            self.char_counter.setStyleSheet(f"color: {COLORS['warning']};")
        else:
            self.char_counter.setStyleSheet(f"color: {COLORS['text_secondary']};")
            
        self.trigger_save()

    def setup_work_card(self):
        self.work_card = create_card_with_save_indicator("Work Experience", self)
        
        self.work_list_layout = QVBoxLayout()
        self.work_list_layout.setSpacing(16)
        self.work_card.content_layout.addLayout(self.work_list_layout)
        
        btn_add = QPushButton("+ Add Work Experience")
        btn_add.setProperty("class", "ghost")
        btn_add.clicked.connect(lambda: self.add_work_entry())
        self.work_card.content_layout.addWidget(btn_add)
        
        self.content_layout.addWidget(self.work_card)

    def add_work_entry(self, data=None):
        entry = WorkExperienceEntry(self, data)
        entry.add_delete_button(lambda: self._remove_entry(self.work_list_layout, entry))
        self.work_list_layout.addWidget(entry)
        self.trigger_save()
        
    def setup_education_card(self):
        self.edu_card = create_card_with_save_indicator("Education", self)
        
        self.edu_list_layout = QVBoxLayout()
        self.edu_list_layout.setSpacing(16)
        self.edu_card.content_layout.addLayout(self.edu_list_layout)
        
        btn_add = QPushButton("+ Add Education")
        btn_add.setProperty("class", "ghost")
        btn_add.clicked.connect(lambda: self.add_edu_entry())
        self.edu_card.content_layout.addWidget(btn_add)
        
        self.content_layout.addWidget(self.edu_card)
        
    def add_edu_entry(self, data=None):
        entry = EducationEntry(self, data)
        entry.add_delete_button(lambda: self._remove_entry(self.edu_list_layout, entry))
        self.edu_list_layout.addWidget(entry)
        self.trigger_save()

    def _remove_entry(self, layout, widget):
        widget.deleteLater()
        self.trigger_save()

    def load_data(self):
        if not self.main_window.current_user: return
        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=self.main_window.current_user.id).first()
            if not profile: return

            self.photo_path = profile.photo_path or ""
            self._refresh_photo_preview(self.photo_path)
            
            c = profile.contact or {}
            self.cf_name.setText(c.get("name", ""))
            self.cf_phone.setText(c.get("phone", ""))
            self.cf_email.setText(c.get("email", ""))
            self.cf_location.setText(c.get("location", ""))
            self.cf_linkedin.setText(c.get("linkedin", ""))
            self.cf_portfolio.setText(c.get("portfolio", ""))
            
            self.summary_edit.setPlainText(profile.summary or "")
            
            # Clear existing lists
            while self.work_list_layout.count():
                w = self.work_list_layout.takeAt(0).widget()
                if w: w.deleteLater()
                
            for w in profile.work_experience or []:
                self.add_work_entry(w)
                
            while self.edu_list_layout.count():
                w = self.edu_list_layout.takeAt(0).widget()
                if w: w.deleteLater()
                
            for e in profile.education or []:
                self.add_edu_entry(e)
                
    def save_data(self):
        if not self.main_window.current_user:
            return
            
        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=self.main_window.current_user.id).first()
            if not profile: return
            
            profile.contact = {
                "name": self.cf_name.text().strip(),
                "phone": self.cf_phone.text().strip(),
                "email": self.cf_email.text().strip(),
                "location": self.cf_location.text().strip(),
                "linkedin": self.cf_linkedin.text().strip(),
                "portfolio": self.cf_portfolio.text().strip()
            }
            profile.photo_path = self.photo_path or None
            
            profile.summary = self.summary_edit.toPlainText().strip()
            
            work_data = []
            for i in range(self.work_list_layout.count()):
                w = self.work_list_layout.itemAt(i).widget()
                if isinstance(w, WorkExperienceEntry):
                    work_data.append(w.get_data())
            profile.work_experience = work_data
            
            edu_data = []
            for i in range(self.edu_list_layout.count()):
                w = self.edu_list_layout.itemAt(i).widget()
                if isinstance(w, EducationEntry):
                    edu_data.append(w.get_data())
            profile.education = edu_data
            
            db.commit()
            
        # Update UI indicators
        self.contact_card.show_saved()
        self.summary_card.show_saved()
        self.work_card.show_saved()
        self.edu_card.show_saved()
