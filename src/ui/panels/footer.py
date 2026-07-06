
from src.ui.widgets.animated_combobox import AnimatedComboBox
from src.ui.widgets.progress_dialog import ProcessingProgressDialog
from src.ui.widgets.update_notification import UpdateNotification
from src.ui.widgets.upscale_settings import UpscaleSettingsDialog
from src.managers.file_list_manager import FileListManager

import os
import time
import psutil
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from src.constants import *
from src.ui.styles import *
from src.utils.helpers import *
from src.config import *

class FooterMixin:
    def add_footer(self, layout):
        """Add a footer with links and version info directly in the main layout"""
        # Create a footer section without a separate frame
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 15, 15, 0)
        
        # Version info
        version_label = QLabel("Version v6.0")
        version_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        footer_layout.addWidget(version_label)
        
        footer_layout.addStretch()
        
        # Contact button with dropdown menu
        contact_btn = QPushButton("Contact")
        contact_btn.setIcon(QIcon(get_icon_path("contact.png")))
        contact_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['secondary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
                min-width: 90px;
                min-height: 25px;
                text-align: center;
                icon-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
            QPushButton::menu-indicator {{
                width: 0px;
                image: none;
            }}
        """)
        contact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        contact_btn.clicked.connect(self.show_contact_popup)
        footer_layout.addWidget(contact_btn)
        
        # Add spacing between buttons
        spacer = QLabel()
        spacer.setFixedWidth(15)
        footer_layout.addWidget(spacer)
        
        # GitHub link with improved styling
        github_btn = QPushButton("GitHub")
        github_btn.setIcon(QIcon(get_icon_path("github.png")))
        github_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['secondary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
                min-width: 90px;
                min-height: 25px;
                text-align: center;
                icon-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        github_btn.clicked.connect(lambda: self.open_url("https://github.com/GuptaAman777/psd-converter"))
        footer_layout.addWidget(github_btn)
        
        # Add the footer layout directly to the main layout
        layout.addLayout(footer_layout)

    def show_contact_popup(self):
        """Show contact info dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Contact & Support")
        dialog.setMinimumSize(450, 450)
        dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Set window icon
        icon_path = get_icon_path("contact.png")
        if os.path.exists(icon_path):
            dialog.setWindowIcon(QIcon(icon_path))
            
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        title = QLabel("Contact & Support")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Get in touch or support the project")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']}; margin-bottom: 15px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        def add_contact_row(icon_name, text, btn_text, action):
            row = QFrame()
            row.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 8px;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(15, 12, 15, 12)
            
            icon_label = QLabel()
            icon_path_val = get_icon_path(icon_name)
            if os.path.exists(icon_path_val):
                icon_label.setPixmap(QPixmap(icon_path_val).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            row_layout.addWidget(icon_label)
            
            text_label = QLabel(text)
            text_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-left: 5px;")
            row_layout.addWidget(text_label)
            
            row_layout.addStretch()
            
            action_btn = QPushButton(btn_text)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']}; color: white;
                    border: none; border-radius: 6px; padding: 6px 15px; font-weight: bold; font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {COLORS['hover']}; }}
            """)
            action_btn.clicked.connect(action)
            row_layout.addWidget(action_btn)
            
            layout.addWidget(row)
            
        # Instagram
        add_contact_row("instagram.png", "Instagram", "Follow", lambda: self.open_url("https://www.instagram.com/gupta_aman_777/"))
        
        # Discord Server
        add_contact_row("discord.png", "Discord Server", "Join", lambda: self.open_url("https://discord.gg/GCrthAhBmy"))
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
        layout.addWidget(separator)
        
        # Email
        email_row = QFrame()
        email_row.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 8px;")
        email_layout = QHBoxLayout(email_row)
        email_layout.setContentsMargins(15, 12, 15, 12)
        
        email_icon = QLabel()
        email_path = get_icon_path("mail.png")
        if os.path.exists(email_path):
            email_icon.setPixmap(QPixmap(email_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        email_layout.addWidget(email_icon)
        
        email_label = QLabel("Email")
        email_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-left: 5px;")
        email_layout.addWidget(email_label)
        
        email_layout.addStretch()
        
        email_id = QLineEdit("gamangupta777@gmail.com")
        email_id.setReadOnly(True)
        email_id.setAlignment(Qt.AlignmentFlag.AlignCenter)
        email_id.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['background']}; 
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 6px 15px; 
                border-radius: 6px; 
                font-family: monospace; 
                font-size: 13px;
                font-weight: bold;
                max-width: 200px;
            }}
        """)
        email_layout.addWidget(email_id)
        
        layout.addWidget(email_row)
        
        # Binance ID
        binance_row = QFrame()
        binance_row.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 8px;")
        binance_layout = QHBoxLayout(binance_row)
        binance_layout.setContentsMargins(15, 12, 15, 12)
        
        binance_icon = QLabel()
        binance_path = get_icon_path("binance.png")
        if os.path.exists(binance_path):
            binance_icon.setPixmap(QPixmap(binance_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        binance_layout.addWidget(binance_icon)
        
        binance_label = QLabel("Binance ID")
        binance_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-left: 5px;")
        binance_layout.addWidget(binance_label)
        
        binance_layout.addStretch()
        
        binance_id = QLineEdit("743667454")
        binance_id.setReadOnly(True)
        binance_id.setAlignment(Qt.AlignmentFlag.AlignCenter)
        binance_id.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['background']}; 
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 6px 15px; 
                border-radius: 6px; 
                font-family: monospace; 
                font-size: 13px;
                font-weight: bold;
                max-width: 100px;
            }}
        """)
        binance_layout.addWidget(binance_id)
        
        layout.addWidget(binance_row)
        
        layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['secondary']}; color: white; 
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold; 
            }} 
            QPushButton:hover {{ background-color: {COLORS['hover']}; }}
        """)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()

