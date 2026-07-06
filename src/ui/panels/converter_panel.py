
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

class ConverterPanelMixin:
    def create_converter_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-bottom-left-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)        
        
        # Title
        title = QLabel("Home")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Format selection with label
        format_layout = QHBoxLayout()
        format_label = QLabel("Output Format:")
        format_label.setFixedWidth(120)
        format_layout.addWidget(format_label)
        
        self.format_combo = AnimatedComboBox()
        self.format_combo.addItems(OUTPUT_FORMATS)
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)
        
        # AI Upscaling options with GPU Info button
        upscale_layout = QHBoxLayout()
        self.upscale_check = QCheckBox("Enable AI Upscaling")
        self.upscale_check.stateChanged.connect(self.toggle_upscale_options)
        upscale_layout.addWidget(self.upscale_check)
        
        self.force_upscale_check = QCheckBox("Force Enable")
        self.force_upscale_check.setStyleSheet("font-size: 10px; color: #FFCC00;")
        self.force_upscale_check.setToolTip("Force enable upscaling even if Vulkan check fails.\nUse this if the GPU check crashes your app.")
        self.force_upscale_check.stateChanged.connect(self.on_force_upscale_changed)
        upscale_layout.addWidget(self.force_upscale_check)
        
        self.upscale_settings_btn = QPushButton("⚙️")
        self.upscale_settings_btn.setFixedSize(32, 32)
        self.upscale_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upscale_settings_btn.setToolTip("Configure upscale model settings")
        self.upscale_settings_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['secondary']}; color: {COLORS['text']}; border: none; border-radius: 6px; font-size: 14px; }}
            QPushButton:hover {{ background-color: {COLORS['hover']}; }}
        """)
        self.upscale_settings_btn.clicked.connect(self.open_upscale_settings)
        upscale_layout.addWidget(self.upscale_settings_btn)
        
        # Default upscale model settings for converter
        self.converter_upscale_settings = {
            'model': 'realesr',
            'style_display': 'AnimeVideo V3 (2x/3x/4x)',
            'style_model': 'realesr-animevideov3',
            'noise_level': -1,
            'noise_display': '-1 (None)',
            'scale': '2x',
        }
        
        upscale_layout.addStretch()
        layout.addLayout(upscale_layout)
        

        
        # Instructions button
        instructions_btn = QPushButton("📖 Instructions")
        instructions_btn.setFont(QFont("Segoe UI", 10))
        instructions_btn.setFixedHeight(35)
        instructions_btn.clicked.connect(self.show_instructions)
        instructions_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        instructions_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['secondary']}; 
                color: {COLORS['text']}; 
                border: none; 
                border-radius: 8px; 
                padding: 8px; 
                font-weight: 600; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['hover']}; 
            }}
        """)
        
        # Create a horizontal layout for the buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(instructions_btn)
        
        # System Info button
        system_info_btn = QPushButton("🖥️ Check Upscale")
        system_info_btn.setFont(QFont("Segoe UI", 10))
        system_info_btn.setFixedHeight(35)
        system_info_btn.clicked.connect(self.show_system_info)
        system_info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        system_info_btn.setStyleSheet(instructions_btn.styleSheet())  # Use same style as instructions button
        buttons_layout.addWidget(system_info_btn)
        
        # Add the buttons layout to the main layout
        layout.addLayout(buttons_layout)
        
        # Help text
        help_text = QLabel("📝 Read the instructions for optimal usage.\n⚙️ Adjust settings to control output quality and file size.\n🖥️ Check Upscale Info to verify AI upscaling availability.")
        help_text.setStyleSheet(f"""
            color: {COLORS['text_secondary']}; 
            font-size: 9pt; 
            margin-top: 10px;
            padding: 8px;
            background-color: rgba(61, 61, 79, 0.3);
            border-radius: 6px;
        """)
        layout.addWidget(help_text)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 15px 0px;")
        layout.addWidget(separator)
        
        # File Selection section
        file_title = QLabel("File Selection & Output")
        file_title.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(file_title)
        
        # Add file selection buttons using the new method
        self.converter_fm.create_action_buttons(layout)
        
        layout.addStretch()
        
        # Convert button at the bottom
        self.convert_btn = QPushButton("✨ Convert")
        self.convert_btn.setFont(QFont("Segoe UI", 12))
        self.convert_btn.setFixedHeight(65)
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['primary']}; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 10px; 
                font-weight: 600; 
                margin-top: 10px;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['hover']}; 
            }}
            QPushButton:disabled {{ 
                background-color: {COLORS['disabled']}; 
                color: {COLORS['text_secondary']}; 
            }}
        """)
        layout.addWidget(self.convert_btn)
        
        return panel

    def update_quality_settings(self):
        """Update quality settings when combo box values change"""
        # Get current settings
        current_settings = self.get_current_settings()
        
        # If we have an active conversion thread, update its settings
        if hasattr(self, 'thread') and self.thread and self.thread.isRunning():
            self.thread.settings = current_settings
            
        # Debug print to verify settings are updated
        print(f"Quality settings updated: {current_settings}")

    def update_convert_button_state(self):
        """Update the state of the convert button based on file selection and output directory"""
        files_selected = len(self.converter_fm.get_selected_files()) > 0
        has_output_dir = bool(self.converter_fm.output_dir)
        self.convert_btn.setEnabled(files_selected and has_output_dir)

