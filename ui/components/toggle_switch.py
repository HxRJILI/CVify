from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from ui.theme import COLORS

class ToggleSwitch(QWidget):
    """
    An iOS-style animated toggle switch.
    """
    toggled = pyqtSignal(bool)
    
    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 28)
        
        self._checked = checked
        self._thumb_position = 28 - 24 if checked else 4
        
        # State colors
        self.bg_color_off = QColor(COLORS['bg_elevated'])
        self.bg_color_on = QColor(COLORS['accent'])
        self.thumb_color = QColor("#FFFFFF")
        
        self.anim = QPropertyAnimation(self, b"thumb_position", self)
        self.anim.setDuration(150)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    @pyqtProperty(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool):
        if self._checked == checked:
            return
        self._checked = checked
        
        target_pos = self.width() - self.height() + 4 if checked else 4
        self.anim.setStartValue(self._thumb_position)
        self.anim.setEndValue(target_pos)
        self.anim.start()
        
        self.toggled.emit(self._checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_checked(not self._checked)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background track
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)
        bg_color = self.bg_color_on if self._checked else self.bg_color_off
        painter.fillPath(path, bg_color)
        
        # Draw thumb
        thumb_size = self.height() - 8
        painter.setBrush(self.thumb_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(self._thumb_position), 4, thumb_size, thumb_size)
