import os
import time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from src.constants import COLORS, APP_VERSION, GITHUB_RELEASES_URL
from src.ui.styles import STYLES
from src.utils.helpers import natural_sort_key, get_file_icon, format_size, get_icon_path

class UpdateNotification(QWidget):
    def __init__(self, parent=None, version="", release_url=""):
        super().__init__(parent)
        self.parent = parent
        self.version = version
        self.release_url = release_url
        self.setup_ui()
        
        # Set up animation
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setDuration(500)
        
        # Auto-close timer
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.start_hide_animation)
        self.close_timer.setSingleShot(True)
        self.close_timer.start(8000)  # Auto-close after 8 seconds
        
        # Track mouse for hover detection
        self.setMouseTracking(True)
        self.mouse_over = False
        
    def setup_ui(self):
        # Set up the widget appearance
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 100)
        
        # Position at top right of the screen
        desktop = QApplication.primaryScreen().geometry()
        self.move(desktop.width() - self.width() - 40, 40)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the notification frame
        self.frame = QFrame(self)
        self.frame.setObjectName("notificationFrame")
        self.frame.setStyleSheet(f"""
            #notificationFrame {{
                background-color: {COLORS['background']};
                border-radius: 10px;
                border: 2px solid {COLORS['primary']};
            }}
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.frame.setGraphicsEffect(shadow)
        
        # Frame layout
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(15, 12, 15, 12)
        frame_layout.setSpacing(8)
        
        # Header layout with icon and close button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Update icon
        update_icon = QLabel("🔄")
        update_icon.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(update_icon)
        
        # Title
        title = QLabel("Update Available")
        title.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                font-size: 16px;
                border: none;
            }}
            QPushButton:hover {{
                color: {COLORS['!tab']};
            }}
        """)
        close_btn.clicked.connect(self.start_hide_animation)
        header_layout.addWidget(close_btn)
        
        frame_layout.addLayout(header_layout)
        
        # Message
        message = QLabel(f"Version {self.version} is now available.")
        message.setWordWrap(True)
        message.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px;")
        frame_layout.addWidget(message)
        
        # Action button
        download_btn = QPushButton("Download Update")
        download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        download_btn.clicked.connect(self.open_download_page)
        frame_layout.addWidget(download_btn)
        
        layout.addWidget(self.frame)
        
    def open_download_page(self):
        """Open the release URL in the default browser"""
        if self.release_url:
            QDesktopServices.openUrl(QUrl(self.release_url))
        self.start_hide_animation()
        
    def start_show_animation(self):
        """Animate the notification sliding in"""
        start_pos = QPoint(self.x() + self.width(), self.y())
        end_pos = QPoint(self.x(), self.y())
        
        self.move(start_pos)
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()
        
    def start_hide_animation(self):
        """Animate the notification sliding out"""
        start_pos = self.pos()
        end_pos = QPoint(self.x() + self.width(), self.y())
        
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.finished.connect(self.close)
        self.animation.start()
        
    def enterEvent(self, event):
        """Handle mouse enter event to pause the auto-close timer"""
        self.mouse_over = True
        self.close_timer.stop()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave event to resume the auto-close timer"""
        self.mouse_over = False
        self.close_timer.start(5000)  # Resume with 5 seconds
        super().leaveEvent(event)

