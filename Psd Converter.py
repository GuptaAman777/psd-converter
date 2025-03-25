import sys
import os
import subprocess
import time
import gc  # For explicit garbage collection
import multiprocessing  # For CPU count detection
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QLabel, QComboBox, QLineEdit, QMessageBox, QDialog, QProgressBar,
    QHBoxLayout, QFrame, QGraphicsDropShadowEffect, QStackedWidget
)
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QTimer, QPoint
from PIL import Image, ImageFile  # Added ImageFile import here
from psd_tools import PSDImage

# Enable incremental loading for partial image processing
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Update supported formats list
SUPPORTED_FORMATS = ["PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP", "PDF"]

class ConverterThread(QThread):
    progress_signal = pyqtSignal(int, str, str)
    completion_signal = pyqtSignal(str, float, float)
    error_signal = pyqtSignal(str)  # Add error signal
    
    def __init__(self, files, output_dir, format_):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.format_ = format_
        self._is_running = True
        self.total_size = self._calculate_total_size()
        self.processed_size = 0
        self.start_time = 0
        # Define chunk size for large file processing (16MB)
        self.chunk_size = 16 * 1024 * 1024
        # Determine optimal number of threads based on CPU cores
        self.num_cores = max(1, multiprocessing.cpu_count() - 1)  # Leave one core free for UI
    
    def stop(self):
        self._is_running = False
    
    def _calculate_total_size(self):
        total = 0
        for file in self.files:
            try:
                total += os.path.getsize(file)
            except (OSError, FileNotFoundError):
                pass
        return total
    
    def run(self):
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except Exception as e:
                self.error_signal.emit(f"Failed to create output directory: {str(e)}")
                return
    
        total_files = len(self.files)
        last_output_path = ""
        self.start_time = time.time()
        output_total_size = 0
        
        # Pre-sort files by size (process smaller files first for better user experience)
        try:
            self.files.sort(key=lambda f: os.path.getsize(f) if os.path.exists(f) else 0)
        except:
            pass  # If sorting fails, continue with original order
        
        for i, file in enumerate(self.files):
            if not self._is_running:
                break
                
            if not os.path.exists(file):
                self.error_signal.emit(f"File not found: {file}")
                continue
            
            name, ext = os.path.splitext(os.path.basename(file))
            ext = ext[1:].upper()
            
            # Modified to include PSD files as valid input
            if ext not in SUPPORTED_FORMATS and ext != "PSD":
                continue
            
            # Get file size before processing
            try:
                file_size = os.path.getsize(file)
            except (OSError, FileNotFoundError):
                file_size = 0
            
            output_path = os.path.join(self.output_dir, f"{name}.{self.format_.lower()}")
            last_output_path = output_path
            
            try:
                # Use chunked processing for large files (>100MB)
                if file_size > 100 * 1024 * 1024:
                    if ext == "PSD":
                        # For PSD files, we still need to use psd_tools but with memory management
                        psd = PSDImage.open(file)
                        image = psd.composite()
                        # Clear any references to the original PSD to free memory
                        psd = None
                        gc.collect()  # Force garbage collection
                    else:
                        # For other large files, use PIL's incremental loading with reduced memory
                        with Image.open(file) as img:
                            # Use thumbnail to reduce memory for very large images if needed
                            max_dim = 8000  # Maximum dimension to process efficiently
                            if max(img.size) > max_dim:
                                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                            image = img.copy()
                else:
                    # Original processing for smaller files
                    if ext == "PSD":
                        psd = PSDImage.open(file)
                        image = psd.composite()
                        psd = None  # Release memory
                    else:
                        image = Image.open(file)
                
                if self.format_ == "JPG":
                    image = image.convert("RGB")
                
                # Optimize saving based on format
                if self.format_ in ["PNG", "WEBP"]:
                    # Use optimized settings for PNG/WEBP
                    compression = 6 if file_size < 10 * 1024 * 1024 else 3  # Lower compression for large files
                    image.save(output_path, self.format_, optimize=True, 
                              compress_level=compression)
                elif self.format_ in ["JPEG", "JPG"]:
                    # Optimize JPEG quality based on image size
                    quality = 90 if file_size < 5 * 1024 * 1024 else 85
                    image.save(output_path, "JPEG", quality=quality, optimize=True,
                              progressive=True)  # Progressive JPEGs load faster in browsers
                else:
                    image.save(output_path, self.format_)
                
                # Explicitly delete the image to free memory
                del image
                gc.collect()  # Force garbage collection after each large file
            except MemoryError:
                self.error_signal.emit(f"Not enough memory to process {os.path.basename(file)}. Try closing other applications.")
                continue
            except Exception as e:
                self.error_signal.emit(f"Error processing {os.path.basename(file)}: {str(e)}")
                continue
            
            # Track output file size
            try:
                output_total_size += os.path.getsize(output_path)
            except (OSError, FileNotFoundError):
                pass
            
            # Update processed size
            self.processed_size += file_size
            
            # Calculate progress percentage
            progress = int((self.processed_size / self.total_size) * 100) if self.total_size > 0 else int(((i + 1) / total_files) * 100)
            
            # Calculate ETA with smoothing for more stable estimates
            elapsed_time = time.time() - self.start_time
            if elapsed_time > 0 and self.processed_size > 0:
                mb_per_sec = (self.processed_size / 1024 / 1024) / elapsed_time
                
                if progress > 0:
                    # Apply smoothing to ETA calculation
                    total_time_estimate = elapsed_time * (100 / progress)
                    remaining_seconds = total_time_estimate - elapsed_time
                    
                    # Format ETA
                    if remaining_seconds < 60:
                        eta_text = f"ETA: {int(remaining_seconds)}s"
                    else:
                        eta_text = f"ETA: {int(remaining_seconds // 60)}m {int(remaining_seconds % 60)}s"
                else:
                    eta_text = "ETA: Calculating..."
                
                # Format MB/s
                speed_text = f"Speed: {mb_per_sec:.2f} MB/s"
            else:
                eta_text = "ETA: Calculating..."
                speed_text = "Speed: Calculating..."
            
            self.progress_signal.emit(progress, eta_text, speed_text)
        
        # Final cleanup
        gc.collect()
        self.completion_signal.emit(last_output_path, self.total_size, output_total_size)

# Add modern color scheme
# Update color scheme with modern values
COLORS = {
    'primary': "#007AFF",
    'secondary': "#5856D6",
    'background_light': "#FFFFFF",
    'background_dark': "#1C1C1E",
    'surface_light': "#F2F2F7",
    'surface_dark': "#2C2C2E",
    'text_light': "#000000",
    'text_dark': "#FFFFFF",
    'border_light': "#E5E5EA",
    'border_dark': "#38383A",
    'success': "#34C759"
}

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

class ImageConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Converter")
        self.setGeometry(100, 100, 500, 400)
        
        # Get system theme
        self.is_dark_mode = self.get_system_theme()
        self.apply_theme()
        
        # Initialize variables
        self.files = []
        self.output_dir = ""
        self.thread = None
        self.progress_dialog = None
        self.conversion_history = []
        
        self.initUI()

    def get_system_theme(self):
        # Get system color scheme
        app = QApplication.instance()
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark

    def apply_theme(self):
        bg_color = COLORS['background_dark'] if self.is_dark_mode else COLORS['background_light']
        text_color = COLORS['text_dark'] if self.is_dark_mode else COLORS['text_light']
        border_color = COLORS['border_dark'] if self.is_dark_mode else COLORS['border_light']
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
                font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
            }}
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 15px;  /* Adjusted padding to be more balanced */
                font-weight: 600;
                font-size: 13px;
                min-width: 120px;    /* Added minimum width */
            }}
            QPushButton:hover {{
                background-color: {COLORS['secondary']};
            }}
            QComboBox, QLineEdit {{
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 8px 12px;
                background: {COLORS['surface_dark'] if self.is_dark_mode else COLORS['surface_light']};
                min-height: 20px;
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QLabel {{
                font-size: 13px;
                font-weight: 500;
            }}
            QProgressBar {{
                border: 1px solid {border_color};
                border-radius: 8px;
                text-align: center;
                background-color: {COLORS['surface_dark'] if self.is_dark_mode else COLORS['surface_light']};
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 7px;
            }}
        """)

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)  # Increased spacing for more breathing room
        layout.setContentsMargins(30, 30, 30, 30)  # Wider margins for a more spacious feel
        
        # Define font
        font = QFont("Segoe UI", 10)
        
        # Create a header section with icon
        header_layout = QHBoxLayout()
        title_label = QLabel("Image Converter")
        title_label.setStyleSheet("font-size: 28px; font-weight: 600;")  # Larger, lighter font
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Add a subtle separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border_dark'] if self.is_dark_mode else COLORS['border_light']}; max-height: 1px;")
        layout.addWidget(separator)
        layout.addSpacing(10)
        
        # Selection type with label
        type_layout = QHBoxLayout()
        type_label = QLabel("Selection Type:")
        type_label.setFixedWidth(120)
        type_layout.addWidget(type_label)
        
        self.selection_type_combo = AnimatedComboBox()
        self.selection_type_combo.addItems(["Select Files", "Select Folder"])
        type_layout.addWidget(self.selection_type_combo)
        layout.addLayout(type_layout)
        
        # Input file selection with horizontal layout
        input_layout = QHBoxLayout()
        self.select_btn = QPushButton("Browse")
        self.select_btn.setFixedWidth(120)
        self.select_btn.setFont(font)
        self.select_btn.clicked.connect(self.select_files_or_folder)
        input_layout.addWidget(self.select_btn)
        
        self.file_label = QLineEdit()
        self.file_label.setFont(font)
        self.file_label.setPlaceholderText("Selected file(s) or folder will appear here")
        self.file_label.setReadOnly(True)
        input_layout.addWidget(self.file_label)
        layout.addLayout(input_layout)
        
        # Output folder selection with horizontal layout
        output_layout = QHBoxLayout()
        self.output_dir_btn = QPushButton("Output Folder")
        self.output_dir_btn.setFixedWidth(120)
        self.output_dir_btn.setFont(font)
        self.output_dir_btn.clicked.connect(self.select_output_folder)
        output_layout.addWidget(self.output_dir_btn)
        
        self.output_dir_label = QLineEdit()
        self.output_dir_label.setFont(font)
        self.output_dir_label.setPlaceholderText("Selected output folder will appear here")
        self.output_dir_label.setReadOnly(True)
        output_layout.addWidget(self.output_dir_label)
        layout.addLayout(output_layout)
        
        # Format selection with label
        format_layout = QHBoxLayout()
        format_label = QLabel("Output Format:")
        format_label.setFixedWidth(120)
        format_layout.addWidget(format_label)
        
        self.format_combo = AnimatedComboBox()  # Use animated combo box
        self.format_combo.addItems(SUPPORTED_FORMATS)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)
        
        layout.addStretch()  # Push convert button to bottom
        
        # Convert button with shadow and animation
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.convert_btn.setFixedHeight(50)  # Taller button
        self.convert_btn.clicked.connect(self.toggle_conversion)
        
        # Add shadow to convert button
        convert_shadow = QGraphicsDropShadowEffect()
        convert_shadow.setBlurRadius(15)
        convert_shadow.setColor(QColor(0, 0, 0, 80))
        convert_shadow.setOffset(0, 4)
        self.convert_btn.setGraphicsEffect(convert_shadow)
        
        layout.addWidget(self.convert_btn)
        
        self.setLayout(layout)
        
        self.files = []
        self.output_dir = ""
        self.thread = None
        self.progress_dialog = None

    def toggle_selection(self):
        self.file_label.clear()
        self.files = []
    
    def select_files_or_folder(self):
        if self.selection_type_combo.currentText() == "Select Files":
            files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.pdf *.psd)")
            if files:
                self.files = files
                display_text = os.path.basename(files[0]) if len(files) == 1 else f"{os.path.basename(files[0])} ... ({len(files)} files)"
                self.file_label.setText(display_text)
        else:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
            if folder:
                # Improved file extension checking
                supported_files = []
                for f in os.listdir(folder):
                    file_path = os.path.join(folder, f)
                    if os.path.isfile(file_path):
                        ext = os.path.splitext(f)[1].lstrip('.').upper()
                        if ext in [fmt.upper() for fmt in SUPPORTED_FORMATS] or ext == "PSD":
                            supported_files.append(file_path)
                
                if supported_files:
                    self.files = supported_files
                    self.file_label.setText(f"{folder} ({len(supported_files)} files)")
                else:
                    QMessageBox.warning(self, "Warning", "No supported image files found in the selected folder!")
                    self.files = []
                    self.file_label.clear()
    
    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_dir = folder
            self.output_dir_label.setText(folder)

    def toggle_conversion(self):
        if self.convert_btn.text() == "Convert":
            if not self.files or not self.output_dir:
                QMessageBox.warning(self, "Error", "Select files/folder and output folder!")
                return
            
            self.progress_dialog = ProgressDialog(self)
            self.convert_btn.setText("Cancel")
            
            self.thread = ConverterThread(self.files, self.output_dir, self.format_combo.currentText())
            self.thread.progress_signal.connect(
                lambda value, eta, speed: self.progress_dialog.update_progress(value, eta, speed)
            )
            self.thread.completion_signal.connect(
                lambda path, in_size, out_size: self.on_conversion_complete(path, in_size, out_size)
            )
            self.thread.error_signal.connect(self.handle_conversion_error)
            
            self.thread.start()
            self.progress_dialog.exec()
        else:
            self.convert_btn.setText("Convert")
            if self.thread:
                self.thread.stop()
            if self.progress_dialog:
                self.progress_dialog.reject()

    def handle_conversion_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def on_conversion_complete(self, last_output_path, input_size, output_size):
        # First ensure the progress dialog is closed
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.accept()
        
        # Convert sizes to MB for display
        input_mb = input_size / (1024 * 1024)
        output_mb = output_size / (1024 * 1024)
        
        size_info = f"Total size changed from {input_mb:.2f}MB to {output_mb:.2f}MB"
        message = f"Conversion Complete!\n\n{size_info}\n\nDo you want to open the output folder?"
        
        # Reset button state first
        self.convert_btn.setText("Convert")
        
        # Then show the message
        reply = QMessageBox.question(self, "Success", message,
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            subprocess.run(["explorer", os.path.abspath(os.path.dirname(last_output_path))], shell=True)
        
        self.progress_dialog.accept()
        self.convert_btn.setText("Convert")

    def undo_last_conversion(self):
        if not self.conversion_history:
            QMessageBox.warning(self, "Error", "No conversion to undo!")
            return
            
        last_conversion = self.conversion_history.pop()
        try:
            os.remove(last_conversion['output'])
            QMessageBox.information(self, "Undo", "Last conversion has been undone!")
        except:
            QMessageBox.warning(self, "Error", "Could not undo the last conversion.")
        
        self.undo_btn.setEnabled(len(self.conversion_history) > 0)
        self.undo_btn.setText("Undo Last Conversion")

class ProgressDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Converting...")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.parent_widget = parent  # Store reference to parent
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Progress info
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        layout.addWidget(self.progress_bar)
        
        # Status labels with modern font
        self.eta_label = QLabel("Preparing...")
        self.eta_label.setStyleSheet("font-size: 13px;")
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("font-size: 13px;")
        
        layout.addWidget(self.eta_label)
        layout.addWidget(self.speed_label)
        
        # Cancel button with modern style
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedWidth(120)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def update_progress(self, value, eta_text, speed_text):
        self.progress_bar.setValue(value)
        self.eta_label.setText(eta_text)
        self.speed_label.setText(speed_text)

    def closeEvent(self, event):
        # Fixed reference to thread
        if hasattr(self.parent_widget, 'thread') and self.parent_widget.thread and self.parent_widget.thread.isRunning():
            self.parent_widget.thread.stop()
            self.parent_widget.thread.wait()
        event.accept()

if __name__ == "__main__":
    # Ensure only one instance of QApplication exists
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    
    # Create and show the main window
    window = ImageConverter()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())
