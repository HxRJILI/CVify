import json
import os
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPlainTextEdit,
    QPushButton, QFrame, QScrollArea, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThreadPool
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap

from ui.theme import COLORS
from ui.components.section_header import SectionHeader
from ui.components.card_widget import CardWidget
from ui.components.loading_overlay import LoadingOverlay
from ui.components.toast import ToastManager
from core.database import SessionLocal
from core.models import CVProfile, GeneratedCV
from utils.worker import Worker
import core.llm_service as llm_service
import core.latex_service as latex_service


class MatchScoreCircle(QWidget):
    """A custom widget to draw a circular progress bar for Job Match Score."""
    def __init__(self, score=0, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.score = score

    def set_score(self, score):
        self.score = score
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        margin = 10
        draw_rect = rect.adjusted(margin, margin, -margin, -margin)

        # Draw background circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS['border']))
        painter.drawEllipse(draw_rect)

        # Draw progress arc
        pen = painter.pen()
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidth(8)
        
        # Color based on score
        if self.score >= 80:
            color = QColor(COLORS['success'])
        elif self.score >= 50:
            color = QColor(COLORS['warning'])
        else:
            color = QColor(COLORS['error'])
            
        pen.setColor(color)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        start_angle = 90 * 16
        span_angle = int(-(self.score / 100.0) * 360 * 16)
        painter.drawArc(draw_rect, start_angle, span_angle)

        # Draw center text
        painter.setPen(QColor(COLORS['text_primary']))
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.score}%")


from PyQt6.QtWidgets import QFileDialog

class GeneratePage(QWidget):
    """The central hub for generating CVs tailored to a specific job description."""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        self.last_match_score = None
        self.last_match_summary = ""
        
        # Overlay for loading states
        self.overlay = LoadingOverlay(self)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(24)
        
        # Header
        self.content_layout.addWidget(SectionHeader(
            "Tailor & Generate", 
            "Paste a job description below. AI will match your profile and generate a highly targeted, ATS-optimised CV."
        ))

        # --- Job Details Section ---
        self.job_card = CardWidget()
        job_layout = self.job_card.content_layout
        
        lbl_target = QLabel("Target Job Title")
        lbl_target.setProperty("class", "subheading")
        self.job_title_input = QLineEdit()
        self.job_title_input.setPlaceholderText("e.g. Senior Software Engineer")
        
        lbl_jd = QLabel("Job Description")
        lbl_jd.setProperty("class", "subheading")
        self.jd_input = QTextEdit()
        self.jd_input.setPlaceholderText("Paste the full job description here...")
        self.jd_input.setMinimumHeight(180)
        
        self.btn_analyze = QPushButton("✧ Analyze Match")
        self.btn_analyze.setProperty("class", "primary")
        self.btn_analyze.clicked.connect(self._analyze_job)
        
        job_layout.addWidget(lbl_target)
        job_layout.addWidget(self.job_title_input)
        job_layout.addSpacing(12)
        job_layout.addWidget(lbl_jd)
        job_layout.addWidget(self.jd_input)
        job_layout.addSpacing(16)
        job_layout.addWidget(self.btn_analyze, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.content_layout.addWidget(self.job_card)

        # --- Analysis Results (Hidden initially) ---
        self.results_card = CardWidget()
        self.results_card.hide()
        results_layout = self.results_card.content_layout
        
        top_res_layout = QHBoxLayout()
        self.match_circle = MatchScoreCircle()
        
        res_info_layout = QVBoxLayout()
        self.res_title = QLabel("Analysis Complete")
        self.res_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_primary']};")
        self.res_desc = QLabel("Your profile is a strong match for this role. We have isolated key keywords to emphasise.")
        self.res_desc.setWordWrap(True)
        self.res_desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        res_info_layout.addWidget(self.res_title)
        res_info_layout.addWidget(self.res_desc)
        res_info_layout.addStretch()
        
        top_res_layout.addWidget(self.match_circle)
        top_res_layout.addSpacing(24)
        top_res_layout.addLayout(res_info_layout)
        
        results_layout.addLayout(top_res_layout)
        results_layout.addSpacing(24)
        
        # Generation actions
        actions_layout = QHBoxLayout()
        self.btn_generate_pdf = QPushButton("Generate PDF (LaTeX)")
        self.btn_generate_pdf.setProperty("class", "primary")
        self.btn_generate_pdf.setMinimumWidth(200)
        self.btn_generate_pdf.clicked.connect(self._generate_cv)
        
        # Mocking an alternative action
        self.btn_preview = QPushButton("Preview Content")
        self.btn_preview.setProperty("class", "ghost")
        
        actions_layout.addWidget(self.btn_preview)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_generate_pdf)
        
        results_layout.addLayout(actions_layout)
        
        self.content_layout.addWidget(self.results_card)

        # PDF Preview Section
        self.pdf_card = CardWidget()
        self.pdf_card.hide()
        pdf_layout = self.pdf_card.content_layout
        self.pdf_title = QLabel("Generated CV Preview")
        self.pdf_title.setProperty("class", "h2")
        pdf_layout.addWidget(self.pdf_title)

        self.latex_editor = QPlainTextEdit()
        self.latex_editor.setMinimumHeight(600)
        self.latex_editor.setStyleSheet("font-family: monospace; font-size: 13px;")
        self.latex_editor.hide()
        pdf_layout.addWidget(self.latex_editor)

        self.preview_scroll = QScrollArea(self.pdf_card)
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(16)
        self.preview_scroll.setWidget(self.preview_container)
        self.preview_scroll.setMinimumHeight(600)
        pdf_layout.addWidget(self.preview_scroll)
        self.preview_scroll.hide()
        self._pending_pdf_toast = ""
        self._preview_image_paths = []

        btn_layout = QHBoxLayout()
        self.btn_toggle_view = QPushButton("Toggle View (PDF/LaTeX)")
        self.btn_toggle_view.setProperty("class", "secondary")
        self.btn_toggle_view.clicked.connect(self._toggle_view)
        self.btn_download = QPushButton("Download Text/PDF")
        self.btn_download.setProperty("class", "primary")
        self.btn_download.clicked.connect(self._download_pdf)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_toggle_view)
        btn_layout.addWidget(self.btn_download)
        pdf_layout.addLayout(btn_layout)

        self.content_layout.addWidget(self.pdf_card)

        self.content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        self.layout.addWidget(scroll)

    def _analyze_job(self):
        self.job_title = self.job_title_input.text().strip()
        self.jd = self.jd_input.toPlainText().strip()

        if not self.job_title or len(self.jd) < 20:
            ToastManager.show_toast("Please provide a valid title and job description.", "error")
            return

        self.overlay.show_overlay("Analyzing Job Match via AI...")

        profile_data = self._get_profile_data()

        self._worker = Worker(llm_service.analyze_match, profile_data, self.jd)
        self._worker.signals.result.connect(self._on_analysis_complete)
        self._worker.signals.error.connect(self._on_generation_error)
        QThreadPool.globalInstance().start(self._worker)

    def _on_analysis_complete(self, result):
        self.overlay.hide_overlay()
        self.btn_analyze.hide()

        score = result.get("score", 0)
        summary = result.get("summary", "Analysis failed.")

        self.last_match_score = score
        self.last_match_summary = summary
        
        self.match_circle.set_score(score)
        self.res_desc.setText(summary)
        self.results_card.show()
        ToastManager.show_toast("Analysis complete! Ready to generate.", "success")

    def _generate_cv(self):
        self.overlay.show_progress("Generating tailored LaTeX via AI...", indeterminate=True)
        self.job_title = self.job_title_input.text().strip() or getattr(self, "job_title", "")
        self.jd = self.jd_input.toPlainText().strip() or getattr(self, "jd", "")

        profile_data = self._get_profile_data()

        user_id = self.main_window.current_user.id if self.main_window.current_user else None
        self._worker = Worker(
            self._llm_and_latex_flow,
            profile_data,
            self.jd,
            self.job_title,
            user_id,
            self.last_match_score,
            self.last_match_summary,
        )
        self._worker.signals.result.connect(self._on_generation_complete)
        self._worker.signals.error.connect(self._on_generation_error)
        QThreadPool.globalInstance().start(self._worker)
        
    def _llm_and_latex_flow(self, profile_data, jd, job_title, user_id, match_score, match_summary):
        # 1. Ask LLM for the LaTeX code
        latex_source = llm_service.generate_latex(profile_data, jd, job_title)
        # 2. Compile it using pdflatex
        pdf_path = latex_service.compile_latex_to_pdf(latex_source, job_title)
        # 3. Persist to history
        if user_id:
            sections = self._extract_sections_from_latex(latex_source)
            self._save_generated_cv(
                user_id=user_id,
                job_title=job_title,
                job_description=jd,
                latex_source=latex_source,
                pdf_path=pdf_path,
                sections_included=sections,
                match_score=match_score,
                match_summary=match_summary,
            )
        return {"pdf_path": pdf_path, "latex_source": latex_source}

    def _extract_sections_from_latex(self, latex_source: str) -> list:
        return [match.strip() for match in re.findall(r"\\section\{([^}]+)\}", latex_source or "") if match.strip()]

    def _save_generated_cv(
        self,
        user_id,
        job_title,
        job_description,
        latex_source,
        pdf_path,
        sections_included,
        match_score,
        match_summary,
    ):
        with SessionLocal() as db:
            record = GeneratedCV(
                user_id=user_id,
                template_id="modern_clean",
                job_title=job_title or "",
                job_description=job_description or "",
                match_score=match_score,
                match_summary=match_summary or "",
                sections_included=sections_included or [],
                latex_source=latex_source or "",
                pdf_path=pdf_path or "",
            )
            db.add(record)
            db.commit()

    def _get_profile_data(self):
        profile_data = {}
        with SessionLocal() as db:
            profile = db.query(CVProfile).filter_by(user_id=self.main_window.current_user.id).first()
            if profile:
                profile_data = {
                    "contact": profile.contact or {},
                    "summary": profile.summary or "",
                    "work_experience": profile.work_experience or [],
                    "education": profile.education or [],
                    "skills_hard": profile.skills_hard or [],
                    "skills_soft": profile.skills_soft or [],
                    "certifications": profile.certifications or [],
                    "projects": profile.projects or [],
                    "awards": profile.awards or [],
                    "volunteer": profile.volunteer or [],
                    "languages": profile.languages or [],
                    "publications": profile.publications or [],
                    "affiliations": profile.affiliations or [],
                    "interests": profile.interests or [],
                    "conferences": profile.conferences or [],
                    "photo_path": profile.photo_path or "",
                }
        return profile_data

    def _on_generation_complete(self, result):
        self.overlay.hide_overlay()
        if isinstance(result, dict):
            pdf_path = result.get("pdf_path", "")
            latex_source = result.get("latex_source", "")
        else:
            pdf_path = result
            latex_source = ""

        self.current_pdf_path = pdf_path
        self.current_tex_path = pdf_path.replace('.pdf', '.tex') if pdf_path.endswith('.pdf') else pdf_path
        self.current_latex_source = latex_source

        if latex_source and self.current_tex_path:
            try:
                if not os.path.exists(self.current_tex_path) or os.path.getsize(self.current_tex_path) == 0:
                    with open(self.current_tex_path, 'w', encoding='utf-8') as f:
                        f.write(latex_source)
            except Exception:
                pass
        
        self.pdf_card.show()
        if pdf_path.endswith('.pdf'):
            self._load_pdf_preview(pdf_path, "CV Generated successfully!")
            # Pre-load latex editor so user can toggle to it
            if latex_source:
                self.latex_editor.setPlainText(latex_source)
            else:
                try:
                    with open(self.current_tex_path, 'r', encoding='utf-8') as f:
                        self.latex_editor.setPlainText(f.read())
                except Exception:
                    self.latex_editor.setPlainText("% LaTeX source could not be loaded. Try regenerating the CV.\n")
            ToastManager.show_toast(f"CV Generated successfully!", "success")
        else:
            self.pdf_title.setText("Generated CV Source (LaTeX)")
            self.preview_scroll.hide()
            self.latex_editor.show()
            if latex_source:
                self.latex_editor.setPlainText(latex_source)
            else:
                try:
                    with open(self.current_tex_path, 'r', encoding='utf-8') as f:
                        self.latex_editor.setPlainText(f.read())
                except Exception as e:
                    self.latex_editor.setPlainText(f"Error reading LaTeX file: {e}")
            ToastManager.show_toast(f"LaTeX generated instead. Install 'pdflatex' to compile PDF natively.", "warning")

    def _toggle_view(self):
        if self.latex_editor.isVisible():
            latex_source = self.latex_editor.toPlainText().strip()
            if not latex_source or "\\documentclass" not in latex_source:
                cached_source = getattr(self, "current_latex_source", "")
                if cached_source:
                    latex_source = cached_source
                    self.latex_editor.setPlainText(cached_source)
            if not latex_source or "\\documentclass" not in latex_source:
                fallback_tex = getattr(self, "current_tex_path", "")
                if fallback_tex:
                    try:
                        with open(fallback_tex, 'r', encoding='utf-8') as f:
                            latex_source = f.read()
                            self.latex_editor.setPlainText(latex_source)
                    except Exception:
                        latex_source = ""
            if not latex_source or "\\documentclass" not in latex_source:
                ToastManager.show_toast("LaTeX source is empty or invalid. Regenerate the CV first.", "warning")
                return
            # Compiling into PDF
            self.overlay.show_progress("Compiling PDF...", indeterminate=True)
            job_title = getattr(self, 'job_title', 'Job')
            
            self._compile_worker = Worker(self._compile_latex_only, latex_source, job_title)
            self._compile_worker.signals.result.connect(self._on_compile_complete)
            self._compile_worker.signals.error.connect(self._on_generation_error)
            QThreadPool.globalInstance().start(self._compile_worker)
        else:
            self.pdf_title.setText("Generated CV Source (LaTeX)")
            self.preview_scroll.hide()
            self.latex_editor.show()

    def _compile_latex_only(self, latex_source, job_title):
        return latex_service.compile_latex_to_pdf(latex_source, job_title)

    def _on_compile_complete(self, pdf_path):
        self.overlay.hide_overlay()
        self.current_pdf_path = pdf_path
        if pdf_path.endswith('.pdf'):
            self._load_pdf_preview(pdf_path, "PDF compiled successfully!")
        else:
            ToastManager.show_toast("Could not compile to PDF. Is 'pdflatex' installed?", "error")

    def _load_pdf_preview(self, pdf_path, success_toast):
        self.pdf_title.setText("Generated CV Preview (PDF)")
        self.latex_editor.hide()
        self.preview_scroll.show()
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            self.preview_scroll.hide()
            self.latex_editor.show()
            self.pdf_title.setText("Generated CV Source (LaTeX)")
            ToastManager.show_toast("PDF file is missing or empty. Showing LaTeX instead.", "warning")
            return

        self._pending_pdf_toast = success_toast
        self.overlay.show_progress("Rendering PDF preview...", indeterminate=True)
        self._render_worker = Worker(self._render_pdf_to_images, pdf_path)
        self._render_worker.signals.result.connect(self._on_render_complete)
        self._render_worker.signals.error.connect(self._on_generation_error)
        QThreadPool.globalInstance().start(self._render_worker)

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
            self.pdf_title.setText("Generated CV Source (LaTeX)")
            ToastManager.show_toast("PDF preview failed to render. Showing LaTeX instead.", "warning")
            return

        self._preview_image_paths = image_paths
        self._refresh_preview_images()
        if self._pending_pdf_toast:
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

    def _download_pdf(self):
        if not hasattr(self, 'current_pdf_path') or not self.current_pdf_path:
            return

        import shutil
        import os
        from PyQt6.QtWidgets import QFileDialog

        # If it's a .tex file, save the edited text before downloading
        if self.current_pdf_path.endswith('.tex'):
            try:
                with open(self.current_pdf_path, 'w', encoding='utf-8') as f:
                    f.write(self.latex_editor.toPlainText())
            except Exception as e:
                print(f"Failed to auto-save latex editor content: {e}")

        default_name = os.path.basename(self.current_pdf_path)
        ext = '.pdf' if self.current_pdf_path.endswith('.pdf') else '.tex'
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Generated Document",
            default_name,
            f"Document (*{ext})"
        )
        
        if save_path:
            try:
                shutil.copy2(self.current_pdf_path, save_path)
                ToastManager.show_toast("File saved successfully!", "success")
            except Exception as e:
                ToastManager.show_toast(f"Failed to save file: {e}", "error")

    def _on_generation_error(self, error_trace):
        self.overlay.hide_overlay()
        print(error_trace)
        ToastManager.show_toast("Generation error: Please refer to terminal output.", "error")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())
        if self.preview_scroll.isVisible() and self._preview_image_paths:
            self._refresh_preview_images()
