import math
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QGridLayout, QSizePolicy, QGraphicsOpacityEffect,
    QFrame
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QVariantAnimation, 
    QPoint, pyqtProperty, pyqtSignal, QRect, QSequentialAnimationGroup, 
    QPauseAnimation, QParallelAnimationGroup, QRectF
)
from PyQt6.QtGui import (
    QPainter, QColor, QPainterPath, QPen, QFont, QRadialGradient, QBrush, QPixmap
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from ui.theme import COLORS

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False

class AnimatedTitleLabel(QWidget):
    """Animated hero title that cycles words with fade/slide."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.words = ["Build", "Perfect", "Generate"]
        self.current_idx = 0
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        prefix = QLabel("Land the Job.")
        prefix.setStyleSheet("font-size: 34px; font-weight: bold;")
        self.layout.addWidget(prefix)
        
        self.dynamic_word_container = QWidget()
        self.dynamic_word_container.setFixedSize(160, 50)
        self.dynamic_word_layout = QVBoxLayout(self.dynamic_word_container)
        self.dynamic_word_layout.setContentsMargins(0,0,0,0)
        
        self.dynamic_label = QLabel(self.words[self.current_idx])
        self.dynamic_label.setStyleSheet(f"font-size: 34px; font-weight: bold; color: {COLORS['accent']};")
        self.dynamic_word_layout.addWidget(self.dynamic_label)
        
        self.opacity_effect = QGraphicsOpacityEffect(self.dynamic_label)
        self.dynamic_label.setGraphicsEffect(self.opacity_effect)
        
        self.layout.addWidget(self.dynamic_word_container)
        
        suffix = QLabel("the CV.")
        suffix.setStyleSheet("font-size: 34px; font-weight: bold;")
        self.layout.addWidget(suffix)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_word)
        self.timer.start(3000)

    def animate_word(self):
        # Slide and fade out
        self.out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.out_anim.setDuration(300)
        self.out_anim.setStartValue(1.0)
        self.out_anim.setEndValue(0.0)
        self.out_anim.finished.connect(self._change_word_and_fade_in)
        self.out_anim.start()

    def _change_word_and_fade_in(self):
        self.current_idx = (self.current_idx + 1) % len(self.words)
        self.dynamic_label.setText(self.words[self.current_idx])
        
        self.in_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.in_anim.setDuration(300)
        self.in_anim.setStartValue(0.0)
        self.in_anim.setEndValue(1.0)
        self.in_anim.start()

class FloatingCardsGLWidget(QOpenGLWidget):
    """3D Floating CV Cards animation using PyOpenGL."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16) # ~60fps
        self.start_time = time.time()

    def initializeGL(self):
        if not HAS_OPENGL:
            return
        glClearColor(15/255, 15/255, 19/255, 1.0) # bg_primary match roughly
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, w, h):
        if not HAS_OPENGL:
            return
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if h > 0:
            gluPerspective(45.0, w / h, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        if not HAS_OPENGL:
            return
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -5.0)
        
        t = time.time() - self.start_time
        
        # We will draw 3 cards, each with slightly different transforms
        cards = [
            {"x": -1.2, "z": -1.0, "bob": math.sin(t * 1.5) * 0.2, "rot": t * 15, "color": (108/255, 99/255, 255/255, 0.8)},
            {"x": 0.0,  "z": 1.0,  "bob": math.sin(t * 1.2 + 1) * 0.25, "rot": t * -10, "color": (128/255, 121/255, 255/255, 0.9)},
            {"x": 1.2,  "z": -1.5, "bob": math.sin(t * 1.8 + 2) * 0.15, "rot": t * 20, "color": (90/255, 90/255, 114/255, 0.7)},
        ]
        
        for c in cards:
            glPushMatrix()
            glTranslatef(c["x"], c["bob"], c["z"])
            glRotatef(c["rot"], 0, 1, 0)
            
            # Draw card outline
            glColor4f(*c["color"])
            glLineWidth(2.0)
            
            half_w, half_h = 0.6, 0.8
            glBegin(GL_LINE_LOOP)
            glVertex3f(-half_w, -half_h, 0)
            glVertex3f(half_w, -half_h, 0)
            glVertex3f(half_w, half_h, 0)
            glVertex3f(-half_w, half_h, 0)
            glEnd()
            
            # Inner mockup lines
            glBegin(GL_LINES)
            glVertex3f(-0.4, 0.6, 0); glVertex3f(0.0, 0.6, 0)
            glVertex3f(-0.4, 0.4, 0); glVertex3f(0.4, 0.4, 0)
            glVertex3f(-0.4, 0.2, 0); glVertex3f(0.4, 0.2, 0)
            glVertex3f(-0.4, 0.0, 0); glVertex3f(0.1, 0.0, 0)
            glEnd()
            
            glPopMatrix()

class ValuePropCard(QWidget):
    def __init__(self, title, desc, icon_text, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_surface']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(self)
        
        icon_lbl = QLabel(icon_text)
        icon_lbl.setStyleSheet(f"font-size: 28px; color: {COLORS['accent']}; font-weight: bold; background: transparent;")
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text_primary']}; background: transparent;")
        
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent;")
        desc_lbl.setWordWrap(True)
        
        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch()

class FlowDiagramWidget(QWidget):
    """Horizontal 3-step diagram with animated dashed lines."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self._dash_offset = 0.0
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(2000)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(20.0)
        self.anim.setLoopCount(-1) # infinite
        self.anim.valueChanged.connect(self._update_offset)
        self.anim.start()

    def _update_offset(self, val):
        self._dash_offset = float(val)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        steps = ["1. Fill Profile", "2. Choose Template", "3. Download PDF"]
        w = self.width()
        centers = [w * 0.2, w * 0.5, w * 0.8]
        y = 50
        
        # Draw dotted lines
        pen = QPen(QColor(COLORS['accent']))
        pen.setWidth(2)
        pen.setDashPattern([4, 4])
        pen.setDashOffset(self._dash_offset)
        painter.setPen(pen)
        
        painter.drawLine(int(centers[0] + 30), int(y), int(centers[1] - 30), int(y))
        painter.drawLine(int(centers[1] + 30), int(y), int(centers[2] - 30), int(y))
        
        # Draw circles and text
        for i, cx in enumerate(centers):
            # Circle
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(COLORS['bg_elevated'])))
            painter.drawEllipse(QPoint(int(cx), int(y)), 30, 30)
            
            # Step Number
            painter.setPen(QPen(QColor(COLORS['accent'])))
            painter.setFont(QFont("Inter", 16, QFont.Weight.Bold))
            num_rect = QRectF(cx - 30, y - 30, 60, 60)
            painter.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, str(i + 1))
            
            # Step Text
            painter.setPen(QPen(QColor(COLORS['text_primary'])))
            painter.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
            text_rect = QRectF(cx - 80, y + 40, 160, 30)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, steps[i])

class TestimonialStrip(QScrollArea):
    """Auto-scrolling testimonial strip."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFixedHeight(180)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("border: none; background: transparent;")
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.layout = QHBoxLayout(self.content_widget)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.setWidget(self.content_widget)
        
        testimonials = [
            ("Got 3 interviews in a week after switching to CVify.", "— Alex, Software Engineer"),
            ("The templates are incredibly clean and professional.", "— Sarah, Product Manager"),
            ("ATS parsing actually works perfectly now.", "— Mark, Data Scientist"),
            ("Saves me hours of tweaking LaTeX formatting.", "— Emma, UX Designer"),
            ("The AI keyword optimization is magical.", "— James, Marketing Lead"),
            ("Landed my dream job at a FAANG company!", "— Chris, Full Stack Dev"),
            # Duplicates to allow seamless loop
            ("Got 3 interviews in a week after switching to CVify.", "— Alex, Software Engineer"),
            ("The templates are incredibly clean and professional.", "— Sarah, Product Manager"),
        ]
        
        for text, author in testimonials:
            card = QWidget()
            card.setFixedSize(280, 120)
            card.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS['bg_surface']};
                    border-radius: 12px;
                    border: 1px solid {COLORS['border']};
                }}
            """)
            card_layout = QVBoxLayout(card)
            t_lbl = QLabel(f"\"{text}\"")
            t_lbl.setWordWrap(True)
            t_lbl.setStyleSheet(f"font-size: 13px; font-style: italic; color: {COLORS['text_primary']}; background: transparent; border: none;")
            
            a_lbl = QLabel(author)
            a_lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLORS['text_secondary']}; background: transparent; border: none;")
            
            card_layout.addWidget(t_lbl)
            card_layout.addStretch()
            card_layout.addWidget(a_lbl)
            self.layout.addWidget(card)
            
        self.layout.addStretch()
        
        # Animation for scrolling
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self._do_scroll)
        self.scroll_timer.start(50) # 60fps scrolling
        
        self._current_scroll = 0.0

    def _do_scroll(self):
        self._current_scroll += 1.0
        max_scroll = self.content_widget.width() - self.width()
        
        if self._current_scroll > (1480): # Reset point hack based on total widths
            self._current_scroll = 0
            
        self.horizontalScrollBar().setValue(int(self._current_scroll))


class HomePage(QWidget):
    """The landing/marketing page for CVify."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Sticky Nav Bar
        self.nav_bar = QWidget()
        self.nav_bar.setFixedHeight(60)
        self.nav_bar.setStyleSheet(f"background-color: {COLORS['bg_surface']}; border-bottom: 1px solid {COLORS['border']};")
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(24, 0, 24, 0)
        
        logo = QLabel("CVify")
        logo.setStyleSheet(f"color: {COLORS['accent']}; font-size: 20px; font-weight: bold;")
        
        nav_layout.addWidget(logo)
        nav_layout.addStretch()
        
        btn_login = QPushButton("Login")
        btn_login.setProperty("class", "ghost")
        btn_login.clicked.connect(lambda: self.main_window.navigate('login'))
        
        btn_signup = QPushButton("Sign Up")
        btn_signup.clicked.connect(lambda: self.main_window.navigate('signup'))
        
        nav_layout.addWidget(btn_login)
        nav_layout.addWidget(btn_signup)
        
        self.main_layout.addWidget(self.nav_bar)
        
        # Scrollable content
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(64)
        self.content_layout.setContentsMargins(0, 64, 0, 64)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Hero Section
        self.hero_widget = QWidget()
        hero_layout = QHBoxLayout(self.hero_widget)
        hero_layout.setContentsMargins(64, 0, 64, 0)
        
        hero_text_col = QVBoxLayout()
        hero_title = AnimatedTitleLabel()
        
        hero_subtitle = QLabel("CVify uses AI to craft ATS-optimised CVs tailored\nexactly to your target job description.")
        hero_subtitle.setStyleSheet(f"font-size: 16px; color: {COLORS['text_secondary']};")
        
        hero_btns = QHBoxLayout()
        hero_btn_start = QPushButton("Get Started Free")
        hero_btn_start.clicked.connect(lambda: self.main_window.navigate('signup'))
        hero_btn_learn = QPushButton("Learn More")
        hero_btn_learn.setProperty("class", "ghost")
        hero_btns.addWidget(hero_btn_start)
        hero_btns.addWidget(hero_btn_learn)
        hero_btns.addStretch()
        
        hero_text_col.addWidget(hero_title)
        hero_text_col.addWidget(hero_subtitle)
        hero_text_col.addSpacing(24)
        hero_text_col.addLayout(hero_btns)
        
        hero_layout.addLayout(hero_text_col, stretch=1)
        
        self.gl_widget = FloatingCardsGLWidget()
        hero_layout.addWidget(self.gl_widget, stretch=1)
        
        self.content_layout.addWidget(self.hero_widget)
        
        # Value Props Section
        self.value_props_widget = QWidget()
        vp_layout = QGridLayout(self.value_props_widget)
        vp_layout.setContentsMargins(64, 0, 64, 0)
        vp_layout.setSpacing(24)
        
        props = [
            ("ATS Optimised", "LaTeX templates designed to parse perfectly on all Applicant Tracking Systems.", "📄"),
            ("AI-Powered", "Uses deep context matching to highlight the most relevant skills you possess.", "🤖"),
            ("5 Pro Templates", "From Executive to Creative, choose exactly the right vibe.", "🎨"),
            ("Instant PDF", "Blazing fast local TeX compilation to High-Definition PDF.", "⚡"),
            ("Your Data, Private", "Built on local SQLite. Your profile is safe and secure.", "🔒"),
            ("Section Picker", "Toggle sections on and off to fit a 1-page max constraint.", "✅")
        ]
        
        for i, (title, desc, icon) in enumerate(props):
            row = i // 3
            col = i % 3
            card = ValuePropCard(title, desc, icon)
            vp_layout.addWidget(card, row, col)
            
        self.content_layout.addWidget(self.value_props_widget)
        
        # How It Works
        self.how_it_works_label = QLabel("How It Works")
        self.how_it_works_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['text_primary']};")
        self.how_it_works_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.how_it_works_label)
        
        self.flow_diagram = FlowDiagramWidget()
        self.content_layout.addWidget(self.flow_diagram)
        
        # Testimonials
        self.test_label = QLabel("Loved By Professionals")
        self.test_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['text_primary']};")
        self.test_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.test_label)
        
        self.testimonial_strip = TestimonialStrip()
        self.content_layout.addWidget(self.testimonial_strip)
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
