import os
import time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from src.constants import COLORS, APP_VERSION, GITHUB_RELEASES_URL
from src.ui.styles import STYLES
from src.utils.helpers import natural_sort_key, get_file_icon, format_size, get_icon_path

class AnimatedComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Hover animation
        self._animation = QPropertyAnimation(self, b"size")
        self._animation.setDuration(100)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.update_style()
        
    def update_style(self):
        if self.isEnabled():
            self.setStyleSheet(f"""
                QComboBox {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {COLORS['background']};
                    border: 2px solid {COLORS['border']};
                    border-radius: 8px;
                    selection-background-color: {COLORS['primary']};
                    selection-color: white;
                    color: {COLORS['text']};
                    padding: 5px;
                    outline: none; 
                }}
                QComboBox QAbstractItemView::item {{
                    min-height: 20px;
                    padding: 5px;
                    border-radius: 8px;
                }}
                QComboBox QAbstractItemView::item:hover {{
                    background-color: {COLORS['hover']};
                }}
                QComboBox QAbstractItemView::item:focus {{
                    border: none;  
                    outline: none; 
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 30px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid {COLORS['text']};
                    margin-right: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QComboBox {{
                    background-color: {COLORS['panel']};
                    color: #777777;
                    border: 1px solid #444444;
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {COLORS['panel']};
                    border: 2px solid #444444;
                    border-radius: 8px;
                    color: #777777;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 30px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #777777;
                    margin-right: 10px;
                }}
            """)
            
    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.update_style()
        
    def enterEvent(self, event):
        self._animation.setStartValue(self.size())
        self._animation.setEndValue(QSize(self.width(), self.height() + 2))
        self._animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._animation.setStartValue(self.size())
        self._animation.setEndValue(QSize(self.width(), self.height() - 2))
        self._animation.start()
        super().leaveEvent(event)


