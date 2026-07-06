
from src.ui.widgets.animated_combobox import AnimatedComboBox
from src.ui.widgets.progress_dialog import ProcessingProgressDialog
from src.ui.widgets.update_notification import UpdateNotification
from src.ui.widgets.upscale_settings import UpscaleSettingsDialog
from src.managers.file_list_manager import FileListManager
from src.core.stitcher_thread import StitcherThread

import os
import re
import time
import psutil
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from src.constants import *
from src.ui.styles import *
from src.utils.helpers import *
from src.config import *

class StitcherPanelMixin:
    def create_stitcher_panel(self):
        """Create the image stitcher panel with controls for stitching images"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-bottom-left-radius: 10px; border-top-left-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)        
        
        # Title
        title = QLabel("Image Stitcher")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Orientation selection
        orientation_layout = QHBoxLayout()
        orientation_label = QLabel("Stitch Direction:")
        orientation_label.setFixedWidth(120)
        orientation_layout.addWidget(orientation_label)
        
        self.orientation_combo = AnimatedComboBox()
        self.orientation_combo.addItems(["Vertical (Top to Bottom)", "Vertical (Bottom to Top)", "Horizontal (Left to Right)", "Horizontal (Right to Left)"])
        orientation_layout.addWidget(self.orientation_combo)
        layout.addLayout(orientation_layout)
        
        # Spacing between images
        spacing_layout = QHBoxLayout()
        spacing_label = QLabel("Image Spacing:")
        spacing_label.setFixedWidth(120)
        spacing_layout.addWidget(spacing_label)
        
        # Create a container for spacing controls
        spacing_controls = QHBoxLayout()
        spacing_controls.setSpacing(20)
        
        # Add dropdown for preset spacing values
        self.spacing_combo = AnimatedComboBox()
        self.spacing_combo.setMinimumWidth(80)
        self.spacing_combo.addItems(["-10px", "-5px", "0px", "5px", "10px", "15px", "20px"])
        self.spacing_combo.setCurrentIndex(1)  # Default to 5px
        spacing_controls.addWidget(self.spacing_combo)
        
        # Add manual spacing input
        self.manual_spacing_input = QLineEdit()
        self.manual_spacing_input.setPlaceholderText("0")
        self.manual_spacing_input.setMinimumWidth(80)
        self.manual_spacing_input.setFixedHeight(36)
        self.manual_spacing_input.setValidator(QIntValidator())  # Allow only integers (positive and negative)
        self.manual_spacing_input.setEnabled(False)  # Disabled by default
        self.manual_spacing_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QLineEdit:disabled {{
                    background-color: #3d3d4f;
                    color: #888888;
            }}
        """)
        spacing_controls.addWidget(self.manual_spacing_input)
        
        # Add toggle for manual spacing
        self.manual_spacing_toggle = QCheckBox("Custom Pixel     ")
        self.manual_spacing_toggle.setChecked(False)
        self.manual_spacing_toggle.stateChanged.connect(self.toggle_manual_spacing)
        spacing_controls.addWidget(self.manual_spacing_toggle)
        
        spacing_layout.addLayout(spacing_controls)
        layout.addLayout(spacing_layout)
        
        # Alignment selection
        alignment_layout = QHBoxLayout()
        alignment_label = QLabel("Alignment:")
        alignment_label.setFixedWidth(120)
        alignment_layout.addWidget(alignment_label)
        self.stitcher_alignment_combo = AnimatedComboBox()
        self.stitcher_alignment_combo.addItems(["Center", "Start (Left/Top)", "End (Right/Bottom)"])
        alignment_layout.addWidget(self.stitcher_alignment_combo)
        layout.addLayout(alignment_layout)
        
        # Background color selection
        bg_color_layout = QHBoxLayout()
        bg_color_label = QLabel("Background Color:")
        bg_color_label.setFixedWidth(120)
        bg_color_layout.addWidget(bg_color_label)
        self.stitcher_bg_color_combo = AnimatedComboBox()
        self.stitcher_bg_color_combo.addItems(["Transparent", "White", "Black"])
        bg_color_layout.addWidget(self.stitcher_bg_color_combo)
        layout.addLayout(bg_color_layout)
        
        # Resize options selection
        resize_layout = QHBoxLayout()
        resize_label = QLabel("Resize Images:")
        resize_label.setFixedWidth(120)
        resize_layout.addWidget(resize_label)
        self.stitcher_resize_combo = AnimatedComboBox()
        self.stitcher_resize_combo.addItems(["Don't Resize", "Match Smallest", "Match Largest", "Match First"])
        resize_layout.addWidget(self.stitcher_resize_combo)
        layout.addLayout(resize_layout)
        
        # Output format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Output Format:")
        format_label.setFixedWidth(120)
        format_layout.addWidget(format_label)
        
        self.stitcher_format_combo = AnimatedComboBox()
        self.stitcher_format_combo.addItems(["PNG", "JPEG", "WEBP"])
        format_layout.addWidget(self.stitcher_format_combo)
        layout.addLayout(format_layout)
        
        # Instructions button
        instructions_btn = QPushButton("📖 Stitcher Info")
        instructions_btn.setFont(QFont("Segoe UI", 10))
        instructions_btn.setFixedHeight(35)
        instructions_btn.clicked.connect(self.show_stitcher_instructions)
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
        layout.addWidget(instructions_btn)
        
        # Help text
        help_text = QLabel("📝 Image Stitcher combines multiple images into a single image.\n📂 Select folders containing images to stitch them together.")
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
        file_title = QLabel("Folder Selection & Output")
        file_title.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(file_title)
        
        # Add file selection buttons
        self.create_stitcher_action_buttons(layout)
        
        layout.addStretch()
        
        # Stitch button at the bottom
        self.stitch_btn = QPushButton("🧵 Stitch Images")
        self.stitch_btn.setFont(QFont("Segoe UI", 12))
        self.stitch_btn.setFixedHeight(65)
        self.stitch_btn.setEnabled(False)
        self.stitch_btn.clicked.connect(self.start_stitching)
        self.stitch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stitch_btn.setStyleSheet(f"""
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
        layout.addWidget(self.stitch_btn)
        
        return panel

    def create_stitcher_action_buttons(self, layout):
        """Create action buttons for the stitcher panel"""
        # Create a grid layout for the buttons
        button_layout = QGridLayout()
        button_layout.setSpacing(10)
        
        # Add Files button
        add_folders_btn = QPushButton("📁 Add Files")
        add_folders_btn.setFont(QFont("Segoe UI", 10))
        add_folders_btn.setFixedHeight(40)
        add_folders_btn.clicked.connect(self.add_stitcher_files_as_group)
        add_folders_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folders_btn.setStyleSheet(f"""
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
        button_layout.addWidget(add_folders_btn, 0, 0)
        
        # Add Parent Folder button
        add_parent_folder_btn = QPushButton("📂 Add Parent Folder")
        add_parent_folder_btn.setFont(QFont("Segoe UI", 10))
        add_parent_folder_btn.setFixedHeight(40)
        add_parent_folder_btn.clicked.connect(self.add_stitcher_parent_folder)
        add_parent_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_parent_folder_btn.setStyleSheet(add_folders_btn.styleSheet())
        button_layout.addWidget(add_parent_folder_btn, 0, 1)
        
        # Clear Folders button (red color)
        clear_folders_btn = QPushButton("🚫 Clear Folders")
        clear_folders_btn.setFont(QFont("Segoe UI", 10))
        clear_folders_btn.setFixedHeight(40)
        clear_folders_btn.clicked.connect(self.clear_stitcher_folders)
        clear_folders_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_folders_btn.setStyleSheet(f"""
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
        button_layout.addWidget(clear_folders_btn, 1, 0)
        
        # Set Output button
        set_output_btn = QPushButton("📂 Set Output")
        set_output_btn.setFont(QFont("Segoe UI", 10))
        set_output_btn.setFixedHeight(40)
        set_output_btn.clicked.connect(self.set_stitcher_output_dir)
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

    def create_stitcher_right_panel(self):
        """Create the right panel for the stitcher tab with folder list and output directory"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-top-right-radius: 10px; border-bottom-right-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Folder list header
        folder_header = QLabel("Selected Folders:")
        folder_header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 5px;")
        layout.addWidget(folder_header)
        
        # Create a container for the scroll area with rounded corners
        scroll_container = QFrame()
        scroll_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 10px;")
        scroll_container_layout = QVBoxLayout(scroll_container)
        scroll_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Folder list scroll area with improved styling
        self.stitcher_scroll_area = QScrollArea()
        self.stitcher_scroll_area.setWidgetResizable(True)
        self.stitcher_scroll_area.setMinimumHeight(100)
        self.stitcher_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.stitcher_scroll_area.setStyleSheet(f"""
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
        
        # Initial folder container
        self.stitcher_folder_container = QWidget()
        self.stitcher_folder_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 8px;") 
        folder_layout = QVBoxLayout(self.stitcher_folder_container)
        folder_layout.setContentsMargins(10, 10, 10, 10)
        folder_layout.setSpacing(8)
        
        # Enable drag and drop for folder container
        self.stitcher_folder_container.setAcceptDrops(True)
        
        # Override drag and drop events for folder container
        self.stitcher_folder_container.dragEnterEvent = self.stitcher_dragEnterEvent
        self.stitcher_folder_container.dragLeaveEvent = self.stitcher_dragLeaveEvent
        self.stitcher_folder_container.dropEvent = self.stitcher_dropEvent
        self.stitcher_folder_container.dragMoveEvent = self.stitcher_dragMoveEvent
        
        # Store original style to restore after drag leave
        self.stitcher_original_folder_container_style = self.stitcher_folder_container.styleSheet()
        
        # Initial placeholder
        self.stitcher_folder_label = QLabel("No folders/files selected")
        self.stitcher_folder_label.setWordWrap(True)
        self.stitcher_folder_label.setStyleSheet("color: #888888; padding: 10px;")
        folder_layout.addWidget(self.stitcher_folder_label)
        
        self.stitcher_scroll_area.setWidget(self.stitcher_folder_container)
        scroll_container_layout.addWidget(self.stitcher_scroll_area)
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
        
        self.stitcher_output_dir_label = QLabel("No output directory selected")
        self.stitcher_output_dir_label.setWordWrap(True)
        self.stitcher_output_dir_label.setStyleSheet("color: #888888; padding: 10px;")
        output_layout.addWidget(self.stitcher_output_dir_label)
        
        output_container.setLayout(output_layout)
        layout.addWidget(output_container)

        return panel

    def show_stitcher_instructions(self):
        """Show detailed instructions dialog for the Stitcher feature"""
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Use Image Stitcher")
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Set window icon
        icon_path = get_icon_path("icon.ico")
        if os.path.exists(icon_path):
            dialog.setWindowIcon(QIcon(icon_path))
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("How to Use Image Stitcher")
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
        • <b>Purpose:</b> Combine multiple images into a single image<br>
        • <b>Orientation:</b> Horizontal or Vertical stitching<br>
        • <b>Spacing:</b> Adjustable spacing between images<br>
        • <b>Output Formats:</b> PNG, JPG, WEBP, BMP, TIFF<br>
        • <b>Batch Processing:</b> Stitch multiple folders at once
        </p>
        """)
        panel_content.setTextFormat(Qt.TextFormat.RichText)
        panel_content.setWordWrap(True)
        info_panel_layout.addWidget(panel_content)
        instructions_layout.addWidget(info_panel)
        
        instructions_text = """
        <h2 style="font-size: 21px;">Image Stitcher - Complete Guide</h2>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Overview</h3>
        <p style="font-size: 14px; margin: 5px 0;">The Image Stitcher is a powerful tool designed to combine multiple images into a single image. It's perfect for creating panoramas, image strips, or combining related images into a single file.</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 1: Select Folders</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Add Folders</b> to select folders containing images to stitch<br>• Click <b>Add Parent Folder</b> to automatically find all image folders within a parent directory<br>• Each folder will be stitched into a separate output image<br>• You can select/deselect individual folders using the checkboxes</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 2: Choose Stitching Options</h3>
        <p style="font-size: 14px; margin: 5px 0;">Configure how your images will be stitched together:</p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Orientation:</b> Choose between horizontal (side by side) or vertical (stacked) stitching</li>
            <li><b>Spacing:</b> Set the amount of space between images (0px for no gap)</li>
            <li><b>Output Format:</b> Select the file format for your stitched images</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 3: Set Output Directory</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Set Output Directory</b> to choose where stitched images will be saved<br>• If not selected, you'll be prompted to choose a location before stitching begins<br>• The application will create the directory if it doesn't exist</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 4: Preview</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• The preview panel shows which images will be stitched<br>• It displays the first few images from each folder<br>• The preview updates automatically when you change settings or select different folders</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 5: Stitch Images</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click the <b>Stitch Images</b> button to start the stitching process<br>• A progress dialog will show the current status<br>• You can cancel the process at any time<br>• When complete, a summary dialog will show success/failure counts<br>• You can open the output folder directly from this dialog</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Supported Image Formats</h3>
        <p style="font-size: 14px; margin: 5px 0;">The Stitcher supports the following image formats:</p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>PNG</b> (.png): Portable Network Graphics</li>
            <li><b>JPEG</b> (.jpg, .jpeg): Joint Photographic Experts Group</li>
            <li><b>BMP</b> (.bmp): Bitmap Image File</li>
            <li><b>GIF</b> (.gif): Graphics Interchange Format</li>
            <li><b>TIFF</b> (.tif, .tiff): Tagged Image File Format</li>
            <li><b>WEBP</b> (.webp): Web Picture format</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Tips for Best Results</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Image Sizes:</b> For best results, use images with the same dimensions</li>
            <li><b>Image Order:</b> Images are stitched in alphabetical/numerical order by filename</li>
            <li><b>Memory Usage:</b> Stitching very large images or many images at once may require significant memory</li>
            <li><b>Spacing:</b> Use the manual spacing option for precise control over the gap between images</li>
            <li><b>Output Format:</b> PNG is recommended for highest quality, JPEG for smaller file sizes</li>
            <li><b>Folder Organization:</b> Keep related images in separate folders for batch stitching</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Troubleshooting</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Stitching fails:</b> Ensure all source images are valid and not corrupted</li>
            <li><b>Missing output files:</b> Check that you have write permissions for the output directory</li>
            <li><b>Memory errors:</b> Try stitching fewer images at once or use smaller images</li>
            <li><b>Image alignment issues:</b> Ensure all images have the same dimensions for best alignment</li>
            <li><b>Unexpected order:</b> Rename your files to ensure they sort in the desired order</li>
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

    def add_stitcher_files_as_group(self):
        """Add individual image files to stitch"""
        # Initialize stitcher_folders list if it doesn't exist
        if not hasattr(self, 'stitcher_folders'):
            self.stitcher_folders = []
            
        # Initialize stitcher_files dictionary if it doesn't exist
        if not hasattr(self, 'stitcher_files'):
            self.stitcher_files = {}
            
        # Open file selection dialog
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Image Files to Stitch", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.tif *.psd *.pdf)"
        )
        
        if files:
            # Create a virtual folder for these files
            folder_name = f"Custom Selection {len(self.stitcher_folders) + 1}"
            virtual_folder = f"virtual:{folder_name}"
            
            # Add new virtual folder if not already present
            if virtual_folder not in self.stitcher_folders:
                self.stitcher_folders.append(virtual_folder)
                self.stitcher_files[virtual_folder] = files
                self.log(f"Added {len(files)} files as '{folder_name}'", "INFO")
                
                # Update the folder list display
                self.update_stitcher_folder_list()
                
                # Update stitch button state
                self.update_stitch_button_state()
                
                # Update preview
                self.update_stitcher_preview(virtual_folder)

    def add_stitcher_parent_folder(self):
        """Add a parent folder containing subfolders with images"""
        # Initialize stitcher_folders list if it doesn't exist
        if not hasattr(self, 'stitcher_folders'):
            self.stitcher_folders = []
            
        # Open folder selection dialog
        parent_folder = QFileDialog.getExistingDirectory(self, "Select Parent Folder Containing Image Folders")
        if parent_folder:
            # Get all immediate subfolders
            subfolders = [f.path for f in os.scandir(parent_folder) if f.is_dir()]
            
            # Add new folders, avoiding duplicates
            added_count = 0
            for folder in subfolders:
                if folder not in self.stitcher_folders:
                    # Check if folder contains images
                    has_images = False
                    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.gif', '*.tiff', '*.tif', '*.psd', '*.pdf']:
                        if list(Path(folder).glob(ext)):
                            has_images = True
                            break
                    
                    if has_images:
                        self.stitcher_folders.append(folder)
                        added_count += 1
            
            if added_count > 0:
                self.log(f"Added {added_count} folders from parent folder", "INFO")
                # Update the folder list display
                self.update_stitcher_folder_list()
                
                # Update stitch button state
                self.update_stitch_button_state()
            else:
                self.log("No folders with images found in parent folder", "WARNING")
                self.show_message("No Image Folders", "No folders containing supported images were found in the selected parent folder.", QMessageBox.Icon.Warning)

    def clear_stitcher_folders(self):
        """Clear all selected folders"""
        if hasattr(self, 'stitcher_folders') and self.stitcher_folders:
            self.stitcher_folders = []
            self.update_stitcher_folder_list()
            self.update_stitch_button_state()
            # Update preview after clearing
            self.update_stitcher_preview()
            self.log("Cleared all folders from stitcher", "INFO")

    def set_stitcher_output_dir(self):
        """Set the output directory for stitched images"""
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory for Stitched Images")
        if output_dir:
            self.stitcher_output_dir = output_dir
            self.stitcher_output_dir_label.setText(f"📁 {self.stitcher_output_dir}")
            self.stitcher_output_dir_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
            self.update_stitch_button_state()
            self.log(f"Set stitcher output directory: {output_dir}", "INFO")

    def update_stitcher_folder_list(self):
        """Update the folder list display in the stitcher panel"""
        # Clear the folder container
        for i in reversed(range(self.stitcher_folder_container.layout().count())):
            widget = self.stitcher_folder_container.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Initialize folder checkboxes list
        if not hasattr(self, 'stitcher_folder_checkboxes'):
            self.stitcher_folder_checkboxes = []
        else:
            self.stitcher_folder_checkboxes = []
        
        # If no folders, show the placeholder
        if not hasattr(self, 'stitcher_folders') or not self.stitcher_folders:
            self.stitcher_folder_label = QLabel("No files or folders selected")
            self.stitcher_folder_label.setWordWrap(True)
            self.stitcher_folder_label.setStyleSheet("color: #888888; padding: 10px;")
            self.stitcher_folder_container.layout().addWidget(self.stitcher_folder_label)
        else:
            # Create a scroll area for the folder list
            folder_scroll = QScrollArea()
            folder_scroll.setWidgetResizable(True)
            folder_scroll.setFrameShape(QFrame.Shape.NoFrame)
            folder_scroll.setStyleSheet(f"""
                QScrollArea {{ border: none; background-color: transparent; }}
                QScrollBar:vertical {{ background-color: #252535; width: 10px; border-radius: 5px; }}
                QScrollBar::handle:vertical {{ background-color: #4d4d5f; border-radius: 5px; min-height: 20px; }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            """)
            
            # Create a widget to hold the folder list
            folder_list_widget = QWidget()
            folder_list_layout = QVBoxLayout(folder_list_widget)
            folder_list_layout.setContentsMargins(5, 5, 5, 5)
            folder_list_layout.setSpacing(10)
            
            # Add "Select All" checkbox
            select_all_layout = QHBoxLayout()
            self.stitcher_select_all = QCheckBox("Select All")
            self.stitcher_select_all.setChecked(True)
            self.stitcher_select_all.stateChanged.connect(self.toggle_stitcher_select_all)
            select_all_layout.addWidget(self.stitcher_select_all)
            
            # Add folder count label
            self.stitcher_folder_count_label = QLabel(f"Total: {len(self.stitcher_folders)} folders")
            self.stitcher_folder_count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            select_all_layout.addWidget(self.stitcher_folder_count_label, alignment=Qt.AlignmentFlag.AlignRight)
            
            folder_list_layout.addLayout(select_all_layout)
            
            # Add a separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
            folder_list_layout.addWidget(separator)
            
            # Add folders to the list
            for folder_path in self.stitcher_folders:
                folder_item = QFrame()
                folder_item.setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['panel']};
                        border-radius: 6px;
                        border: 2px solid {COLORS['border']};
                        padding: 0px;
                        margin: 3px 0px;
                        min-height: 70px;
                    }}
                """)
                folder_layout = QHBoxLayout(folder_item)
                folder_layout.setContentsMargins(0, 0, 0, 0)
                folder_layout.setSpacing(0)
                
                # Add checkbox with better styling
                checkbox_container = QWidget()
                checkbox_container.setFixedWidth(40)
                checkbox_container.setFixedHeight(70)
                checkbox_container.setStyleSheet("background-color: transparent; ")
                checkbox_layout = QVBoxLayout(checkbox_container)
                checkbox_layout.setContentsMargins(8, 0, 0, 0)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                checkbox = QCheckBox()
                checkbox.setChecked(True)
                checkbox.setFixedSize(24, 24)
                checkbox.folder_path = folder_path  # Store folder path in checkbox
                checkbox.stateChanged.connect(lambda state, path=folder_path: self.update_stitcher_preview(path) if state == Qt.CheckState.Checked else None)
                checkbox.stateChanged.connect(self.update_stitch_button_state)

                checkbox_layout.addWidget(checkbox)
                folder_layout.addWidget(checkbox_container)
                self.stitcher_folder_checkboxes.append(checkbox)
                
                # Add vertical separator
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.VLine)
                separator.setFixedWidth(2)
                separator.setStyleSheet(f"background-color: {COLORS['primary']}; border: none")
                folder_layout.addWidget(separator)
                
                # Get folder name and file info
                if folder_path.startswith("virtual:"):
                    folder_name = folder_path.split(":", 1)[1]
                    files = self.stitcher_files.get(folder_path, [])
                    file_count = len(files)
                    file_names = [os.path.basename(f) for f in files]
                else:
                    folder_name = os.path.basename(folder_path)
                    files = []
                    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.gif', '*.tiff', '*.tif', '*.psd', '*.pdf']:
                        files.extend(list(Path(folder_path).glob(ext)))
                    file_count = len(files)
                    file_names = [f.name for f in files]
                
                # Sort file names naturally
                file_names.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)])
                
                # Create info layout
                info_container = QWidget()
                info_container.setStyleSheet("background-color: transparent; border: none")
                info_layout = QVBoxLayout(info_container)
                info_layout.setContentsMargins(10, 8, 10, 8)
                info_layout.setSpacing(2)
                
                # Create compact info text
                truncated_files = file_names[:3]  # Show first 3 files
                files_text = ", ".join(truncated_files)
                if file_count > 3:
                    files_text += f"... [{file_count}]"
                
                # Format and direction
                format_text = self.stitcher_format_combo.currentText().lower()
                
                # Calculate input and output sizes in bytes
                input_size_bytes = 0
                output_size_bytes = 0
                
                try:
                    # Get actual files to process
                    actual_files = []
                    if folder_path.startswith("virtual:"):
                        actual_files = self.stitcher_files.get(folder_path, [])
                    else:
                        for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.gif', '*.tiff', '*.tif', '*.psd', '*.pdf']:
                            actual_files.extend([str(f) for f in Path(folder_path).glob(ext)])
                    
                    if actual_files:
                        # Sort files naturally
                        actual_files.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', os.path.basename(s))])
                        
                        # Calculate total input size in bytes
                        for file_path in actual_files:
                            try:
                                input_size_bytes += os.path.getsize(file_path)
                            except (OSError, FileNotFoundError):
                                continue
                        
                        # Get spacing value
                        spacing = 0
                        if hasattr(self, 'spacing_combo'):
                            spacing_text = self.spacing_combo.currentText()
                            spacing = int(spacing_text.replace("px", ""))
                        
                        # Check if manual spacing is enabled
                        if hasattr(self, 'manual_spacing_toggle') and self.manual_spacing_toggle.isChecked():
                            try:
                                spacing = int(self.manual_spacing_input.text())
                            except (ValueError, TypeError):
                                spacing = 0
                        
                        # Estimate output size based on format and spacing
                        # First, get average bytes per pixel for the input format
                        from PIL import Image
                        total_pixels = 0
                        total_bytes = 0
                        
                        # Sample up to 3 files for estimation
                        for file_path in actual_files[:3]:
                            try:
                                file_size = os.path.getsize(file_path)
                                with Image.open(file_path) as img:
                                    width, height = img.size
                                    pixels = width * height
                                    total_pixels += pixels
                                    total_bytes += file_size
                            except Exception:
                                continue
                        
                        # Calculate output size based on format compression ratio
                        if total_pixels > 0:
                            bytes_per_pixel = total_bytes / total_pixels
                            
                            # Adjust for output format
                            format_multipliers = {
                                'png': 1.2,  # PNG is lossless, might be larger
                                'jpg': 0.3,  # JPEG is lossy, smaller
                                'jpeg': 0.3,
                                'webp': 0.2,  # WebP is very efficient
                                'bmp': 3.0,   # BMP is uncompressed
                                'tiff': 1.5,  # TIFF can be large
                                'gif': 0.7    # GIF is limited in colors
                            }
                            
                            format_multiplier = format_multipliers.get(format_text.lower(), 1.0)
                            
                            # Adjust for spacing (positive or negative)
                            # Spacing affects the total number of pixels in the output
                            spacing_factor = 1.0
                            if spacing != 0:
                                # Estimate the effect of spacing on total pixels
                                if "Horizontal" in self.orientation_combo.currentText():
                                    spacing_pixels = spacing * (file_count - 1)
                                    spacing_factor = 1.0 + (spacing_pixels / total_pixels)
                                else:
                                    spacing_pixels = spacing * (file_count - 1)
                                    spacing_factor = 1.0 + (spacing_pixels / total_pixels)
                                
                                # Ensure factor is positive
                                spacing_factor = max(0.1, spacing_factor)
                            
                            # Calculate estimated output size
                            output_size_bytes = int(input_size_bytes * format_multiplier * spacing_factor)
                except Exception as e:
                    # If any error occurs, use input size as fallback
                    self.log(f"Error calculating sizes: {str(e)}", "ERROR")
                    output_size_bytes = input_size_bytes
                
                # Format sizes for display
                def format_size(size_bytes):
                    if size_bytes < 1024:
                        return f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        return f"{size_bytes/1024:.1f} KB"
                    else:
                        return f"{size_bytes/(1024*1024):.1f} MB"
                
                input_size_str = format_size(input_size_bytes)
                output_size_str = format_size(output_size_bytes)
                
                # Create the info text in the style of the image
                info_label = QLabel(f"Input : {files_text}\nOutput : {folder_name}_stitched.{format_text}\nInput Size :{input_size_str} → Output Size :{output_size_str}(approx.)")
                info_label.setStyleSheet("color: white; font-size: 10pt; font-weight: 500; font-family: 'Segoe UI', sans-serif;")
                info_label.setWordWrap(True)
                info_layout.addWidget(info_label)
                
                folder_layout.addWidget(info_container, 1)  # Give the info layout stretch
                
                # Add remove button
                remove_btn = QPushButton("×")
                remove_btn.setFixedSize(42, 42)
                remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                remove_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: white;
                        border: none;
                        font-weight: bold;
                        font-size: 26px;
                        margin-right: 20px;
                    }}
                    QPushButton:hover {{
                        color: #FF3B30;
                    }}
                """)
                remove_btn.clicked.connect(lambda checked, path=folder_path: self.remove_stitcher_folder(path))
                folder_layout.addWidget(remove_btn)
                
                folder_list_layout.addWidget(folder_item)
                
                # If this checkbox is checked, update the preview
                if checkbox.isChecked():
                    self.update_stitcher_preview(folder_path)
            
            # Add stretch to push items to the top
            folder_list_layout.addStretch()
            
            # Set the folder list widget as the scroll area's widget
            folder_scroll.setWidget(folder_list_widget)
            
            # Add the scroll area to the folder container
            self.stitcher_folder_container.layout().addWidget(folder_scroll)            

    def toggle_stitcher_select_all(self, state):
        """Toggle all folder checkboxes based on the Select All checkbox state"""
        if hasattr(self, 'stitcher_folder_checkboxes'):
            # Create a copy of the list to avoid issues with deleted objects
            for checkbox in list(self.stitcher_folder_checkboxes):
                # Check if the checkbox is still valid
                try:
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
                except RuntimeError:
                    # Remove invalid checkboxes from the list
                    if checkbox in self.stitcher_folder_checkboxes:
                        self.stitcher_folder_checkboxes.remove(checkbox)
        
        # Update stitch button state
        self.update_stitch_button_state()

    def remove_stitcher_folder(self, folder_path):
        """Remove a folder from the stitcher list"""
        if folder_path in self.stitcher_folders:
            self.stitcher_folders.remove(folder_path)
            
            # If it's a virtual folder, also remove its files
            if folder_path.startswith("virtual:") and hasattr(self, 'stitcher_files'):
                if folder_path in self.stitcher_files:
                    del self.stitcher_files[folder_path]
            
            self.update_stitcher_folder_list()
            self.update_stitch_button_state()
            # Update preview after removing folder
            self.update_stitcher_preview()
            self.log(f"Removed folder: {folder_path}", "INFO")

    def stitcher_dragEnterEvent(self, event):
        """Handle drag enter event for the stitcher folder container"""
        if event.mimeData().hasUrls():
            # Store original style
            if not hasattr(self, 'stitcher_original_folder_container_style'):
                self.stitcher_original_folder_container_style = self.stitcher_folder_container.styleSheet()
            
            # Change style for drop indication
            self.stitcher_folder_container.setStyleSheet(f"background-color: {COLORS['hover']}; border-radius: 8px; border: 2px dashed white;")
            
            # Store original widgets
            self.stitcher_original_widgets = []
            for i in range(self.stitcher_folder_container.layout().count()):
                widget = self.stitcher_folder_container.layout().itemAt(i).widget()
                if widget:
                    self.stitcher_original_widgets.append(widget)
                    widget.setParent(None)
            
            # Create drop indicator
            self.stitcher_drop_indicator_label = QLabel("Drop Folders Here")
            self.stitcher_drop_indicator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stitcher_drop_indicator_label.setStyleSheet(f"""
                color: {COLORS['text']};
                font-size: 18px;
                font-weight: bold;
                background-color: {COLORS['primary']};
                padding: 15px;
                border-radius: 8px;
                opacity: 0.8;
            """)
            
            self.stitcher_folder_container.layout().addWidget(self.stitcher_drop_indicator_label, alignment=Qt.AlignmentFlag.AlignCenter)
            event.accept()
        else:
            event.ignore()

    def stitcher_dragLeaveEvent(self, event):
        """Handle drag leave event for the stitcher folder container"""
        # Restore original style
        if hasattr(self, 'stitcher_original_folder_container_style'):
            self.stitcher_folder_container.setStyleSheet(self.stitcher_original_folder_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'stitcher_drop_indicator_label') and self.stitcher_drop_indicator_label:
            self.stitcher_drop_indicator_label.setParent(None)
            self.stitcher_drop_indicator_label = None
        
        # Clear current layout
        while self.stitcher_folder_container.layout().count():
            item = self.stitcher_folder_container.layout().takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Restore original widgets
        if hasattr(self, 'stitcher_original_widgets') and self.stitcher_original_widgets:
            for widget in self.stitcher_original_widgets:
                self.stitcher_folder_container.layout().addWidget(widget)
            self.stitcher_original_widgets = []
        
        event.accept()

    def stitcher_dragMoveEvent(self, event):
        """Handle drag move event for the stitcher folder container"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def stitcher_dropEvent(self, event):
        """Handle drop event for the stitcher folder container"""
        # Restore original style
        if hasattr(self, 'stitcher_original_folder_container_style'):
            self.stitcher_folder_container.setStyleSheet(self.stitcher_original_folder_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'stitcher_drop_indicator_label') and self.stitcher_drop_indicator_label:
            self.stitcher_drop_indicator_label.setParent(None)
            self.stitcher_drop_indicator_label = None
        
        # Restore original widgets
        if hasattr(self, 'stitcher_original_widgets') and self.stitcher_original_widgets:
            for widget in self.stitcher_original_widgets:
                self.stitcher_folder_container.layout().addWidget(widget)
            self.stitcher_original_widgets = []
        
        # Initialize stitcher_folders list if it doesn't exist
        if not hasattr(self, 'stitcher_folders'):
            self.stitcher_folders = []
            
        # Initialize stitcher_files dictionary if it doesn't exist
        if not hasattr(self, 'stitcher_files'):
            self.stitcher_files = {}
        
        if event.mimeData().hasUrls():
            # Process dropped URLs
            urls = event.mimeData().urls()
            
            # Separate folders and files
            folders = []
            files = []
            
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):
                    folders.append(path)
                elif os.path.isfile(path) and any(path.lower().endswith(f".{fmt.lower()}") for fmt in 
                                                ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "psd", "pdf"]):
                    files.append(path)
            
            # Process folders
            added_folders = 0
            for folder in folders:
                # Check if it's a parent folder with subfolders
                subfolders = [f.path for f in os.scandir(folder) if f.is_dir()]
                
                if subfolders:
                    # It's a parent folder, add all subfolders that contain images
                    for subfolder in subfolders:
                        # Check if subfolder contains images
                        has_images = False
                        for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.gif', '*.tiff', '*.tif', '*.psd', '*.pdf']:
                            if list(Path(subfolder).glob(ext)):
                                has_images = True
                                break
                        
                        if has_images and subfolder not in self.stitcher_folders:
                            self.stitcher_folders.append(subfolder)
                            added_folders += 1
                else:
                    # It's a regular folder, check if it contains images
                    has_images = False
                    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.gif', '*.tiff', '*.tif', '*.psd', '*.pdf']:
                        if list(Path(folder).glob(ext)):
                            has_images = True
                            break
                    
                    if has_images and folder not in self.stitcher_folders:
                        self.stitcher_folders.append(folder)
                        added_folders += 1
            
            # Process files - group them by common prefixes
            if files:
                # Group files by common prefixes using regex pattern matching
                file_groups = {}
                
                for file_path in files:
                    filename = os.path.basename(file_path)
                    # Try to match patterns like "26_1", "26_2" or "image_01", "image_02"
                    match = re.match(r'(.+?)[-_]?\d+', filename)
                    if match:
                        prefix = match.group(1)
                    else:
                        # If no pattern, use the first part of the filename
                        prefix = os.path.splitext(filename)[0]
                    
                    if prefix not in file_groups:
                        file_groups[prefix] = []
                    file_groups[prefix].append(file_path)
                
                # Create virtual folders for each group
                for prefix, group_files in file_groups.items():
                    # Create a unique virtual folder name
                    folder_name = f"{prefix} Group {len(self.stitcher_folders) + 1}"
                    virtual_folder = f"virtual:{folder_name}"
                    
                    # Add to stitcher folders and files
                    if virtual_folder not in self.stitcher_folders:
                        self.stitcher_folders.append(virtual_folder)
                        self.stitcher_files[virtual_folder] = group_files
                        self.log(f"Added {len(group_files)} files as '{folder_name}'", "INFO")
            
            # Update UI
            if added_folders > 0 or files:
                self.update_stitcher_folder_list()
                self.update_stitch_button_state()
                self.log(f"Added {added_folders} folders and {len(files)} files via drag and drop", "INFO")
            else:
                self.log("No valid folders or files found in dropped items", "WARNING")
            
            event.accept()
        else:
            event.ignore()

    def update_stitch_button_state(self):
        """Update the state of the stitch button based on selected folders and output directory"""
        if not hasattr(self, 'stitch_btn'):
            return
            
        # Check if we have folders and an output directory
        has_folders = hasattr(self, 'stitcher_folders') and len(self.stitcher_folders) > 0
        has_output = hasattr(self, 'stitcher_output_dir') and self.stitcher_output_dir
        
        # Check if at least one folder is selected via checkbox
        folders_selected = False
        if hasattr(self, 'stitcher_folder_checkboxes'):
            for checkbox in self.stitcher_folder_checkboxes:
                if checkbox.isChecked():
                    folders_selected = True
                    break
        
        # Make sure all values are boolean before passing to setEnabled
        enable_button = bool(has_folders) and bool(folders_selected) and bool(has_output)
        
        # Enable button if we have folders, at least one is selected, and we have an output directory
        self.stitch_btn.setEnabled(enable_button)

    def start_stitching(self):
        """Start the image stitching process"""
        # Get selected folders
        selected_folders = []
        selected_files = {}
        
        for checkbox in self.stitcher_folder_checkboxes:
            if checkbox.isChecked():
                folder_path = checkbox.folder_path
                selected_folders.append(folder_path)
                
                # If it's a virtual folder, add its files to the selected_files dict
                if folder_path.startswith("virtual:") and hasattr(self, 'stitcher_files'):
                    selected_files[folder_path] = self.stitcher_files.get(folder_path, [])
        
        if not selected_folders:
            self.show_message("No Selections", "Please select at least one folder or file group to stitch.", QMessageBox.Icon.Warning)
            return
        
                # Check if this is a repeated stitching to the same output folder
        should_continue = True
        if hasattr(self, 'last_stitcher_output_dir') and self.last_stitcher_output_dir == self.stitcher_output_dir:
            # Show warning about potential file overwriting
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Warning: Same Output Folder")
            msg_box.setText("You are using the same output folder as your previous stitching.")
            msg_box.setInformativeText("This might overwrite existing files. Do you want to continue?")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            
            # Add buttons
            continue_btn = msg_box.addButton("Continue", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            change_folder_btn = msg_box.addButton("📂 Change Folder", QMessageBox.ButtonRole.ActionRole)
            
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
                    min-width: 150px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['hover']};
                }}
            """)
            
            # Execute the dialog
            msg_box.exec()
            
            # Handle user's choice
            clicked_button = msg_box.clickedButton()
            if clicked_button == cancel_btn:
                should_continue = False
                self.stitch_btn.setText("🧵 Stitch Images")
                self.stitch_btn.setEnabled(True)
                return
            elif clicked_button == change_folder_btn:
                # Open folder selection dialog
                self.set_stitcher_output_dir()
                # Check if user actually selected a new folder
                if not hasattr(self, 'stitcher_output_dir') or self.stitcher_output_dir == self.last_stitcher_output_dir:
                    self.stitch_btn.setText("🧵 Stitch Images")
                    self.stitch_btn.setEnabled(True)
                    return
        
        # Store current output dir for future reference
        self.last_stitcher_output_dir = self.stitcher_output_dir

        # Check if output directory is set
        if not hasattr(self, 'stitcher_output_dir') or not self.stitcher_output_dir:
            self.show_message("No Output Directory", "Please select an output directory for the stitched images.", QMessageBox.Icon.Warning)
            return
        
        # Get stitching options
        orientation_text = self.orientation_combo.currentText()
        is_vertical = "Vertical" in orientation_text
        reverse_order = "Bottom to Top" in orientation_text or "Right to Left" in orientation_text
        
        # Get spacing value - check if manual spacing is enabled
        if hasattr(self, 'manual_spacing_toggle') and self.manual_spacing_toggle.isChecked():
            # Use manual spacing value
            try:
                spacing = int(self.manual_spacing_input.text())
            except (ValueError, TypeError):
                # If invalid value, default to 0
                spacing = 0
        else:
            # Use dropdown spacing value
            spacing_text = self.spacing_combo.currentText()
            spacing = int(spacing_text.replace("px", ""))
        
        output_format = self.stitcher_format_combo.currentText()
        alignment = self.stitcher_alignment_combo.currentText()
        bg_color = self.stitcher_bg_color_combo.currentText()
        resize_option = self.stitcher_resize_combo.currentText()

        self.stitch_btn.setText("Stitching...")
        self.stitch_btn.setEnabled(False)
        
        # Create progress dialog
        self.stitcher_progress_dialog = QDialog(self)
        self.stitcher_progress_dialog.setWindowTitle("Stitching Images")
        self.stitcher_progress_dialog.setFixedSize(400, 200)
        self.stitcher_progress_dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Progress dialog layout
        progress_layout = QVBoxLayout(self.stitcher_progress_dialog)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        progress_layout.setSpacing(10)
        
        # Add progress bar
        self.stitcher_progress_bar = QProgressBar()
        self.stitcher_progress_bar.setRange(0, len(selected_folders))
        self.stitcher_progress_bar.setValue(0)
        self.stitcher_progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid {COLORS['border']};
                    border-radius: 5px;
                    background-color: {COLORS['panel']};
                    height: 20px;
                    text-align: center;
                    padding: 0px;
                }}
                QProgressBar::chunk {{
                    background-color: {COLORS['primary']};
                    border-radius: 4px;
                    margin: 1px;
                    border: 1px solid {COLORS['primary']};
                    min-width: 10px;
                }}
        """)
        progress_layout.addWidget(self.stitcher_progress_bar)
        
        # Add status labels
        self.stitcher_status_label = QLabel("Progress: 0%")
        self.stitcher_status_label.setStyleSheet(f"color: {COLORS['text']};")
        progress_layout.addWidget(self.stitcher_status_label)
        
        self.stitcher_folder_label = QLabel("Preparing...")
        self.stitcher_folder_label.setStyleSheet(f"color: {COLORS['text']};")
        progress_layout.addWidget(self.stitcher_folder_label)
        
        # Add cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['error']};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['error_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.stop_stitching)
        progress_layout.addWidget(cancel_btn)
        
        # Create and start the stitcher thread
        self.stitcher_thread = StitcherThread(
            selected_folders,
            self.stitcher_output_dir,
            is_vertical,
            spacing,
            output_format,
            virtual_files=selected_files,
            alignment=alignment,
            bg_color=bg_color,
            resize_option=resize_option,
            reverse_order=reverse_order
        )
        
        # Connect signals
        self.stitcher_thread.progress_signal.connect(self.update_stitcher_progress)
        self.stitcher_thread.finished_signal.connect(self.stitching_finished)
        self.stitcher_thread.error_signal.connect(self.stitching_error)
        
        # Start thread and show dialog
        self.stitcher_thread.start()
        self.stitcher_progress_dialog.exec()

    def update_stitcher_preview(self, folder_path=None):
        """Update the preview of stitched images"""
        if not hasattr(self, 'stitcher_preview_label'):
            return
            
        # Clear the preview container
        self.stitcher_preview_label.setText("")
        
        # If no folder is selected or no folders exist, show default message
        if folder_path is None or not hasattr(self, 'stitcher_folders') or not self.stitcher_folders:
            self.stitcher_preview_label.setText("No folders/files selected for stitching")
            return
            
        # Get the files to preview
        files_to_preview = []
        if folder_path.startswith("virtual:"):
            # For virtual folders, use the stored files
            files_to_preview = self.stitcher_files.get(folder_path, [])[:5]  # Preview first 5 files
        else:
            # For real folders, get image files
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
                files = list(Path(folder_path).glob(ext))
                files_to_preview.extend([str(f) for f in files])
                if len(files_to_preview) >= 5:  # Limit to 5 files for preview
                    files_to_preview = files_to_preview[:5]
                    break
        
        if not files_to_preview:
            self.stitcher_preview_label.setText("No images found for preview")
            return
            
        try:
            # Create a preview of the first few images
            folder_name = os.path.basename(folder_path) if not folder_path.startswith('virtual:') else folder_path.split(':', 1)[1]
            preview_text = f"<h3>Preview of {folder_name}</h3>"
            
            # Show files that will be stitched
            preview_text += "<p><b>Files to be stitched:</b></p>"
            preview_text += "<ul>"
            for f in files_to_preview:
                preview_text += f"<li>{os.path.basename(f)}</li>"
            
            if len(files_to_preview) < len(self.stitcher_files.get(folder_path, [])) if folder_path.startswith("virtual:") else True:
                preview_text += "<li>...</li>"
            preview_text += "</ul>"
            
            # Show stitch direction
            orientation = self.orientation_combo.currentText()
            preview_text += f"<p><b>Stitch direction:</b> {orientation}</p>"
            
            # Show spacing
            spacing_text = self.spacing_combo.currentText()
            preview_text += f"<p><b>Spacing:</b> {spacing_text}</p>"
            
            # Show output format
            output_format = self.stitcher_format_combo.currentText()
            preview_text += f"<p><b>Output format:</b> {output_format}</p>"
            
            # Show output directory
            output_dir = getattr(self, 'stitcher_output_dir', 'Not set')
            preview_text += f"<p><b>Output directory:</b> {output_dir}</p>"
            
            self.stitcher_preview_label.setText(preview_text)
            self.stitcher_preview_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
            self.stitcher_preview_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            
        except Exception as e:
            self.stitcher_preview_label.setText(f"Error generating preview: {str(e)}")
            self.log(f"Preview error: {str(e)}", "ERROR")

    def update_stitcher_progress(self, value, folder_name):
        """Update the stitcher progress dialog"""
        if hasattr(self, 'stitcher_progress_dialog') and self.stitcher_progress_dialog:
            self.stitcher_progress_bar.setValue(value)
            
            # Calculate percentage
            total = self.stitcher_progress_bar.maximum()
            percent = int((value / total) * 100) if total > 0 else 0
            
            # Update status labels
            self.stitcher_status_label.setText(f"Progress: {percent}% ({value}/{total} folders)")
            self.stitcher_folder_label.setText(f"Stitching folder: {folder_name}")

    def stitching_finished(self, success_count, error_count, output_dir):
        """Handle completion of the stitching process"""
        # Close the progress dialog
        if hasattr(self, 'stitcher_progress_dialog') and self.stitcher_progress_dialog:
            self.stitcher_progress_dialog.close()
        
        # Show completion message
        message = f"Stitching completed!\n\n{success_count} folders successfully stitched."
        if error_count > 0:
            message += f"\n{error_count} folders failed."
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Stitching Completed")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Information)
        
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
                min-width: 120px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        
        # Add buttons
        open_btn = msg_box.addButton("📂 Open Output Folder", QMessageBox.ButtonRole.ActionRole)
        open_btn.setStyleSheet(f"""
            background-color: {COLORS['primary']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-width: 150px;
        """)
        
        close_btn = msg_box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        close_btn.setStyleSheet(f"""
            background-color: {COLORS['secondary']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-width: 150px;
        """)
        
        # Log completion with appropriate status
        if error_count == 0:
            self.log(f"Stitching completed successfully: {success_count} images created", "SUCCESS")
        else:
            self.log(f"Stitching completed with issues: {success_count} succeeded, {error_count} failed", "WARNING")
        
        # Show dialog and handle response
        msg_box.exec()
        
        # Handle button clicks
        if msg_box.clickedButton() == open_btn:
            # Open the output folder
            if os.path.exists(output_dir):
                QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))

        self.stitch_btn.setText("🧵 Stitch Images")
        self.stitch_btn.setEnabled(True)        

    def stitching_error(self, error_message):
        """Handle errors from the stitcher thread"""
        self.log(f"Stitching error: {error_message}", "ERROR")

    def stop_stitching(self):
        """Stop the stitching process when user cancels"""
        if hasattr(self, 'stitcher_thread') and self.stitcher_thread:
            self.stitcher_thread.running = False
            self.stitcher_thread.wait(1000)  # Wait for thread to finish cleanly
            self.log("Stitching process cancelled by user", "WARNING")
            
            # Close the progress dialog
            if hasattr(self, 'stitcher_progress_dialog') and self.stitcher_progress_dialog:
                self.stitcher_progress_dialog.close()     

            self.stitch_btn.setText("🧵 Stitch Images")
            self.stitch_btn.setEnabled(True)         

