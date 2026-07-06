
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

class DenoiserPanelMixin:
    def toggle_denoiser_select_all(self, state):
        """Toggle all file checkboxes based on the select all checkbox"""
        if not hasattr(self, 'denoiser_file_checkboxes'):
            return
            
        # Create a copy of the list to avoid issues with deleted objects
        for checkbox in list(self.denoiser_file_checkboxes):
            # Check if the checkbox is still valid
            try:
                checkbox.setChecked(state == Qt.CheckState.Checked.value)
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.denoiser_file_checkboxes:
                    self.denoiser_file_checkboxes.remove(checkbox)
        
        # Also update all file type checkboxes
        self.update_denoiser_file_type_checkbox_state()
        self.update_denoise_button_state()

    def update_denoiser_select_all_checkbox_state(self):
        """Update the state of the denoiser 'Select All' checkbox based on all file checkboxes"""
        if hasattr(self, 'denoiser_select_all') and hasattr(self, 'denoiser_file_checkboxes'):
            # Count checked and enabled checkboxes
            checked_count = 0
            enabled_count = 0
            
            for checkbox in self.denoiser_file_checkboxes:
                try:
                    if checkbox.isEnabled():
                        enabled_count += 1
                        if checkbox.isChecked():
                            checked_count += 1
                except RuntimeError:
                    continue
            
            # Update the "Select All" checkbox without triggering its signal
            if enabled_count > 0:
                self.denoiser_select_all.blockSignals(True)
                self.denoiser_select_all.setChecked(checked_count == enabled_count)
                self.denoiser_select_all.setText(f"Select All ({checked_count}/{enabled_count} selected)")
                self.denoiser_select_all.blockSignals(False)
                
                # Also update the file count label if it exists
                if hasattr(self, 'denoiser_file_count_label'):
                    self.denoiser_file_count_label.setText(f"Total: {len(self.denoiser_files)} files, {checked_count} selected")           

    def toggle_denoiser_file_type(self, state, file_ext):
        """Toggle all checkboxes for a specific file type in the denoiser panel"""
        if not hasattr(self, 'denoiser_file_checkboxes'):
            return
            
        # Count how many checkboxes we're changing
        changed_count = 0
        
        # Create a copy of the list to avoid issues with deleted objects
        for checkbox in list(self.denoiser_file_checkboxes):
            try:
                if hasattr(checkbox, 'file_ext') and checkbox.file_ext == file_ext:
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
                    changed_count += 1
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.denoiser_file_checkboxes:
                    self.denoiser_file_checkboxes.remove(checkbox)
        
        # Update the "Select All" checkbox state
        self.update_denoiser_select_all_checkbox_state()
        self.update_denoise_button_state()

    def update_denoiser_file_type_checkbox_state(self, state=None):
        """Update the file type checkbox state based on individual file checkboxes"""
        # Group checkboxes by file extension
        file_ext_groups = {}
        for checkbox in self.denoiser_file_checkboxes:
            try:
                if hasattr(checkbox, 'file_ext') and checkbox.isEnabled():
                    file_ext = checkbox.file_ext
                    if file_ext not in file_ext_groups:
                        file_ext_groups[file_ext] = []
                    file_ext_groups[file_ext].append(checkbox)
            except RuntimeError:
                continue
        
        # Find file type checkboxes in the UI
        file_type_checkboxes = []
        for i in range(self.denoiser_file_container.layout().count()):
            widget = self.denoiser_file_container.layout().itemAt(i).widget()
            if isinstance(widget, QScrollArea):
                scroll_widget = widget.widget()
                if scroll_widget:
                    for j in range(scroll_widget.layout().count()):
                        item = scroll_widget.layout().itemAt(j)
                        if item.widget() and isinstance(item.widget(), QFrame):
                            frame = item.widget()
                            # Check if frame has a layout before accessing it
                            if frame.layout() is not None:
                                for k in range(frame.layout().count()):
                                    item2 = frame.layout().itemAt(k)
                                    if item2 and item2.layout():
                                        for l in range(item2.layout().count()):
                                            widget2 = item2.layout().itemAt(l).widget()
                                            if isinstance(widget2, QCheckBox) and hasattr(widget2, 'file_ext'):
                                                file_type_checkboxes.append(widget2)
        
        # Update file type checkboxes based on individual checkboxes
        for checkbox in file_type_checkboxes:
            if hasattr(checkbox, 'file_ext'):
                file_ext = checkbox.file_ext
                if file_ext in file_ext_groups:
                    # Count checked checkboxes of this type
                    checked_count = sum(1 for cb in file_ext_groups[file_ext] if cb.isChecked())
                    total_count = len(file_ext_groups[file_ext])
                    
                    # Check if all checkboxes of this type are checked
                    all_checked = checked_count == total_count
                    
                    # Update the file type checkbox without triggering its signal
                    checkbox.blockSignals(True)
                    checkbox.setChecked(all_checked)
                    
                    # Update the text to show selected count
                    if hasattr(checkbox, 'original_text'):
                        checkbox.setText(f"{checkbox.original_text} ({checked_count}/{total_count} selected)")
                    
                    checkbox.blockSignals(False)
        
        # Update the "Select All" checkbox state and count
        self.update_denoiser_select_all_checkbox_state()
        
        # Update the denoise button state
        self.update_denoise_button_state()

    def add_denoiser_files_to_list(self, file_paths):
        """Add files to the denoiser file list"""
        # Store existing checkbox states before clearing the layout
        checkbox_states = {}
        for checkbox in list(self.denoiser_file_checkboxes):
            try:
                if hasattr(checkbox, 'file_path'):
                    checkbox_states[checkbox.file_path] = checkbox.isChecked()
            except RuntimeError:
                # Remove invalid checkboxes
                if checkbox in self.denoiser_file_checkboxes:
                    self.denoiser_file_checkboxes.remove(checkbox)
        
        # Clear the file container
        for i in reversed(range(self.denoiser_file_container.layout().count())):
            item = self.denoiser_file_container.layout().itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new files to the list, avoiding duplicates
        existing_files = set(self.denoiser_files)
        for file_path in file_paths:
            if file_path not in existing_files:
                self.denoiser_files.append(file_path)
                existing_files.add(file_path)
        
        # Sort all files using natural sort
        self.denoiser_files.sort(key=self.natural_sort_key)
        
        # Reset file_checkboxes list
        self.denoiser_file_checkboxes = []
        
        # If no files, show the placeholder
        if not self.denoiser_files:
            self.denoiser_file_label = QLabel("No files selected")
            self.denoiser_file_label.setWordWrap(True)
            self.denoiser_file_label.setStyleSheet("color: #888888; padding: 10px;")
            self.denoiser_file_container.layout().addWidget(self.denoiser_file_label)
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
            if hasattr(self, 'denoiser_selected_folder') and self.denoiser_selected_folder:
                folder_label = QLabel(f"📁 Selected Folder: {self.denoiser_selected_folder}")
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
            self.denoiser_select_all = QCheckBox("Select All")
            self.denoiser_select_all.stateChanged.connect(self.toggle_denoiser_select_all)
            self.denoiser_select_all.setChecked(True)
            select_all_layout.addWidget(self.denoiser_select_all)
            
            # Add file count
            self.denoiser_file_count_label = QLabel(f"Total: {len(self.denoiser_files)} files")
            self.denoiser_file_count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9pt;")
            select_all_layout.addWidget(self.denoiser_file_count_label, alignment=Qt.AlignmentFlag.AlignRight)
            
            file_list_layout.addLayout(select_all_layout)
            
            # Add a separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
            file_list_layout.addWidget(separator)
            
            # Group files by extension
            file_groups = {}
            for file_path in self.denoiser_files:
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
                    lambda state, ext=file_ext: self.toggle_denoiser_file_type(state, ext)
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
                    
                    # Connect checkbox state change
                    checkbox.stateChanged.connect(self.update_denoiser_file_type_checkbox_state)
                    
                    self.denoiser_file_checkboxes.append(checkbox)
                    
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
            self.denoiser_file_container.layout().addWidget(file_scroll)
            
            # Update the "Select All" checkbox state
            self.update_denoiser_select_all_checkbox_state()
        
        # Update the denoise button state
        self.update_denoise_button_state()

    def clear_denoiser_files(self):
        """Clear all files from the denoiser file list"""
        self.denoiser_files = []
        self.denoiser_file_checkboxes = []

        # Clear the output directory
        self.denoiser_output_dir = ""
        self.denoiser_output_dir_label.setText("No output directory selected")
        self.denoiser_output_dir_label.setStyleSheet("color: #888888; padding: 10px;")
        
        # Clear the file container
        for i in reversed(range(self.denoiser_file_container.layout().count())):
            widget = self.denoiser_file_container.layout().itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        # Add the placeholder label
        self.denoiser_file_label = QLabel("No files selected")
        self.denoiser_file_label.setWordWrap(True)
        self.denoiser_file_label.setStyleSheet("color: #888888; padding: 10px;")
        self.denoiser_file_container.layout().addWidget(self.denoiser_file_label)
        
        # Update the denoise button state
        self.update_denoise_button_state()        

    def select_denoise_output_dir(self):
        """This is a duplicate method - use set_denoiser_output_dir instead"""
        return self.set_denoiser_output_dir()

    def create_denoiser_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-bottom-left-radius: 10px; border-top-left-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)        
        
        # Title
        title = QLabel("AI Image Denoiser")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Model selection with label
        model_layout = QHBoxLayout()
        model_label = QLabel("Denoiser Type:")
        model_label.setFixedWidth(120)
        model_layout.addWidget(model_label)
        
        self.denoiser_model_combo = AnimatedComboBox()
        self.denoiser_model_combo.addItems(["Anime/Manga Style"])
        self.denoiser_model_combo.setToolTip("Only Anime/Manga style (CUnet) supports pure denoising without upscaling.")
        model_layout.addWidget(self.denoiser_model_combo)
        layout.addLayout(model_layout)
        
        # Noise Level selection
        noise_level_layout = QHBoxLayout()
        noise_level_label = QLabel("Noise Level:")
        noise_level_label.setFixedWidth(120)
        noise_level_layout.addWidget(noise_level_label)
        
        self.noise_level_combo = AnimatedComboBox()
        self.noise_level_combo.addItems([
            "Level 0 (Light)",
            "Level 1 (Low)",
            "Level 2 (Medium)",
            "Level 3 (Strong)"
        ])
        self.noise_level_combo.setCurrentText("Level 1 (Medium)")
        noise_level_layout.addWidget(self.noise_level_combo)
        layout.addLayout(noise_level_layout)
        
        # Add help buttons
        buttons_layout = QHBoxLayout()
        
        # Instructions button
        instructions_btn = QPushButton("📖 Denoiser Info")
        instructions_btn.setFont(QFont("Segoe UI", 10))
        instructions_btn.setFixedHeight(35)
        instructions_btn.clicked.connect(self.show_denoiser_instructions)
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
        buttons_layout.addWidget(instructions_btn)
        
        # System Info button
        system_info_btn = QPushButton("🖥️ Check GPU")
        system_info_btn.setFont(QFont("Segoe UI", 10))
        system_info_btn.setFixedHeight(35)
        system_info_btn.clicked.connect(self.show_system_info)
        system_info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        system_info_btn.setStyleSheet(instructions_btn.styleSheet())
        buttons_layout.addWidget(system_info_btn)
        
        layout.addLayout(buttons_layout)
        
        # Help text
        help_text = QLabel("📝 AI denoising uses neural networks to remove noise and improve image quality.\n⚙️ Different models are optimized for different types of images.\n🖥️ GPU acceleration is required for reasonable performance.")
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
        self.denoiser_fm.create_action_buttons(layout)
        
        layout.addStretch()
        
        # Denoise button at the bottom
        self.denoise_btn = QPushButton("✨ Denoise")
        self.denoise_btn.setFont(QFont("Segoe UI", 12))
        self.denoise_btn.setFixedHeight(65)
        self.denoise_btn.setEnabled(False)
        self.denoise_btn.clicked.connect(self.start_denoising)
        self.denoise_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.denoise_btn.setStyleSheet(f"""
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
        layout.addWidget(self.denoise_btn)
        
        return panel

    def create_denoiser_right_panel(self):
        """Create the right panel for the denoiser tab with file list and output directory"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-top-right-radius: 10px; border-bottom-right-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # File list header
        file_header = QLabel("Selected Files:")
        file_header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 5px;")
        layout.addWidget(file_header)
        
        # Create a container for the scroll area with rounded corners
        scroll_container = QFrame()
        scroll_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 10px;")
        scroll_container_layout = QVBoxLayout(scroll_container)
        scroll_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # File list scroll area with improved styling
        self.denoiser_scroll_area = QScrollArea()
        self.denoiser_scroll_area.setWidgetResizable(True)
        self.denoiser_scroll_area.setMinimumHeight(200)
        self.denoiser_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.denoiser_scroll_area.setStyleSheet(f"""
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
        self.denoiser_file_container = QWidget()
        self.denoiser_file_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 8px;")
        file_layout = QVBoxLayout(self.denoiser_file_container)
        file_layout.setContentsMargins(10, 10, 10, 10)
        file_layout.setSpacing(8)
        
        # Enable drag and drop
        self.denoiser_file_container.setAcceptDrops(True)
        self.denoiser_file_container.dragEnterEvent = self.denoiser_dragEnterEvent
        self.denoiser_file_container.dragLeaveEvent = self.denoiser_dragLeaveEvent
        self.denoiser_file_container.dropEvent = self.denoiser_dropEvent
        self.denoiser_file_container.dragMoveEvent = self.denoiser_dragMoveEvent
        
        # Store original style
        self.denoiser_original_file_container_style = self.denoiser_file_container.styleSheet()
        
        # Initial placeholder
        self.denoiser_file_label = QLabel("No files selected")
        self.denoiser_file_label.setWordWrap(True)
        self.denoiser_file_label.setStyleSheet("color: #888888; padding: 10px;")
        file_layout.addWidget(self.denoiser_file_label)
        
        self.denoiser_scroll_area.setWidget(self.denoiser_file_container)
        scroll_container_layout.addWidget(self.denoiser_scroll_area)
        layout.addWidget(scroll_container)
        
        # Output directory header
        output_header = QLabel("Output Directory:")
        output_header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 5px;")
        layout.addWidget(output_header)
        
        # Output directory display
        output_container = QWidget()
        output_container.setMinimumHeight(40)
        output_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 8px;")
        output_layout = QVBoxLayout(output_container)
        
        self.denoiser_output_dir_label = QLabel("No output directory selected")
        self.denoiser_output_dir_label.setWordWrap(True)
        self.denoiser_output_dir_label.setStyleSheet("color: #888888; padding: 10px;")
        output_layout.addWidget(self.denoiser_output_dir_label)
        
        output_container.setLayout(output_layout)
        layout.addWidget(output_container)
        
        return panel

    def create_denoiser_action_buttons(self, layout):
        """Create action buttons for the denoiser panel"""
        # Create a grid layout for the buttons
        button_layout = QGridLayout()
        button_layout.setSpacing(10)
        
        # Add Files button
        add_files_btn = QPushButton("📁 Add Files")
        add_files_btn.setFont(QFont("Segoe UI", 10))
        add_files_btn.setFixedHeight(40)
        add_files_btn.clicked.connect(self.add_denoiser_files)
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
        add_folder_btn.clicked.connect(self.add_denoiser_folder)
        add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder_btn.setStyleSheet(add_files_btn.styleSheet())
        button_layout.addWidget(add_folder_btn, 0, 1)
        
        # Clear Files button
        clear_files_btn = QPushButton("🚫 Clear Files")
        clear_files_btn.setFont(QFont("Segoe UI", 10))
        clear_files_btn.setFixedHeight(40)
        clear_files_btn.clicked.connect(self.clear_denoiser_files)
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
        
        # Set Output button
        set_output_btn = QPushButton("📂 Set Output")
        set_output_btn.setFont(QFont("Segoe UI", 10))
        set_output_btn.setFixedHeight(40)
        set_output_btn.clicked.connect(self.set_denoiser_output_dir)
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

    def denoiser_dragEnterEvent(self, event):
        """Handle drag enter event for the denoiser file container"""
        if event.mimeData().hasUrls():
            # Store original style
            if not hasattr(self, 'denoiser_original_file_container_style'):
                self.denoiser_original_file_container_style = self.denoiser_file_container.styleSheet()
            
            # Change style for drop indication
            self.denoiser_file_container.setStyleSheet(f"background-color: {COLORS['hover']}; border-radius: 8px; border: 2px dashed white;")
            
            # Store original widgets
            self.denoiser_original_widgets = []
            for i in range(self.denoiser_file_container.layout().count()):
                widget = self.denoiser_file_container.layout().itemAt(i).widget()
                if widget:
                    self.denoiser_original_widgets.append(widget)
                    widget.setParent(None)
            
            # Create drop indicator
            self.denoiser_drop_indicator_label = QLabel("Drop Files or Folders Here")
            self.denoiser_drop_indicator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.denoiser_drop_indicator_label.setStyleSheet(f"""
                color: {COLORS['text']};
                font-size: 18px;
                font-weight: bold;
                background-color: {COLORS['primary']};
                padding: 15px;
                border-radius: 8px;
                opacity: 0.8;
            """)
            
            self.denoiser_file_container.layout().addWidget(self.denoiser_drop_indicator_label, alignment=Qt.AlignmentFlag.AlignCenter)
            event.accept()
        else:
            event.ignore()

    def denoiser_dragLeaveEvent(self, event):
        """Handle drag leave event for denoiser file container"""
        # Restore original style
        if hasattr(self, 'denoiser_original_file_container_style'):
            self.denoiser_file_container.setStyleSheet(self.denoiser_original_file_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'denoiser_drop_indicator_label') and self.denoiser_drop_indicator_label:
            self.denoiser_drop_indicator_label.setParent(None)
            self.denoiser_drop_indicator_label = None
        
        # Clear current layout
        while self.denoiser_file_container.layout().count():
            item = self.denoiser_file_container.layout().takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Restore original widgets
        if hasattr(self, 'denoiser_original_widgets') and self.denoiser_original_widgets:
            for widget in self.denoiser_original_widgets:
                self.denoiser_file_container.layout().addWidget(widget)
            self.denoiser_original_widgets = []
        
        event.accept()

    def denoiser_dragMoveEvent(self, event):
        """Handle drag move event for the denoiser file container"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def denoiser_dropEvent(self, event):
        """Handle drop event for the denoiser file container"""
        # Restore original style
        if hasattr(self, 'denoiser_original_file_container_style'):
            self.denoiser_file_container.setStyleSheet(self.denoiser_original_file_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'denoiser_drop_indicator_label') and self.denoiser_drop_indicator_label:
            self.denoiser_drop_indicator_label.setParent(None)
            self.denoiser_drop_indicator_label = None
        
        # Restore original widgets
        if hasattr(self, 'denoiser_original_widgets') and self.denoiser_original_widgets:
            for widget in self.denoiser_original_widgets:
                self.denoiser_file_container.layout().addWidget(widget)
            self.denoiser_original_widgets = []
        
        if event.mimeData().hasUrls():
            # Store existing files to avoid duplicates
            existing_files = set(self.denoiser_files)
            initial_file_count = len(self.denoiser_files)
            folder_paths = set()  # Track folders for display
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.denoiser_files:
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
                            if any(file.lower().endswith(f".{fmt.lower()}") for fmt in DENOISE_FORMATS):
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
                elif os.path.isfile(path) and any(path.lower().endswith(f".{fmt.lower()}") for fmt in DENOISE_FORMATS):
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
                self.denoiser_selected_folder = list(folder_paths)[0] if len(folder_paths) == 1 else "Multiple Folders"
            
            if new_files:
                # Add new files to the existing list
                self.denoiser_files.extend(new_files)
                
                # Sort all files using natural sort
                self.denoiser_files.sort(key=self.natural_sort_key)
                
                # Update the UI with all files
                self.add_denoiser_files_to_list(self.denoiser_files)
                
                # Show warning if files were skipped
                if skipped_files:
                    self.show_duplicate_warning(skipped_files)
            else:
                # No valid files were found, but we still need to update the UI
                # to show the drop folder label and provide feedback
                self.add_denoiser_files_to_list(self.denoiser_files)
                
                # If no files were added but folders were dropped, show a styled message
                if folder_paths and len(self.denoiser_files) == initial_file_count and not skipped_files:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("No Valid Files")
                    msg_box.setText("No supported image files were found in the dropped folders.")
                    msg_box.setInformativeText(f"Supported formats: {', '.join(DENOISE_FORMATS)}")
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

    def add_denoiser_files(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(f"Supported Files (*.{' *.'.join(map(str.lower, DENOISE_FORMATS))})")
        
        if file_dialog.exec():
            # Get the new files
            new_files = file_dialog.selectedFiles()
            
            # Keep existing files and add new ones, avoiding duplicates
            existing_files = set(self.denoiser_files)
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.denoiser_files:
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
                        self.denoiser_files.append(file_path)
                        existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Sort files using natural sort
            self.denoiser_files.sort(key=self.natural_sort_key)
            
            # Get the parent directory of the first selected file if not already set
            if not hasattr(self, 'denoiser_selected_folder') or not self.denoiser_selected_folder:
                if self.denoiser_files:
                    self.denoiser_selected_folder = os.path.dirname(self.denoiser_files[0])
            
            # Show warning if files were skipped
            if skipped_files:
                self.show_duplicate_warning(skipped_files)
                    
            self.add_denoiser_files_to_list(self.denoiser_files)

    def add_denoiser_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
        if folder:
            # Store existing files to avoid duplicates
            existing_files = set(self.denoiser_files)
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.denoiser_files:
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Find all supported files in the folder
            supported_extensions = tuple(f'.{ext.lower()}' for ext in DENOISE_FORMATS)
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
                                self.denoiser_files.append(file_path)
                                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Sort files using natural sort
            self.denoiser_files.sort(key=self.natural_sort_key)
            
            # Set the selected folder if not already set or if new files were added
            if (not hasattr(self, 'denoiser_selected_folder') or not self.denoiser_selected_folder) and new_files:
                self.denoiser_selected_folder = folder
            
            # Show warning if files were skipped
            if skipped_files:
                self.show_duplicate_warning(skipped_files)
                
            self.add_denoiser_files_to_list(self.denoiser_files)

    def update_denoise_button_state(self):
        """Update the state of the denoise button based on file selection and output directory"""
        files_selected = len(self.denoiser_fm.get_selected_files()) > 0
        has_output_dir = bool(self.denoiser_fm.output_dir)
        self.denoise_btn.setEnabled(files_selected and has_output_dir)

    def set_denoiser_output_dir(self):
        """Open folder dialog to set the output directory for denoised images"""
        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.FileMode.Directory)
        folder_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if folder_dialog.exec():
            self.denoiser_output_dir = folder_dialog.selectedFiles()[0]
            self.denoiser_output_dir_label.setText(f"📁 {self.denoiser_output_dir}")
            # Use COLORS dictionary instead of hardcoded color
            self.denoiser_output_dir_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
            
            # Update the denoise button state
            self.update_denoise_button_state()

    def toggle_denoiser_output_format(self, state):
        """Toggle the output format combobox based on the 'Keep Original Format' checkbox"""
        is_checked = state == Qt.CheckState.Checked
        self.denoiser_format_combo.setEnabled(not is_checked)
        
        # Apply the same styling as used in toggle_output_format
        if is_checked:
            self.denoiser_format_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: #3d3d4f;
                    color: #888888;
                    border: 1px solid #3d3d4f;
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
            """)
        else:
            self.denoiser_format_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
                QComboBox:hover {{
                    border: 1px solid {COLORS['primary']};
                }}
            """)

    def update_denoiser_progress(self, value, eta_text, speed_text):
        """Update the denoiser progress dialog"""
        if self.denoiser_progress_dialog:
            self.denoiser_progress_dialog.update_progress(value, eta_text, speed_text)

    def show_denoiser_instructions(self):
        """Show detailed instructions dialog for the Denoiser feature"""
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Use Image Denoiser")
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Set window icon
        icon_path = get_icon_path("icon.ico")
        if os.path.exists(icon_path):
            dialog.setWindowIcon(QIcon(icon_path))
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("How to Use Image Denoiser")
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
        • <b>Purpose:</b> Remove noise and improve image quality<br>
        • <b>Supported Formats:</b> PNG, JPG, JPEG, WEBP<br>
        • <b>Strength Levels:</b> Light, Medium, Strong<br>
        • <b>Batch Processing:</b> Process multiple images at once<br>
        • <b>Preserves:</b> Original image dimensions and aspect ratio
        </p>
        """)
        panel_content.setTextFormat(Qt.TextFormat.RichText)
        panel_content.setWordWrap(True)
        info_panel_layout.addWidget(panel_content)
        instructions_layout.addWidget(info_panel)
        
        instructions_text = """
        <h2 style="font-size: 21px;">Image Denoiser - Complete Guide</h2>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Overview</h3>
        <p style="font-size: 14px; margin: 5px 0;">The Image Denoiser is designed to remove noise, grain, and compression artifacts from your images, resulting in cleaner, smoother images while preserving important details.</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 1: Select Files</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Add Files</b> to select individual images to denoise<br>• Click <b>Add Folder</b> to select all supported images in a folder<br>• You can select/deselect individual files using the checkboxes</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 2: Choose Denoising Options</h3>
        <p style="font-size: 14px; margin: 5px 0;">Configure how your images will be denoised:</p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Strength:</b> Choose between Light, Medium, or Strong denoising</li>
            <li><b>Output Format:</b> Select the file format for your denoised images</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 3: Set Output Directory</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Set Output Directory</b> to choose where denoised images will be saved<br>• If not selected, you'll be prompted to choose a location before processing begins</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 4: Start Denoising</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click the <b>Denoise Images</b> button to start the denoising process<br>• A progress dialog will show the current status<br>• You can cancel the process at any time<br>• When complete, a summary dialog will show success/failure counts</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Denoising Strength Levels</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Light:</b> Subtle noise reduction, preserves most details. Best for slightly noisy images or when detail preservation is critical.</li>
            <li><b>Medium:</b> Balanced noise reduction and detail preservation. Good for most images with moderate noise.</li>
            <li><b>Strong:</b> Aggressive noise reduction. Best for very noisy images, but may smooth out some fine details.</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Tips for Best Results</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Start Light:</b> Begin with Light strength and increase if needed</li>
            <li><b>Preview:</b> Check a single image first to determine the best strength setting</li>
            <li><b>High-Resolution:</b> Higher resolution images generally benefit more from denoising</li>
            <li><b>Output Format:</b> PNG is recommended for highest quality, JPEG for smaller file sizes</li>
            <li><b>Memory Usage:</b> Denoising large images requires significant memory</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Supported Models</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Anime/Manga Style (CUnet):</b> The only style supported for pure denoising, as it natively contains 1x resolution models.</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Hardware Requirements</h3>
        <p style="font-size: 14px; margin: 5px 0;">For maximum stability, the denoiser strictly runs on your dedicated GPU using Vulkan. If you experience crashes, it means your system's GPU lacks the necessary compute capabilities or memory. CPU processing has been permanently disabled.</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Troubleshooting</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Blurry Results:</b> Try using a lighter strength setting</li>
            <li><b>Processing Fails:</b> Ensure you have enough system memory for large images</li>
            <li><b>Slow Processing:</b> Denoising is computationally intensive, especially for large images</li>
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

