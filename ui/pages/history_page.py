import os
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QPlainTextEdit, QTextEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QThreadPool
from PyQt6.QtGui import QPixmap

from ui.theme import COLORS
from ui.components.section_header import SectionHeader
from ui.components.card_widget import CardWidget
from ui.components.loading_overlay import LoadingOverlay
from ui.components.toast import ToastManager
from utils.worker import Worker
from core.database import SessionLocal
from core.models import GeneratedCV
import core.latex_service as latex_service
import core.llm_service as llm_service


class HistoryCard(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, record: GeneratedCV, parent=None):
        super().__init__(parent)
        self.record_id = record.id
        self.setObjectName("history_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("active", False)

        self.setStyleSheet(f"""
            QFrame#history_card {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
            QFrame#history_card[active="true"] {{
                border: 1px solid {COLORS['accent']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_text = record.job_title or "Generated CV"
        created = record.created_at.strftime("%Y-%m-%d %H:%M") if record.created_at else "Unknown date"
        score_text = f"Match: {record.match_score}%" if record.match_score is not None else "Match: N/A"

        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 14px;")

        self.subtitle_label = QLabel(created)
        self.subtitle_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")

        self.score_label = QLabel(score_text)
        self.score_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 12px; font-weight: bold;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.score_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.record_id)
        super().mousePressEvent(event)

    def set_active(self, active: bool):
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class HistoryPage(QWidget):
    """Browse and refine generated CVs."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.overlay = LoadingOverlay(self)

        self.current_cv_id = None
        self.current_pdf_path = ""
        self.current_latex_source = ""
        self._preview_image_paths = []
        self.history_min_height = 300
        self.history_max_height = 560

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(24)

        self.content_layout.addWidget(SectionHeader(
            "History",
            "Review past CVs, refine LaTeX, and recompile with targeted improvements."
        ))

        self.history_card = CardWidget("Generated CVs")
        history_layout = self.history_card.content_layout

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.history_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.history_container = QWidget()
        self.history_list_layout = QVBoxLayout(self.history_container)
        self.history_list_layout.setContentsMargins(0, 0, 0, 0)
        self.history_list_layout.setSpacing(12)
        self.history_scroll.setWidget(self.history_container)

        history_layout.addWidget(self.history_scroll)
        self.content_layout.addWidget(self.history_card)

        detail_layout = QHBoxLayout()
        detail_layout.setSpacing(24)

        self.preview_card = CardWidget("Preview")
        preview_layout = self.preview_card.content_layout

        preview_actions = QHBoxLayout()
        self.btn_edit_latex = QPushButton("Edit LaTeX")
        self.btn_edit_latex.setProperty("class", "secondary")
        self.btn_edit_latex.clicked.connect(self._show_latex_editor)

        self.btn_recompile = QPushButton("Recompile PDF")
        self.btn_recompile.setProperty("class", "primary")
        self.btn_recompile.clicked.connect(self._recompile_pdf)

        preview_actions.addWidget(self.btn_edit_latex)
        preview_actions.addStretch()
        preview_actions.addWidget(self.btn_recompile)
        preview_layout.addLayout(preview_actions)

        self.preview_title = QLabel("Select a CV to preview")
        self.preview_title.setStyleSheet(f"color: {COLORS['text_secondary']};")
        preview_layout.addWidget(self.preview_title)

        self.latex_editor = QPlainTextEdit()
        self.latex_editor.setMinimumHeight(600)
        self.latex_editor.setStyleSheet("font-family: monospace; font-size: 13px;")
        self.latex_editor.hide()
        preview_layout.addWidget(self.latex_editor)

        self.preview_scroll = QScrollArea(self.preview_card)
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(16)
        self.preview_scroll.setWidget(self.preview_container)
        self.preview_scroll.setMinimumHeight(600)
        self.preview_scroll.hide()
        preview_layout.addWidget(self.preview_scroll)

        detail_layout.addWidget(self.preview_card, stretch=3)

        self.info_panel = QWidget()
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(16)

        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self.score_card, self.score_value = self._build_info_card("Match Score")
        self.job_card, self.job_value = self._build_info_card("Job Title")
        self.date_card, self.date_value = self._build_info_card("Generated")

        info_row.addWidget(self.score_card)
        info_row.addWidget(self.job_card)
        info_row.addWidget(self.date_card)

        self.summary_card = CardWidget("Match Summary")
        summary_layout = self.summary_card.content_layout
        self.summary_label = QLabel("Select a CV to see match insights.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        summary_layout.addWidget(self.summary_label)

        self.prompt_card = CardWidget("Refine with AI")
        prompt_layout = self.prompt_card.content_layout
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Describe the changes you want, e.g. 'Emphasize data analytics outcomes and add metrics.'")
        self.prompt_input.setMinimumHeight(120)
        prompt_layout.addWidget(self.prompt_input)

        self.btn_apply_prompt = QPushButton("Apply Prompt")
        self.btn_apply_prompt.setProperty("class", "primary")
        self.btn_apply_prompt.clicked.connect(self._apply_prompt)
        prompt_layout.addWidget(self.btn_apply_prompt, alignment=Qt.AlignmentFlag.AlignRight)

        info_layout.addLayout(info_row)
        info_layout.addWidget(self.summary_card)
        info_layout.addStretch()
        info_layout.addWidget(self.prompt_card)

        detail_layout.addWidget(self.info_panel, stretch=2)

        self.content_layout.addLayout(detail_layout)
        self.content_layout.addStretch()

        scroll.setWidget(content_widget)
        self.layout.addWidget(scroll)

        self._history_cards = []
        self._load_history()

    def _build_info_card(self, title: str):
        card = CardWidget()
        card.main_layout.setContentsMargins(16, 16, 16, 16)
        layout = card.content_layout

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        value_label = QLabel("--")
        value_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 16px; font-weight: bold;")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def _load_history(self):
        self._clear_history_cards()
        user = self.main_window.current_user
        if not user:
            return

        with SessionLocal() as db:
            records = (
                db.query(GeneratedCV)
                .filter_by(user_id=user.id)
                .order_by(GeneratedCV.created_at.desc())
                .all()
            )

        if not records:
            empty_label = QLabel("No generated CVs yet. Create one in the Generate tab.")
            empty_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            self.history_list_layout.addWidget(empty_label)
            self._update_history_scroll_height()
            return

        for record in records:
            card = HistoryCard(record)
            card.clicked.connect(self._on_card_selected)
            self.history_list_layout.addWidget(card)
            self._history_cards.append(card)

        self.history_list_layout.addStretch()
        self._update_history_scroll_height()

    def _update_history_scroll_height(self):
        content_height = self.history_container.sizeHint().height() + 12
        target_height = max(self.history_min_height, content_height)
        target_height = min(target_height, self.history_max_height)
        self.history_scroll.setFixedHeight(target_height)

    def _clear_history_cards(self):
        while self.history_list_layout.count():
            item = self.history_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._history_cards = []

    def _on_card_selected(self, record_id: int):
        for card in self._history_cards:
            card.set_active(card.record_id == record_id)

        with SessionLocal() as db:
            record = db.query(GeneratedCV).filter_by(id=record_id).first()

        if not record:
            return

        self.current_cv_id = record.id
        self.current_pdf_path = record.pdf_path or ""
        self.current_latex_source = record.latex_source or ""

        self.preview_title.setText("Generated CV Preview")
        self.latex_editor.setPlainText(self.current_latex_source)
        self._update_info_cards(record)

        if self.current_pdf_path and os.path.exists(self.current_pdf_path):
            self._load_pdf_preview(self.current_pdf_path, "Preview loaded.")
        else:
            self._show_latex_editor()

    def _update_info_cards(self, record: GeneratedCV):
        self.score_value.setText(f"{record.match_score}%" if record.match_score is not None else "N/A")
        self.job_value.setText(record.job_title or "Unknown")
        if record.created_at:
            self.date_value.setText(record.created_at.strftime("%Y-%m-%d"))
        else:
            self.date_value.setText("Unknown")
        self.summary_label.setText(record.match_summary or "No summary available for this CV.")

    def _show_latex_editor(self):
        if not self.current_cv_id:
            return
        self.preview_scroll.hide()
        self.latex_editor.show()

    def _recompile_pdf(self):
        if not self.current_cv_id:
            return

        latex_source = self.latex_editor.toPlainText().strip()
        if not latex_source or "\\documentclass" not in latex_source:
            ToastManager.show_toast("LaTeX source is empty or invalid.", "warning")
            return

        self.overlay.show_progress("Recompiling PDF...", indeterminate=True)
        self._compile_worker = Worker(self._compile_latex_only, latex_source)
        self._compile_worker.signals.result.connect(self._on_compile_complete)
        self._compile_worker.signals.error.connect(self._on_generation_error)
        QThreadPool.globalInstance().start(self._compile_worker)

    def _compile_latex_only(self, latex_source):
        return latex_service.compile_latex_to_pdf(latex_source, "History")

    def _on_compile_complete(self, pdf_path):
        self.overlay.hide_overlay()
        if not pdf_path or not pdf_path.endswith(".pdf"):
            ToastManager.show_toast("Compilation failed. Is pdflatex installed?", "error")
            return

        self.current_pdf_path = pdf_path
        self.current_latex_source = self.latex_editor.toPlainText()
        self._persist_current_latex(self.current_latex_source, pdf_path)
        self._load_pdf_preview(pdf_path, "PDF recompiled successfully.")

    def _persist_current_latex(self, latex_source: str, pdf_path: str = ""):
        if not self.current_cv_id:
            return

        sections = [
            match.strip()
            for match in re.findall(r"\\section\{([^}]+)\}", latex_source or "")
            if match.strip()
        ]

        with SessionLocal() as db:
            record = db.query(GeneratedCV).filter_by(id=self.current_cv_id).first()
            if record:
                record.latex_source = latex_source
                record.sections_included = sections
                if pdf_path:
                    record.pdf_path = pdf_path
                db.commit()

    def _load_pdf_preview(self, pdf_path, success_toast):
        self.preview_title.setText("Generated CV Preview (PDF)")
        self.latex_editor.hide()
        self.preview_scroll.show()

        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            self.preview_scroll.hide()
            self.latex_editor.show()
            ToastManager.show_toast("PDF file is missing or empty. Showing LaTeX instead.", "warning")
            return

        self.overlay.show_progress("Rendering PDF preview...", indeterminate=True)
        self._render_worker = Worker(self._render_pdf_to_images, pdf_path)
        self._render_worker.signals.result.connect(self._on_render_complete)
        self._render_worker.signals.error.connect(self._on_generation_error)
        QThreadPool.globalInstance().start(self._render_worker)
        self._pending_pdf_toast = success_toast

    def _render_pdf_to_images(self, pdf_path):
        import fitz

        previews_dir = Path(os.path.expanduser("~/Documents/CVify/previews"))
        previews_dir.mkdir(parents=True, exist_ok=True)
        preview_dir = previews_dir / Path(pdf_path).stem
        preview_dir.mkdir(parents=True, exist_ok=True)

        for existing in preview_dir.glob("*.png"):
            try:
                existing.unlink()
            except OSError:
                pass

        doc = fitz.open(pdf_path)
        image_paths = []
        zoom = 2.0
        matrix = fitz.Matrix(zoom, zoom)
        for index in range(doc.page_count):
            page = doc.load_page(index)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image_path = preview_dir / f"page_{index + 1}.png"
            pix.save(str(image_path))
            image_paths.append(str(image_path))
        doc.close()
        return image_paths

    def _on_render_complete(self, image_paths):
        self.overlay.hide_overlay()
        if not image_paths:
            self.preview_scroll.hide()
            self.latex_editor.show()
            ToastManager.show_toast("PDF preview failed to render. Showing LaTeX instead.", "warning")
            return

        self._preview_image_paths = image_paths
        self._refresh_preview_images()
        if getattr(self, "_pending_pdf_toast", ""):
            ToastManager.show_toast(self._pending_pdf_toast, "success")
            self._pending_pdf_toast = ""

    def _refresh_preview_images(self):
        self._clear_preview_images()
        target_width = max(self.preview_scroll.viewport().width() - 24, 200)
        for image_path in self._preview_image_paths:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                continue
            scaled = pixmap.scaledToWidth(target_width, Qt.TransformationMode.SmoothTransformation)
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setPixmap(scaled)
            self.preview_layout.addWidget(label)
        self.preview_layout.addStretch()

    def _clear_preview_images(self):
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _apply_prompt(self):
        if not self.current_cv_id:
            ToastManager.show_toast("Select a CV first.", "warning")
            return

        prompt_text = self.prompt_input.toPlainText().strip()
        if not prompt_text:
            ToastManager.show_toast("Enter a prompt to apply.", "warning")
            return

        latex_source = self.latex_editor.toPlainText().strip()
        if not latex_source:
            ToastManager.show_toast("LaTeX source is empty.", "warning")
            return

        self.overlay.show_progress("Applying AI edits...", indeterminate=True)
        self._edit_worker = Worker(self._apply_prompt_worker, latex_source, prompt_text)
        self._edit_worker.signals.result.connect(self._on_prompt_applied)
        self._edit_worker.signals.error.connect(self._on_generation_error)
        QThreadPool.globalInstance().start(self._edit_worker)

    def _apply_prompt_worker(self, latex_source, prompt_text):
        job_description = ""
        with SessionLocal() as db:
            record = db.query(GeneratedCV).filter_by(id=self.current_cv_id).first()
            if record:
                job_description = record.job_description or ""
        return llm_service.apply_latex_prompt(latex_source, prompt_text, job_description)

    def _on_prompt_applied(self, updated_latex):
        self.overlay.hide_overlay()
        if not updated_latex or "\\documentclass" not in updated_latex:
            ToastManager.show_toast("AI response was not valid LaTeX.", "error")
            return

        self.latex_editor.setPlainText(updated_latex)
        self.current_latex_source = updated_latex
        self._persist_current_latex(updated_latex)
        ToastManager.show_toast("LaTeX updated. Recompiling preview...", "success")
        self._recompile_pdf()

    def _on_generation_error(self, error_trace):
        self.overlay.hide_overlay()
        print(error_trace)
        ToastManager.show_toast("Operation failed. Check terminal output.", "error")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())
        if self.preview_scroll.isVisible() and self._preview_image_paths:
            self._refresh_preview_images()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_history()
