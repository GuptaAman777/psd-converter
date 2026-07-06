
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

class SettingsPanelMixin:
    def create_settings_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 10px;")
        layout = QHBoxLayout(panel)  # Changed to horizontal layout
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(0)
        
        # Create vertical tab bar on the left
        tab_bar_frame = QFrame()
        tab_bar_frame.setMinimumWidth(170)
        tab_bar_frame.setStyleSheet(f"""
            background-color: {COLORS['background']};
            border-radius: 0px;
            border-bottom-left-radius: 10px;
            border-top-left-radius: 10px;
        """)
        tab_bar_layout = QVBoxLayout(tab_bar_frame)
        tab_bar_layout.setContentsMargins(0, 20, 20, 20)  # Added proper margins
        tab_bar_layout.setSpacing(10)  # Increased spacing between elements
        tab_bar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        tab_bar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title at the top of the tab bar
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #ffffff; padding: 5px 20px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tab_bar_layout.addWidget(title)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px")
        tab_bar_layout.addWidget(separator)
        
        # Create stacked widget for content
        self.settings_stack = QStackedWidget()
        self.settings_stack.setStyleSheet(f"""
            background-color: {COLORS['panel']};
            border-radius: 0px;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
        """)
        
        # Create settings content
        settings_content = QWidget()
        settings_layout = QVBoxLayout(settings_content)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)
        
        # Image Formats Group
        image_group = QGroupBox("Image Settings (Converter Only)")
        image_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 12pt;
                font-weight: bold;
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 1ex;
                padding: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        image_layout = QVBoxLayout(image_group)
        
        # JPEG/WEBP Quality
        jpeg_layout, self.jpeg_quality_combo = self._create_combo_setting("JPEG Quality:", ["Maximum", "High", "Medium", "Low"])
        webp_layout, self.webp_quality_combo = self._create_combo_setting("WEBP Quality:", ["Maximum", "High", "Medium", "Low"])
        png_layout, self.png_compression_combo = self._create_combo_setting("PNG Compression:", ["Maximum", "Normal", "Fast", "None"])
        
        # Connect signals to update settings immediately
        self.jpeg_quality_combo.currentTextChanged.connect(self.update_quality_settings)
        self.webp_quality_combo.currentTextChanged.connect(self.update_quality_settings)
        self.png_compression_combo.currentTextChanged.connect(self.update_quality_settings)
        
        # Add settings to image group
        image_layout.addLayout(jpeg_layout)
        image_layout.addLayout(webp_layout)
        image_layout.addLayout(png_layout)
        settings_layout.addWidget(image_group)
        
        # Document Formats Group
        doc_group = QGroupBox("Document Settings (Converter Only)")
        doc_group.setStyleSheet(image_group.styleSheet())  # Reuse the style
        doc_layout = QVBoxLayout(doc_group)
        
        # PDF Settings
        pdf_dpi_layout, self.pdf_dpi_combo = self._create_combo_setting("PDF Resolution:", ["72 DPI", "150 DPI", "300 DPI", "600 DPI"])
        self.pdf_dpi_combo.setCurrentText("150 DPI")  # Set default to 150 DPI
        pdf_quality_layout, self.pdf_quality_combo = self._create_combo_setting("PDF Quality:", ["High", "Medium", "Low"])

        # Connect PDF settings signals
        self.pdf_dpi_combo.currentTextChanged.connect(self.update_quality_settings)
        self.pdf_quality_combo.currentTextChanged.connect(self.update_quality_settings)
        
        # Add settings to document group
        doc_layout.addLayout(pdf_dpi_layout)
        doc_layout.addLayout(pdf_quality_layout)
        settings_layout.addWidget(doc_group)
        
        # Create updates content
        updates_content = QWidget()
        updates_layout = QVBoxLayout(updates_content)
        updates_layout.setContentsMargins(20, 20, 20, 20)
        updates_layout.setSpacing(15)
        
        # Updates title
        updates_title = QLabel("Check for Updates")
        updates_title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        updates_layout.addWidget(updates_title)
        
        # Current version info
        self.current_version_label = QLabel("Current Version: 6.0")
        self.current_version_label.setStyleSheet("font-size: 12pt;")
        updates_layout.addWidget(self.current_version_label)
        
        # Latest version info
        self.latest_version_label = QLabel("Latest Version: Checking...")
        self.latest_version_label.setStyleSheet("font-size: 12pt;")
        updates_layout.addWidget(self.latest_version_label)
        
        # Status message
        self.update_status = QLabel("")
        self.update_status.setWordWrap(True)
        self.update_status.setStyleSheet("font-size: 11pt; margin-top: 10px;")
        updates_layout.addWidget(self.update_status)
        
        # Release notes
        self.release_notes = QTextEdit()
        self.release_notes.setReadOnly(True)
        self.release_notes.setMinimumHeight(200)
        self.release_notes.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10pt;
            }}
            
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{ background-color: {COLORS['background']}; width: 10px; border-radius: 5px; }}
            QScrollBar::handle:vertical {{ background-color: #4d4d5f; border-radius: 5px; min-height: 20px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)

        self.release_notes.setPlaceholderText("Release notes will appear here...")
        updates_layout.addWidget(self.release_notes)
        
        # Create a horizontal layout for update buttons
        update_buttons_layout = QHBoxLayout()
        
        # Check for updates button
        check_updates_btn = QPushButton("🔄 Check for Updates")
        check_updates_btn.setFixedHeight(45)
        check_updates_btn.setFont(QFont("Segoe UI", 10))
        check_updates_btn.clicked.connect(self.check_for_updates)
        check_updates_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['primary']}; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 10px; 
                font-weight: 600; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['hover']}; 
            }}
        """)
        update_buttons_layout.addWidget(check_updates_btn)
        
        # Download latest release button
        download_btn = QPushButton("⬇️ Download Latest Release")
        download_btn.setFixedHeight(45)
        download_btn.setFont(QFont("Segoe UI", 10))
        download_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/GuptaAman777/psd-converter/releases/latest")))
        download_btn.setStyleSheet(check_updates_btn.styleSheet())
        update_buttons_layout.addWidget(download_btn)
        
        # Add the buttons layout to the main layout
        updates_layout.addLayout(update_buttons_layout)
        
        # Create another horizontal layout for GitHub button
        github_layout = QHBoxLayout()
        
        # Visit GitHub button
        github_btn = QPushButton("🌐 Visit GitHub Repository")
        github_btn.setFixedHeight(45)
        github_btn.setFont(QFont("Segoe UI", 10))
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/GuptaAman777/psd-converter")))
        github_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['secondary']}; 
                color: {COLORS['text']}; 
                border: none; 
                border-radius: 8px; 
                padding: 10px; 
                font-weight: 600; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['hover']}; 
            }}
        """)
        github_layout.addWidget(github_btn)
        
        # Add the GitHub button layout to the main layout
        updates_layout.addLayout(github_layout)        

        # Create logger content
        logger_content = QWidget()
        logger_layout = QVBoxLayout(logger_content)
        logger_layout.setContentsMargins(20, 20, 20, 20)
        logger_layout.setSpacing(15)
        
        # Add filter controls
        filter_layout = QHBoxLayout()
        
        # Auto-refresh toggle
        self.auto_refresh = QCheckBox("Auto Refresh")
        self.auto_refresh.setChecked(True)
        self.auto_refresh.stateChanged.connect(self.toggle_auto_refresh)
        filter_layout.addWidget(self.auto_refresh)        

        # Log level filter
        level_label = QLabel("Filter Level:")
        level_label.setFixedWidth(80)
        self.log_level_combo = AnimatedComboBox()
        self.log_level_combo.addItems(["All", "ERROR", "WARNING", "INFO", "SUCCESS", "TERMINAL"])
        self.log_level_combo.currentTextChanged.connect(self.filter_logs)
        filter_layout.addWidget(level_label)
        filter_layout.addWidget(self.log_level_combo)
        
        # Add refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.clicked.connect(self.update_logger_display)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['secondary']};
                border-radius: 15px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        filter_layout.addWidget(refresh_btn)
        
        # Add word wrap toggle
        self.word_wrap = QCheckBox("Word Wrap")
        self.word_wrap.setChecked(False)
        filter_layout.addWidget(self.word_wrap)
        
        # Search box
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText("Search logs...")
        self.log_search.textChanged.connect(self.filter_logs)
        self.log_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
        """)
        filter_layout.addWidget(self.log_search)
        
        logger_layout.addLayout(filter_layout)
        
        # Create logger text edit
        self.logger_text = QTextEdit()
        self.logger_text.setReadOnly(True)
        self.logger_text.setMinimumHeight(300)  # Increased height since it has its own tab now
        self.logger_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                min-width: 400px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 16px;
                margin: 3px;
                border-radius: 8px;
            }}
            QScrollBar:vertical:hover {{
                width: 20px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #4d4d5f;
                min-height: 30px;
                border-radius: 6px;
                margin: 3px 3px 3px 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #5d5d6f;
            }}
            QScrollBar::add-line:vertical, 
            QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, 
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            
            /* Horizontal scrollbar styling to match vertical */
            QScrollBar:horizontal {{
                background: transparent;
                height: 16px;
                margin: 3px;
                border-radius: 8px;
            }}
            QScrollBar:horizontal:hover {{
                height: 20px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: #4d4d5f;
                min-width: 30px;
                border-radius: 6px;
                margin: 3px 3px 3px 3px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: #5d5d6f;
            }}
            QScrollBar::add-line:horizontal, 
            QScrollBar::sub-line:horizontal {{
                width: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:horizontal, 
            QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """)
        
        # Connect signals AFTER creating the widget
        self.logger_text.textChanged.connect(self.on_log_changed)
        self.word_wrap.stateChanged.connect(lambda state: 
            self.logger_text.setLineWrapMode(
                QTextEdit.LineWrapMode.WidgetWidth if state else QTextEdit.LineWrapMode.NoWrap
            )
        )
        
        # Add statistics label
        self.log_stats = QLabel()
        self.log_stats.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9pt;")
        logger_layout.addWidget(self.logger_text)
        logger_layout.addWidget(self.log_stats)

        # Add logger controls
        logger_controls = QHBoxLayout()
        
        clear_log_btn = QPushButton("🧹 Clear Log")
        clear_log_btn.setFixedHeight(35)
        clear_log_btn.setFont(QFont("Segoe UI", 10))
        clear_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_log_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['error']}; 
                color: {COLORS['text']}; 
                border: none; 
                border-radius: 8px; 
                padding: 8px; 
                font-weight: 600; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['error_hover']}; 
            }}
        """)
        clear_log_btn.clicked.connect(self.clear_log)
        
        save_log_btn = QPushButton("📥 Save Log")
        save_log_btn.setFixedHeight(35)
        save_log_btn.setFont(QFont("Segoe UI", 10))
        save_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_log_btn.setStyleSheet(f"""
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
        save_log_btn.clicked.connect(self.save_log)
        
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setFixedHeight(35)
        copy_btn.setFont(QFont("Segoe UI", 10))
        copy_btn.clicked.connect(self.copy_logs)
        copy_btn.setStyleSheet(save_log_btn.styleSheet())
        
        export_html_btn = QPushButton("📥 Export HTML")
        export_html_btn.setFixedHeight(35)
        export_html_btn.setFont(QFont("Segoe UI", 10))
        export_html_btn.clicked.connect(self.export_html_logs)
        export_html_btn.setStyleSheet(save_log_btn.styleSheet())
        
        logger_controls.addWidget(clear_log_btn)
        logger_controls.addWidget(copy_btn)
        logger_controls.addWidget(save_log_btn)
        logger_controls.addWidget(export_html_btn)
        
        logger_layout.addLayout(logger_controls)
        
        # Add content to stacked widget
        self.settings_stack.addWidget(settings_content)
        self.settings_stack.addWidget(updates_content)
        self.settings_stack.addWidget(logger_content)
        
        settings_btn = QPushButton("⚙️\nSettings")
        settings_btn.setFixedSize(80, 70)  # Increased width to accommodate text
        settings_btn.setCheckable(True)
        settings_btn.setChecked(True)  # Start with settings tab active
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: none;
                border-radius: 8px;
                padding: 5px;
                margin: 5px;
                text-align: center;
                min-width: 140px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['!tab']};
                font-size: 13px;
                min-width: 140px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: white;
                font-weight: bold;
                font-size: 14px;
            }}
            /* Adjust line spacing */
            QPushButton {{
                text-align: center;
                line-height: 1.0;
            }}
        """)
        
        # Create about content
        about_content = QWidget()
        about_layout = QVBoxLayout(about_content)
        about_layout.setContentsMargins(20, 20, 20, 20)
        about_layout.setSpacing(15)
        
        # About title
        about_title = QLabel("About PSD Converter")
        about_title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        about_layout.addWidget(about_title)
        
        # Create a scroll area for the about content
        about_scroll = QScrollArea()
        about_scroll.setWidgetResizable(True)
        about_scroll.setFrameShape(QFrame.Shape.NoFrame)
        about_scroll.setStyleSheet(f"""
            QScrollArea {{ 
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{ 
                background-color: {COLORS['background']}; 
                width: 10px; 
                border-radius: 5px; 
            }}
            QScrollBar::handle:vertical {{ 
                background-color: #4d4d5f; 
                border-radius: 5px; 
                min-height: 20px; 
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ 
                background-color: transparent; 
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ 
                height: 0px; 
            }}
        """)
        
        # Create a widget to hold all the about content
        about_content_widget = QWidget()
        about_content_layout = QVBoxLayout(about_content_widget)
        about_content_layout.setSpacing(20)
        
        # Logo section
        logo_frame = QFrame()
        logo_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.5 {COLORS['panel']}, stop:1 transparent);
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        logo_layout = QVBoxLayout(logo_frame)
        
        group_name = QLabel("Alvanheim Scanlation Group")
        group_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_name.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['primary']};")
        logo_layout.addWidget(group_name)
        
        about_content_layout.addWidget(logo_frame)
        
        # Function to create section frames
        def create_section(title, content_widgets):
            section_frame = QFrame()
            section_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['background']};
                    border-radius: 8px;
                    padding: 15px;
                }}
            """)
            
            # Add shadow effect
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0, 0, 0, 50))
            shadow.setOffset(0, 2)
            section_frame.setGraphicsEffect(shadow)
            
            section_layout = QVBoxLayout(section_frame)
            section_layout.setSpacing(10)
            
            # Section title with left border
            title_frame = QFrame()
            title_frame.setStyleSheet(f"""
                QFrame {{
                    border-left: 3px solid {COLORS['primary']};
                    padding-left: 7px;
                    margin-bottom: 5px;
                }}
            """)
            title_layout = QVBoxLayout(title_frame)
            title_layout.setContentsMargins(0, 0, 0, 0)
            
            title_label = QLabel(title)
            title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['secondary']};")
            title_layout.addWidget(title_label)
            
            section_layout.addWidget(title_frame)
            
            # Add content widgets
            for widget in content_widgets:
                section_layout.addWidget(widget)
                
            return section_frame
        
        # About This Tool section
        about_tool_text1 = QLabel("The <span style='color: " + COLORS['primary'] + "; font-weight: bold;'>PSD Converter</span> was developed to address the challenges faced by our scanlation group in handling image conversions, upscaling, denoising, and other image processing tasks essential for manga scanlation.")
        about_tool_text1.setWordWrap(True)
        about_tool_text1.setStyleSheet("line-height: 1.6; font-size: 11pt; margin: 5px 0;")
        about_tool_text1.setContentsMargins(5, 5, 5, 5)
        
        about_tool_text2 = QLabel("As a dedicated scanlation team, we were struggling with fragmented image conversion tools and complex workflows. This all-in-one solution streamlines our process and helps produce high-quality scanlations efficiently.")
        about_tool_text2.setWordWrap(True)
        about_tool_text2.setStyleSheet("line-height: 1.6; font-size: 11pt; margin: 5px 0;")
        about_tool_text2.setContentsMargins(5, 5, 5, 5)
        
        about_tool_section = create_section("About This Tool", [about_tool_text1, about_tool_text2])
        about_content_layout.addWidget(about_tool_section)
        
        # Features section
        features_list = QWidget()
        features_layout = QVBoxLayout(features_list)
        features_layout.setSpacing(10)
        features_layout.setContentsMargins(5, 5, 5, 5)
        
        feature_items = [
            "• Convert between multiple image formats (PNG, JPEG, WEBP, etc.)\n• Full support for PSD files with layer preservation\n• AI-powered upscaling for enhancing image quality\n• Advanced denoising algorithms for cleaner results\n• Efficient batch processing capabilities\n• PDF conversion and optimization\n• Customizable quality settings for perfect output"
        ]
        
        for feature in feature_items:
            feature_item = QHBoxLayout()
            feature_item.setContentsMargins(0, 2, 0, 2)
            
            feature_text = QLabel(feature)
            feature_text.setWordWrap(True)
            feature_text.setStyleSheet("font-size: 11pt; line-height: 1.4;")
            feature_item.addWidget(feature_text)
            
            features_layout.addLayout(feature_item)
        
        features_section = create_section("Key Features", [features_list])
        about_content_layout.addWidget(features_section)
        
        alvanheim_text1 = QLabel("We are a passionate team of manga enthusiasts dedicated to translating and sharing quality manga with the global community. Our mission is to provide high-quality scanlations while respecting the original work and creators.")
        alvanheim_text1.setWordWrap(True)
        alvanheim_text1.setStyleSheet("line-height: 1.6; font-size: 11pt; margin: 5px 0;")
        alvanheim_text1.setContentsMargins(5, 5, 5, 5)
        
        alvanheim_text2 = QLabel("Join our community to access exclusive releases and connect with fellow manga fans!")
        alvanheim_text2.setWordWrap(True)
        alvanheim_text2.setStyleSheet("line-height: 1.6; font-size: 11pt; margin: 5px 0;")
        alvanheim_text2.setContentsMargins(5, 5, 5, 5)
        
        alvanheim_section = create_section("Alvanheim Scanlation Group", [alvanheim_text1, alvanheim_text2])
        about_content_layout.addWidget(alvanheim_section)
        
        # Developer section
        developer_widget = QWidget()
        developer_layout = QVBoxLayout(developer_widget)
        developer_layout.setContentsMargins(5, 5, 5, 5)
        developer_layout.setSpacing(10)
        
        developer_text1 = QLabel("Created with ♥ by: <a href='https://github.com/GuptaAman777' style='color: " + COLORS['primary'] + "; text-decoration: none; font-weight: bold;'>GuptaAman777</a>")
        developer_text1.setOpenExternalLinks(True)
        developer_text1.setStyleSheet("font-size: 11pt; margin: 5px 0;")
        developer_layout.addWidget(developer_text1)
        
        developer_text2 = QLabel("For support, feature requests, or bug reports, please visit the GitHub repository.")
        developer_text2.setWordWrap(True)
        developer_text2.setStyleSheet("font-size: 11pt; margin: 5px 0;")
        developer_layout.addWidget(developer_text2)
        
        developer_section = create_section("Developer", [developer_widget])
        about_content_layout.addWidget(developer_section)
        
        acknowledgements_text1 = QLabel("Special thanks to all members of Alvanheim Scanlation Group for their valuable feedback and support during development.")
        acknowledgements_text1.setWordWrap(True)
        acknowledgements_text1.setStyleSheet("line-height: 1.6; font-size: 11pt; margin: 5px 0;")
        acknowledgements_text1.setContentsMargins(5, 5, 5, 5)
        
        acknowledgements_text2 = QLabel("This tool leverages several powerful open-source libraries including PyQt6, Pillow, psd-tools, and PyMuPDF.")
        acknowledgements_text2.setWordWrap(True)
        acknowledgements_text2.setStyleSheet("line-height: 1.6; font-size: 11pt; margin: 5px 0;")
        acknowledgements_text2.setContentsMargins(5, 5, 5, 5)
        
        acknowledgements_section = create_section("Acknowledgements", [acknowledgements_text1, acknowledgements_text2])
        about_content_layout.addWidget(acknowledgements_section)
        
        # Copyright footer
        copyright_label = QLabel("PSD Converter v6.0 © 2026 Alvanheim Scanlation Group")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet(f"font-style: italic; color: {COLORS['text_secondary']}; font-size: 10pt; margin-top: 10px;")
        about_content_layout.addWidget(copyright_label)
        
        # Add spacing at the bottom
        about_content_layout.addSpacing(20)
        
        # Set the content widget to the scroll area
        about_scroll.setWidget(about_content_widget)
        about_layout.addWidget(about_scroll)
        
        # Social buttons layout
        social_buttons_layout = QHBoxLayout()
        
        # Discord button
        discord_btn = QPushButton("🎮 Join Our Discord")
        discord_btn.setFixedHeight(45)
        discord_btn.setFont(QFont("Segoe UI", 10))
        discord_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/GCrthAhBmy")))
        discord_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: #5865F2; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 10px; 
                font-weight: 600; 
            }}
            QPushButton:hover {{ 
                background-color: #4752C4; 
            }}
        """)
        social_buttons_layout.addWidget(discord_btn)
        
        about_layout.addLayout(social_buttons_layout)
        
        # GitHub profile button
        github_profile_btn = QPushButton("🌐 Visit Developer's GitHub")
        github_profile_btn.setFixedHeight(45)
        github_profile_btn.setFont(QFont("Segoe UI", 10))
        github_profile_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/GuptaAman777")))
        github_profile_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['secondary']}; 
                color: {COLORS['text']}; 
                border: none; 
                border-radius: 8px; 
                padding: 10px; 
                font-weight: 600; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['hover']}; 
            }}
        """)
        about_layout.addWidget(github_profile_btn)
        
        # Add content to stacked widget
        self.settings_stack.addWidget(settings_content)
        self.settings_stack.addWidget(updates_content)
        self.settings_stack.addWidget(logger_content)
        self.settings_stack.addWidget(about_content)

        updates_btn = QPushButton("🔄\nUpdates")
        updates_btn.setFixedSize(80, 70)
        updates_btn.setCheckable(True)
        updates_btn.setStyleSheet(settings_btn.styleSheet())
        
        logger_btn = QPushButton("📋\nLogger")
        logger_btn.setFixedSize(80, 70)  # Increased width to accommodate text
        logger_btn.setCheckable(True)
        logger_btn.setStyleSheet(settings_btn.styleSheet())
        
        about_btn = QPushButton("ℹ️\nAbout")
        about_btn.setFixedSize(80, 70)
        about_btn.setCheckable(True)
        about_btn.setStyleSheet(settings_btn.styleSheet())
        
        # Add tooltips
        settings_btn.setToolTip("Settings")
        updates_btn.setToolTip("Check for Updates")
        logger_btn.setToolTip("Logger")
        about_btn.setToolTip("About")
        
        # Connect button signals
        settings_btn.clicked.connect(lambda: self.switch_settings_tab(0, settings_btn, [updates_btn, logger_btn, about_btn]))
        updates_btn.clicked.connect(lambda: self.switch_settings_tab(1, updates_btn, [settings_btn, logger_btn, about_btn]))
        logger_btn.clicked.connect(lambda: self.switch_settings_tab(2, logger_btn, [settings_btn, updates_btn, about_btn]))
        about_btn.clicked.connect(lambda: self.switch_settings_tab(3, about_btn, [settings_btn, updates_btn, logger_btn]))
        
        # Add buttons to tab bar with proper spacing
        tab_bar_layout.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        tab_bar_layout.addSpacing(10)  # Add explicit spacing between buttons
        tab_bar_layout.addWidget(updates_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        tab_bar_layout.addSpacing(10)  # Add explicit spacing between buttons
        tab_bar_layout.addWidget(logger_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        tab_bar_layout.addSpacing(10)  # Add explicit spacing between buttons
        tab_bar_layout.addWidget(about_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        tab_bar_layout.addStretch()
        
        # Add frames to main layout
        layout.addWidget(tab_bar_frame)
        layout.addWidget(self.settings_stack)
        
        # Initialize with any existing logs
        self.update_logger_display()
        
        # Check for updates when the panel is created
        QTimer.singleShot(1000, self.check_for_updates)
        
        return panel

    def check_for_updates(self):
        """Check for updates from GitHub repository"""
        self.update_status.setText("Checking for updates...")
        self.update_status.setStyleSheet(f"color: {COLORS['text']};")
        self.latest_version_label.setText("Latest Version: Checking...")
        
        # Get current version from a version file or hardcoded value
        current_version = "6.0"  # You can replace this with a dynamic version
        self.current_version_label.setText(f"Current Version: {current_version}")
        
        # Create a worker thread to check for updates
        class UpdateCheckerThread(QThread):
            update_found = pyqtSignal(str, str, str, bool)
            error_occurred = pyqtSignal(str)
            
            def run(self):
                try:
                    import requests
                    import json
                    
                    # GitHub API URL for the latest release
                    url = "https://api.github.com/repos/GuptaAman777/psd-converter/releases/latest"
                    
                    # Send request with a timeout
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        latest_version = data.get('tag_name', '').lstrip('v')
                        release_notes = data.get('body', 'No release notes available.')
                        release_url = data.get('html_url', '')
                        
                        # Compare versions (simple string comparison for now)
                        update_available = latest_version != current_version
                        
                        self.update_found.emit(latest_version, release_notes, release_url, update_available)
                    else:
                        self.error_occurred.emit(f"Error checking for updates: HTTP {response.status_code}")
                except Exception as e:
                    self.error_occurred.emit(f"Error checking for updates: {str(e)}")
        
        # Create and start the thread
        self.update_checker = UpdateCheckerThread()
        self.update_checker.update_found.connect(self.handle_update_result)
        self.update_checker.error_occurred.connect(self.handle_update_error)
        self.update_checker.start()

    def handle_update_result(self, latest_version, release_notes, release_url, update_available):
        """Handle the result of the update check"""
        self.latest_version_label.setText(f"Latest Version: {latest_version}")
        
        # Format release notes with Markdown
        formatted_notes = release_notes.replace('## ', '<h2>').replace('### ', '<h3>')
        formatted_notes = formatted_notes.replace('\n- ', '\n• ')
        
        # Enhance the release notes display with better scrolling
        self.release_notes.setHtml(f"""
            <html>
            <head>
                <style>
                    body {{ 
                        font-family: 'Segoe UI', sans-serif; 
                        color: {COLORS['text']}; 
                        margin: 0;
                        padding: 0;
                    }}
                    h2 {{ color: {COLORS['primary']}; margin-top: 10px; }}
                    h3 {{ color: {COLORS['secondary']}; margin-top: 8px; }}
                    a {{ color: {COLORS['primary']}; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    .notes-container {{ 
                        white-space: pre-wrap; 
                        overflow-y: auto;
                        padding: 5px;
                    }}
                    ul {{ padding-left: 20px; }}
                    li {{ margin-bottom: 5px; }}
                </style>
            </head>
            <body>
                <h2>Release Notes</h2>
                <div class="notes-container">{formatted_notes}</div>
                <p><a href="{release_url}">View on GitHub</a></p>
            </body>
            </html>
        """)
        
        # Ensure the QTextEdit is properly configured for scrolling
        self.release_notes.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.release_notes.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.release_notes.setReadOnly(True)
        
        # Get current version from the version label
        current_version = self.current_version_label.text().replace("Current Version: ", "")
        
        # Compare versions (simple string comparison)
        try:
            # Convert versions to tuples of integers for proper comparison
            current_parts = [int(x) for x in current_version.split('.')]
            latest_parts = [int(x) for x in latest_version.split('.')]
            
            # Pad shorter version with zeros
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            
            # Check if current version is higher than latest
            if current_parts > latest_parts:
                self.update_status.setText("You are using an Early Access version! Please report any bugs to the developer.")
                self.update_status.setStyleSheet(f"color: #FFD700;")  # Gold color for early access
                self.log("Early Access version detected", "WARNING")
            elif update_available:
                self.update_status.setText("A new version is available! You can download it from the GitHub repository.")
                self.update_status.setStyleSheet(f"color: {COLORS['success']};")
                
                # Show update notification
                self.update_notification = UpdateNotification(self, latest_version, release_url)
                self.update_notification.show()
                self.update_notification.start_show_animation()
                
            else:
                self.update_status.setText("You have the latest version.")
                self.update_status.setStyleSheet(f"color: {COLORS['text']};")
        except ValueError:
            # Fallback to simple string comparison if version parsing fails
            if update_available:
                self.update_status.setText("A new version is available! You can download it from the GitHub repository.")
                self.update_status.setStyleSheet(f"color: {COLORS['success']};")
                
                # Show update notification
                self.update_notification = UpdateNotification(self, latest_version, release_url)
                self.update_notification.show()
                self.update_notification.start_show_animation()
            else:
                self.update_status.setText("You have the latest version.")
                self.update_status.setStyleSheet(f"color: {COLORS['text']};")

    def update_logger_display(self):
        """Update the logger text edit with all log messages"""
        try:
            if hasattr(self, 'logger_text') and self.logger_text is not None:
                self.logger_text.clear()
                for log_entry in self.log_messages:
                    # Apply color based on log level
                    if "[ERROR]" in log_entry:
                        self.logger_text.append(f'<span style="color: {COLORS["error"]};">{log_entry}</span>')
                    elif "[WARNING]" in log_entry:
                        self.logger_text.append(f'<span style="color: #FFCC00;">{log_entry}</span>')
                    elif "[SUCCESS]" in log_entry:
                        self.logger_text.append(f'<span style="color: {COLORS["success"]};">{log_entry}</span>')
                    elif "[TERMINAL]" in log_entry:
                        self.logger_text.append(f'<span style="color: #00BFFF;">{log_entry}</span>')
                    else:
                        self.logger_text.append(log_entry)
                
                # Scroll to the bottom to show the latest log
                self.logger_text.verticalScrollBar().setValue(
                    self.logger_text.verticalScrollBar().maximum()
                )
        except Exception as e:
            print(f"Error updating logger display: {str(e)}")

