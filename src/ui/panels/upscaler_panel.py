
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

class UpscalerPanelMixin:
    def _update_upscale_availability(self, format_text):
        """Helper method to update upscale availability"""
        
        # Check GPU compatibility for upscaling
        gpu_compatible = self.check_gpu_compatibility()
        print(f"GPU compatibility check result: {gpu_compatible}")  # Debug output
        
        # Force enable overrides Vulkan check
        force_enabled = hasattr(self, 'force_upscale_check') and self.force_upscale_check.isChecked()
        
        if self.vulkan_support or force_enabled:
            self.upscale_check.setEnabled(True)
            self.upscale_check.setStyleSheet(f"font-size: 13px; color: #ffffff;")
            self.upscale_check.setToolTip("Enable AI upscaling")
        else:
            self.upscale_check.setEnabled(False)
            self.upscale_check.setChecked(False)
            self.upscale_check.setStyleSheet(f"font-size: 13px; color: #888888;")
            self.upscale_check.setToolTip("AI Upscaling requires Vulkan support")

    def toggle_waifu2x_options(self, model_text, noise_label, noise_combo, style_label, style_combo):
        """Show or hide waifu2x-specific options based on the selected model"""
        is_waifu2x = model_text.lower() == "waifu2x"
        noise_label.setVisible(is_waifu2x)
        noise_combo.setVisible(is_waifu2x)
        style_label.setVisible(is_waifu2x)
        style_combo.setVisible(is_waifu2x)                

    def on_upscaler_model_changed(self, model_name):
        """Handle changes to the upscaler model selection"""
        model_lower = model_name.lower()
        is_waifu2x = model_lower == "waifu2x"
        is_cugan = model_lower == "realcugan"
        is_esrgan = model_lower == "realesr"
        
        if is_waifu2x:
            
            self.upscaler_factor_combo.clear()
            self.upscaler_factor_combo.addItems(["1x", "2x", "4x"])
            
            if hasattr(self, 'style_combo'):
                self.style_combo.clear()
                style_options = {
                    "CUnet (Best Quality)": "models-cunet",
                    "Upconv (Anime/Art)": "models-upconv_7_anime_style_art_rgb",
                    "Upconv (Photo)": "models-upconv_7_photo"
                }
                self.style_combo.addItems(list(style_options.keys()))
                self.style_combo.setProperty("modelMapping", style_options)
            
        elif is_cugan:
            
            self.upscaler_factor_combo.clear()
            self.upscaler_factor_combo.addItems(["2x", "3x", "4x"])
            
            if hasattr(self, 'style_combo'):
                self.style_combo.clear()
                style_options = {
                    "SE (Standard)": "models-se",
                    "Pro (Advanced)": "models-pro",
                    "Nose (Retain Details)": "models-nose"
                }
                self.style_combo.addItems(list(style_options.keys()))
                self.style_combo.setProperty("modelMapping", style_options)
            
        elif is_esrgan:
            
            self.upscaler_factor_combo.clear()
            self.upscaler_factor_combo.addItems(["2x", "3x", "4x"])
            
            if hasattr(self, 'style_combo'):
                self.style_combo.clear()
                style_options = {
                    "AnimeVideo V3 (2x/3x/4x)": "realesr-animevideov3",
                    "RealESRGAN+ (4x only)": "realesrgan-x4plus",
                    "RealESRGAN+ Anime (4x only)": "realesrgan-x4plus-anime"
                }
                self.style_combo.addItems(list(style_options.keys()))
                self.style_combo.setProperty("modelMapping", style_options)
        
        else:
            
            self.upscaler_factor_combo.clear()
            self.upscaler_factor_combo.addItems(["2x", "3x", "4x"])
        
        if hasattr(self, 'advanced_options_container'):
            self.advanced_options_container.setVisible(is_waifu2x or is_cugan or is_esrgan)
            if hasattr(self, 'style_combo') and self.style_combo.count() > 0:
                self.on_style_changed(self.style_combo.currentText())
        
        # Update the upscale button state
        self.update_upscale_button_state()

    def create_upscaler_panel(self):
        """Create the upscaler panel with controls for upscaling images"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-bottom-left-radius: 10px; border-top-left-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)        
        
        # Title
        title = QLabel("AI Image Upscaler")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("AI Model:")
        model_label.setFixedWidth(120)
        model_layout.addWidget(model_label)
        
        self.upscaler_model_combo = AnimatedComboBox()
        self.upscaler_model_combo.addItems(UPSCALE_MODELS)
        self.upscaler_model_combo.currentTextChanged.connect(self.on_upscaler_model_changed)
        model_layout.addWidget(self.upscaler_model_combo)
        

        layout.addLayout(model_layout)
        
        # Create advanced options container
        self.advanced_options_container = QWidget()
        
        advanced_options_layout = QHBoxLayout(self.advanced_options_container)
        advanced_options_layout.setSpacing(20)
        advanced_options_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add noise level selection
        self.upscaler_noise_level_label = QLabel("Noise Level:")
        self.upscaler_noise_level_combo = AnimatedComboBox()
        self.upscaler_noise_level_combo.addItems(["-1 (None)", "0 (Low)", "1 (Light)", "2 (Medium)", "3 (High)"])
        self.upscaler_noise_level_combo.setCurrentIndex(1)  # Default to low noise reduction
        advanced_options_layout.addWidget(self.upscaler_noise_level_label)
        advanced_options_layout.addWidget(self.upscaler_noise_level_combo)
        
        # Add style selection
        style_label = QLabel("Style:")
        self.style_combo = AnimatedComboBox()
        
        # Create a dictionary to map display names to actual model values
        style_options = {
            "CUnet (Best Quality)": "models-cunet",
            "Upconv (Anime/Art)": "models-upconv_7_anime_style_art_rgb",
            "Upconv (Photo)": "models-upconv_7_photo"
        }
        
        # Add the display names to the combo box
        self.style_combo.addItems(list(style_options.keys()))
        self.style_combo.setCurrentIndex(0)  # Default to cunet
        
        # Store the mapping for later use
        self.style_combo.setProperty("modelMapping", style_options)
        
        # Connect to style change event
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        
        advanced_options_layout.addWidget(style_label)
        advanced_options_layout.addWidget(self.style_combo)
        
        # Initially hide advanced options container (will be updated by on_upscaler_model_changed)
        self.advanced_options_container.setVisible(False)
        
        # Add the container to the main layout
        layout.addWidget(self.advanced_options_container)
                
        # Upscale factor selection
        upscale_factor_layout = QHBoxLayout()
        upscale_factor_label = QLabel("Upscale Factor:")
        upscale_factor_label.setFixedWidth(120)
        upscale_factor_layout.addWidget(upscale_factor_label)
        
        self.upscaler_factor_combo = AnimatedComboBox()
        self.upscaler_factor_combo.addItems(["2x", "3x", "4x"])
        self.upscaler_factor_combo.currentTextChanged.connect(self.on_scale_changed)
        upscale_factor_layout.addWidget(self.upscaler_factor_combo)
        layout.addLayout(upscale_factor_layout)
        
        # Instructions button
        instructions_btn = QPushButton("📖 Upscaler Info")
        instructions_btn.setFont(QFont("Segoe UI", 10))
        instructions_btn.setFixedHeight(35)
        instructions_btn.clicked.connect(self.show_upscaler_instructions)
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
        system_info_btn = QPushButton("🖥️ Check GPU")
        system_info_btn.setFont(QFont("Segoe UI", 10))
        system_info_btn.setFixedHeight(35)
        system_info_btn.clicked.connect(self.show_system_info)
        system_info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        system_info_btn.setStyleSheet(instructions_btn.styleSheet())  # Use same style as instructions button
        buttons_layout.addWidget(system_info_btn)
        
        # Add the buttons layout to the main layout
        layout.addLayout(buttons_layout)
        
        # Help text
        help_text = QLabel("📝 AI upscaling uses neural networks to enhance image quality and resolution.\n⚙️ Different models produce different results based on image content.\n🖥️ GPU acceleration is required for reasonable performance.")
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
        
        # Add file selection buttons
        self.upscaler_fm.create_action_buttons(layout)
        
        layout.addStretch()
        
        # Upscale button at the bottom
        self.upscale_btn = QPushButton("✨ Upscale")
        self.upscale_btn.setFont(QFont("Segoe UI", 12))
        self.upscale_btn.setFixedHeight(65)
        self.upscale_btn.setEnabled(False)
        self.upscale_btn.clicked.connect(self.start_upscaling)
        self.upscale_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upscale_btn.setStyleSheet(f"""
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
        layout.addWidget(self.upscale_btn)
        
        # Initialize advanced options for the default selected model
        self.on_upscaler_model_changed(self.upscaler_model_combo.currentText())
        
        return panel

    def create_upscaler_action_buttons(self, layout):
        """Create action buttons for the upscaler panel"""
        # Create a grid layout for the buttons
        button_layout = QGridLayout()
        button_layout.setSpacing(10)
        
        # Add Files button
        add_files_btn = QPushButton("📁 Add Files")
        add_files_btn.setFont(QFont("Segoe UI", 10))
        add_files_btn.setFixedHeight(40)
        add_files_btn.clicked.connect(self.add_upscaler_files)
        add_files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_files_btn.setStyleSheet(f"""
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
        button_layout.addWidget(add_files_btn, 0, 0)
        
        # Add Folder button
        add_folder_btn = QPushButton("📂 Add Folder")
        add_folder_btn.setFont(QFont("Segoe UI", 10))
        add_folder_btn.setFixedHeight(40)
        add_folder_btn.clicked.connect(self.add_upscaler_folder)
        add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder_btn.setStyleSheet(add_files_btn.styleSheet())
        button_layout.addWidget(add_folder_btn, 0, 1)
        
        # Clear Files button (red color)
        clear_files_btn = QPushButton("🚫 Clear Files")
        clear_files_btn.setFont(QFont("Segoe UI", 10))
        clear_files_btn.setFixedHeight(40)
        clear_files_btn.clicked.connect(self.clear_upscaler_files)
        clear_files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_files_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['error']}; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 8px; 
                font-weight: 600; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['error_hover']}; 
            }}
        """)
        button_layout.addWidget(clear_files_btn, 1, 0)
        
        # Set Output button (exact match to Home panel)
        set_output_btn = QPushButton("📂 Set Output")
        set_output_btn.setFont(QFont("Segoe UI", 10))
        set_output_btn.setFixedHeight(40)
        set_output_btn.clicked.connect(self.set_upscaler_output_dir)
        set_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_output_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: #FFB940; 
                color: {COLORS['text']}; 
                border: none; 
                border-radius: 8px; 
                padding: 10px; 
                font-weight: 600; 
            }}
            QPushButton:hover {{ 
                background-color: #C4821A; 
            }}
        """)
        button_layout.addWidget(set_output_btn, 1, 1)
        
        layout.addLayout(button_layout)

    def create_upscaler_right_panel(self):
        """Create the right panel for the upscaler tab with file list and output directory"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-top-right-radius: 10px; border-bottom-right-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # File list header without select all checkbox
        file_header = QLabel("Selected Files:")
        file_header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 5px;")
        layout.addWidget(file_header)
        
        # Create a container for the scroll area with rounded corners
        scroll_container = QFrame()
        scroll_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 10px;")
        scroll_container_layout = QVBoxLayout(scroll_container)
        scroll_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # File list scroll area with improved styling
        self.upscaler_scroll_area = QScrollArea()
        self.upscaler_scroll_area.setWidgetResizable(True)
        self.upscaler_scroll_area.setMinimumHeight(200)  # Increased height
        self.upscaler_scroll_area.setFrameShape(QFrame.Shape.NoFrame)  # Remove frame
        self.upscaler_scroll_area.setStyleSheet(f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{ background-color: #252535; width: 10px; border-radius: 5px; }}
            QScrollBar::handle:vertical {{ background-color: #4d4d5f; border-radius: 5px; min-height: 20px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar:horizontal {{ background-color: #252535; height: 10px; border-radius: 5px; }}
            QScrollBar::handle:horizontal {{ background-color: #4d4d5f; border-radius: 5px; min-width: 20px; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background-color: transparent; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        """)
        
        # Initial file container
        self.upscaler_file_container = QWidget()
        self.upscaler_file_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 8px;") 
        file_layout = QVBoxLayout(self.upscaler_file_container)
        file_layout.setContentsMargins(10, 10, 10, 10)
        file_layout.setSpacing(8)  # Increased spacing between items
        
        # Enable drag and drop for file container
        self.upscaler_file_container.setAcceptDrops(True)
        
        # Override drag and drop events for file container
        self.upscaler_file_container.dragEnterEvent = self.upscaler_dragEnterEvent
        self.upscaler_file_container.dragLeaveEvent = self.upscaler_dragLeaveEvent
        self.upscaler_file_container.dropEvent = self.upscaler_dropEvent
        self.upscaler_file_container.dragMoveEvent = self.upscaler_dragMoveEvent
        
        # Store original style to restore after drag leave
        self.upscaler_original_file_container_style = self.upscaler_file_container.styleSheet()
        
        # Initial placeholder
        self.upscaler_file_label = QLabel("No files selected")
        self.upscaler_file_label.setWordWrap(True)
        self.upscaler_file_label.setStyleSheet("color: #888888; padding: 10px;")
        file_layout.addWidget(self.upscaler_file_label)
        
        self.upscaler_scroll_area.setWidget(self.upscaler_file_container)
        scroll_container_layout.addWidget(self.upscaler_scroll_area)
        layout.addWidget(scroll_container)
        
        # Output directory header
        output_header = QLabel("Output Directory:")
        output_header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 5px;")
        layout.addWidget(output_header)
        
        # Output directory display
        output_container = QWidget()
        output_container.setMinimumHeight(40)  # Increased height
        output_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 8px;")
        output_layout = QVBoxLayout(output_container)
        
        self.upscaler_output_dir_label = QLabel("No output directory selected")
        self.upscaler_output_dir_label.setWordWrap(True)
        self.upscaler_output_dir_label.setStyleSheet("color: #888888; padding: 10px;")
        output_layout.addWidget(self.upscaler_output_dir_label)
        
        output_container.setLayout(output_layout)
        layout.addWidget(output_container)

        return panel

    def add_upscaler_files(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(f"Supported Files (*.{' *.'.join(map(str.lower, UPSCALE_FORMATS))})")
        
        if file_dialog.exec():
            # Get the new files
            new_files = file_dialog.selectedFiles()
            
            # Keep existing files and add new ones, avoiding duplicates
            existing_files = set(self.upscaler_files)
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.upscaler_files:
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Add new files, checking for duplicates
            for file_path in new_files:
                if file_path not in existing_files:
                    filename = os.path.basename(file_path)
                    name, ext = os.path.splitext(filename)
                    
                    # Check if this filename+extension combination already exists
                    if (name.lower(), ext.lower()) in existing_name_ext_pairs:
                        skipped_files.append(file_path)
                    else:
                        self.upscaler_files.append(file_path)
                        existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Sort files using natural sort
            self.upscaler_files.sort(key=self.natural_sort_key)
            
            # Get the parent directory of the first selected file if not already set
            if not hasattr(self, 'upscaler_selected_folder') or not self.upscaler_selected_folder:
                if self.upscaler_files:
                    self.upscaler_selected_folder = os.path.dirname(self.upscaler_files[0])
            
            # Show warning if files were skipped
            if skipped_files:
                self.show_duplicate_warning(skipped_files)
                    
            self.add_upscaler_files_to_list(self.upscaler_files)

    def add_upscaler_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
        if folder:
            # Store existing files to avoid duplicates
            existing_files = set(self.upscaler_files)
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.upscaler_files:
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Find all supported files in the folder
            supported_extensions = tuple(f'.{ext.lower()}' for ext in UPSCALE_FORMATS)
            new_files = []
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(supported_extensions):
                        file_path = os.path.join(root, file)
                        if file_path not in existing_files:
                            name, ext = os.path.splitext(file)
                            name = os.path.basename(name)
                            
                            # Check if this filename+extension combination already exists
                            if (name.lower(), ext.lower()) in existing_name_ext_pairs:
                                skipped_files.append(file_path)
                            else:
                                new_files.append(file_path)
                                self.upscaler_files.append(file_path)
                                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Sort files using natural sort
            self.upscaler_files.sort(key=self.natural_sort_key)
            
            # Set the selected folder if not already set or if new files were added
            if (not hasattr(self, 'upscaler_selected_folder') or not self.upscaler_selected_folder) and new_files:
                self.upscaler_selected_folder = folder
            
            # Show warning if files were skipped
            if skipped_files:
                self.show_duplicate_warning(skipped_files)
                
            self.add_upscaler_files_to_list(self.upscaler_files)

    def toggle_upscaler_select_all(self, state):
        """Toggle all file checkboxes based on the select all checkbox"""
        if not hasattr(self, 'upscaler_file_checkboxes'):
            return
            
        # Create a copy of the list to avoid issues with deleted objects
        for checkbox in list(self.upscaler_file_checkboxes):
            # Check if the checkbox is still valid
            try:
                checkbox.setChecked(state == Qt.CheckState.Checked.value)
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.upscaler_file_checkboxes:
                    self.upscaler_file_checkboxes.remove(checkbox)
        
        # Also update all file type checkboxes
        self.update_upscaler_file_type_checkbox_state()
        self.update_upscale_button_state()

    def update_upscaler_select_all_checkbox_state(self):
        """Update the state of the upscaler 'Select All' checkbox based on all file checkboxes"""
        if hasattr(self, 'upscaler_select_all') and hasattr(self, 'upscaler_file_checkboxes'):
            # Count checked and enabled checkboxes
            checked_count = 0
            enabled_count = 0
            
            for checkbox in self.upscaler_file_checkboxes:
                try:
                    if checkbox.isEnabled():
                        enabled_count += 1
                        if checkbox.isChecked():
                            checked_count += 1
                except RuntimeError:
                    continue
            
            # Update the "Select All" checkbox without triggering its signal
            if enabled_count > 0:
                self.upscaler_select_all.blockSignals(True)
                self.upscaler_select_all.setChecked(checked_count == enabled_count)
                self.upscaler_select_all.setText(f"Select All ({checked_count}/{enabled_count} selected)")
                self.upscaler_select_all.blockSignals(False)
                
                # Also update the file count label if it exists
                if hasattr(self, 'upscaler_file_count_label'):
                    self.upscaler_file_count_label.setText(f"Total: {len(self.upscaler_files)} files, {checked_count} selected")

    def toggle_upscaler_file_type(self, state, file_ext):
        """Toggle all checkboxes for a specific file type in the upscaler panel"""
        if not hasattr(self, 'upscaler_file_checkboxes'):
            return
            
        # Count how many checkboxes we're changing
        changed_count = 0
        
        # Create a copy of the list to avoid issues with deleted objects
        for checkbox in list(self.upscaler_file_checkboxes):
            try:
                if hasattr(checkbox, 'file_ext') and checkbox.file_ext == file_ext:
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
                    changed_count += 1
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.upscaler_file_checkboxes:
                    self.upscaler_file_checkboxes.remove(checkbox)
        
        # Update the "Select All" checkbox state
        self.update_upscaler_select_all_checkbox_state()
        self.update_upscale_button_state()

    def update_upscaler_file_type_checkbox_state(self):
        """Update the state of file type checkboxes based on individual file checkboxes"""
        if not hasattr(self, 'upscaler_file_checkboxes'):
            return
            
        # Get all file type checkboxes from the UI
        file_type_checkboxes = []
        
        # Find the file list widget
        file_scroll = None
        for i in range(self.upscaler_file_container.layout().count()):
            widget = self.upscaler_file_container.layout().itemAt(i).widget()
            if isinstance(widget, QScrollArea):
                file_scroll = widget
                break
                
        if not file_scroll:
            return
            
        # Get the file list widget
        file_list_widget = file_scroll.widget()
        if not file_list_widget:
            return
            
        # Find all file type checkboxes
        for i in range(file_list_widget.layout().count()):
            item = file_list_widget.layout().itemAt(i)
            widget = item.widget() if item else None
            
            if isinstance(widget, QFrame):
                # This is likely a file type group
                # Check if the widget has a layout before accessing it
                if widget.layout() is not None:
                    for j in range(widget.layout().count()):
                        item2 = widget.layout().itemAt(j)
                        if item2 and item2.layout():
                            # This might be the header layout with the checkbox
                            for k in range(item2.layout().count()):
                                w = item2.layout().itemAt(k).widget()
                                if isinstance(w, QCheckBox) and hasattr(w, 'file_ext'):
                                    file_type_checkboxes.append(w)
        
        # Update each file type checkbox based on its files
        for file_type_checkbox in file_type_checkboxes:
            file_ext = file_type_checkbox.file_ext
            
            # Count checked files of this type
            total_count = 0
            checked_count = 0
            
            for checkbox in self.upscaler_file_checkboxes:
                try:
                    if hasattr(checkbox, 'file_ext') and checkbox.file_ext == file_ext:
                        total_count += 1
                        if checkbox.isChecked():
                            checked_count += 1
                except RuntimeError:
                    continue
            
            # Update the checkbox state without triggering signals
            if total_count > 0:
                file_type_checkbox.blockSignals(True)
                file_type_checkbox.setChecked(checked_count == total_count)
                file_type_checkbox.setText(f"{file_type_checkbox.original_text} ({checked_count}/{total_count} selected)")
                file_type_checkbox.blockSignals(False)

    def add_upscaler_files_to_list(self, file_paths):
        """Add files to the upscaler file list"""
        if not file_paths:
            return
        
        # Initialize file list if it doesn't exist
        if not hasattr(self, 'upscaler_files'):
            self.upscaler_files = []
        
        # Initialize file checkboxes list if it doesn't exist
        if not hasattr(self, 'upscaler_file_checkboxes'):
            self.upscaler_file_checkboxes = []
        
        # Store existing checkbox states before clearing the layout
        checkbox_states = {}
        for checkbox in list(self.upscaler_file_checkboxes):
            try:
                if hasattr(checkbox, 'file_path'):
                    checkbox_states[checkbox.file_path] = checkbox.isChecked()
            except RuntimeError:
                # Remove invalid checkboxes
                if checkbox in self.upscaler_file_checkboxes:
                    self.upscaler_file_checkboxes.remove(checkbox)
        
        # Clear the file container
        for i in reversed(range(self.upscaler_file_container.layout().count())):
            item = self.upscaler_file_container.layout().itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new files to the list, avoiding duplicates
        existing_files = set(self.upscaler_files)
        for file_path in file_paths:
            if file_path not in existing_files:
                self.upscaler_files.append(file_path)
                existing_files.add(file_path)
        
        # Sort all files using natural sort
        self.upscaler_files.sort(key=self.natural_sort_key)
        
        # Reset file_checkboxes list
        self.upscaler_file_checkboxes = []
        
        # If no files, show the placeholder
        if not self.upscaler_files:
            self.upscaler_file_label = QLabel("No files selected")
            self.upscaler_file_label.setWordWrap(True)
            self.upscaler_file_label.setStyleSheet("color: #888888; padding: 10px;")
            self.upscaler_file_container.layout().addWidget(self.upscaler_file_label)
        else:
            # Create a scroll area for the file list
            file_scroll = QScrollArea()
            file_scroll.setWidgetResizable(True)
            file_scroll.setFrameShape(QFrame.Shape.NoFrame)
            file_scroll.setStyleSheet(f"""
                QScrollArea {{ border: none; background-color: transparent; }}
                QScrollBar:vertical {{ background-color: #252535; width: 10px; border-radius: 5px; }}
                QScrollBar::handle:vertical {{ background-color: #4d4d5f; border-radius: 5px; min-height: 20px; }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            """)
            
            # Create a widget to hold the file list
            file_list_widget = QWidget()
            file_list_layout = QVBoxLayout(file_list_widget)
            file_list_layout.setContentsMargins(5, 5, 5, 5)
            file_list_layout.setSpacing(10)
            
            # If files were added through folder selection, show the folder path
            if hasattr(self, 'upscaler_selected_folder') and self.upscaler_selected_folder:
                folder_label = QLabel(f"📁 Selected Folder: {self.upscaler_selected_folder}")
                folder_label.setStyleSheet(f"color: {COLORS['text']}; padding: 5px; font-weight: bold;")
                file_list_layout.addWidget(folder_label)
                
                # Add a separator
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
                file_list_layout.addWidget(separator)
            
            # Add "Select All" checkbox inside the file list widget
            select_all_layout = QHBoxLayout()
            
            # Create a new select all checkbox
            self.upscaler_select_all = QCheckBox("Select All")
            self.upscaler_select_all.stateChanged.connect(self.toggle_upscaler_select_all)
            self.upscaler_select_all.setChecked(True)
            select_all_layout.addWidget(self.upscaler_select_all)
            
            # Add file count
            self.upscaler_file_count_label = QLabel(f"Total: {len(self.upscaler_files)} files")
            self.upscaler_file_count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9pt;")
            select_all_layout.addWidget(self.upscaler_file_count_label, alignment=Qt.AlignmentFlag.AlignRight)
            
            file_list_layout.addLayout(select_all_layout)
            
            # Add a separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
            file_list_layout.addWidget(separator)
            
            # Group files by extension
            file_groups = {}
            for file_path in self.upscaler_files:
                file_ext = os.path.splitext(file_path)[1].lower()[1:]  # Get extension without dot
                if file_ext not in file_groups:
                    file_groups[file_ext] = []
                file_groups[file_ext].append(file_path)
            
            # Create a section for each file type
            for file_ext, files in file_groups.items():
                # Create a group frame for each file type
                group_frame = QFrame()
                group_frame.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 8px;")
                group_layout = QVBoxLayout(group_frame)
                group_layout.setContentsMargins(10, 10, 10, 10)
                group_layout.setSpacing(5)
                
                # Add file type header with count
                header_layout = QHBoxLayout()
                
                # Add "Select All" checkbox for this file type
                original_text = f"{file_ext.upper()} Files ({len(files)})"
                file_type_checkbox = QCheckBox(original_text)
                file_type_checkbox.setStyleSheet("font-weight: bold; font-size: 11pt;")
                file_type_checkbox.file_ext = file_ext
                file_type_checkbox.original_text = original_text  # Store original text
                
                # Check if all files of this type were previously checked
                all_checked = True
                for file_path in files:
                    if file_path in checkbox_states and not checkbox_states[file_path]:
                        all_checked = False
                        break
                file_type_checkbox.setChecked(all_checked)
                
                # Connect to toggle all checkboxes of this file type
                file_type_checkbox.stateChanged.connect(
                    lambda state, ext=file_ext: self.toggle_upscaler_file_type(state, ext)
                )
                
                header_layout.addWidget(file_type_checkbox)
                header_layout.addStretch()
                
                group_layout.addLayout(header_layout)
                
                # Add a separator
                type_separator = QFrame()
                type_separator.setFrameShape(QFrame.Shape.HLine)
                type_separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
                group_layout.addWidget(type_separator)
                
                # Create a grid layout for files
                grid_layout = QGridLayout()
                grid_layout.setSpacing(5)
                
                # Calculate number of columns based on container width
                # We'll use 4 columns as a default, but this could be adjusted
                num_columns = 4
                
                # Add files to the grid
                for i, file_path in enumerate(files):
                    file_name = os.path.basename(file_path)
                    
                    # Create a horizontal layout for each file
                    file_item = QWidget()
                    file_layout = QHBoxLayout(file_item)
                    file_layout.setContentsMargins(2, 2, 2, 2)
                    file_layout.setSpacing(5)
                    
                    # Add checkbox
                    checkbox = QCheckBox()
                    # Set initial state based on saved state or default to checked
                    initial_state = True
                    # Check if we have a saved state for this file
                    if file_path in checkbox_states:
                        initial_state = checkbox_states[file_path]
                    
                    checkbox.file_path = file_path  # Store file path as attribute
                    checkbox.file_ext = file_ext    # Store file extension
                    checkbox.setChecked(initial_state)
                    
                    # Connect checkbox state change to update file type checkbox state
                    checkbox.stateChanged.connect(self.update_upscaler_file_type_checkbox_state)
                    # Also connect to update the upscale button state
                    checkbox.stateChanged.connect(self.update_upscale_button_state)
                    
                    self.upscaler_file_checkboxes.append(checkbox)
                    
                    file_layout.addWidget(checkbox)
                    
                    # Add file icon based on extension
                    icon_text = "📄"
                    if file_ext.lower() in ["jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff"]:
                        icon_text = "🖼️"
                    elif file_ext.lower() == "pdf":
                        icon_text = "📑"
                    
                    icon_label = QLabel(icon_text)
                    file_layout.addWidget(icon_label)
                    
                    # Add file name (truncated if too long)
                    max_length = 15  # Shorter length for 4-column layout
                    display_name = file_name if len(file_name) <= max_length else file_name[:max_length-3] + "..."
                    file_name_label = QLabel(display_name)
                    file_name_label.setToolTip(file_name)  # Show full name on hover
                    file_name_label.setStyleSheet(f"color: {COLORS['text']};")
                    
                    file_layout.addWidget(file_name_label, 1)  # Stretch factor 1
                    
                    # Add to grid layout
                    row = i // num_columns
                    col = i % num_columns
                    grid_layout.addWidget(file_item, row, col)
                
                group_layout.addLayout(grid_layout)
                file_list_layout.addWidget(group_frame)
            
            file_scroll.setWidget(file_list_widget)
            
            # Add the scroll area to the file container
            self.upscaler_file_container.layout().addWidget(file_scroll)
            
            # Update the "Select All" checkbox state
            self.update_upscaler_select_all_checkbox_state()
        
        # Update the upscale button state
        self.update_upscale_button_state()

    def clear_upscaler_files(self):
        """Clear all files from the upscaler file list"""
        self.upscaler_files = []
        self.upscaler_file_checkboxes = []

        # Clear the output directory
        self.upscaler_output_dir = ""
        self.upscaler_output_dir_label.setText("No output directory selected")
        self.upscaler_output_dir_label.setStyleSheet("color: #888888; padding: 10px;")
        
        # Clear the file container
        for i in reversed(range(self.upscaler_file_container.layout().count())):
            widget = self.upscaler_file_container.layout().itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        # Add the placeholder label
        self.upscaler_file_label = QLabel("No files selected")
        self.upscaler_file_label.setWordWrap(True)
        self.upscaler_file_label.setStyleSheet("color: #888888; padding: 10px;")
        self.upscaler_file_container.layout().addWidget(self.upscaler_file_label)
        
        # Update the upscale button state
        self.update_upscale_button_state()

    def set_upscaler_output_dir(self):
        """Open folder dialog to set the output directory for upscaled images"""
        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.FileMode.Directory)
        folder_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if folder_dialog.exec():
            self.upscaler_output_dir = folder_dialog.selectedFiles()[0]
            self.upscaler_output_dir_label.setText(f"📁 {self.upscaler_output_dir}")
            self.upscaler_output_dir_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
            
            # Update the upscale button state
            self.update_upscale_button_state()

    def update_upscale_button_state(self):
        """Update the state of the upscale button based on file selection and output directory"""
        files_selected = len(self.upscaler_fm.get_selected_files()) > 0
        has_output_dir = bool(self.upscaler_fm.output_dir)
        self.upscale_btn.setEnabled(files_selected and has_output_dir)

    def upscaler_dragEnterEvent(self, event):
        """Handle drag enter event for the upscaler file container"""
        if event.mimeData().hasUrls():
            # Store original style
            if not hasattr(self, 'upscaler_original_file_container_style'):
                self.upscaler_original_file_container_style = self.upscaler_file_container.styleSheet()
            
            # Change the style to indicate drop is possible
            self.upscaler_file_container.setStyleSheet(f"background-color: {COLORS['hover']}; border-radius: 8px; border: 2px dashed white;")
            
            # Store original widgets
            self.upscaler_original_widgets = []
            for i in range(self.upscaler_file_container.layout().count()):
                widget = self.upscaler_file_container.layout().itemAt(i).widget()
                if widget:
                    self.upscaler_original_widgets.append(widget)
                    widget.setParent(None)
            
            # Create drop indicator label
            self.upscaler_drop_indicator_label = QLabel("Drop Files or Folders Here")
            self.upscaler_drop_indicator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.upscaler_drop_indicator_label.setStyleSheet(f"""
                color: {COLORS['text']};
                font-size: 18px;
                font-weight: bold;
                background-color: {COLORS['primary']};
                padding: 15px;
                border-radius: 8px;
                opacity: 0.8;
            """)
            
            # Add to the existing layout
            self.upscaler_file_container.layout().addWidget(self.upscaler_drop_indicator_label, alignment=Qt.AlignmentFlag.AlignCenter)
            
            event.accept()
        else:
            event.ignore()

    def upscaler_dragLeaveEvent(self, event):
        """Handle drag leave event for upscaler file container"""
        # Restore original style
        if hasattr(self, 'upscaler_original_file_container_style'):
            self.upscaler_file_container.setStyleSheet(self.upscaler_original_file_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'upscaler_drop_indicator_label') and self.upscaler_drop_indicator_label:
            self.upscaler_drop_indicator_label.setParent(None)
            self.upscaler_drop_indicator_label = None
        
        # Clear the current layout
        while self.upscaler_file_container.layout().count():
            item = self.upscaler_file_container.layout().takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Restore original widgets
        if hasattr(self, 'upscaler_original_widgets') and self.upscaler_original_widgets:
            for widget in self.upscaler_original_widgets:
                self.upscaler_file_container.layout().addWidget(widget)
            self.upscaler_original_widgets = []
        
        event.accept()

    def upscaler_dragMoveEvent(self, event):
        """Handle drag move event for the upscaler file container"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def upscaler_dropEvent(self, event):
        """Handle drop event for the upscaler file container"""
        # Restore original style
        if hasattr(self, 'upscaler_original_file_container_style'):
            self.upscaler_file_container.setStyleSheet(self.upscaler_original_file_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'upscaler_drop_indicator_label') and self.upscaler_drop_indicator_label:
            self.upscaler_drop_indicator_label.setParent(None)
            self.upscaler_drop_indicator_label = None
        
        # Restore original widgets
        if hasattr(self, 'upscaler_original_widgets') and self.upscaler_original_widgets:
            for widget in self.upscaler_original_widgets:
                self.upscaler_file_container.layout().addWidget(widget)
            self.upscaler_original_widgets = []
        
        if event.mimeData().hasUrls():
            # Store existing files to avoid duplicates
            existing_files = set(self.upscaler_files)
            initial_file_count = len(self.upscaler_files)
            folder_paths = set()  # Track folders for display
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.upscaler_files:
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Get the file paths from the dropped URLs
            new_files = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    # If it's a directory, add all image files in it
                    folder_paths.add(path)
                    for root, _, files in os.walk(path):
                        for file in files:
                            if any(file.lower().endswith(f".{fmt.lower()}") for fmt in UPSCALE_FORMATS):
                                file_path = os.path.join(root, file)
                                if file_path not in existing_files:
                                    # Check for duplicate filename+extension
                                    filename = os.path.basename(file_path)
                                    name, ext = os.path.splitext(filename)
                                    
                                    if (name.lower(), ext.lower()) in existing_name_ext_pairs:
                                        skipped_files.append(file_path)
                                    else:
                                        new_files.append(file_path)
                                        existing_files.add(file_path)
                                        existing_name_ext_pairs.add((name.lower(), ext.lower()))
                elif os.path.isfile(path) and any(path.lower().endswith(f".{fmt.lower()}") for fmt in UPSCALE_FORMATS):
                    # If it's a file with supported extension, add it
                    if path not in existing_files:
                        # Check for duplicate filename+extension
                        filename = os.path.basename(path)
                        name, ext = os.path.splitext(filename)
                        
                        if (name.lower(), ext.lower()) in existing_name_ext_pairs:
                            skipped_files.append(path)
                        else:
                            new_files.append(path)
                            existing_files.add(path)
                            existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Update the selected folder if folders were dropped
            if folder_paths:
                self.upscaler_selected_folder = list(folder_paths)[0] if len(folder_paths) == 1 else "Multiple Folders"
            
            if new_files:
                # Add new files to the existing list
                self.upscaler_files.extend(new_files)
                
                # Sort all files using natural sort
                self.upscaler_files.sort(key=self.natural_sort_key)
                
                # Update the UI with all files
                self.add_upscaler_files_to_list(self.upscaler_files)
                
                # Show warning if files were skipped
                if skipped_files:
                    self.show_duplicate_warning(skipped_files)
            else:
                # No valid files were found, but we still need to update the UI
                # to show the drop folder label and provide feedback
                self.add_upscaler_files_to_list(self.upscaler_files)
                
                # If no files were added but folders were dropped, show a styled message
                if folder_paths and len(self.upscaler_files) == initial_file_count and not skipped_files:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("No Valid Files")
                    msg_box.setText("No supported image files were found in the dropped folders.")
                    msg_box.setInformativeText(f"Supported formats: {', '.join(UPSCALE_FORMATS)}")
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    
                    # Style the message box
                    msg_box.setStyleSheet(f"""
                        QMessageBox {{
                            background-color: {COLORS['background']};
                            color: {COLORS['text']};
                        }}
                        QLabel {{
                            color: {COLORS['text']};
                            font-size: 12px;
                        }}
                        QPushButton {{
                            background-color: {COLORS['primary']};
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 16px;
                            font-weight: bold;
                            min-width: 80px;
                        }}
                        QPushButton:hover {{
                            background-color: {COLORS['hover']};
                        }}
                    """)
                    
                    msg_box.exec()
                # If files were skipped but none were added, show the duplicate warning
                elif skipped_files:
                    self.show_duplicate_warning(skipped_files)
            
            event.accept()
        else:
            event.ignore()

    def select_upscale_output_dir(self):
        """This is a duplicate method - use set_denoiser_output_dir instead"""
        return self.set_upscaler_output_dir()

    def update_upscaler_progress(self, value, eta_text, speed_text):
        """Update the upscaler progress dialog"""
        if self.upscaler_progress_dialog:
            self.upscaler_progress_dialog.update_progress(value, eta_text, speed_text)

    def open_upscaler_output_folder(self):
        """Open the upscaler output folder"""
        if self.upscaler_output_dir and os.path.exists(self.upscaler_output_dir):
            os.startfile(self.upscaler_output_dir)

    def show_upscaler_instructions(self):
        """Show detailed instructions dialog for the Upscaler feature"""
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Use Image Upscaler")
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Set window icon
        icon_path = get_icon_path("icon.ico")
        if os.path.exists(icon_path):
            dialog.setWindowIcon(QIcon(icon_path))
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("How to Use Image Upscaler")
        title.setStyleSheet("font-size: 18px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Create scroll area for instructions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{ background-color: #252535; width: 10px; border-radius: 5px; }}
            QScrollBar::handle:vertical {{ background-color: #4d4d5f; border-radius: 5px; min-height: 20px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)
        
        # Container for instructions
        instructions_widget = QWidget()
        instructions_layout = QVBoxLayout(instructions_widget)
        
        # Add a rounded panel with key information at the top
        info_panel = QFrame()
        info_panel.setStyleSheet(f"""
            background-color: {COLORS['panel']}; 
            border-radius: 10px; 
            padding: 15px;
            margin-bottom: 15px;
        """)
        info_panel_layout = QVBoxLayout(info_panel)
        
        # Panel title
        panel_title = QLabel("Quick Reference")
        panel_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #0078d4; margin-bottom: 10px;")
        info_panel_layout.addWidget(panel_title)
        
        # Panel content
        panel_content = QLabel("""
        <p style="font-size: 14px; line-height: 1.5;">
        • <b>Purpose:</b> Increase image resolution with AI enhancement<br>
        • <b>Supported Formats:</b> PNG, JPG, JPEG, WEBP<br>
        • <b>Scale Factors:</b> 2x, 3x, 4x<br>
        • <b>Models:</b> Multiple AI models optimized for different image types<br>
        • <b>Batch Processing:</b> Process multiple images at once
        </p>
        """)
        panel_content.setTextFormat(Qt.TextFormat.RichText)
        panel_content.setWordWrap(True)
        info_panel_layout.addWidget(panel_content)
        instructions_layout.addWidget(info_panel)
        
        instructions_text = """
        <h2 style="font-size: 21px;">Image Upscaler - Complete Guide</h2>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Overview</h3>
        <p style="font-size: 14px; margin: 5px 0;">The Image Upscaler uses AI-powered technology to increase the resolution of your images while enhancing details and reducing artifacts. It's perfect for enlarging small images or improving image quality for printing.</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 1: Select Files</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Add Files</b> to select individual images to upscale<br>• Click <b>Add Folder</b> to select all supported images in a folder<br>• You can select/deselect individual files using the checkboxes</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 2: Choose Upscaling Options</h3>
        <p style="font-size: 14px; margin: 5px 0;">Configure how your images will be upscaled:</p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Scale Factor:</b> Choose between 1x, 2x, 4x for Waifu2x, and 2x, 3x, 4x for others.</li>
            <li><b>Model:</b> Select the AI model that best suits your image type.</li>
            <li><b>Output Format:</b> Select the file format for your upscaled images.</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 3: Set Output Directory</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Set Output Directory</b> to choose where upscaled images will be saved<br>• If not selected, you'll be prompted to choose a location before processing begins</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 4: Start Upscaling</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click the <b>Upscale Images</b> button to start the upscaling process<br>• A progress dialog will show the current status<br>• You can cancel the process at any time<br>• When complete, a summary dialog will show success/failure counts</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Available Models</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>waifu2x:</b> Excellent for anime/manga style images. Supports noise reduction levels (-1 to 3). <b>Note:</b> 1x denoise only works with the CUnet style!</li>
            <li><b>realcugan:</b> Specialized in anime images with different styles (SE, Pro, Nose).</li>
            <li><b>realesr:</b> Optimized for anime and animation style images with good detail preservation.</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Hardware Requirements</h3>
        <p style="font-size: 14px; margin: 5px 0;">For maximum stability, the upscaler strictly runs on your dedicated GPU using Vulkan. If you experience crashes, it means your system's GPU lacks the necessary compute capabilities or memory. CPU processing has been permanently disabled.</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Upscaling Factors</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>2x:</b> Doubles the resolution. Best for moderate enlargement with faster processing.</li>
            <li><b>3x:</b> Triples the resolution. Good balance between quality and processing time.</li>
            <li><b>4x:</b> Quadruples the resolution. Best for maximum enlargement, but requires more processing time.</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Tips for Best Results</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Model Selection:</b> Choose the model that best matches your image type</li>
            <li><b>Image Type:</b> Different models work better with different image styles</li>
            <li><b>Start Small:</b> For very large images, try 2x scale first</li>
            <li><b>Memory Usage:</b> Upscaling requires significant memory, especially at 4x</li>
            <li><b>Output Format:</b> PNG is recommended for highest quality</li>
            <li><b>Processing Time:</b> Larger images and higher scale factors take longer to process</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Troubleshooting</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Out of Memory:</b> Try processing fewer images at once or use a lower scale factor</li>
            <li><b>Slow Processing:</b> Upscaling is computationally intensive, especially for large images</li>
            <li><b>Artifacts:</b> Some images may show artifacts in areas with fine details</li>
            <li><b>Missing Output Files:</b> Check that you have write permissions for the output directory</li>
        </ul>
        """
        
        instructions = QLabel(instructions_text)
        instructions.setWordWrap(True)
        instructions.setTextFormat(Qt.TextFormat.RichText)
        instructions.setStyleSheet("font-size: 14px; line-height: 1.4;")
        instructions_layout.addWidget(instructions)
        
        scroll.setWidget(instructions_widget)
        layout.addWidget(scroll)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(40)
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(dialog.accept)
        close_btn.setStyleSheet(f"""
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
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()

    def upscaler_dropEvent(self, event):
        """Handle drop event for the upscaler file container"""
        # Restore original style
        if hasattr(self, 'upscaler_original_file_container_style'):
            self.upscaler_file_container.setStyleSheet(self.upscaler_original_file_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'upscaler_drop_indicator_label') and self.upscaler_drop_indicator_label:
            self.upscaler_drop_indicator_label.setParent(None)
            self.upscaler_drop_indicator_label = None
        
        # Restore original widgets
        if hasattr(self, 'upscaler_original_widgets') and self.upscaler_original_widgets:
            for widget in self.upscaler_original_widgets:
                self.upscaler_file_container.layout().addWidget(widget)
            self.upscaler_original_widgets = []
        
        if event.mimeData().hasUrls():
            # Store existing files to avoid duplicates
            existing_files = set(self.upscaler_files)
            initial_file_count = len(self.upscaler_files)
            folder_paths = set()  # Track folders for display
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.upscaler_files:
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Get the file paths from the dropped URLs
            new_files = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    # If it's a directory, add all image files in it
                    folder_paths.add(path)
                    for root, _, files in os.walk(path):
                        for file in files:
                            if any(file.lower().endswith(f".{fmt.lower()}") for fmt in UPSCALE_FORMATS):
                                file_path = os.path.join(root, file)
                                if file_path not in existing_files:
                                    # Check for duplicate filename+extension
                                    filename = os.path.basename(file_path)
                                    name, ext = os.path.splitext(filename)
                                    
                                    if (name.lower(), ext.lower()) in existing_name_ext_pairs:
                                        skipped_files.append(file_path)
                                    else:
                                        new_files.append(file_path)
                                        existing_files.add(file_path)
                                        existing_name_ext_pairs.add((name.lower(), ext.lower()))
                elif os.path.isfile(path) and any(path.lower().endswith(f".{fmt.lower()}") for fmt in UPSCALE_FORMATS):
                    # If it's a file with supported extension, add it
                    if path not in existing_files:
                        # Check for duplicate filename+extension
                        filename = os.path.basename(path)
                        name, ext = os.path.splitext(filename)
                        
                        if (name.lower(), ext.lower()) in existing_name_ext_pairs:
                            skipped_files.append(path)
                        else:
                            new_files.append(path)
                            existing_files.add(path)
                            existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Update the selected folder if folders were dropped
            if folder_paths:
                self.upscaler_selected_folder = list(folder_paths)[0] if len(folder_paths) == 1 else "Multiple Folders"
                
                # If we have a folder path but no output directory set yet, suggest the folder as output
                if not hasattr(self, 'upscaler_output_dir') or not self.upscaler_output_dir:
                    folder_path = list(folder_paths)[0]
                    # Create an "upscaled" subfolder
                    suggested_output = os.path.join(folder_path, "upscaled")
                    self.upscaler_output_dir = suggested_output
                    self.last_upscale_output_dir = suggested_output
                    
                    # Update the output directory label
                    if hasattr(self, 'upscaler_output_dir_label'):
                        # Truncate path if too long
                        display_path = suggested_output
                        if len(display_path) > 40:
                            display_path = "..." + display_path[-40:]
                        
                        # Add folder icon to the label text
                        self.upscaler_output_dir_label.setText(f"📁 {display_path}")
                        self.upscaler_output_dir_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
                        self.upscaler_output_dir_label.setToolTip(suggested_output)
            
            if new_files:
                # Add new files to the existing list
                self.upscaler_files.extend(new_files)
                
                # Sort all files using natural sort
                self.upscaler_files.sort(key=self.natural_sort_key)
                
                # Update the UI with all files
                self.add_upscaler_files_to_list(self.upscaler_files)
                
                # Show warning if files were skipped
                if skipped_files:
                    self.show_duplicate_warning(skipped_files)
            else:
                # No valid files were found, but we still need to update the UI
                # to show the drop folder label and provide feedback
                self.add_upscaler_files_to_list(self.upscaler_files)
                
                # If no files were added but folders were dropped, show a styled message
                if folder_paths and len(self.upscaler_files) == initial_file_count and not skipped_files:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("No Valid Files")
                    msg_box.setText("No supported image files were found in the dropped folders.")
                    msg_box.setInformativeText(f"Supported formats: {', '.join(UPSCALE_FORMATS)}")
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    
                    # Style the message box
                    msg_box.setStyleSheet(f"""
                        QMessageBox {{
                            background-color: {COLORS['background']};
                            color: {COLORS['text']};
                        }}
                        QLabel {{
                            color: {COLORS['text']};
                            font-size: 12px;
                        }}
                        QPushButton {{
                            background-color: {COLORS['primary']};
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 16px;
                            font-weight: bold;
                            min-width: 80px;
                        }}
                        QPushButton:hover {{
                            background-color: {COLORS['hover']};
                        }}
                    """)
                    
                    msg_box.exec()
                # If files were skipped but none were added, show the duplicate warning
                elif skipped_files:
                    self.show_duplicate_warning(skipped_files)
            
            # Update the upscale button state
            self.update_upscale_button_state()
            
            event.accept()
        else:
            event.ignore()

    def update_upscale_availability(self):
        """Update the upscale checkbox based on current format"""
        if not hasattr(self, 'upscale_check'):
            return  # Skip if UI elements aren't created yet
            
        # Force enable overrides Vulkan check
        force_enabled = hasattr(self, 'force_upscale_check') and self.force_upscale_check.isChecked()
        
        if self.vulkan_support or force_enabled:
            self.upscale_check.setEnabled(True)
            self.upscale_check.setStyleSheet("font-size: 13px; color: #ffffff;")
            self.upscale_check.setToolTip("Enable AI-powered upscaling")
        else:
            self.upscale_check.setEnabled(False)
            self.upscale_check.setChecked(False)
            self.upscale_check.setStyleSheet("font-size: 13px; color: #888888;")
            self.upscale_check.setToolTip("Enable AI-powered upscaling (Vulkan not detected, will use CPU fallback which is slower)")

    def toggle_upscale_options(self, state):
        pass

    def on_force_upscale_changed(self, state):
        """Handle force enable checkbox - bypasses Vulkan check"""
        self.update_upscale_availability()

    def open_upscale_settings(self):
        """Open the upscale model settings dialog"""
        dialog = UpscaleSettingsDialog(self, self.converter_upscale_settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.converter_upscale_settings = dialog.get_settings()
            self.log(f"Upscale settings updated: {self.converter_upscale_settings['model']} - {self.converter_upscale_settings['style_display']}", "INFO")
