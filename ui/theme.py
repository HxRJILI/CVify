COLORS = {
    "bg_primary":      "#0F0F13",   # App background
    "bg_surface":      "#1A1A24",   # Cards, panels
    "bg_elevated":     "#22222F",   # Inputs, hover states
    "bg_sidebar":      "#13131C",   # Sidebar background
    "accent":          "#6C63FF",   # Primary purple accent
    "accent_hover":    "#8079FF",
    "accent_glow":     "#6C63FF33", # Glow effect (25% opacity)
    "text_primary":    "#F0F0F8",
    "text_secondary":  "#9898B0",
    "text_muted":      "#5A5A72",
    "border":          "#2A2A3D",
    "border_focus":    "#6C63FF",
    "success":         "#3DD68C",
    "error":           "#FF5C5C",
    "warning":         "#FFB547",
    "info":            "#5CC8FF",
}

def get_stylesheet() -> str:
    """Returns the global QSS stylesheet for the application."""
    return f"""
        QWidget {{
            background-color: {COLORS["bg_primary"]};
            color: {COLORS["text_primary"]};
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            line-height: 1.6;
        }}
        
        /* Primary Button */
        QPushButton {{
            background-color: {COLORS["accent"]};
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {COLORS["accent_hover"]};
        }}
        QPushButton:pressed {{
            background-color: {COLORS["border_focus"]};
        }}
        
        /* Secondary / Ghost Button */
        QPushButton.ghost {{
            background-color: transparent;
            color: {COLORS["accent"]};
            border: 1px solid {COLORS["border"]};
        }}
        QPushButton.ghost:hover {{
            background-color: {COLORS["bg_elevated"]};
        }}
        
        /* Destructive Button */
        QPushButton.destructive {{
            background-color: transparent;
            color: {COLORS["error"]};
            border: 1px solid {COLORS["error"]};
        }}
        QPushButton.destructive:hover {{
            background-color: {COLORS["bg_elevated"]};
        }}
        
        /* Inputs */
        QLineEdit, QTextEdit {{
            background-color: {COLORS["bg_elevated"]};
            color: {COLORS["text_primary"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 12px;
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 1px solid {COLORS["border_focus"]};
        }}
        
        /* Scrollbars */
        QScrollBar:vertical {{
            border: none;
            background: {COLORS["bg_surface"]};
            width: 6px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLORS["accent"]};
            min-height: 20px;
            border-radius: 3px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            border: none;
            background: {COLORS["bg_surface"]};
            height: 6px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {COLORS["accent"]};
            min-width: 20px;
            border-radius: 3px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        /* Labels styles */
        QLabel.heading {{
            font-size: 22px;
            font-weight: 600; /* SemiBold */
            color: {COLORS["text_primary"]};
            background: transparent;
        }}
        
        QLabel.subheading {{
            font-size: 16px;
            font-weight: 400; /* Regular */
            color: {COLORS["text_secondary"]};
            background: transparent;
        }}
        
        QLabel.error_text {{
            color: {COLORS["error"]};
            background: transparent;
            font-size: 12px;
        }}
        
        /* Standard card surface */
        QWidget.card {{
            background-color: {COLORS["bg_surface"]};
            border-radius: 12px;
        }}
    """
