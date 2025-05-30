import sys, os, subprocess, time, gc, re
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QLabel, QComboBox, QLineEdit, QMessageBox, QDialog, QProgressBar,
    QHBoxLayout, QFrame, QGraphicsDropShadowEffect, QStackedWidget, QScrollArea, QCheckBox, QGridLayout, QTabWidget, QGroupBox, QSizePolicy, QTextEdit, QMenu
)
from PyQt6.QtGui import QFont, QColor, QIcon, QDesktopServices, QIntValidator
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QTimer, QPoint, QRect, QUrl
from PIL import Image, ImageFile
from psd_tools import PSDImage

# Try to import PDF-specific libraries
try:
    import fitz  # PyMuPDF
    PDF_CONVERTER = "pymupdf"
except ImportError:
    PDF_CONVERTER = None

# Update SUPPORTED_FORMATS
INPUT_FORMATS = ["PNG", "JPEG", "JPG", "BMP", "GIF", "TIFF", "WEBP", "PDF", "PSD"]
OUTPUT_FORMATS = ["PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP", "PDF"]
UPSCALE_FORMATS = ["PNG", "JPEG", "JPG", "WEBP"] 
DENOISE_FORMATS = ["PNG", "JPEG", "JPG", "WEBP"]
UPSCALE_FACTORS = ["1x", "2x", "3x", "4x"]
UPSCALE_MODELS = ["realesr-animevideov3", "waifu2x"]

# Color scheme
COLORS = {
    'primary': "#007AFF", 'secondary': "#007AFF", 'background': "#1e1e2e",
    'panel': "#2d2d3f", 'surface': "#1e1e2e", 'text': "#ffffff",
    'text_secondary': "#aaaaaa", 'border': "#3d3d4f",
    'success': "#34c759", 'error': "#FF3B30", 'disabled': "#003063", 'hover':"#0064d1", '!tab': "#262636", 'error_hover': "#c2281f"
}

class StitcherThread(QThread):
    """Thread for stitching images together"""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(int, int, str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, folders, output_dir, is_vertical, spacing, output_format, virtual_files=None):
        super().__init__()
        self.folders = folders
        self.output_dir = output_dir
        self.is_vertical = is_vertical
        self.spacing = spacing
        self.output_format = output_format.lower()
        self.virtual_files = virtual_files or {}
        self.running = True
    
    def run(self):
        """Run the stitching process"""
        success_count = 0
        error_count = 0
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Process each folder
        for i, folder_path in enumerate(self.folders):
            if not self.running:
                break
                
            try:
                # Get folder name for output file
                if folder_path.startswith("virtual:"):
                    folder_name = folder_path.split(":", 1)[1]
                else:
                    folder_name = os.path.basename(folder_path)
                
                # Emit progress signal
                self.progress_signal.emit(i, folder_name)
                
                # Get files to stitch
                files_to_stitch = []
                if folder_path.startswith("virtual:"):
                    # For virtual folders, use the stored files
                    files_to_stitch = self.virtual_files.get(folder_path, [])
                else:
                    # For real folders, get image files
                    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.gif', '*.tiff', '*.tif']:
                        files_to_stitch.extend([str(f) for f in Path(folder_path).glob(ext)])
                
                # Sort files naturally
                files_to_stitch.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', os.path.basename(s))])
                
                if not files_to_stitch:
                    raise ValueError(f"No images found in {folder_name}")
                
                # Stitch images
                output_path = os.path.join(self.output_dir, f"{folder_name}_stitched.{self.output_format}")
                self._stitch_images(files_to_stitch, output_path)
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                self.error_signal.emit(f"Error stitching {folder_path}: {str(e)}")
        
        # Emit finished signal
        self.finished_signal.emit(success_count, error_count, self.output_dir)
    
    def _stitch_images(self, image_paths, output_path):
        """Stitch images together and save to output path"""
        if not image_paths:
            raise ValueError("No images to stitch")
        
        # Open all images
        images = []
        for path in image_paths:
            try:
                img = Image.open(path)
                # Convert to RGB if needed (for transparency handling)
                if img.mode == 'RGBA' and self.output_format.lower() in ['jpg', 'jpeg']:
                    img = img.convert('RGB')
                images.append(img)
            except Exception as e:
                self.error_signal.emit(f"Error opening image {path}: {str(e)}")
                continue
        
        if not images:
            raise ValueError("No valid images to stitch")
        
        # Calculate dimensions of the stitched image
        if self.is_vertical:
            # Vertical stitching (top to bottom)
            width = max(img.width for img in images)
            height = sum(img.height for img in images) + self.spacing * (len(images) - 1)
        else:
            # Horizontal stitching (left to right)
            width = sum(img.width for img in images) + self.spacing * (len(images) - 1)
            height = max(img.height for img in images)
        
        # Create a new image with the calculated dimensions
        mode = 'RGB' if self.output_format.lower() in ['jpg', 'jpeg'] else 'RGBA'
        stitched = Image.new(mode, (width, height), (0, 0, 0, 0))
        
        # Paste images into the stitched image
        x_offset = 0
        y_offset = 0
        
        for img in images:
            if self.is_vertical:
                # Center horizontally
                x_offset = (width - img.width) // 2
                stitched.paste(img, (x_offset, y_offset))
                y_offset += img.height + self.spacing
            else:
                # Center vertically
                y_offset = (height - img.height) // 2
                stitched.paste(img, (x_offset, y_offset))
                x_offset += img.width + self.spacing
        
        # Save the stitched image
        if self.output_format.lower() == 'jpg' or self.output_format.lower() == 'jpeg':
            stitched.save(output_path, 'JPEG', quality=95)
        elif self.output_format.lower() == 'png':
            stitched.save(output_path, 'PNG')
        elif self.output_format.lower() == 'webp':
            stitched.save(output_path, 'WEBP', quality=95)
        else:
            stitched.save(output_path)
        
        # Close all images to free memory
        for img in images:
            img.close()
            
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

class ConverterThread(QThread):
    progress_signal = pyqtSignal(int, str, str)
    completion_signal = pyqtSignal(str, float, float, int, int)
    error_signal = pyqtSignal(str, str)
    
    
    def __init__(self, files, output_dir, output_format, settings, enable_upscale=False, upscale_factor="2x"):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.output_format = output_format.lower()
        self.settings = settings 
        self.enable_upscale = enable_upscale
        self.upscale_factor = upscale_factor
        self.running = True
        self.cancelled = False
        self.total_files = len(files)
        self.processed_files = 0
        self.start_time = 0
        self.total_input_size = 0
        self.total_output_size = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_output_path = ""
        
    def stop(self):
        """Stop the thread and terminate any running process"""
        self.running = False
        self.cancelled = True
        
        # Terminate any running subprocess
        if hasattr(self, 'process') and self.process:
            try:
                self.process.terminate()
            except Exception as e:
                print(f"Error terminating process: {str(e)}")
        
    def run(self):
        self.start_time = time.time()
        
        # Calculate total input size for progress tracking
        for file_path in self.files:
            try:
                self.total_input_size += os.path.getsize(file_path)
            except:
                pass
        
        for file_path in self.files:
            if not self.running:
                break
                
            try:
                # Get file extension and base name
                file_ext = os.path.splitext(file_path)[1].lower()
                base_name = os.path.basename(file_path)
                base_name_without_ext = os.path.splitext(base_name)[0]
                
                # Create output filename
                output_filename = f"{base_name_without_ext}.{self.output_format}"
                output_path = os.path.join(self.output_dir, output_filename)
                
                # Convert based on file type
                if file_ext == '.psd':
                    self._convert_psd(file_path, output_path)
                elif file_ext == '.pdf' and self.output_format != 'pdf':
                    self._convert_pdf(file_path, output_path)
                else:
                    self._convert_image(file_path, output_path)
                
                # Apply AI upscaling if enabled
                if self.enable_upscale and self.output_format.lower() in ['png', 'jpg', 'jpeg', 'webp']:
                    scale_factor = int(self.upscale_factor[0])
                    temp_output = output_path
                    
                    # Create a temporary filename for the upscaled version
                    temp_upscaled = os.path.join(
                        self.output_dir,
                        f"{base_name_without_ext}_temp.{self.output_format}"
                    )
                    
                    # Use RealESRGAN for upscaling
                    realesrgan_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "esr", "realesrgan-ncnn-vulkan.exe")
                    
                    # Check if the upscaler exists
                    if not os.path.exists(realesrgan_path):
                        raise Exception(f"AI upscaler not found at: {realesrgan_path}")
                    
                    try:
                        # Create startupinfo to hide console window
                        startupinfo = None
                        if os.name == 'nt':  # Windows
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            startupinfo.wShowWindow = 0  # SW_HIDE
                            
                        # Run the upscaler with hidden console
                        result = subprocess.run([
                            realesrgan_path,
                            "-i", temp_output,
                            "-o", temp_upscaled,
                            "-n", "realesr-animevideov3",
                            "-s", str(scale_factor)
                        ], stdout=subprocess.DEVNULL, 
                           stderr=subprocess.PIPE,  # Capture only stderr for error messages
                           timeout=300, 
                           startupinfo=startupinfo, 
                           creationflags=subprocess.CREATE_NO_WINDOW)
                        
                        # Check process result and error output
                        if result.returncode != 0:
                            error_msg = result.stderr.decode().strip() if result.stderr else "Unknown error occurred"
                            raise Exception(f"Upscaling process failed: {error_msg}")
                            
                        # Check if the output file exists
                        if not os.path.exists(temp_upscaled):
                            raise Exception("Upscaling failed: Output file was not created")
                            
                        # Update output path to upscaled version
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        os.rename(temp_upscaled, output_path)
                        
                    except subprocess.TimeoutExpired:
                        if os.path.exists(temp_upscaled):
                            os.remove(temp_upscaled)
                        raise Exception("Upscaling process timed out after 5 minutes")
                    except Exception as e:
                        if os.path.exists(temp_upscaled):
                            os.remove(temp_upscaled)
                        raise Exception(f"Upscaling error: {str(e)}")                   
                    
                # Update progress
                self.processed_files += 1
                self.success_count += 1
                self.last_output_path = output_path
                
                # Calculate output size
                if os.path.exists(output_path):
                    self.total_output_size += os.path.getsize(output_path)
                
                # Update progress
                progress = int((self.processed_files / self.total_files) * 100)
                
                # Calculate ETA
                elapsed_time = time.time() - self.start_time
                if self.processed_files > 0:
                    avg_time_per_file = elapsed_time / self.processed_files
                    remaining_files = self.total_files - self.processed_files
                    eta_seconds = avg_time_per_file * remaining_files
                    
                    # Format ETA
                    if eta_seconds < 60:
                        eta_text = f"ETA: {int(eta_seconds)} seconds"
                    else:
                        eta_text = f"ETA: {int(eta_seconds / 60)} minutes {int(eta_seconds % 60)} seconds"
                else:
                    eta_text = "Calculating ETA..."
                
                # Calculate processing speed
                if elapsed_time > 0:
                    files_per_second = self.processed_files / elapsed_time
                    speed_text = f"Speed: {files_per_second:.2f} files/second"
                else:
                    speed_text = "Calculating speed..."
                
                self.progress_signal.emit(progress, eta_text, speed_text)
                
            except Exception as e:
                self.failure_count += 1
                error_message = f"Error converting {file_path}: {str(e)}"
                self.error_signal.emit(error_message, "conversion_error")
                
                # Update progress even on error
                self.processed_files += 1
                progress = int((self.processed_files / self.total_files) * 100)
                self.progress_signal.emit(progress, "Processing...", "Error occurred on last file")
        
        # Clean up temp directory
        self.cleanup_temp_directory()
        
        # Emit completion signal
        self.completion_signal.emit(
            self.last_output_path,
            self.total_input_size,
            self.total_output_size,
            self.success_count,
            self.failure_count
        )
    
    def cleanup_temp_directory(self):
        """Clean up any temporary files created during conversion"""
        try:
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        print(f"Error deleting temporary file {file_path}: {str(e)}")
        except Exception as e:
            print(f"Error cleaning up temporary directory: {str(e)}")
    
    def _convert_psd(self, input_path, output_path):
        try:
            psd = PSDImage.open(input_path)
            psd_image = psd.composite()
            
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            if not os.access(output_dir, os.W_OK):
                raise Exception(f"Output directory is not writable: {output_dir}")
            
            # Handle color mode conversion for different formats
            if self.output_format.lower() in ['jpg', 'jpeg'] and psd_image.mode in ['RGBA', 'LA', 'P']:
                psd_image = psd_image.convert('RGB')
            
            # Save with appropriate settings for each format
            if self.output_format.lower() in ['jpg', 'jpeg']:
                quality = self._get_quality_value(self.settings['jpeg_quality'])
                psd_image.save(output_path, quality=quality, optimize=True)
                
            elif self.output_format.lower() == 'png':
                compression = self._get_compression_level(self.settings['png_compression'])
                # Fix PNG compression by using correct parameters
                psd_image.save(output_path, format='PNG', compress_level=int(compression), optimize=False)
                
            elif self.output_format.lower() == 'webp':
                quality = self._get_quality_value(self.settings['webp_quality'])
                psd_image.save(output_path, quality=quality, method=6)
                
            elif self.output_format.lower() == 'tiff':
                psd_image.save(output_path, format='TIFF', compression='tiff_deflate')
                
            elif self.output_format.lower() == 'bmp':
                psd_image.save(output_path, format='BMP')
                
            elif self.output_format.lower() == 'gif':
                if psd_image.mode != 'P':
                    psd_image = psd_image.convert('P')
                psd_image.save(output_path, format='GIF')
                
            elif self.output_format.lower() == 'pdf':
                # Convert PSD to PDF with quality settings
                psd_image_rgb = psd_image.convert('RGB')
                
                # Get PDF quality and DPI settings
                quality_setting = self.settings.get('pdf_quality', 'High')
                dpi_setting = self.settings.get('pdf_dpi', '150 DPI')
                
                # Extract DPI value from setting
                dpi = int(dpi_setting.split()[0])
                
                # Apply quality factor based on setting
                quality_factor = 1.0
                if quality_setting == 'High':
                    quality_factor = 1.0  # No compression
                elif quality_setting == 'Medium':
                    quality_factor = 0.8  # Medium compression
                else:  # Low
                    quality_factor = 0.6  # Higher compression
                
                # Save with appropriate resolution and quality
                psd_image_rgb.save(output_path, format='PDF', resolution=dpi, quality=int(95 * quality_factor))
                
            else:
                psd_image.save(output_path)
            
            del psd, psd_image
            gc.collect()
            
        except Exception as e:
            raise Exception(f"PSD conversion error: {str(e)}")
    
    def _convert_pdf(self, input_path, output_path):
        try:
            if PDF_CONVERTER == "pymupdf":
                pdf_document = fitz.open(input_path)
                
                # Get DPI setting
                dpi_setting = self.settings.get('pdf_dpi', '150 DPI')
                dpi = int(dpi_setting.split()[0])  # Extract numeric part
                
                # Get quality setting
                quality_setting = self.settings.get('pdf_quality', 'High')
                quality_factor = 1.0
                if quality_setting == 'High':
                    quality_factor = 2.0
                elif quality_setting == 'Medium':
                    quality_factor = 1.5
                else:  # Low
                    quality_factor = 1.0
                
                # Calculate zoom factor based on DPI and quality
                zoom_factor = (dpi / 72.0) * quality_factor
                
                # If there's only one page, convert directly
                if pdf_document.page_count == 1:
                    page = pdf_document.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
                    
                    # Convert pixmap to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Save with appropriate settings for each format
                    if self.output_format.lower() in ['jpg', 'jpeg']:
                        quality = self._get_quality_value(self.settings['jpeg_quality'])
                        img.save(output_path, quality=quality, optimize=True)
                    elif self.output_format.lower() == 'png':
                        compression = self._get_compression_level(self.settings['png_compression'])
                        img.save(output_path, format='PNG', compress_level=int(compression), optimize=False)
                    elif self.output_format.lower() == 'webp':
                        quality = self._get_quality_value(self.settings['webp_quality'])
                        img.save(output_path, quality=quality, method=6)
                    elif self.output_format.lower() == 'tiff':
                        img.save(output_path, format='TIFF', compression='tiff_deflate')
                    elif self.output_format.lower() == 'bmp':
                        img.save(output_path, format='BMP')
                    elif self.output_format.lower() == 'gif':
                        if img.mode != 'P':
                            img = img.convert('P')
                        img.save(output_path, format='GIF')
                    elif self.output_format.lower() == 'pdf':
                        # Just copy the PDF file if output is also PDF
                        pdf_document.save(output_path, garbage=3, deflate=True)
                    else:
                        img.save(output_path)
                else:
                    # For multi-page PDFs, convert only the first page
                    base_name = os.path.splitext(output_path)[0]
                    output_path = f"{base_name}_page1.{self.output_format}"
                    
                    page = pdf_document.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
                    
                    # Convert pixmap to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Save with appropriate settings for each format
                    if self.output_format.lower() in ['jpg', 'jpeg']:
                        quality = self._get_quality_value(self.settings['jpeg_quality'])
                        img.save(output_path, quality=quality, optimize=True)
                    elif self.output_format.lower() == 'png':
                        compression = self._get_compression_level(self.settings['png_compression'])
                        img.save(output_path, format='PNG', compress_level=int(compression), optimize=False)
                    elif self.output_format.lower() == 'webp':
                        quality = self._get_quality_value(self.settings['webp_quality'])
                        img.save(output_path, quality=quality, method=6)
                    elif self.output_format.lower() == 'tiff':
                        img.save(output_path, format='TIFF', compression='tiff_deflate')
                    elif self.output_format.lower() == 'bmp':
                        img.save(output_path, format='BMP')
                    elif self.output_format.lower() == 'gif':
                        if img.mode != 'P':
                            img = img.convert('P')
                        img.save(output_path, format='GIF')
                    elif self.output_format.lower() == 'pdf':
                        # For PDF to PDF, extract just the first page
                        new_pdf = fitz.open()
                        new_pdf.insert_pdf(pdf_document, from_page=0, to_page=0)
                        new_pdf.save(output_path, garbage=3, deflate=True)
                        new_pdf.close()
                    else:
                        img.save(output_path)
                
                pdf_document.close()
            else:
                raise Exception("No PDF converter available. Please install PyMuPDF.")
                
        except Exception as e:
            raise Exception(f"PDF conversion error: {str(e)}")
    
    def _convert_image(self, input_path, output_path):
        try:
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            
            with Image.open(input_path) as img:
                # Handle color mode conversion for different formats
                if self.output_format.lower() in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'LA', 'P']:
                    img = img.convert('RGB')
                elif self.output_format.lower() == 'png' and img.mode == 'P':
                    img = img.convert('RGBA')
                
                # Save with appropriate settings for each format
                if self.output_format.lower() in ['jpg', 'jpeg']:
                    quality = self._get_quality_value(self.settings['jpeg_quality'])
                    img.save(output_path, quality=quality, optimize=True)
                    
                elif self.output_format.lower() == 'png':
                    compression = self._get_compression_level(self.settings['png_compression'])
                    # Fix PNG compression by using correct parameters
                    img.save(output_path, format='PNG', compress_level=int(compression), optimize=False)
                    
                elif self.output_format.lower() == 'webp':
                    quality = self._get_quality_value(self.settings['webp_quality'])
                    img.save(output_path, quality=quality, method=6)
                    
                elif self.output_format.lower() == 'tiff':
                    img.save(output_path, format='TIFF', compression='tiff_deflate')
                    
                elif self.output_format.lower() == 'bmp':
                    img.save(output_path, format='BMP')
                    
                elif self.output_format.lower() == 'gif':
                    if img.mode != 'P':
                        img = img.convert('P')
                    img.save(output_path, format='GIF')
                    
                elif self.output_format.lower() == 'pdf':
                    # Convert image to PDF with quality settings
                    img_rgb = img.convert('RGB')
                    
                    # Get PDF quality and DPI settings
                    quality_setting = self.settings.get('pdf_quality', 'High')
                    dpi_setting = self.settings.get('pdf_dpi', '150 DPI')
                    
                    # Extract DPI value from setting
                    dpi = int(dpi_setting.split()[0])
                    
                    # Apply quality factor based on setting
                    quality_factor = 1.0
                    if quality_setting == 'High':
                        quality_factor = 1.0  # No compression
                    elif quality_setting == 'Medium':
                        quality_factor = 0.8  # Medium compression
                    else:  # Low
                        quality_factor = 0.6  # Higher compression
                    
                    # Save with appropriate resolution and quality
                    img_rgb.save(output_path, format='PDF', resolution=dpi, quality=int(95 * quality_factor))
                    
                else:
                    img.save(output_path)
                    
        except Exception as e:
            raise Exception(f"Image conversion error: {str(e)}")

    def _get_quality_value(self, quality_setting):
        """Convert quality setting to numerical value"""
        quality_map = {
            "Maximum": 95,
            "High": 85,
            "Medium": 70,
            "Low": 50
        }
        return quality_map.get(quality_setting, 85)

    def _get_compression_level(self, compression_setting):
        """Convert compression setting to numerical value"""
        compression_map = {
            "None": 0,
            "Fast": 1,
            "Normal": 6,
            "Maximum": 9
        }
        return compression_map.get(compression_setting, 6)

class UpscalerThread(QThread):
    """Thread for upscaling images"""
    progress_signal = pyqtSignal(int, str, str)
    completion_signal = pyqtSignal(str, int, int, int, int)
    error_signal = pyqtSignal(str, str)
    log_signal = pyqtSignal(str, str)
    
    def __init__(self, files, output_dir, upscale_factor="2x", model="realesr-animevideov3", keep_format=True, output_format="PNG", noise_level=1, waifu2x_model="models-cunet", use_cpu=False):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.upscale_factor = upscale_factor
        self.model = model
        self.keep_format = keep_format
        self.output_format = output_format
        self.noise_level = noise_level
        self.waifu2x_model = waifu2x_model
        self.use_cpu = use_cpu 
        self.running = True
        self.cancelled = False
        self.total_files = len(files)
        self.processed_files = 0
        self.start_time = 0
        self.total_input_size = 0
        self.total_output_size = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_output_path = ""
        self.failed_files = {}
    
    def stop(self):
        self.running = False
        self.cancelled = True
        # Terminate any running process
        if hasattr(self, 'process') and self.process:
            try:
                self.process.terminate()
            except:
                pass
        
    def cleanup_temp_directory(self):
        """Clean up temporary directory and files"""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                # Remove all files in the temp directory
                for file in os.listdir(self.temp_dir):
                    try:
                        os.remove(os.path.join(self.temp_dir, file))
                    except:
                        pass
                # Remove the directory itself
                try:
                    os.rmdir(self.temp_dir)
                except:
                    pass
        except Exception as e:
            print(f"Error cleaning up temp directory: {str(e)}")
    
    def run(self):
        """Main thread execution method"""
        self.start_time = time.time()
        
        # Create a temporary directory for processing
        self.temp_dir = os.path.join(self.output_dir, "temp_upscale")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        # Calculate total input size for progress tracking
        for file_path in self.files:
            try:
                self.total_input_size += os.path.getsize(file_path)
            except Exception as e:
                self.failed_files[file_path] = f"Failed to get file size: {str(e)}"  # More descriptive error
                self.failure_count += 1
                continue
        
        for i, file_path in enumerate(self.files):
            if not self.running or self.cancelled:
                break
                
            try:
                # Get file extension and base name
                file_ext = os.path.splitext(file_path)[1].lower()
                base_name = os.path.basename(file_path)
                base_name_without_ext = os.path.splitext(base_name)[0]
                
                # Log the upscaling process
                self.log_signal.emit(f"Upscaling {file_path} with {self.upscale_factor} using {self.model}", "INFO")

                # Determine output format
                output_ext = file_ext if self.keep_format else f".{self.output_format}"
                if not output_ext.startswith('.'):
                    output_ext = f".{output_ext}"
                
                # Create output filename with _upscaled suffix
                output_filename = f"{base_name_without_ext}_upscaled{self.upscale_factor}{output_ext}"
                output_path = os.path.join(self.output_dir, output_filename)
                
                # Apply AI upscaling
                self._upscale_image(file_path, output_path)
                
                # Update progress
                self.processed_files += 1
                self.success_count += 1
                self.last_output_path = output_path
                
                # Calculate output size
                if os.path.exists(output_path):
                    self.total_output_size += os.path.getsize(output_path)
                
                # Update progress
                progress = int((self.processed_files / self.total_files) * 100)
                
                # Calculate ETA and speed
                self._update_progress_info(progress)
                
            except Exception as e:
                self.failure_count += 1
                error_message = f"Error upscaling {file_path}: {str(e)}"
                self.error_signal.emit(error_message, "upscaling_error")
                
                # Update progress even on error
                self.processed_files += 1
                progress = int((self.processed_files / self.total_files) * 100)
                self.progress_signal.emit(progress, "Processing...", "Error occurred on last file") 
        
        # Clean up temp directory
        self.cleanup_temp_directory()
        
        # Only emit completion signal if not cancelled
        if not self.cancelled:
            self.completion_signal.emit(
                self.last_output_path,
                self.total_input_size,
                self.total_output_size,
                self.success_count,
                self.failure_count
            )
    
    def _update_progress_info(self, progress):
        """Calculate and emit progress information including ETA and speed"""
        elapsed_time = time.time() - self.start_time
        
        # Calculate ETA
        if self.processed_files > 0:
            avg_time_per_file = elapsed_time / self.processed_files
            remaining_files = self.total_files - self.processed_files
            eta_seconds = avg_time_per_file * remaining_files
            
            # Format ETA
            if eta_seconds < 60:
                eta_text = f"ETA: {int(eta_seconds)} seconds"
            else:
                eta_text = f"ETA: {int(eta_seconds / 60)} minutes {int(eta_seconds % 60)} seconds"
        else:
            eta_text = "Calculating ETA..."
        
        # Calculate processing speed
        if elapsed_time > 0:
            files_per_second = self.processed_files / elapsed_time
            speed_text = f"Speed: {files_per_second:.2f} files/second"
        else:
            speed_text = "Calculating speed..."
        
        self.progress_signal.emit(progress, eta_text, speed_text)
    
    def _upscale_image(self, input_path, output_path):
        """Upscale an image using the selected AI model"""
        # Check if input file exists and is a supported format
        if not os.path.exists(input_path):
            raise Exception(f"Input file not found: {input_path}")
        
        # Get file extension
        file_ext = os.path.splitext(input_path)[1].lower().lstrip('.')
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Get scale factor (extract the number from strings like "2x")
        scale_factor = int(self.upscale_factor[0])
        
        # Create startupinfo to hide console window
        startupinfo = None
        if os.name == 'nt':  # Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
        
        try:
            # Choose the appropriate upscaler based on the model
            if self.model.lower() == "waifu2x":
                # Get waifu2x-ncnn-vulkan path
                waifu2x_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "waifu2x-ncnn-vulkan")
                waifu2x_path = os.path.join(waifu2x_dir, "waifu2x-ncnn-vulkan_waifu2xEX.exe")
                
                # Check if the directory exists, create if not
                if not os.path.exists(waifu2x_dir):
                    os.makedirs(waifu2x_dir)
                    raise Exception(f"Waifu2x directory created at: {waifu2x_dir}. Please download and place waifu2x-ncnn-vulkan.exe in this directory.")
                
                # Check if the executable exists with primary name
                if not os.path.exists(waifu2x_path):
                    # Try alternate executable name
                    waifu2x_path = os.path.join(waifu2x_dir, "waifu2x-ncnn-vulkan.exe")
                    if not os.path.exists(waifu2x_path):
                        raise Exception(f"Waifu2x executable not found in waifu2x-ncnn-vulkan directory. Please download and place it there.")
                
                # Set GPU ID based on CPU preference
                gpu_id = "-1" if self.use_cpu else "auto"
                
                # Run waifu2x with noise reduction and upscaling
                cmd = [
                    waifu2x_path,
                    "-i", input_path,
                    "-o", output_path,
                    "-n", str(self.noise_level),  # Use the noise level parameter
                    "-s", str(scale_factor),
                    "-m", self.waifu2x_model,  # Model path
                    "-f", os.path.splitext(output_path)[1].lower().lstrip('.'),
                    "-g", gpu_id,  # Use CPU (-1) or GPU (auto)
                    "-j", f"{os.cpu_count()}:{os.cpu_count()}:{os.cpu_count()}"
                ]
                
                device_type = "CPU" if self.use_cpu else "GPU"
                self.log_signal.emit(f"Running waifu2x with noise level {self.noise_level}, model {self.waifu2x_model}, using {device_type}", "INFO")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    timeout=300, 
                    startupinfo=startupinfo, 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Get realesrgan-ncnn-vulkan path
                esr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "esr")
                esr_path = os.path.join(esr_dir, "realesrgan-ncnn-vulkan.exe")
                
                # Check if the directory exists, create if not
                if not os.path.exists(esr_dir):
                    os.makedirs(esr_dir)
                    raise Exception(f"ESR directory created at: {esr_dir}. Please download and place realesrgan-ncnn-vulkan.exe in this directory.")
                
                # Check if the executable exists
                if not os.path.exists(esr_path):
                    raise Exception(f"ESRGAN executable not found in esr directory. Please download and place it there.")
                
                # Set GPU ID based on CPU preference
                gpu_id = "-1" if self.use_cpu else "auto"
                
                # Run realesrgan-ncnn-vulkan
                cmd = [
                    esr_path,
                    "-i", input_path,
                    "-o", output_path,
                    "-s", str(scale_factor),
                    "-n", self.model,  # Use the model name
                    "-f", os.path.splitext(output_path)[1].lower().lstrip('.'),
                    "-g", "auto"
                ]
                
                device_type = "CPU" if self.use_cpu else "GPU"
                self.log_signal.emit(f"Running ESRGAN with model {self.model}, using {device_type}", "INFO")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    timeout=300, 
                    startupinfo=startupinfo, 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            # Check if the output file was created
            if not os.path.exists(output_path):
                stderr = result.stderr.decode('utf-8', errors='ignore')
                raise Exception(f"Failed to create output file. Error: {stderr}")
            
            # Return the output path
            return output_path
            
        except subprocess.TimeoutExpired:
            raise Exception(f"Upscaling timed out after 5 minutes. The image may be too large.")
        except Exception as e:
            raise Exception(f"Error during upscaling: {str(e)}")
            
class UpscalerProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upscaling...")
        self.setFixedSize(450, 220)
        self.setModal(True)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Apply theme
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS['background']}; color: {COLORS['text']}; border-radius: 10px; }}")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 25)
        layout.setSpacing(15)
        
        # Title with modern font
        title = QLabel("Upscaling Images...")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)
        
        # Progress bar with modern styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet(f"""
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

        layout.addWidget(self.progress_bar)
        
        # Status labels with modern font
        self.eta_label = QLabel("Preparing...")
        self.eta_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.eta_label)
        
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.speed_label)
        
        layout.addStretch()
        
        # Cancel button with modern styling
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(45)
        self.cancel_btn.setMinimumWidth(160) 
        self.cancel_btn.setFont(QFont("Segoe UI", 10)) 
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['error']}; color: white; border: none; border-radius: 8px; 
                          padding: 10px; font-weight: 600; margin-bottom: 5px; }}
            QPushButton:hover {{ background-color: #FF6B6B; }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_upscaling)
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
        
    def cancel_upscaling(self):
        """Signal to cancel the upscaling process"""
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk { 
                background-color: #d13438; 
                border-radius: 8px; 
            }
        """)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelling...")
        self.parent().log("Upscaling process cancelled by user", "INFO")
        self.parent().stop_upscaling()
    
    def update_progress(self, value, eta_text, speed_text):
        self.progress_bar.setValue(value)
        self.eta_label.setText(eta_text)
        self.speed_label.setText(speed_text)

class DenoiserThread(QThread):
    """Thread for handling image denoising operations"""
    progress_signal = pyqtSignal(int, str, str)
    completion_signal = pyqtSignal(str, float, float, int, int)
    error_signal = pyqtSignal(str, str)
    log_signal = pyqtSignal(str, str)  # Add this signal for logging
    
    def __init__(self, files, output_dir, noise_level=1, model="anime", keep_format=True, output_format="PNG"):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.noise_level = noise_level
        self.model = "models-cunet" if model == "anime" else "models-upconv_7_photo"
        self.keep_format = keep_format
        self.output_format = output_format.lower()
        self.running = True
        self.cancelled = False
        self.total_files = len(files)
        self.processed_files = 0
        self.start_time = 0
        self.total_input_size = 0
        self.total_output_size = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_output_path = ""
    
    def stop(self):
        """Stop the thread"""
        self.running = False
    
    def run(self):
        """Main thread execution method"""
        self.start_time = time.time()
        
        # Calculate total input size
        for file_path in self.files:
            try:
                self.total_input_size += os.path.getsize(file_path)
            except:
                pass
        
        for file_path in self.files:
            if not self.running:
                break
                
            try:
                # Get file extension and base name
                file_ext = os.path.splitext(file_path)[1].lower()
                base_name = os.path.basename(file_path)
                base_name_without_ext = os.path.splitext(base_name)[0]
                
                # Log the denoising process
                self.log_signal.emit(f"Denoising {file_path} with noise level {self.noise_level} using {self.model}", "INFO")

                # Determine output format
                output_ext = file_ext if self.keep_format else f".{self.output_format}"
                if not output_ext.startswith('.'):
                    output_ext = f".{output_ext}"
                
                # Create output filename with _denoised suffix
                output_filename = f"{base_name_without_ext}_denoised{output_ext}"
                output_path = os.path.join(self.output_dir, output_filename)
                
                # Run waifu2x-ncnn-vulkan for denoising
                self._denoise_image(file_path, output_path)
                
                # Update progress
                self.processed_files += 1
                self.success_count += 1
                self.last_output_path = output_path
                
                # Calculate output size
                if os.path.exists(output_path):
                    self.total_output_size += os.path.getsize(output_path)
                
                # Update progress
                progress = int((self.processed_files / self.total_files) * 100)
                elapsed_time = time.time() - self.start_time
                remaining_files = self.total_files - self.processed_files
                
                if self.processed_files > 0 and remaining_files > 0:
                    # Calculate ETA
                    avg_time_per_file = elapsed_time / self.processed_files
                    eta_seconds = avg_time_per_file * remaining_files
                    
                    # Format ETA
                    if eta_seconds < 60:
                        eta_text = f"ETA: {eta_seconds:.0f} seconds"
                    elif eta_seconds < 3600:
                        eta_text = f"ETA: {eta_seconds/60:.1f} minutes"
                    else:
                        eta_text = f"ETA: {eta_seconds/3600:.1f} hours"
                    
                    # Calculate processing speed
                    if elapsed_time > 0:
                        files_per_second = self.processed_files / elapsed_time
                        speed_text = f"Speed: {files_per_second:.2f} files/sec"
                    else:
                        speed_text = "Speed: calculating..."
                    
                    # Send progress update
                    self.progress_signal.emit(progress, eta_text, speed_text)
                else:
                    self.progress_signal.emit(progress, "Processing...", "Starting...")
                
            except Exception as e:
                self.failure_count += 1
                error_message = f"Error denoising {file_path}: {str(e)}"
                self.error_signal.emit(error_message, "denoising_error")
                
                # Update progress even on error
                self.processed_files += 1
                progress = int((self.processed_files / self.total_files) * 100)
                self.progress_signal.emit(progress, "Processing...", "Error occurred on last file")
        
        # Emit completion signal
        self.completion_signal.emit(
            self.last_output_path,
            self.total_input_size,
            self.total_output_size,
            self.success_count,
            self.failure_count
        )
    
    def _denoise_image(self, input_path, output_path):
        """Run waifu2x-ncnn-vulkan to denoise an image"""
        # Check if input file exists and is a supported format
        if not os.path.exists(input_path):
            raise Exception(f"Input file not found: {input_path}")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Check if output directory is writable
        if not os.access(output_dir, os.W_OK):
            raise Exception(f"Output directory is not writable: {output_dir}")
        
        # Get waifu2x-ncnn-vulkan path
        denoiser_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                   "waifu2x-ncnn-vulkan", 
                                   "waifu2x-ncnn-vulkan_waifu2xEX.exe")
        
        # Check if the denoiser exists
        if not os.path.exists(denoiser_path):
            # Try alternate executable name
            denoiser_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                      "waifu2x-ncnn-vulkan", 
                                      "waifu2x-ncnn-vulkan.exe")
            if not os.path.exists(denoiser_path):
                raise Exception(f"Denoiser executable not found in waifu2x-ncnn-vulkan directory")
        
        try:
            # Create startupinfo to hide console window
            startupinfo = None
            if os.name == 'nt':  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE
            
            # Run the denoiser
            result = subprocess.run([
                denoiser_path,
                "-i", input_path,
                "-o", output_path,
                "-n", str(self.noise_level),  # Noise level (-1 to 3)
                "-s", "1",  # Scale 1x (no upscaling)
                "-m", self.model,  # Model path
                "-f", os.path.splitext(output_path)[1].lower().lstrip('.'),  # Force output format
                "-g", "auto",  # Auto GPU selection
                "-j", f"{os.cpu_count()}:{os.cpu_count()}:{os.cpu_count()}"
                 # Use 2 threads for loading/processing/saving
            ], stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE,
               timeout=300, 
               startupinfo=startupinfo, 
               creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Check process result and error output
            if result.returncode != 0:
                error_msg = result.stderr.decode().strip() if result.stderr else "Unknown error occurred"
                raise Exception(f"Denoising process failed: {error_msg}")
            
            # Check if the output file exists
            if not os.path.exists(output_path):
                raise Exception("Denoising failed: Output file was not created")
                
        except subprocess.TimeoutExpired:
            raise Exception("Denoising process timed out after 5 minutes")
        except Exception as e:
            raise Exception(f"Denoising error: {str(e)}")

class DenoiserProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Denoising...")
        self.setFixedSize(450, 220)
        self.setModal(True)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Apply theme
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS['background']}; color: {COLORS['text']}; border-radius: 10px; }}")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 25)
        layout.setSpacing(15)
        
        # Title with modern font
        title = QLabel("Denoising Images...")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)
        
        # Progress bar with modern styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet(f"""
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

        layout.addWidget(self.progress_bar)
        
        # Status labels
        self.eta_label = QLabel("Preparing...")
        self.eta_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.eta_label)
        
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.speed_label)
        
        layout.addStretch()
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(45)
        self.cancel_btn.setMinimumWidth(160) 
        self.cancel_btn.setFont(QFont("Segoe UI", 10)) 
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['error']}; color: white; border: none; border-radius: 8px; 
                          padding: 10px; font-weight: 600; margin-bottom: 5px; }}
            QPushButton:hover {{ background-color: #FF6B6B; }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_denoising)
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
    
    def cancel_denoising(self):
        """Signal to cancel the denoising process"""
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk { 
                background-color: #d13438; 
                border-radius: 8px; 
            }
        """)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelling...")
        self.parent().log("Denoising process cancelled by user", "INFO")
        self.parent().stop_denoising()
    
    def update_progress(self, value, eta_text, speed_text):
        self.progress_bar.setValue(value)
        self.eta_label.setText(eta_text)
        self.speed_label.setText(speed_text)

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
        
        # Add styling for dropdown items
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
        """)
        
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

class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Converting Files...")
        self.setFixedSize(450, 220)
        self.setModal(True)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Apply theme
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS['background']}; color: {COLORS['text']}; border-radius: 10px; }}")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 25)
        layout.setSpacing(15)
        
        # Title with modern font
        title = QLabel("Converting Files")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)
        
        # Progress bar with modern styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet(f"""
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

        layout.addWidget(self.progress_bar)
        
        # Status labels with modern font
        self.eta_label = QLabel("Preparing...")
        self.eta_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.eta_label)
        
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.speed_label)
        
        layout.addStretch()
        
        # Cancel button with modern styling
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(45)
        self.cancel_btn.setMinimumWidth(160) 
        self.cancel_btn.setFont(QFont("Segoe UI", 10)) 
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['error']}; color: white; border: none; border-radius: 8px; 
                          padding: 10px; font-weight: 600; margin-bottom: 5px; }}
            QPushButton:hover {{ background-color: #FF6B6B; }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
    
    def cancel_conversion(self):
        """Cancel the conversion process"""
        # Update UI to show cancellation in progress
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk { 
                background-color: #d13438; 
                border-radius: 8px; 
            }
        """)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelling...")
        self.parent().log("Conversion process cancelled by user", "INFO")                
        self.parent().stop_conversion()        
    
    def update_progress(self, value, eta_text, speed_text):
        self.progress_bar.setValue(value)
        self.eta_label.setText(eta_text)
        self.speed_label.setText(speed_text)

class ImageConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.vulkan_support = False  # Add this line to track Vulkan support

        # Initialize logger
        self.log_messages = []
        
        # Redirect stdout to capture terminal output
        self.setup_stdout_redirect()

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Show the experimental warning dialog
        QTimer.singleShot(100, self.show_experimental_warning)

        # Set window title and size
        self.setWindowTitle("Image/PSD Converter")
        self.setGeometry(100, 100, 850, 550)
        
        # Initialize variables for converter tab
        self.files = []
        self.output_dir = ""
        self.thread = None
        self.progress_dialog = None
        self.conversion_history = []
        self.selected_folder = None
        self.file_checkboxes = []  # Add this to track checkboxes
        
        # Initialize variables for upscaler tab
        self.upscaler_files = []
        self.upscaler_output_dir = ""
        self.upscaler_thread = None
        self.upscaler_progress_dialog = None
        self.upscaler_selected_folder = None
        self.upscaler_file_checkboxes = []
        
        # Initialize combo box references
        self.jpeg_quality_combo = None
        self.webp_quality_combo = None
        self.png_compression_combo = None
        self.pdf_dpi_combo = None
        self.pdf_quality_combo = None

        self.denoiser_files = []
        self.denoiser_output_dir = ""
        self.denoiser_thread = None
        self.denoiser_progress_dialog = None
        self.denoiser_selected_folder = None
        self.denoiser_file_checkboxes = [] 
        
        # Initialize UI
        self.initUI()
        self.animate_window()
        self.update_convert_button_state()
        self.update_upscale_button_state()
        
        # Initialize upscale options
        initial_format = self.format_combo.currentText().lower()
        self._update_upscale_availability(initial_format)
        self.update_upscale_availability()

    def show_experimental_warning(self):
        """Show a warning dialog about the experimental state of the application"""
        # Check if we should show the warning
        try:
            import json
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    try:
                        settings = json.load(f)
                        if settings.get('hide_experimental_warning', False):
                            return  # Don't show the dialog
                    except:
                        pass
        except:
            pass
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Important Notice")
        dialog.setMinimumSize(650, 500)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)
        
        # Create a rounded container for the warning content
        warning_container = QFrame()
        warning_container.setStyleSheet(f"""
            background-color: {COLORS['panel']}; 
            border-radius: 15px;
        """)
        
        container_layout = QVBoxLayout(warning_container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(15)
        
        # Warning icon and title with softer styling
        title_layout = QHBoxLayout()
        
        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 36px; color: #FFB940;")
        title_layout.addWidget(warning_icon)
        
        title = QLabel("Experimental Software - Please Read")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #FFB940;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        container_layout.addLayout(title_layout)
        
        # Horizontal line with softer color
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet(f"background-color: {COLORS['border']}; margin: 0px 5px;")
        container_layout.addWidget(line)
        
        # Create content widget for scrolling
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Warning message with softer colors and more rounded elements
        warning_text = """
        <p style="font-size: 14pt; font-weight: bold; color: #FFB940;">Before You Begin</p>
        
        <p>This application is currently in an <b>experimental state</b> and is still being refined. Please take a moment to read these important notes:</p>
        
        <p style="font-weight: bold; font-size: 13pt; color: #0078d4;">Recommended Precautions:</p>
        <ul>
            <li><b>Back up your files</b> before processing them with this application</li>
            <li>Read the instructions for each feature before using it</li>
            <li>Test with a small number of files before processing large batches</li>
            <li>Verify the output files after processing to ensure they meet your expectations</li>
        </ul>
        
        <p style="font-weight: bold; font-size: 13pt; color: #0078d4;">Things to Be Aware Of:</p>
        <ul>
            <li>The application may occasionally behave unexpectedly during file processing</li>
            <li>Some operations may take longer than expected with large files</li>
            <li>Output quality depends on your selected settings and source file quality</li>
            <li>System resource usage may be high during AI operations</li>
        </ul>
        
        <p style="font-weight: bold; font-size: 13pt; color: #0078d4;">Best Practices:</p>
        <ul>
            <li>Work with copies of your original files when possible</li>
            <li>Check the system compatibility information before using AI features</li>
            <li>For large batches, consider processing files in smaller groups</li>
            <li>If you encounter issues, check the instructions or restart the application</li>
        </ul>
        
        <p style="color: #0078d4; font-weight: bold;">By clicking "I Understand" below, you acknowledge that you've read these notes and are ready to proceed.</p>
        """
        
        warning_label = QLabel(warning_text)
        warning_label.setWordWrap(True)
        warning_label.setTextFormat(Qt.TextFormat.RichText)
        warning_label.setStyleSheet("font-size: 12px; line-height: 1.4;")
        content_layout.addWidget(warning_label)
        
        # Create a scroll area with proper styling
        scroll = QScrollArea()
        scroll.setWidget(content_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
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
        """)
        
        container_layout.addWidget(scroll)
        main_layout.addWidget(warning_container)
        
        # Checkbox for "Don't show again" with rounded styling
        dont_show_check = QCheckBox("Don't show this message again")
        dont_show_check.setStyleSheet(f"""
            QCheckBox {{ color: {COLORS['text']}; font-size: 12px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
            QCheckBox::indicator:unchecked {{ background-color: {COLORS['panel']}; border: 1px solid {COLORS['text']}; border-radius: 4px; }}
            QCheckBox::indicator:checked {{ background-color: {COLORS['primary']}; border: 1px solid {COLORS['primary']}; border-radius: 4px; }}
        """)
        main_layout.addWidget(dont_show_check)
        
        # Buttons with more rounded styling
        button_layout = QHBoxLayout()
        
        exit_btn = QPushButton("Exit Application")
        exit_btn.setFixedHeight(45)
        exit_btn.setMinimumWidth(150)
        exit_btn.clicked.connect(lambda: sys.exit(0))
        exit_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['secondary']}; 
                color: {COLORS['text']}; 
                border: none; 
                border-radius: 10px; 
                padding: 10px; 
                font-weight: 600; 
                font-size: 14px;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['hover']}; 
            }}
        """)
        
        understand_btn = QPushButton("I Understand")
        understand_btn.setFixedHeight(45)
        understand_btn.setMinimumWidth(150)
        understand_btn.clicked.connect(dialog.accept)
        understand_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['error']}; 
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 10px; 
                font-weight: 600; 
                font-size: 14px;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['error_hover']}; 
            }}
        """)
        
        button_layout.addWidget(exit_btn)
        button_layout.addStretch()
        button_layout.addWidget(understand_btn)
        
        main_layout.addLayout(button_layout)
        
        # Save the preference if "Don't show again" is checked
        def on_dialog_closed():
            if dont_show_check.isChecked():
                # Save the preference to a settings file
                try:
                    import json
                    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
                    
                    # Load existing settings if available
                    settings = {}
                    if os.path.exists(settings_path):
                        with open(settings_path, 'r') as f:
                            try:
                                settings = json.load(f)
                            except:
                                settings = {}
                    
                    # Update settings
                    settings['hide_experimental_warning'] = True
                    
                    # Save settings
                    with open(settings_path, 'w') as f:
                        json.dump(settings, f)
                except:
                    pass
        
        dialog.finished.connect(on_dialog_closed)
        dialog.exec()

    def show_message(self, title, message, icon=QMessageBox.Icon.Information):
        """Show a message dialog with the specified title, message, and icon"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 10pt;
                font-family: 'Segoe UI';
            }}
        """)
        
        # Style the OK button
        ok_btn = msg_box.addButton(QMessageBox.StandardButton.Ok)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        
        msg_box.exec()        
        
    def _update_upscale_availability(self, format_text):
        """Helper method to update upscale availability"""
        format_lower = format_text.lower()
        can_upscale = format_lower in ['png', 'jpg', 'jpeg', 'webp']
        
        # Check GPU compatibility for upscaling
        gpu_compatible = self.check_gpu_compatibility()
        print(f"GPU compatibility check result: {gpu_compatible}")  # Debug output
        
        # Force enable upscaling if format is compatible
        if can_upscale:
            self.upscale_check.setEnabled(True)
            self.upscale_check.setStyleSheet(f"font-size: 13px; color: #ffffff;")
            self.upscale_check.setToolTip("Enable AI upscaling")
            # Only enable the combo box if the checkbox is checked
            self.upscale_combo.setEnabled(self.upscale_check.isChecked())
        else:
            self.upscale_check.setEnabled(False)
            self.upscale_check.setChecked(False)
            self.upscale_combo.setEnabled(False)
            self.upscale_check.setStyleSheet(f"font-size: 13px; color: #888888;")
            self.upscale_check.setToolTip("This format does not support upscaling")

    def check_gpu_compatibility(self):
        """Check if GPU supports upscaling using ESRGAN-style detection"""
        try:
            if os.name == 'nt':  # Windows
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                    result = subprocess.run(
                        ['wmic', 'path', 'win32_VideoController', 'get', 'name'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        startupinfo=startupinfo,
                        text=True,
                        timeout=3
                    )
                    
                    output = result.stdout.strip().lower()
                    gpu_lines = [line.strip() for line in output.split('\n') if line.strip()]
                    
                    # Remove header
                    if len(gpu_lines) > 1:
                        gpu_lines = gpu_lines[1:]
                    
                    # Log all detected GPUs for debugging
                    self.log(f"Detected GPUs: {gpu_lines}", "INFO")
                    
                    # Check for hybrid graphics (multiple GPUs)
                    has_hybrid_graphics = len(gpu_lines) > 1
                    if has_hybrid_graphics:
                        self.log("Hybrid graphics detected (integrated + dedicated GPU)", "INFO")
                    
                    # Priority order: NVIDIA > RX > Others
                    for gpu in gpu_lines:
                        if 'nvidia' in gpu:
                            self.log(f"NVIDIA GPU detected: {gpu}", "INFO")
                            # Show a hint for hybrid graphics systems
                            if has_hybrid_graphics:
                                self.log("For optimal performance, ensure this application uses your NVIDIA GPU", "WARNING")
                                self.show_hybrid_graphics_hint()
                            return True
                        elif 'rx' in gpu or 'radeon' in gpu and not 'graphics' in gpu:
                            self.log(f"AMD dedicated GPU detected: {gpu}", "INFO")
                            # Show a hint for hybrid graphics systems
                            if has_hybrid_graphics:
                                self.log("For optimal performance, ensure this application uses your AMD GPU", "WARNING")
                                self.show_hybrid_graphics_hint()
                            return True
                    
                    # If no preferred GPU found, check for any discrete GPU
                    for gpu in gpu_lines:
                        if not any(x in gpu for x in ['intel', 'uhd', 'hd graphics', 'radeon(tm)', 'graphics', 'hd']):
                            self.log(f"Discrete GPU detected: {gpu}", "INFO")
                            return True
                    
                    # Integrated graphics found
                    if gpu_lines:
                        self.log(f"Integrated graphics detected: {gpu_lines[0]}", "WARNING")
                        return True
                        
                except Exception as e:
                    self.log(f"GPU detection error: {str(e)}", "WARNING")
            
            # Fallback
            self.log("Using fallback GPU detection", "WARNING")
            return True
            
        except Exception as e:
            self.log(f"GPU detection failed: {str(e)}", "ERROR")
            return True
            
    def show_hybrid_graphics_hint(self):
        """Show a hint dialog for users with hybrid graphics systems"""
        # Check if we've already shown this hint
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    if settings.get('hide_hybrid_graphics_hint', False):
                        return  # Don't show if user chose not to see it again
            except:
                pass  # Continue if settings file can't be read
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Hybrid Graphics Detected")
        dialog.setFixedWidth(500)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border-radius: 10px;
            }}
        """)
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Hybrid Graphics System Detected")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        main_layout.addWidget(title)
        
        # Description
        description = QLabel(
            "Your system has both integrated and dedicated graphics. For best performance "
            "with upscaling, ensure this application uses your dedicated GPU.\n\n"
            "How to set this up:\n"
            "• NVIDIA: Right-click desktop → NVIDIA Control Panel → Manage 3D settings → Program Settings → Add this app\n"
            "• AMD: Right-click desktop → AMD Software → Graphics → Advanced → System → Switchable Graphics → Add this app\n\n"
            "Select 'High Performance' or your dedicated GPU for this application."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"font-size: 12px; color: {COLORS['text']}; margin: 10px 0;")
        main_layout.addWidget(description)
        
        # Don't show again checkbox
        dont_show_check = QCheckBox("Don't show this message again")
        dont_show_check.setStyleSheet(f"font-size: 12px; color: {COLORS['text']};")
        main_layout.addWidget(dont_show_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        understand_btn = QPushButton("I Understand")
        understand_btn.clicked.connect(dialog.accept)
        understand_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['primary']}; 
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 10px; 
                font-weight: 600; 
                font-size: 14px;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['hover']}; 
            }}
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(understand_btn)
        
        main_layout.addLayout(button_layout)
        
        # Save the preference if "Don't show again" is checked
        def on_dialog_closed():
            if dont_show_check.isChecked():
                try:
                    import json
                    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
                    
                    # Load existing settings if available
                    settings = {}
                    if os.path.exists(settings_path):
                        with open(settings_path, 'r') as f:
                            try:
                                settings = json.load(f)
                            except:
                                settings = {}
                    
                    # Update settings
                    settings['hide_hybrid_graphics_hint'] = True
                    
                    # Save settings
                    with open(settings_path, 'w') as f:
                        json.dump(settings, f)
                except:
                    pass
        
        dialog.finished.connect(on_dialog_closed)
        dialog.exec()

    def stop_conversion(self):
        """Stop the conversion thread when cancel is clicked"""
        if hasattr(self, 'thread') and self.thread and self.thread.isRunning():
            # Set a flag to indicate cancellation
            self.thread.cancelled = True
            self.thread.running = False
            
            # Update failure count for remaining files
            if hasattr(self.thread, 'total_files') and hasattr(self.thread, 'processed_files'):
                remaining = self.thread.total_files - self.thread.processed_files
                self.thread.failure_count += remaining
            
            # Call the thread's stop method which handles process termination
            self.thread.stop()  
            self.thread.wait(1000)  # Wait for thread to finish
            
            # Close the progress dialog if it's open
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            # Show cancellation message
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Conversion Cancelled")
            msg_box.setText("The conversion process has been cancelled.")
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
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['hover']};
                }}
            """)
            
            # Add buttons
            if hasattr(self, 'output_dir') and self.output_dir and os.path.exists(self.output_dir):
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
            
            ok_btn = msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            
            # Execute the dialog
            msg_box.exec()
            
            # Handle button clicks
            clicked_button = msg_box.clickedButton()
            if 'open_btn' in locals() and clicked_button == open_btn:
                # Open the output folder
                os.startfile(self.output_dir)
            
            # Reset the convert button
            self.convert_btn.setText("✨ Convert")
            self.update_convert_button_state()
            
            # Clear the thread reference
            self.thread = None

    def get_resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def animate_window(self):
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setStartValue(QRect(self.x(), self.y() - 20, self.width(), self.height()))
        self.animation.setEndValue(QRect(self.x(), self.y(), self.width(), self.height()))
        self.animation.start()

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
        
        
        upscale_layout.addStretch()
        layout.addLayout(upscale_layout)
        
        # Upscale factor selection
        upscale_factor_layout = QHBoxLayout()
        upscale_factor_label = QLabel("Upscale Factor:")
        upscale_factor_label.setFixedWidth(120)
        upscale_factor_layout.addWidget(upscale_factor_label)
        
        self.upscale_combo = AnimatedComboBox()
        self.upscale_combo.addItems(UPSCALE_FACTORS)
        self.upscale_combo.setEnabled(False)
        self.upscale_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #3d3d4f;
                color: #888888;
                border: 1px solid #3d3d4f;
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        upscale_factor_layout.addWidget(self.upscale_combo)
        layout.addLayout(upscale_factor_layout)
        
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
        self.create_action_buttons(layout)
        
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
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
            border-top-left-radius: 10px;
            border-bottom-left-radius: 10px;
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
        self.current_version_label = QLabel("Current Version: 5.3")
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
        copyright_label = QLabel("PSD Converter v5.3 © 2025 Alvanheim Scanlation Group")
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
        
    def switch_settings_tab(self, index, active_btn, inactive_btns):
        """Switch between settings tabs and update button states"""
        self.settings_stack.setCurrentIndex(index)
        active_btn.setChecked(True)
        
        # Handle multiple inactive buttons
        if isinstance(inactive_btns, list):
            for btn in inactive_btns:
                btn.setChecked(False)
        else:
            inactive_btns.setChecked(False)
            
    def check_for_updates(self):
        """Check for updates from GitHub repository"""
        self.update_status.setText("Checking for updates...")
        self.update_status.setStyleSheet(f"color: {COLORS['text']};")
        self.latest_version_label.setText("Latest Version: Checking...")
        
        # Get current version from a version file or hardcoded value
        current_version = "5.3"  # You can replace this with a dynamic version
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
    
    def handle_update_error(self, error_message):
        """Handle errors during update check"""
        self.latest_version_label.setText("Latest Version: Unknown")
        self.update_status.setText(error_message)
        self.update_status.setStyleSheet(f"color: {COLORS['error']};")
        self.release_notes.setHtml(f"""
            <html>
            <body style="font-family: 'Segoe UI', sans-serif; color: {COLORS['text']};">
                <p>Could not retrieve release notes. Please check your internet connection or try again later.</p>
            </body>
            </html>
        """)
        self.log(error_message, "ERROR")
    
    def toggle_auto_refresh(self, state):
        """Toggle automatic log refresh"""
        if state:
            self.update_logger_display()
    
    def on_log_changed(self):
        """Handler for when log content changes"""
        if self.auto_refresh.isChecked():
            self.update_log_statistics(self.log_messages)
            # Auto-scroll only if near bottom
            scrollbar = self.logger_text.verticalScrollBar()
            if scrollbar.value() >= scrollbar.maximum() - 50:
                scrollbar.setValue(scrollbar.maximum())

    def filter_logs(self):
        """Filter logs based on level and search text"""
        level = self.log_level_combo.currentText()
        search = self.log_search.text().lower()
        
        filtered_logs = []
        for log in self.log_messages:
            if level != "All" and f"[{level}]" not in log:
                continue
            if search and search not in log.lower():
                continue
            filtered_logs.append(log)
        
        # Update display with filtered logs
        self.logger_text.clear()
        for log in filtered_logs:
            if "[ERROR]" in log:
                self.logger_text.append(f'<span style="color: {COLORS["error"]};">{log}</span>')
            elif "[WARNING]" in log:
                self.logger_text.append(f'<span style="color: #FFCC00;">{log}</span>')
            elif "[SUCCESS]" in log:
                self.logger_text.append(f'<span style="color: {COLORS["success"]};">{log}</span>')
            elif "[TERMINAL]" in log:
                self.logger_text.append(f'<span style="color: #00BFFF;">{log}</span>')
            else:
                self.logger_text.append(log)
        
        # Update statistics
        self.update_log_statistics(filtered_logs)

    def update_log_statistics(self, logs):
        """Update log statistics display"""
        total = len(logs)
        errors = sum(1 for log in logs if "[ERROR]" in log)
        warnings = sum(1 for log in logs if "[WARNING]" in log)
        success = sum(1 for log in logs if "[SUCCESS]" in log)
        
        stats = f"Total: {total} | Errors: {errors} | Warnings: {warnings} | Success: {success}"
        self.log_stats.setText(stats)

    def copy_logs(self):
        """Copy logs to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.logger_text.toPlainText())
        self.log("Logs copied to clipboard", "SUCCESS")

    def export_html_logs(self):
        """Export logs as formatted HTML"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export HTML Logs", 
            os.path.expanduser("~/Desktop/image_converter_log.html"),
            "HTML Files (*.html)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    html = f"""
                    <html>
                    <head>
                        <style>
                            body {{ font-family: 'Consolas', monospace; background: {COLORS['background']}; color: {COLORS['text']}; padding: 20px; }}
                            .error {{ color: {COLORS['error']}; }}
                            .warning {{ color: #FFCC00; }}
                            .success {{ color: {COLORS['success']}; }}
                            .terminal {{ color: #00BFFF; }}
                        </style>
                    </head>
                    <body>
                        <pre>{self.logger_text.toHtml()}</pre>
                    </body>
                    </html>
                    """
                    f.write(html)
                self.log(f"Logs exported to HTML: {file_path}", "SUCCESS")
            except Exception as e:
                self.log(f"Error exporting HTML: {str(e)}", "ERROR")

    def setup_stdout_redirect(self):
        """Set up redirection of stdout to capture terminal output in the logger"""
        try:
            class StdoutRedirector:
                def __init__(self, logger_instance):
                    self.logger_instance = logger_instance
                    # Store original stdout safely
                    try:
                        self.original_stdout = sys.stdout
                    except Exception:
                        self.original_stdout = None
                    self.buffer = ""
                
                def write(self, text):
                    try:
                        # Write to the original stdout if it exists
                        if self.original_stdout and self.original_stdout != self:
                            try:
                                self.original_stdout.write(text)
                            except Exception:
                                pass  # Silently fail if we can't write to original stdout
                        
                        # Accumulate text until we get a newline
                        self.buffer += text
                        if '\n' in text:
                            lines = self.buffer.split('\n')
                            for line in lines[:-1]:  # Process all complete lines
                                if line.strip():  # Only log non-empty lines
                                    self.logger_instance.log(line, "TERMINAL")
                            self.buffer = lines[-1]  # Keep any partial line
                    except Exception:
                        # Silently fail if there's an error in write
                        pass
                
                def flush(self):
                    try:
                        if self.original_stdout and self.original_stdout != self:
                            try:
                                self.original_stdout.flush()
                            except Exception:
                                pass  # Silently fail if we can't flush original stdout
                        
                        if self.buffer.strip():
                            self.logger_instance.log(self.buffer, "TERMINAL")
                            self.buffer = ""
                    except Exception:
                        # Silently fail if there's an error in flush
                        pass
            
            # Set up the redirector
            self.stdout_redirector = StdoutRedirector(self)
            sys.stdout = self.stdout_redirector
        except Exception as e:
            print(f"Error setting up stdout redirection: {str(e)}")
            # Don't redirect if there's an error
            self.stdout_redirector = None
    
    def log(self, message, level="INFO"):
        """Add a log message to the logger"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {message}"
            
            # Initialize log_messages if it doesn't exist
            if not hasattr(self, 'log_messages'):
                self.log_messages = []
                
            # Add to log messages list
            self.log_messages.append(log_entry)
            
            # Update the logger display if it exists and is initialized
            if hasattr(self, 'logger_text') and self.logger_text is not None:
                try:
                    self.update_logger_display()
                except Exception:
                    pass  # Silently fail if we can't update the logger display
                
            # Print to console as well for debugging, but only if not from terminal
            # to avoid infinite recursion
            if level != "TERMINAL" and hasattr(self, 'stdout_redirector') and self.stdout_redirector is not None:
                try:
                    if (hasattr(self.stdout_redirector, 'original_stdout') and 
                        self.stdout_redirector.original_stdout is not None and
                        self.stdout_redirector.original_stdout != self.stdout_redirector):
                        try:
                            self.stdout_redirector.original_stdout.write(log_entry + "\n")
                        except Exception:
                            pass  # Silently fail if we can't write to original stdout
                except Exception:
                    pass  # Silently fail if there's an error accessing stdout_redirector
        except Exception:
            # Silently fail if logging fails - we don't want to cause more errors
            pass
    
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
    
    def clear_log(self):
        """Clear all log messages"""
        self.log_messages = []
        if hasattr(self, 'logger_text'):
            self.logger_text.clear()
        self.log("Log cleared", "INFO")
    
    def save_log(self):
        """Save log messages to a file"""
        if not self.log_messages:
            self.show_message("No Logs", "There are no log messages to save.", QMessageBox.Icon.Information)
            return
            
        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", os.path.expanduser("~/Desktop/image_converter_log.txt"),
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    for log_entry in self.log_messages:
                        f.write(f"{log_entry}\n")
                self.log(f"Log saved to {file_path}", "SUCCESS")
                self.show_message("Log Saved", f"Log has been saved to:\n{file_path}", QMessageBox.Icon.Information)
            except Exception as e:
                error_msg = f"Error saving log: {str(e)}"
                self.log(error_msg, "ERROR")
                self.show_message("Error", error_msg, QMessageBox.Icon.Critical)
    
    def _create_combo_setting(self, label_text, items):
        """Helper method to create a consistent combo box setting layout"""
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFixedWidth(120)
        layout.addWidget(label)
        
        combo = AnimatedComboBox()
        combo.addItems(items)
        # Remove custom styling to use the AnimatedComboBox default styling
        layout.addWidget(combo)
        
        return layout, combo
    
    def get_current_settings(self):
        """Method to get all current settings as a dictionary"""
        return {
            'jpeg_quality': self.jpeg_quality_combo.currentText(),
            'webp_quality': self.webp_quality_combo.currentText(),
            'png_compression': self.png_compression_combo.currentText(),
            'pdf_dpi': self.pdf_dpi_combo.currentText(),
            'pdf_quality': self.pdf_quality_combo.currentText()
        }


    def initUI(self):
        # Apply theme with Chrome-like tab design
        try:
            # Handle check.png path for PyInstaller
            if hasattr(sys, '_MEIPASS'):
                check_icon_path = os.path.join(sys._MEIPASS, 'check.png')
            else:
                check_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check.png')
            
            # Make sure the path uses forward slashes for CSS
            check_icon_path = check_icon_path.replace('\\', '/')
            
            # Check if the file exists
            if not os.path.exists(check_icon_path):
                # Fallback to a data URI for the check mark
                check_icon = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH4QgPDRknzD4ZXwAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAAdklEQVQoz2NgQAL///9XBGIhIP7JgAf8/PnzDhD/B+L/QGyAT8MFIP4HxReA2BCXhgtQ8SD8H4j1cWm4gKQBhPVxafgPNQSEQXgDLg2KUEOQsQIuDYpIGkBYAZeG/0gagPg/LkuxasAXDhegBiHjC7g0gPAFADhkUP+PuogwAAAAAElFTkSuQmCC"
            else:
                check_icon = f"url('{check_icon_path}')"
        except Exception as e:
            print(f"Error setting up check icon: {str(e)}")
            # Fallback to a data URI for the check mark
            check_icon = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH4QgPDRknzD4ZXwAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAAdklEQVQoz2NgQAL///9XBGIhIP7JgAf8/PnzDhD/B+L/QGyAT8MFIP4HxReA2BCXhgtQ8SD8H4j1cWm4gKQBhPVxafgPNQSEQXgDLg0KUEOQsQIuDYpIGkBYAZeG/0gagPg/LkuxasAXDhegBiHjC7g0gPAFADhkUP+PuogwAAAAAElFTkSuQmCC"

        self.setStyleSheet(f"""
            QWidget {{ 
                background-color: {COLORS['background']}; 
                color: {COLORS['text']}; 
                font-family: 'Segoe UI', Arial, sans-serif; 
            }}
            QTabWidget::pane {{ 
                border: none; 
                background: {COLORS['panel']}; 
                border-radius: 10px;
                margin-top: 0px;
            }}
            QTabBar::tab {{ 
                background: {COLORS['background']}; 
                color: {COLORS['text']}; 
                padding: 12px 35px;
                border: none;
                margin-right: 4px;
                font-weight: 500;
                font-size: 13px;
                min-width: 120px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{ 
                background: {COLORS['panel']}; 
                color: {COLORS['text']};
                font-weight: 600;
            }}
            QTabBar::tab:!selected {{ 
                background: {COLORS['background']}; 
                border-radius: 8px;
                padding: 0px 0px;
                margin: 6px 7px 6px 2px;
                min-width: 120px;
                padding: 12px 35px;
            }}
            QTabBar::tab:hover:!selected {{
                background: {COLORS['!tab']}; 
                border-radius: 8px;
                padding: 0px 0px;
                margin: 6px 7px 6px 2px;
            }}
            QTabWidget {{ 
                background: transparent;
            }}
            QFrame {{ 
                border-radius: 10px; 
            }}

            QCheckBox {{
                spacing: 8px;
                color: {COLORS['text']};
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['background']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS['primary']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
                image: {check_icon};
                padding: 0px;
            }}
            QCheckBox:disabled {{
                color: {COLORS['text_secondary']};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {COLORS['background']};
                border-color: {COLORS['border']};
            }}
        """)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)  # Adjusted left margin to 15
        main_layout.setSpacing(0)  # Remove spacing between tab and content

        # Create tab widget with standard tab bar
        tab_widget = QTabWidget()
        tab_widget.setContentsMargins(0, 0, 0, 0)

        # Create Home tab (Converter)
        home_tab = QWidget()
        home_layout = QHBoxLayout(home_tab)
        home_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        home_layout.setSpacing(0)
        
        # Add converter settings and file panel to Home tab
        converter_panel = self.create_converter_panel()
        file_panel = self.create_right_panel()
        home_layout.addWidget(converter_panel, 2)
        home_layout.addWidget(file_panel, 3)

        # Create Upscaler tab
        upscaler_tab = QWidget()
        upscaler_layout = QHBoxLayout(upscaler_tab)
        upscaler_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        upscaler_layout.setSpacing(0)
        
        # Add upscaler settings and file panel to Upscaler tab
        upscaler_panel = self.create_upscaler_panel()
        upscaler_file_panel = self.create_upscaler_right_panel()
        upscaler_layout.addWidget(upscaler_panel, 2)
        upscaler_layout.addWidget(upscaler_file_panel, 3)

        # In the initUI method, after creating the tab widget
        denoiser_tab = QWidget()
        denoiser_layout = QHBoxLayout(denoiser_tab)
        denoiser_layout.setContentsMargins(0, 0, 0, 0)
        denoiser_layout.setSpacing(0)

        # Add denoiser settings and file panel
        denoiser_panel = self.create_denoiser_panel()
        denoiser_file_panel = self.create_denoiser_right_panel()
        denoiser_layout.addWidget(denoiser_panel, 2)
        denoiser_layout.addWidget(denoiser_file_panel, 3)
        
        # Create Image Stitcher tab
        stitcher_tab = QWidget()
        stitcher_layout = QHBoxLayout(stitcher_tab)
        stitcher_layout.setContentsMargins(0, 0, 0, 0)
        stitcher_layout.setSpacing(0)
        
        # Add stitcher settings and file panel
        stitcher_panel = self.create_stitcher_panel()
        stitcher_file_panel = self.create_stitcher_right_panel()
        stitcher_layout.addWidget(stitcher_panel, 2)
        stitcher_layout.addWidget(stitcher_file_panel, 3)

        # Create Settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        settings_layout.setSpacing(10)

        # Add settings panel
        settings_panel = self.create_settings_panel()
        settings_layout.addWidget(settings_panel)

        # Add tabs
        tab_widget.addTab(home_tab, "🏠 Converter")
        tab_widget.addTab(upscaler_tab, "🔍 Upscaler")
        tab_widget.addTab(denoiser_tab, "🧹 Denoiser")
        tab_widget.addTab(stitcher_tab, "🧵 Stitcher")
        tab_widget.addTab(settings_tab, "⚙️ Settings")
        
        main_layout.addWidget(tab_widget)

        # Add footer
        self.add_footer(main_layout)
        
        self.setLayout(main_layout)
        
    def toggle_noise_level_visibility(self, visible):
        """Show or hide the noise level selection based on the selected model"""
        # Check if the noise level combo exists
        if hasattr(self, 'noise_level_combo'):
            self.noise_level_combo.setVisible(visible)
            
        # Find the noise level label (it's usually next to the combo)
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLabel) and "Noise Level:" in item.widget().text():
                item.widget().setVisible(visible)
                break

    def toggle_waifu2x_options(self, model_text, noise_label, noise_combo, style_label, style_combo):
        """Show or hide waifu2x-specific options based on the selected model"""
        is_waifu2x = model_text.lower() == "waifu2x"
        noise_label.setVisible(is_waifu2x)
        noise_combo.setVisible(is_waifu2x)
        style_label.setVisible(is_waifu2x)
        style_combo.setVisible(is_waifu2x)                
    
    def on_upscaler_model_changed(self, model_name):
        """Handle changes to the upscaler model selection"""
        # Show noise level selection only for waifu2x model
        is_waifu2x = model_name.lower() == "waifu2x"
        
        # Enable/disable CPU checkbox based on model
        # ESR models don't support CPU processing
        if is_waifu2x:
            self.use_cpu_checkbox.setEnabled(True)
            self.use_cpu_checkbox.setText("Use CPU (slower)")
            
            # Update scale factors for waifu2x (include 1x)
            self.upscaler_factor_combo.clear()
            self.upscaler_factor_combo.addItems(["1x", "2x", "3x", "4x"])
        else:
            self.use_cpu_checkbox.setChecked(False)  # Uncheck when ESR is selected
            self.use_cpu_checkbox.setEnabled(False)  # Disable when ESR is selected
            self.use_cpu_checkbox.setText("Use CPU (Not Supported)")
            
            # Update scale factors for realesr (exclude 1x)
            self.upscaler_factor_combo.clear()
            self.upscaler_factor_combo.addItems(["2x", "3x", "4x"])
        
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
        
        self.use_cpu_checkbox = QCheckBox("Use CPU (slower)")
        self.use_cpu_checkbox.setChecked(False)
        self.use_cpu_checkbox.setStyleSheet("font-size: 8pt;")
        model_layout.addWidget(self.use_cpu_checkbox)
        
        # Initialize CPU checkbox state based on the default selected model
        initial_model = self.upscaler_model_combo.currentText()
        is_waifu2x = initial_model.lower() == "waifu2x"
        self.use_cpu_checkbox.setEnabled(is_waifu2x)
        if not is_waifu2x:
            self.use_cpu_checkbox.setText("Use CPU (Not Supported)")

        layout.addLayout(model_layout)
        
        # Create waifu2x options container
        waifu2x_options_container = QWidget()
        waifu2x_options_layout = QHBoxLayout(waifu2x_options_container)
        waifu2x_options_layout.setSpacing(20)
        waifu2x_options_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add noise level selection for waifu2x
        noise_level_label = QLabel("Noise Level:")
        self.noise_level_combo = AnimatedComboBox()
        self.noise_level_combo.addItems(["-1 (None)", "0 (Low)", "1 (Light)", "2 (Medium)", "3 (High)"])
        self.noise_level_combo.setCurrentIndex(1)  # Default to low noise reduction
        waifu2x_options_layout.addWidget(noise_level_label)
        waifu2x_options_layout.addWidget(self.noise_level_combo)
        
        # Add style selection
        style_label = QLabel("Style:")
        self.waifu2x_model_combo = AnimatedComboBox()
        
        # Create a dictionary to map display names to actual model values
        style_options = {
            "CUnet (Best Quality)": "models-cunet",
            "Upconv (Anime/Art)": "models-upconv_7_anime_style_art_rgb",
            "Upconv (Photo)": "models-upconv_7_photo"
        }
        
        # Add the display names to the combo box
        self.waifu2x_model_combo.addItems(list(style_options.keys()))
        self.waifu2x_model_combo.setCurrentIndex(0)  # Default to cunet
        
        # Store the mapping for later use
        self.waifu2x_model_combo.setProperty("modelMapping", style_options)
        
        waifu2x_options_layout.addWidget(style_label)
        waifu2x_options_layout.addWidget(self.waifu2x_model_combo)
        
        # Initially hide waifu2x options container
        waifu2x_options_container.setVisible(is_waifu2x)
        
        # Add the container to the main layout
        layout.addWidget(waifu2x_options_container)
        
        # Connect model selection to show/hide waifu2x options
        self.upscaler_model_combo.currentTextChanged.connect(
            lambda text: waifu2x_options_container.setVisible(text.lower() == "waifu2x")
        )
                
        # Upscale factor selection
        upscale_factor_layout = QHBoxLayout()
        upscale_factor_label = QLabel("Upscale Factor:")
        upscale_factor_label.setFixedWidth(120)
        upscale_factor_layout.addWidget(upscale_factor_label)
        
        self.upscaler_factor_combo = AnimatedComboBox()
        # Initialize with appropriate scale factors based on the initial model
        if is_waifu2x:
            self.upscaler_factor_combo.addItems(["1x", "2x", "3x", "4x"])
        else:
            self.upscaler_factor_combo.addItems(["2x", "3x", "4x"])
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
        self.create_upscaler_action_buttons(layout)
        
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

    def natural_sort_key(self, s):
        """Natural sort key function for sorting filenames with numbers correctly"""
        import re
        return [int(text) if text.isdigit() else text.lower() 
                for text in re.split('([0-9]+)', os.path.basename(s))]

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

    def clear_files(self):
        """Clear all files from the file list"""
        self.files = []
        self.file_checkboxes = []

                # Clear the output directory
        self.output_dir = ""
        self.output_dir_label.setText("No output directory selected")
        self.output_dir_label.setStyleSheet("color: #888888; padding: 10px;")
        
        # Clear the file container
        for i in reversed(range(self.file_container.layout().count())):
            widget = self.file_container.layout().itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        # Add the placeholder label
        self.file_label = QLabel("No files selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #888888; padding: 10px;")
        self.file_container.layout().addWidget(self.file_label)
        
        # Update the convert button state
        self.update_convert_button_state()        
    
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
        # Check if any files are selected and output directory is set
        files_selected = False
        if hasattr(self, 'upscaler_file_checkboxes') and self.upscaler_file_checkboxes:
            for checkbox in self.upscaler_file_checkboxes:
                try:
                    if checkbox.isChecked():
                        files_selected = True
                        break
                except RuntimeError:
                    continue
        
        # Enable the upscale button if files are selected and output directory is set
        has_output_dir = hasattr(self, 'upscaler_output_dir') and bool(self.upscaler_output_dir)
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
    
    def select_denoise_output_dir(self):
        """This is a duplicate method - use set_denoiser_output_dir instead"""
        return self.set_denoiser_output_dir()

    def toggle_output_format(self, state):
        """Toggle output format combo box based on checkbox state"""
        if self.keep_format_check.isChecked():
            self.upscaler_format_combo.setEnabled(False)
            self.upscaler_format_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: #3d3d4f;
                    color: #888888;
                    border: 1px solid #3d3d4f;
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
            """)
        else:
            self.upscaler_format_combo.setEnabled(True)
            self.upscaler_format_combo.setStyleSheet(f"""
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
    
    def start_upscaling(self):
        """Start the upscaling process"""
        # Get selected files
        selected_files = []
        for checkbox in self.upscaler_file_checkboxes:
            if checkbox.isChecked():
                selected_files.append(checkbox.file_path)
        
        if not selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to upscale.")
            return
        
        if not self.upscaler_output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select an output directory.")
            return
        
        # Check if this is a repeated upscaling to the same output folder
        should_continue = True
        if hasattr(self, 'last_upscaler_output_dir') and self.last_upscaler_output_dir == self.upscaler_output_dir:
            # Show warning about potential file overwriting
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Warning: Same Output Folder")
            msg_box.setText("You are using the same output folder as your previous upscaling.")
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
            elif clicked_button == change_folder_btn:
                # Open folder selection dialog
                self.set_upscaler_output_dir()
                # Check if user actually selected a new folder
                if self.upscaler_output_dir != self.last_upscaler_output_dir:
                    # Make sure the folder icon is displayed
                    self.upscaler_output_dir_label.setText(f"📁 {self.upscaler_output_dir}")
                    should_continue = True
                else:
                    should_continue = False
        
        # Log the start of upscaling
        self.log(f"Starting upscaling of {len(selected_files)} files with {self.upscaler_factor_combo.currentText()} factor", "INFO")

        # Store current output dir for future reference
        self.last_upscaler_output_dir = self.upscaler_output_dir
        
        # If user chose not to continue, exit the method
        if not should_continue:
            return

        # Get upscaling options
        upscale_factor = self.upscaler_factor_combo.currentText()
        model = self.upscaler_model_combo.currentText()
        
        # Check if CPU mode is enabled
        use_cpu = self.use_cpu_checkbox.isChecked()

        # For waifu2x, get the actual model value from the display name
        waifu2x_model = "models-cunet"  # Default model
        if model.lower() == "waifu2x":
            display_name = self.waifu2x_model_combo.currentText()
            model_mapping = self.waifu2x_model_combo.property("modelMapping")
            waifu2x_model = model_mapping[display_name]
        
        # Get noise level if waifu2x is selected
        noise_level = 1  # Default to medium noise reduction
        if model.lower() == "waifu2x" and hasattr(self, 'noise_level_combo'):
            noise_level_text = self.noise_level_combo.currentText().split()[0]
            try:
                noise_level = int(noise_level_text)
            except ValueError:
                # Keep default if parsing fails
                pass
        
        # Always use original format instead of keep_format_check
        keep_format = True
        output_format = "PNG"
        
        # Clean up any existing thread
        if hasattr(self, 'upscaler_thread') and self.upscaler_thread:
            try:
                self.upscaler_thread.progress_signal.disconnect()
                self.upscaler_thread.completion_signal.disconnect()
                self.upscaler_thread.error_signal.disconnect()
            except:
                pass
        
        # Create and start the upscaler thread
        self.upscaler_thread = UpscalerThread(
            selected_files,
            self.upscaler_output_dir,
            upscale_factor=upscale_factor,
            model=model,
            keep_format=keep_format,
            output_format=output_format if output_format else "PNG",
            noise_level=noise_level,
            waifu2x_model=waifu2x_model,  # Pass the waifu2x model
            use_cpu=use_cpu  # Pass the CPU preference
        )
        
        # Connect signals
        self.upscaler_thread.progress_signal.connect(self.update_upscaler_progress)
        self.upscaler_thread.completion_signal.connect(self.upscaling_completed)
        self.upscaler_thread.error_signal.connect(self.upscaling_error)
        self.upscaler_thread.log_signal.connect(self.log)
        
        # Create progress dialog
        if hasattr(self, 'upscaler_progress_dialog') and self.upscaler_progress_dialog:
            self.upscaler_progress_dialog.close()
            self.upscaler_progress_dialog.deleteLater()
        
        self.upscaler_progress_dialog = UpscalerProgressDialog(self)
        self.upscaler_progress_dialog.cancel_btn.clicked.connect(self.stop_upscaling)
        
        # Update button text
        self.upscale_btn.setText("Upscaling...")
        self.upscale_btn.setEnabled(False)
        
        # Start thread and show dialog
        self.upscaler_thread.start()
        self.upscaler_progress_dialog.exec()
    
    def update_upscaler_progress(self, value, eta_text, speed_text):
        """Update the upscaler progress dialog"""
        if self.upscaler_progress_dialog:
            self.upscaler_progress_dialog.update_progress(value, eta_text, speed_text)
    
    def upscaling_completed(self, last_output_path, input_size, output_size, success_count, failure_count):
        """Show a completion message for upscaling with statistics"""
        # First close the progress dialog if it's still open
        if hasattr(self, 'upscaler_progress_dialog') and self.upscaler_progress_dialog and self.upscaler_progress_dialog.isVisible():
            self.upscaler_progress_dialog.accept()
            self.upscaler_progress_dialog = None
            
        # Don't show completion message if the operation was cancelled
        if hasattr(self, 'upscaler_thread') and self.upscaler_thread and self.upscaler_thread.cancelled:
            # Reset the upscale button
            self.upscale_btn.setText("✨ Upscale")
            self.update_upscale_button_state()
            # Clear the thread reference to prevent multiple dialogs
            self.upscaler_thread = None
            return
            
        # Format sizes in MB
        input_mb = input_size / (1024 * 1024)
        output_mb = output_size / (1024 * 1024)
        
        # Calculate size increase percentage
        if input_size > 0:
            increase = ((output_size - input_size) / input_size) * 100
            size_text = f"Size increased by {increase:.1f}%"
        else:
            size_text = "Size comparison not available"
        
        # Create message with failed files information
        message = f"Upscaling completed!\n\n"
        message += f"Files processed: {success_count} successful, {failure_count} failed\n"
        message += f"Input size: {input_mb:.2f} MB\n"
        message += f"Output size: {output_mb:.2f} MB\n"
        message += f"{size_text}\n\n"
        
        # Add failed files information if any
        if hasattr(self.upscaler_thread, 'failed_files') and self.upscaler_thread.failed_files:
            message += "Failed files:\n"
            for file, error in self.upscaler_thread.failed_files.items():
                message += f"• {os.path.basename(file)}: {error}\n"

        # Show styled message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Upscaling Completed")
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
        
        # Show dialog and handle response
        msg_box.exec()
        
        # Handle button clicks
        if msg_box.clickedButton() == open_btn:
            # Open the output folder
            output_dir = os.path.dirname(last_output_path) if last_output_path else self.upscaler_output_dir
            if output_dir and os.path.exists(output_dir):
                os.startfile(output_dir)

        # Reset the upscale button
        self.upscale_btn.setText("✨ Upscale")
        self.update_upscale_button_state()

        # Log completion
        self.log(f"Upscaling completed: {success_count} succeeded, {failure_count} failed", 
                "SUCCESS" if failure_count == 0 else "INFO")

    def upscaling_error(self, error_message, error_type):
        """Handle upscaling errors"""
        QMessageBox.warning(self, "Upscaling Error", error_message)
    
    def denoising_error(self, error_message, error_type):
        """Handle denoising errors"""
        QMessageBox.warning(self, "denoising Error", error_message)    

    def stop_upscaling(self):
        """Stop the upscaling thread"""
        if not hasattr(self, 'upscaler_thread') or not self.upscaler_thread:
            return
            
        # Set flags to stop the thread gracefully
        self.upscaler_thread.running = False
        self.upscaler_thread.cancelled = True
        
        # Use the stop method instead
        self.upscaler_thread.stop()
        
        # Disable the cancel button to prevent multiple clicks
        if hasattr(self, 'upscaler_progress_dialog') and self.upscaler_progress_dialog:
            self.upscaler_progress_dialog.cancel_btn.setEnabled(False)
            self.upscaler_progress_dialog.cancel_btn.setText("Cancelling...")
            # Close the progress dialog immediately
            self.upscaler_progress_dialog.accept()
            self.upscaler_progress_dialog = None
        
        # Show cancellation message
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Upscaling Cancelled")
        msg_box.setText("The upscaling process has been cancelled.")
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
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        
        # Add buttons
        if self.upscaler_output_dir and os.path.exists(self.upscaler_output_dir):
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
        
        ok_btn = msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        ok_btn.setStyleSheet(f"""
            background-color: {COLORS['secondary']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-width: 150px;
        """)
        
        # Show dialog and handle response
        msg_box.exec()
        
        # Handle button clicks
        if hasattr(msg_box, 'clickedButton') and 'open_btn' in locals() and msg_box.clickedButton() == open_btn:
            # Open the output folder
            if self.upscaler_output_dir and os.path.exists(self.upscaler_output_dir):
                os.startfile(self.upscaler_output_dir)
                
        # Reset the upscale button
        self.upscale_btn.setText("✨ Upscale")
        self.update_upscale_button_state()
        
        # Clear the thread reference to prevent multiple dialogs
        self.upscaler_thread = None

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
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
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
            <li><b>Scale Factor:</b> Choose between 2x, 3x, or 4x enlargement</li>
            <li><b>Model:</b> Select the AI model that best suits your image type</li>
            <li><b>Output Format:</b> Select the file format for your upscaled images</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 3: Set Output Directory</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Set Output Directory</b> to choose where upscaled images will be saved<br>• If not selected, you'll be prompted to choose a location before processing begins</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 4: Start Upscaling</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click the <b>Upscale Images</b> button to start the upscaling process<br>• A progress dialog will show the current status<br>• You can cancel the process at any time<br>• When complete, a summary dialog will show success/failure counts</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Available Models</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>realesr-animevideov3:</b> Optimized for anime and animation style images with good detail preservation</li>
            <li><b>waifu2x:</b> Excellent for anime/manga style images with multiple noise reduction options</li>
            <li><b style="color: #0078d4;">More models coming soon!</b> We're constantly working to add more specialized AI models</li>
        </ul>
        
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
    
    def show_system_info(self):
        """Check system compatibility for AI upscaling"""
        # Create a dialog to display system information
        dialog = QDialog(self)
        dialog.setWindowTitle("System Compatibility Check")
        dialog.setMinimumSize(500, 400)
        dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("System Compatibility for AI Upscaling")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Check for RealESRGAN executable
        realesrgan_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "esr", "realesrgan-ncnn-vulkan.exe")
        has_realesrgan = os.path.exists(realesrgan_path)
        
        # Create status indicators
        realesrgan_status = QLabel(f"AI Upscaler: {'✅ Found' if has_realesrgan else '❌ Not Found'}")
        realesrgan_status.setStyleSheet(f"font-size: 12pt; color: {'#34c759' if has_realesrgan else '#FF3B30'};")
        layout.addWidget(realesrgan_status)
        
        # Check for Vulkan support
        vulkan_status = QLabel("Checking Vulkan support...")
        vulkan_status.setStyleSheet("font-size: 12pt;")
        layout.addWidget(vulkan_status)
        
        # RAM check
        try:
            import psutil
            ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
            ram_status = QLabel(f"System RAM: {ram_gb} GB {'✅ Sufficient' if ram_gb >= 4 else '⚠️ Low'}")
            ram_status.setStyleSheet(f"font-size: 12pt; color: {'#34c759' if ram_gb >= 4 else '#FFCC00'};")
        except ImportError:
            ram_status = QLabel("System RAM: Unable to check")
            ram_status.setStyleSheet("font-size: 12pt; color: #FFCC00;")
        layout.addWidget(ram_status)
        
        # Additional information
        info_text = QLabel("""
        <h3>Requirements for optimal performance:</h3>
        <ul>
            <li>GPU with Vulkan support</li>
            <li>4GB+ RAM (8GB+ recommended for 4x upscaling)</li>
            <li>The AI upscaler executable must be in the 'esr' folder</li>
        </ul>
        
        <h3>Troubleshooting:</h3>
        <ul>
            <li>If the upscaler is not found, ensure the 'esr' folder contains 'realesrgan-ncnn-vulkan.exe'</li>
            <li>If Vulkan is not supported, update your graphics drivers or use a computer with a compatible GPU</li>
            <li>For memory errors, try upscaling smaller images or using a lower upscaling factor</li>
        </ul>
        """)
        info_text.setTextFormat(Qt.TextFormat.RichText)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("font-size: 11pt; line-height: 1.4; margin-top: 10px;")
        layout.addWidget(info_text)
        
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
        
        # Check Vulkan support in a separate thread to avoid UI freezing
        def check_vulkan():
            try:
                # Try to run the upscaler with --help to see if it works
                if has_realesrgan:
                    startupinfo = None
                    if os.name == 'nt':  # Windows
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = 0  # SW_HIDE
                    
                    result = subprocess.run(
                        [realesrgan_path, "--help"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    # If the command runs without error, Vulkan is likely supported
                    if result.returncode == 0:
                        vulkan_status.setText("Vulkan Support: ✅ Available")
                        vulkan_status.setStyleSheet("font-size: 12pt; color: #34c759;")
                        self.vulkan_support = True
                    else:
                        error_output = result.stderr.decode()
                        if "vulkan" in error_output.lower():
                            vulkan_status.setText("Vulkan Support: ❌ Not Available")
                            vulkan_status.setStyleSheet("font-size: 12pt; color: #FF3B30;")
                        else:
                            vulkan_status.setText("Vulkan Support: ⚠️ Unknown")
                            vulkan_status.setStyleSheet("font-size: 12pt; color: #FFCC00;")
                else:
                    vulkan_status.setText("Vulkan Support: ⚠️ Cannot check (upscaler not found)")
                    vulkan_status.setStyleSheet("font-size: 12pt; color: #FFCC00;")
            except Exception as e:
                vulkan_status.setText(f"Vulkan Support: ⚠️ Error checking ({str(e)})")
                vulkan_status.setStyleSheet("font-size: 12pt; color: #FFCC00;")
        
        # Run the Vulkan check in a separate thread
        import threading
        vulkan_thread = threading.Thread(target=check_vulkan)
        vulkan_thread.daemon = True
        vulkan_thread.start()
        
        dialog.exec()

    def add_footer(self, layout):
        """Add a footer with links and version info directly in the main layout"""
        # Create a footer section without a separate frame
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 15, 15, 0)
        
        # Version info
        version_label = QLabel("Version v5.3")
        version_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        footer_layout.addWidget(version_label)
        
        footer_layout.addStretch()
        
        # Contact button with dropdown menu
        contact_btn = QPushButton("Contact")
        contact_btn.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "contact.png")))
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
        
        # Create contact menu
        contact_menu = QMenu(self)
        contact_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 12px;
                min-width: 80px;
            }}
            QMenu::item {{
                padding: 10px 25px 10px 15px;
                background-color: {COLORS['panel']};
                border-radius: 10px;
                margin: 3px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['!tab']};
                color: white;
                font-weight: bold;
                padding: 10px 25px 10px 15px;
                border-radius: 12px;
                margin: 0px;
            }}
            QMenu::icon {{
                padding-right: 20px;
            }}
        """)
        
        # Add contact options with appropriate icons
        email_action = contact_menu.addAction("Email")
        email_action.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "mail.png")))
        email_action.triggered.connect(lambda: self.open_url("mailto:gamangupta777@gmail.com"))
        
        instagram_action = contact_menu.addAction("Instagram")
        instagram_action.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "instagram.png")))
        instagram_action.triggered.connect(lambda: self.open_url("https://www.instagram.com/gupta_aman_777/"))
        
        discord_user_action = contact_menu.addAction("Discord")
        discord_user_action.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "discord.png")))
        discord_user_action.triggered.connect(lambda: self.open_url("https://discordapp.com/users/1006449075882835968/"))
        
        discord_server_action = contact_menu.addAction("Discord Server")
        discord_server_action.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "discord.png")))
        discord_server_action.triggered.connect(lambda: self.open_url("https://discord.gg/GCrthAhBmy"))
        
        contact_btn.setMenu(contact_menu)
        footer_layout.addWidget(contact_btn)
        
        # Add spacing between buttons
        spacer = QLabel()
        spacer.setFixedWidth(15)
        footer_layout.addWidget(spacer)
        
        # Donation button with proper spacing and improved styling
        donate_btn = QPushButton("Donate")
        donate_btn.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "donate.png")))
        donate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
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
        donate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        donate_btn.clicked.connect(lambda: self.open_url("https://razorpay.me/@alvanheim"))
        footer_layout.addWidget(donate_btn)
        
        # Add spacing between buttons
        spacer2 = QLabel()
        spacer2.setFixedWidth(15)
        footer_layout.addWidget(spacer2)
        
        # GitHub link with improved styling
        github_btn = QPushButton("GitHub")
        github_btn.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "github.png")))
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
    
    def open_url(self, url):
        """Open a URL in the default browser"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            self.log(f"Error opening URL: {str(e)}", "ERROR")

    def create_right_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-top-right-radius: 10px; border-bottom-right-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # File list header (kept in right panel)
        file_header = QLabel("Selected Files:")
        file_header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 5px;")
        layout.addWidget(file_header)
        
        # Create a container for the scroll area with rounded corners
        scroll_container = QFrame()
        scroll_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 10px;")
        scroll_container_layout = QVBoxLayout(scroll_container)
        scroll_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # File list scroll area with improved styling
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(120)  # Increased height
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)  # Remove frame
        self.scroll_area.setStyleSheet(f"""
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
        self.file_container = QWidget()
        self.file_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 8px;") 
        file_layout = QVBoxLayout(self.file_container)
        file_layout.setContentsMargins(10, 10, 10, 10)
        file_layout.setSpacing(5)
        
        # Enable drag and drop for file container
        self.file_container.setAcceptDrops(True)
        
        # Override drag and drop events for file container
        self.file_container.dragEnterEvent = self.dragEnterEvent
        self.file_container.dragLeaveEvent = self.dragLeaveEvent
        self.file_container.dropEvent = self.dropEvent
        self.file_container.dragMoveEvent = self.dragMoveEvent
        
        # Store original style to restore after drag leave
        self.original_file_container_style = self.file_container.styleSheet()
        
        self.file_label = QLabel("No files selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #888888; padding: 10px;")
        file_layout.addWidget(self.file_label)
        
        self.scroll_area.setWidget(self.file_container)
        scroll_container_layout.addWidget(self.scroll_area)
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
        
        self.output_dir_label = QLabel("No output directory selected")
        self.output_dir_label.setWordWrap(True)
        self.output_dir_label.setStyleSheet("color: #888888; padding: 10px;")
        output_layout.addWidget(self.output_dir_label)
        
        output_container.setLayout(output_layout)
        layout.addWidget(output_container)

        return panel

    def dragEnterEvent(self, event):
        """Handle drag enter event for file container"""
        if event.mimeData().hasUrls():
            # Change style to indicate drop area
            self.file_container.setStyleSheet(f"""
                background-color: {COLORS['hover']}; 
                border-radius: 8px;
                border: 2px dashed {COLORS['primary']};
            """)
            
            # Store the original widgets before clearing the layout
            if not hasattr(self, 'original_widgets'):
                self.original_widgets = []
                layout = self.file_container.layout()
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if widget:
                        self.original_widgets.append(widget)
                        widget.setParent(None)  # Remove from layout without deleting
            
            # Clear the current layout
            while self.file_container.layout().count():
                item = self.file_container.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            
            # Add drop indicator label
            self.drop_indicator_label = QLabel("DROP FILES HERE")
            self.drop_indicator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.drop_indicator_label.setStyleSheet(f"""
                color: {COLORS['text']};
                font-size: 18px;
                font-weight: bold;
                background-color: {COLORS['primary']};
                padding: 15px;
                border-radius: 8px;
                opacity: 0.8;
            """)
            
            # Add to the existing layout
            self.file_container.layout().addWidget(self.drop_indicator_label, alignment=Qt.AlignmentFlag.AlignCenter)
            
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave event for file container"""
        # Restore original style
        if hasattr(self, 'original_file_container_style'):
            self.file_container.setStyleSheet(self.original_file_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'drop_indicator_label') and self.drop_indicator_label:
            self.drop_indicator_label.setParent(None)
            self.drop_indicator_label = None
        
        # Clear the current layout
        while self.file_container.layout().count():
            item = self.file_container.layout().takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Restore original widgets
        if hasattr(self, 'original_widgets') and self.original_widgets:
            for widget in self.original_widgets:
                self.file_container.layout().addWidget(widget)
            self.original_widgets = []
        
        event.accept()

    def dragMoveEvent(self, event):
        """Handle drag move event for file container"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle drop event for file container"""
        # Restore original style
        if hasattr(self, 'original_file_container_style'):
            self.file_container.setStyleSheet(self.original_file_container_style)
        
        # Remove drop indicator
        if hasattr(self, 'drop_indicator_label') and self.drop_indicator_label:
            self.drop_indicator_label.setParent(None)
            self.drop_indicator_label = None
        
        # Restore original widgets
        if hasattr(self, 'original_widgets') and self.original_widgets:
            for widget in self.original_widgets:
                self.file_container.layout().addWidget(widget)
            self.original_widgets = []
        
        if event.mimeData().hasUrls():
            # Store existing files to avoid duplicates
            existing_files = set(self.files)
            initial_file_count = len(self.files)
            folder_paths = set()  # Track folders for display
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.files:
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
                            if any(file.lower().endswith(f".{fmt.lower()}") for fmt in INPUT_FORMATS):
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
                elif os.path.isfile(path) and any(path.lower().endswith(f".{fmt.lower()}") for fmt in INPUT_FORMATS):
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
                self.selected_folder = list(folder_paths)[0] if len(folder_paths) == 1 else "Multiple Folders"
            
            if new_files:
                # Add new files to the existing list
                self.files.extend(new_files)
                
                # Sort all files using natural sort
                self.files.sort(key=self.natural_sort_key)
                
                # Update the UI with all files
                self.add_files_to_list(self.files)
                self.update_convert_button_state()
                
                # Show warning if files were skipped
                if skipped_files:
                    self.show_duplicate_warning(skipped_files)
            else:
                # No valid files were found, but we still need to update the UI
                # to show the drop folder label and provide feedback
                self.add_files_to_list(self.files)
                
                # If no files were added but folders were dropped, show a styled message
                if folder_paths and len(self.files) == initial_file_count and not skipped_files:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("No Valid Files")
                    msg_box.setText("No supported image files were found in the dropped folders.")
                    msg_box.setInformativeText(f"Supported formats: {', '.join(INPUT_FORMATS)}")
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

    def process_dropped_folder_keep_existing(self, folder_path, existing_files):
        """Process a dropped folder to extract all supported files while keeping existing files"""
        supported_extensions = tuple(f'.{ext.lower()}' for ext in INPUT_FORMATS)
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(supported_extensions):
                    file_path = os.path.join(root, file)
                    if file_path not in existing_files:
                        self.files.append(file_path)
        
        # Set the selected folder for reference if not already set
        if not hasattr(self, 'selected_folder') or not self.selected_folder:
            self.selected_folder = folder_path

    def process_dropped_folder(self, folder_path):
        """Process a dropped folder to extract all supported files"""
        supported_extensions = tuple(f'.{ext.lower()}' for ext in INPUT_FORMATS)
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(supported_extensions):
                    self.files.append(os.path.join(root, file))
        
        # Set the selected folder for reference
        self.selected_folder = folder_path

    def create_action_buttons(self, layout):
        """Create action buttons for the converter panel"""
        # Create a grid layout for the buttons
        button_layout = QGridLayout()
        button_layout.setSpacing(10)
        
        # Add Files button
        add_files_btn = QPushButton("📁 Add Files")
        add_files_btn.setFont(QFont("Segoe UI", 10))
        add_files_btn.setFixedHeight(40)
        add_files_btn.clicked.connect(self.add_files)
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
        add_folder_btn.clicked.connect(self.add_folder)
        add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder_btn.setStyleSheet(add_files_btn.styleSheet())
        button_layout.addWidget(add_folder_btn, 0, 1)
        
        # Clear Files button (red color)
        clear_files_btn = QPushButton("🚫 Clear Files")
        clear_files_btn.setFont(QFont("Segoe UI", 10))
        clear_files_btn.setFixedHeight(40)
        clear_files_btn.clicked.connect(self.clear_files)
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
        set_output_btn.clicked.connect(self.select_output_dir)
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
    
    def add_files(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(f"Supported Files (*.{' *.'.join(map(str.lower, INPUT_FORMATS))})")
        
        if file_dialog.exec():
            # Get the new files
            new_files = file_dialog.selectedFiles()
            
            # Keep existing files and add new ones, avoiding duplicates
            existing_files = set(self.files)
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.files:
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
                        self.files.append(file_path)
                        existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Natural sort files
            def natural_sort_key(s):
                import re
                return [int(text) if text.isdigit() else text.lower()
                        for text in re.split('([0-9]+)', s)]
            
            # Sort files using natural sort
            self.files.sort(key=natural_sort_key)
            
            # Get the parent directory of the first selected file if not already set
            if not hasattr(self, 'selected_folder') or not self.selected_folder:
                if self.files:
                    self.selected_folder = os.path.dirname(self.files[0])
            
            # Show warning if files were skipped
            if skipped_files:
                self.show_duplicate_warning(skipped_files)
                    
            self.add_files_to_list(self.files)
            self.update_convert_button_state()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
        if folder:
            # Store existing files to avoid duplicates
            existing_files = set(self.files)
            
            # Track existing filenames and extensions to prevent duplicates
            existing_name_ext_pairs = set()
            skipped_files = []
            
            # Build the set of existing filename+extension pairs
            for file_path in self.files:
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Find all supported files in the folder
            supported_extensions = tuple(f'.{ext.lower()}' for ext in INPUT_FORMATS)
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
                                self.files.append(file_path)
                                existing_name_ext_pairs.add((name.lower(), ext.lower()))
            
            # Natural sort files using a key function
            def natural_sort_key(s):
                import re
                return [int(text) if text.isdigit() else text.lower()
                        for text in re.split('([0-9]+)', s)]
            
            # Sort files using natural sort
            self.files.sort(key=natural_sort_key)
            
            # Set the selected folder if not already set or if new files were added
            if (not hasattr(self, 'selected_folder') or not self.selected_folder) and new_files:
                self.selected_folder = folder
            
            # Show warning if files were skipped
            if skipped_files:
                self.show_duplicate_warning(skipped_files)
                
            self.add_files_to_list(self.files)
            self.update_convert_button_state()

    def show_duplicate_warning(self, skipped_files):
        """Show a warning dialog with collapsible details about skipped duplicate files"""
        # Create a custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Files Skipped")
        dialog.setMinimumWidth(550)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setStyleSheet(f"""
            background-color: {COLORS['background']};
            color: {COLORS['text']};
            border-radius: 12px;
        """)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Create a rounded container for the content
        content_container = QFrame()
        content_container.setStyleSheet(f"""
            background-color: {COLORS['panel']}; 
            border-radius: 15px;
        """)
        
        container_layout = QVBoxLayout(content_container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(15)
        
        # Friendly icon and title with softer styling
        title_layout = QHBoxLayout()
        
        info_icon = QLabel("📋")  # Changed from info to clipboard icon
        info_icon.setStyleSheet("font-size: 28px;")
        title_layout.addWidget(info_icon)
        
        title = QLabel("Similar Files Found")  # Changed from "Duplicate Files" to sound less threatening
        title.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {COLORS['primary']};")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        container_layout.addLayout(title_layout)
        
        # Horizontal line with softer color
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet(f"background-color: {COLORS['border']}; margin: 0px 5px;")
        container_layout.addWidget(line)
        
        # Message with friendlier wording
        message = QLabel(f"To keep your file list organized, {len(skipped_files)} file(s) with the same name and type were not added.")
        message.setWordWrap(True)
        message.setStyleSheet(f"font-size: 12pt; margin: 10px 0px; color: {COLORS['text']};")
        container_layout.addWidget(message)
        
        # Collapsible details section with rounded styling
        details_button = QPushButton("View Files")  # Changed from "View Details" to be more specific
        details_button.setCheckable(True)
        details_button.setCursor(Qt.CursorShape.PointingHandCursor)
        details_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['secondary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        container_layout.addWidget(details_button)
        
        # Create details area (initially hidden)
        details_widget = QWidget()
        details_widget.setVisible(False)
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 10, 0, 0)
        details_layout.setSpacing(5)
        
        # Create a scroll area for the file list with improved styling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
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
        """)
        
        # Create content widget for the scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        
        # Sort files in natural order
        def natural_sort_key(s):
            import re
            return [int(text) if text.isdigit() else text.lower()
                    for text in re.split('([0-9]+)', s)]
        
        sorted_files = sorted(skipped_files, key=natural_sort_key)
        
        # Create a grid layout for the files (4x4)
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(10)
        
        # Add files to the grid in a 4x4 layout
        for i, file_path in enumerate(sorted_files):
            row = i // 4
            col = i % 4
            
            # Create a frame for each file with rounded corners
            file_frame = QFrame()
            file_frame.setStyleSheet(f"""
                background-color: {COLORS['background']}; 
                border-radius: 8px;
                padding: 5px;
            """)
            
            file_layout = QVBoxLayout(file_frame)
            file_layout.setContentsMargins(8, 8, 8, 8)
            file_layout.setSpacing(5)
            
            # Add file icon
            file_ext = os.path.splitext(file_path)[1].lower()
            icon_text = "📄"
            if file_ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"]:
                icon_text = "🖼️"
            elif file_ext == ".pdf":
                icon_text = "📑"
            elif file_ext == ".psd":
                icon_text = "🎨"
                
            icon_label = QLabel(icon_text)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("font-size: 24px;")
            file_layout.addWidget(icon_label)
            
            # Add filename (truncated if needed)
            filename = os.path.basename(file_path)
            if len(filename) > 15:
                display_name = filename[:12] + "..."
            else:
                display_name = filename
                
            name_label = QLabel(display_name)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
            name_label.setToolTip(file_path)  # Show full path on hover
            file_layout.addWidget(name_label)
            
            # Add directory in smaller text
            dir_path = os.path.dirname(file_path)
            if len(dir_path) > 20:
                dir_display = "..." + dir_path[-18:]
            else:
                dir_display = dir_path
                
            dir_label = QLabel(dir_display)
            dir_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dir_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9px;")
            dir_label.setToolTip(dir_path)  # Show full directory on hover
            file_layout.addWidget(dir_label)
            
            grid_layout.addWidget(file_frame, row, col)
        
        content_layout.addWidget(grid_widget)
        scroll.setWidget(content_widget)
        details_layout.addWidget(scroll)
        container_layout.addWidget(details_widget)
        
        # Add the container to the main layout
        layout.addWidget(content_container)
        
        # Toggle details visibility when button is clicked
        def toggle_details():
            details_widget.setVisible(details_button.isChecked())
            details_button.setText("Hide Files" if details_button.isChecked() else "View Files")
            # Resize dialog to fit content
            dialog.adjustSize()
        
        details_button.clicked.connect(toggle_details)
        
        # Add OK button with rounded styling
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("Continue")  # Changed from "OK" to "Continue"
        ok_button.setFixedHeight(40)
        ok_button.setMinimumWidth(120)
        ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_button.clicked.connect(dialog.accept)
        ok_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        # Show the dialog
        dialog.exec()

    def toggle_all_files(self, state):
        """Toggle all file checkboxes based on the Select All checkbox state"""
        if not hasattr(self, 'file_checkboxes'):
            return
            
        # Get current output format
        current_output_format = self.format_combo.currentText().lower()
        
        # Debug print
        print(f"Toggle all files: {state}, checkbox count: {len(self.file_checkboxes)}")
        
        # Create a copy of the list to avoid issues with deleted objects
        for checkbox in list(self.file_checkboxes):
            # Check if the checkbox is still valid and enabled
            try:
                if checkbox.isEnabled():
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.file_checkboxes:
                    self.file_checkboxes.remove(checkbox)
        
        # Also update all file type checkboxes
        self.update_file_type_checkbox_state()
    
    def toggle_select_all(self, state):
        """Toggle all file checkboxes based on the Select All checkbox state"""
        if not hasattr(self, 'file_checkboxes'):
            return
        
        # Get current output format
        current_output_format = self.format_combo.currentText().lower()
        
        # Create a copy of the list to avoid issues with deleted objects
        for checkbox in list(self.file_checkboxes):
            # Check if the checkbox is still valid and enabled
            try:
                if checkbox.isEnabled():
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.file_checkboxes:
                    self.file_checkboxes.remove(checkbox)
        
        # Also update all file type checkboxes
        self.update_file_type_checkbox_state()

    def update_upscale_availability(self):
        """Update the upscale checkbox based on Vulkan support"""
        if not hasattr(self, 'upscale_check') or not hasattr(self, 'upscale_combo'):
            return  # Skip if UI elements aren't created yet
            
        if not self.vulkan_support:
            self.upscale_check.setEnabled(False)
            self.upscale_check.setChecked(False)
            self.upscale_combo.setEnabled(False)
            self.upscale_check.setStyleSheet("font-size: 13px; color: #888888;")
            self.upscale_check.setToolTip("AI Upscaling requires Vulkan support")
        else:
            # Only enable if the current format supports upscaling
            format_lower = self.format_combo.currentText().lower() if hasattr(self, 'format_combo') else ""
            can_upscale = format_lower in ['png', 'jpg', 'jpeg', 'webp']
            self.upscale_check.setEnabled(can_upscale)
            self.upscale_combo.setEnabled(can_upscale and self.upscale_check.isChecked())
            
            if can_upscale:
                self.upscale_check.setStyleSheet("font-size: 13px; color: #ffffff;")
            else:
                self.upscale_check.setStyleSheet("font-size: 13px; color: #888888;")
            
            self.upscale_check.setToolTip("Enable AI-powered upscaling")        

    def update_file_type_checkbox_state(self):
        """Update the state of file type checkboxes based on individual file checkboxes"""
        # Get current output format
        current_output_format = self.format_combo.currentText().lower()
        
        # Group checkboxes by file extension
        file_ext_groups = {}
        for checkbox in self.file_checkboxes:
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
        for i in range(self.file_container.layout().count()):
            widget = self.file_container.layout().itemAt(i).widget()
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
        self.update_select_all_checkbox_state()
    
    def update_select_all_checkbox_state(self):
        """Update the state of the "Select All" checkbox based on all file checkboxes"""
        if hasattr(self, 'select_all_checkbox') and hasattr(self, 'file_checkboxes'):
            # Count checked and enabled checkboxes
            checked_count = 0
            enabled_count = 0
            
            for checkbox in self.file_checkboxes:
                try:
                    if checkbox.isEnabled():
                        enabled_count += 1
                        if checkbox.isChecked():
                            checked_count += 1
                except RuntimeError:
                    continue
            
            # Update the "Select All" checkbox without triggering its signal
            if enabled_count > 0:
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(checked_count == enabled_count)
                self.select_all_checkbox.setText(f"Select All ({checked_count}/{enabled_count} selected)")
                self.select_all_checkbox.blockSignals(False)
                
                # Also update the file count label if it exists
                if hasattr(self, 'file_count_label'):
                    self.file_count_label.setText(f"Total: {len(self.files)} files, {checked_count} selected")            

    def add_files_to_list(self, file_paths):
        """Add files to the converter file list"""
        # Store existing checkbox states before clearing the layout
        checkbox_states = {}
        if hasattr(self, 'file_checkboxes'):
            for checkbox in self.file_checkboxes:
                try:
                    if hasattr(checkbox, 'file_path'):
                        checkbox_states[checkbox.file_path] = checkbox.isChecked()
                except RuntimeError:
                    pass
        
        # Clear the file container
        for i in reversed(range(self.file_container.layout().count())):
            widget = self.file_container.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Reset file_checkboxes list
        self.file_checkboxes = []
        
        # If no files, show the placeholder
        if not file_paths:
            self.file_label = QLabel("No files selected")
            self.file_label.setWordWrap(True)
            self.file_label.setStyleSheet("color: #888888; padding: 10px;")
            self.file_container.layout().addWidget(self.file_label)
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
            if hasattr(self, 'selected_folder') and self.selected_folder:
                folder_label = QLabel(f"📁 Selected Folder: {self.selected_folder}")
                folder_label.setStyleSheet(f"color: {COLORS['text']}; padding: 5px; font-weight: bold;")
                file_list_layout.addWidget(folder_label)
                
                # Add a separator
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
                file_list_layout.addWidget(separator)
            
            # Add "Select All" checkbox inside the file list widget
            select_all_layout = QHBoxLayout()
            # Create a new select all checkbox if it doesn't exist or if it's been deleted
            try:
                # Try to access the checkbox to see if it's still valid
                if not hasattr(self, 'select_all_checkbox') or not self.select_all_checkbox.isVisible():
                    self.select_all_checkbox = QCheckBox("Select All")
                    self.select_all_checkbox.stateChanged.connect(self.toggle_all_files)
            except (RuntimeError, AttributeError):
                # If there's an error, recreate the checkbox
                self.select_all_checkbox = QCheckBox("Select All")
                self.select_all_checkbox.stateChanged.connect(self.toggle_all_files)
                
            self.select_all_checkbox.setChecked(True)
            select_all_layout.addWidget(self.select_all_checkbox)
            
            # Add file count
            self.file_count_label = QLabel(f"Total: {len(file_paths)} files")
            self.file_count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9pt;")
            select_all_layout.addWidget(self.file_count_label, alignment=Qt.AlignmentFlag.AlignRight)
            
            file_list_layout.addLayout(select_all_layout)

            # Add a separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
            file_list_layout.addWidget(separator)
            
            # Group files by extension
            file_groups = {}
            for file_path in file_paths:
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
                    lambda state, ext=file_ext: self.toggle_file_type(state, ext)
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
                    checkbox.stateChanged.connect(self.update_file_type_checkbox_state)
                    # Also connect to update the convert button state
                    checkbox.stateChanged.connect(self.update_convert_button_state)
                    
                    self.file_checkboxes.append(checkbox)
                    
                    file_layout.addWidget(checkbox)
                    
                    # Add file icon based on extension
                    icon_text = "📄"
                    if file_ext.lower() in ["jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff"]:
                        icon_text = "🖼️"
                    elif file_ext.lower() == "pdf":
                        icon_text = "📑"
                    elif file_ext.lower() == "psd":
                        icon_text = "🎨"
                    
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
            self.file_container.layout().addWidget(file_scroll)
            
            # Update the "Select All" checkbox state
            self.update_select_all_checkbox_state()
        
        # Update the convert button state
        self.update_convert_button_state()
    
    def update_quality_settings(self):
        """Update quality settings when combo box values change"""
        # Get current settings
        current_settings = self.get_current_settings()
        
        # If we have an active conversion thread, update its settings
        if hasattr(self, 'thread') and self.thread and self.thread.isRunning():
            self.thread.settings = current_settings
            
        # Debug print to verify settings are updated
        print(f"Quality settings updated: {current_settings}")

    def toggle_all_files(self, state):
        """Toggle all file checkboxes based on the Select All checkbox state"""
        if not hasattr(self, 'file_checkboxes'):
            return
            
        # Get current output format
        current_output_format = self.format_combo.currentText().lower()
        
        # Debug print
        print(f"Toggle all files: {state}, checkbox count: {len(self.file_checkboxes)}")
        
        # Create a copy of the list to avoid issues with deleted objects
        for checkbox in list(self.file_checkboxes):
            # Check if the checkbox is still valid and enabled
            try:
                if checkbox.isEnabled():
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.file_checkboxes:
                    self.file_checkboxes.remove(checkbox)
        
        # Also update all file type checkboxes
        self.update_file_type_checkbox_state()
    
    
    def update_checkbox_state(self, state, file_path):
        """Update the state of a checkbox in the main UI based on changes in the dialog"""
        for checkbox in list(self.file_checkboxes):
            try:
                if hasattr(checkbox, 'file_path') and checkbox.file_path == file_path:
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
                    break
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.file_checkboxes:
                    self.file_checkboxes.remove(checkbox)
    
    def toggle_file_type(self, state, file_ext):
        """Toggle all checkboxes for a specific file type"""
        if not hasattr(self, 'file_checkboxes'):
            return
        
        # Update main UI checkboxes
        for checkbox in list(self.file_checkboxes):
            try:
                if hasattr(checkbox, 'file_ext') and checkbox.file_ext == file_ext and checkbox.isEnabled():
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
            except RuntimeError:
                # Remove invalid checkboxes from the list
                if checkbox in self.file_checkboxes:
                    self.file_checkboxes.remove(checkbox)
        
        # Also update any checkboxes in an open dialog
        if hasattr(self, 'dialog_checkboxes'):
            for checkbox in self.dialog_checkboxes:
                try:
                    if hasattr(checkbox, 'file_ext') and checkbox.file_ext == file_ext and checkbox.isEnabled():
                        checkbox.setChecked(state == Qt.CheckState.Checked.value)
                except RuntimeError:
                    pass  # Dialog checkboxes are temporary, no need to maintain the list
    
    def on_format_changed(self, format_text):
        # Update this method to handle checkbox state
        format_lower = format_text.lower()
        can_upscale = format_lower in ['png', 'jpg', 'jpeg', 'webp']
        
        # Use the vulkan_support variable to determine if upscaling is available
        if self.vulkan_support:
            self.upscale_check.setEnabled(can_upscale)
            self.upscale_check.setChecked(False if not can_upscale else self.upscale_check.isChecked())
            self.upscale_combo.setEnabled(can_upscale and self.upscale_check.isChecked())
            
            # Update checkbox text color based on whether upscaling is available
            if can_upscale:
                self.upscale_check.setStyleSheet("font-size: 13px; color: #ffffff;")
            else:
                self.upscale_check.setStyleSheet("font-size: 13px; color: #888888;")
        else:
            # Disable upscaling if Vulkan is not supported
            self.upscale_check.setEnabled(False)
            self.upscale_check.setChecked(False)
            self.upscale_combo.setEnabled(False)
            self.upscale_check.setStyleSheet("font-size: 13px; color: #888888;")
            self.upscale_check.setToolTip("AI Upscaling requires Vulkan support")
            
        if not can_upscale or not self.vulkan_support:
            self.upscale_check.setChecked(False)
            
        # Update file checkboxes based on new format
        if hasattr(self, 'file_checkboxes'):
            current_output_format = format_text.lower()
            
            for checkbox in self.file_checkboxes:
                file_ext = os.path.splitext(checkbox.file_path)[1].lower()[1:]  # Get extension without dot
                
                # Disable checkbox if file format matches output format
                if file_ext == current_output_format:
                    checkbox.setChecked(False)
                    checkbox.setEnabled(False)
                    checkbox.setStyleSheet(f"QCheckBox::indicator {{ background-color: #555555; }}")
                else:
                    checkbox.setEnabled(True)
                    checkbox.setStyleSheet("")
                    # If "Select All" is checked, check this box too
                    if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox.isChecked():
                        checkbox.setChecked(True)
            
            # Update the file list display - pass self.files to the method
            self.add_files_to_list(self.files)
            
    def select_output_dir(self):
        dir_dialog = QFileDialog()
        dir_dialog.setFileMode(QFileDialog.FileMode.Directory)
        dir_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if dir_dialog.exec():
            self.output_dir = dir_dialog.selectedFiles()[0]
            self.output_dir_label.setText(f"📁 {self.output_dir}")
            self.output_dir_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
            self.update_convert_button_state()
    
    
    def update_convert_button_state(self):
        """Update the state of the convert button based on file selection and output directory"""
        # Check if any files are selected and output directory is set
        files_selected = False
        if hasattr(self, 'file_checkboxes'):
            for checkbox in self.file_checkboxes:
                try:
                    if checkbox.isChecked():
                        files_selected = True
                        break
                except RuntimeError:
                    continue
        
        # Enable the convert button if files are selected and output directory is set
        self.convert_btn.setEnabled(files_selected and bool(self.output_dir))
        
    def toggle_upscale_options(self, state):
        is_enabled = state == Qt.CheckState.Checked.value
        self.upscale_combo.setEnabled(is_enabled)

        # Update the visual appearance based on enabled state
        if is_enabled:
            self.upscale_combo.setStyleSheet(f"""
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
            """)
        else:
            self.upscale_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: #3d3d4f;
                    color: #888888;
                    border: 1px solid #3d3d4f;
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
            """)
    
    def get_selected_files(self):
        """Get list of files that are currently checked"""
        selected_files = []
        for checkbox in self.file_checkboxes:
            try:
                if checkbox.isChecked() and checkbox.isEnabled():
                    selected_files.append(checkbox.file_path)
            except RuntimeError:
                continue
        return selected_files

    def start_conversion(self):
        if not self.files or not self.output_dir:
            return
        
        # Get only selected files before starting conversion
        files_to_convert = self.get_selected_files()
        if not files_to_convert:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to convert.")
            return
        
        # Check if this is a repeated conversion to the same output folder
        should_continue = True
        if hasattr(self, 'last_output_dir') and self.last_output_dir == self.output_dir:
            # Show warning about potential file overwriting
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Warning: Same Output Folder")
            msg_box.setText("You are using the same output folder as your previous conversion.")
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
            elif clicked_button == change_folder_btn:
                # Open folder selection dialog
                self.select_output_dir()
                # Check if user actually selected a new folder
                if self.output_dir != self.last_output_dir:
                    # Make sure the folder icon is displayed
                    self.output_dir_label.setText(f"📁 {self.output_dir}")
                    should_continue = True
                else:
                    should_continue = False
        
        self.log("Starting conversion process", "INFO")

        # Store current output dir for future reference
        self.last_output_dir = self.output_dir
        
        # If user chose not to continue, exit the method
        if not should_continue:
            return
            
        # Get current settings using the correct combo box references
        current_settings = {
            'jpeg_quality': self.jpeg_quality_combo.currentText(),
            'webp_quality': self.webp_quality_combo.currentText(),
            'png_compression': self.png_compression_combo.currentText(),
            'pdf_dpi': self.pdf_dpi_combo.currentText(),
            'pdf_quality': self.pdf_quality_combo.currentText()
        }
            
        # Create and configure the converter thread
        self.thread = ConverterThread(
            files_to_convert,
            self.output_dir,
            self.format_combo.currentText().lower(),
            current_settings,
            self.upscale_check.isChecked(),
            self.upscale_combo.currentText()
        )
        
        # Connect signals
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.completion_signal.connect(self.conversion_complete)
        self.thread.error_signal.connect(self.handle_error)
        
        # Show progress dialog
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.show()
        
        # Start conversion
        self.thread.start()
    
        # Reset the convert button
        self.convert_btn.setText("Converting...")
        self.convert_btn.setEnabled(False)

    def update_progress(self, value, eta_text, speed_text):
        if self.progress_dialog:
            self.progress_dialog.update_progress(value, eta_text, speed_text)
    
    def conversion_complete(self, last_output_path, input_size, output_size, success_count, failure_count):
        """Show a completion message with statistics"""
        
        self.log(f"Conversion completed: {success_count} succeeded, {failure_count} failed", 
                "SUCCESS" if failure_count == 0 else "INFO")
        
        # First close the progress dialog if it's still open
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.accept()
            self.progress_dialog = None
            
        # Don't show completion message if the operation was cancelled
        if hasattr(self, 'thread') and self.thread and self.thread.cancelled:
            return
            
        # Format sizes in MB
        input_mb = input_size / (1024 * 1024)
        output_mb = output_size / (1024 * 1024)

        # Calculate size reduction percentage
        if input_size > 0:
            reduction = ((input_size - output_size) / input_size) * 100
            if reduction > 0:
                size_text = f"Size reduced by {reduction:.1f}%"
            else:
                size_text = f"Size increased by {abs(reduction):.1f}%"
        else:
            size_text = "Size comparison not available"
        
        # Create message
        message = f"Conversion completed!\n\n"
        message += f"Files processed: {success_count} successful, {failure_count} failed\n"
        message += f"Input size: {input_mb:.2f} MB\n"
        message += f"Output size: {output_mb:.2f} MB\n"
        message += f"{size_text}"
        
        # Show styled message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Conversion Completed")
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
        
        # Show dialog and handle response
        msg_box.exec()
        
        # Handle button clicks
        if msg_box.clickedButton() == open_btn:
            # Open the output folder
            output_dir = os.path.dirname(last_output_path)
            if os.path.exists(output_dir):
                os.startfile(output_dir)

        # Reset the convert button
        self.convert_btn.setText("✨ Convert")
        self.update_convert_button_state()        
    
    def handle_error(self, error_message, error_type):
        QMessageBox.warning(self, "Conversion Error", error_message)
        self.log(f"Conversion error: {error_message}", "ERROR")
    
    def open_output_folder(self):
        if self.output_dir and os.path.exists(self.output_dir):
            os.startfile(self.output_dir)

    def show_system_info(self):
        """Show system information dialog with brand icons"""
        try:
            # Create loading dialog
            loading_dialog = QDialog(self)
            loading_dialog.setWindowTitle("Loading")
            loading_dialog.setFixedSize(300, 100)
            loading_dialog.setStyleSheet("")  # Remove styling from the dialog itself
            loading_dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint)
            loading_dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Make window background transparent
            
            # Create a container frame that will have the rounded corners
            container_frame = QFrame(loading_dialog)
            container_frame.setStyleSheet(f"""
                background-color: {COLORS['background']}; 
                color: {COLORS['text']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            """)
            container_frame.setGeometry(0, 0, 300, 100)  # Same size as dialog
            
            # Add drop shadow effect to the container
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 0)
            container_frame.setGraphicsEffect(shadow)
            
            # Center the loading dialog on the parent
            loading_dialog.move(
                self.x() + (self.width() - loading_dialog.width()) // 2,
                self.y() + (self.height() - loading_dialog.height()) // 2
            )
            
            # Create loading layout for the container frame (not the dialog)
            loading_layout = QVBoxLayout(container_frame)
            loading_layout.setContentsMargins(20, 20, 20, 15)  # Add more padding
            
            # Loading label
            loading_label = QLabel("Verifying Upscaling Availability.....")
            loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            loading_label.setStyleSheet("font-size: 14px; font-weight: 500; background-color: transparent;")
            loading_layout.addWidget(loading_label)
            
            # Progress bar
            progress = QProgressBar()
            progress.setRange(0, 0)  # Indeterminate progress
            progress.setTextVisible(False)
            progress.setStyleSheet(f"""
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
            loading_layout.addWidget(progress)
            
            # Show the loading dialog without blocking
            loading_dialog.show()
            QApplication.processEvents()
            
            # Create the actual system info dialog (but don't show it yet)
            dialog = QDialog(self)
            dialog.setWindowTitle("System Information")
            dialog.setMinimumSize(500, 400)
            dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
            
            # Set window icon
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                dialog.setWindowIcon(QIcon(icon_path))
            
            # Create a worker thread to gather system info
            class SystemInfoWorker(QThread):
                finished_signal = pyqtSignal(dict)
                
                def run(self):
                    try:
                        # Gather all system information
                        import platform
                        import sys
                        
                        info = {}
                        info['os_name'] = platform.system() + " " + platform.release()
                        info['processor'] = platform.processor()
                        info['python_version'] = platform.python_version()
                        
                        # Memory info
                        try:
                            import psutil
                            memory = psutil.virtual_memory()
                            info['memory_total'] = round(memory.total / (1024**3), 2)
                            info['memory_available'] = round(memory.available / (1024**3), 2)
                            info['memory_percent'] = memory.percent
                            info['has_psutil'] = True
                        except ImportError:
                            info['has_psutil'] = False
                        
                                                # GPU info
                        info['gpu_names'] = []
                        info['vulkan_support'] = False
                        
                        try:
                            import subprocess
                            import re
                            import tempfile
                            import time
                            import os
                            
                            # Create a hidden process
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            
                            # Method 1: Try using DXDIAG
                            try:
                                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
                                temp_file.close()
                                
                                subprocess.run(
                                    ['dxdiag', '/t', temp_file.name],
                                    startupinfo=startupinfo,
                                    timeout=5
                                )
                                
                                time.sleep(0.5)
                                
                                with open(temp_file.name, 'r', errors='ignore') as f:
                                    content = f.read()
                                    
                                    # Find all display devices sections
                                    display_sections = re.findall(r"-------------\r?\nDisplay Devices\r?\n-------------\r?\n.*?Card name:(.*?)(?:\r?\n)", content, re.DOTALL)
                                    if display_sections:
                                        for gpu in display_sections:
                                            gpu_name = gpu.strip()
                                            if gpu_name and gpu_name not in info['gpu_names']:
                                                info['gpu_names'].append(gpu_name)
                                
                                os.unlink(temp_file.name)
                            except Exception as e:
                                print(f"DXDIAG method failed: {str(e)}")
                            
                            # Method 2: Fallback to WMI
                            if not info['gpu_names']:
                                result = subprocess.run(
                                    ['wmic', 'path', 'win32_VideoController', 'get', 'Name'], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE,
                                    startupinfo=startupinfo,
                                    text=True,
                                    timeout=3
                                )
                                
                                if result.returncode == 0:
                                    lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                                    if len(lines) > 1:
                                        # Skip the header line "Name"
                                        for i in range(1, len(lines)):
                                            gpu_name = lines[i]
                                            if gpu_name and gpu_name not in info['gpu_names']:
                                                info['gpu_names'].append(gpu_name)
                            
                            # Method 3: PowerShell fallback
                            if not info['gpu_names']:
                                ps_cmd = "Get-WmiObject win32_VideoController | Select-Object -ExpandProperty Name"
                                result = subprocess.run(
                                    ['powershell', '-Command', ps_cmd],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    startupinfo=startupinfo,
                                    text=True,
                                    timeout=3
                                )
                                
                                if result.returncode == 0 and result.stdout.strip():
                                    gpu_list = result.stdout.strip().split('\n')
                                    for gpu_name in gpu_list:
                                        gpu_name = gpu_name.strip()
                                        if gpu_name and gpu_name not in info['gpu_names']:
                                            info['gpu_names'].append(gpu_name)
                            
                            # If no GPUs were found, add "Unknown"
                            if not info['gpu_names']:
                                info['gpu_names'].append("Unknown")
                            
                            # Check for Vulkan support
                            vulkan_check = subprocess.run(
                                ['where', 'vulkaninfo'], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                startupinfo=startupinfo,
                                text=True,
                                timeout=2
                            )
                            info['vulkan_support'] = vulkan_check.returncode == 0
                            
                            if not info['vulkan_support']:
                                vulkan_dll_check = subprocess.run(
                                    ['where', 'vulkan-1.dll'], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE,
                                    startupinfo=startupinfo,
                                    text=True,
                                    timeout=2
                                )
                                info['vulkan_support'] = vulkan_dll_check.returncode == 0
                            
                            if not info['vulkan_support']:
                                system32_path = os.path.join(os.environ['SystemRoot'], 'System32')
                                info['vulkan_support'] = os.path.exists(os.path.join(system32_path, 'vulkan-1.dll'))
                                
                        except Exception as e:
                            print(f"GPU detection error: {str(e)}")
                        
                        self.finished_signal.emit(info)
                    except Exception as e:
                        print(f"Worker thread error: {str(e)}")
                        self.finished_signal.emit({})
            
            # Create and start the worker thread
            self.worker = SystemInfoWorker()
            
            # Connect the finished signal to update the UI
            def update_system_info_ui(info):
                try:
                    # Close the loading dialog
                    loading_dialog.close()
                    
                    # Update the main window's vulkan_support variable
                    self.vulkan_support = info.get('vulkan_support', False)
                    
                    # Update UI based on Vulkan support
                    self.update_upscale_availability()
                    
                    layout = QVBoxLayout(dialog)
                    layout.setContentsMargins(20, 20, 20, 20)

                    # Title
                    title = QLabel("System Information")
                    title.setStyleSheet("font-size: 18px; font-weight: 600; margin-bottom: 10px;")
                    layout.addWidget(title)
                    
                    # Create scroll area for system info
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
                    
                    # Container for system info
                    info_container = QWidget()
                    info_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    info_layout = QVBoxLayout(info_container)
                    info_layout.setSpacing(15)
                    
                    # Vulkan compatibility status - moved to top
                    if info.get('vulkan_support', False):
                        # Vulkan support confirmation
                        support_frame = QFrame()
                        support_frame.setStyleSheet(f"background-color: #2C3D2C; border-radius: 10px; padding: 5px;")
                        support_layout = QHBoxLayout(support_frame)
                        
                        support_icon = QLabel("✓")  # Checkmark icon
                        support_icon.setStyleSheet("font-size: 24px; padding: 5px; color: #8AFF8A;")
                        support_layout.addWidget(support_icon)
                        
                        support_text = QLabel("<b>AI Upscaling Available</b><br>Your system supports Vulkan,<br>enabling AI-powered image upscaling.")
                        support_text.setTextFormat(Qt.TextFormat.RichText)
                        support_text.setStyleSheet("font-size: 12px; line-height: 1.5; color: #8AFF8A;")
                        support_text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                        support_layout.addWidget(support_text)
                        support_layout.addStretch()
                        
                        info_layout.addWidget(support_frame)
                    else:
                        # Vulkan not supported warning
                        warning_frame = QFrame()
                        warning_frame.setStyleSheet(f"background-color: #3D2C2C; border-radius: 10px; padding: 5px;")
                        warning_layout = QHBoxLayout(warning_frame)
                        
                        warning_icon = QLabel("⚠️")  # Warning icon
                        warning_icon.setStyleSheet("font-size: 24px; padding: 5px;")
                        warning_layout.addWidget(warning_icon)
                        
                        warning_text = QLabel("<b>AI Upscaling Not Available</b><br>Your system does not support Vulkan,<br>which is required for AI upscaling.")
                        warning_text.setTextFormat(Qt.TextFormat.RichText)
                        warning_text.setStyleSheet("font-size: 12px; line-height: 1.5; color: #FF9E9E;")
                        warning_text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                        warning_layout.addWidget(warning_text)
                        warning_layout.addStretch()
                        
                        info_layout.addWidget(warning_frame)
                    
                    # OS Section
                    os_frame = QFrame()
                    os_frame.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 10px; padding: 5px;")
                    os_layout = QHBoxLayout(os_frame)
                    
                    os_icon = QLabel("🖥️")  # Computer icon
                    os_icon.setStyleSheet("font-size: 24px; padding: 5px;")
                    os_layout.addWidget(os_icon)
                    
                    os_info = QLabel(f"<b>Operating System</b><br>{info.get('os_name', 'Unknown')}")
                    os_info.setTextFormat(Qt.TextFormat.RichText)
                    os_info.setStyleSheet("font-size: 12px; line-height: 1.5;")
                    os_layout.addWidget(os_info)
                    os_layout.addStretch()
                    
                    info_layout.addWidget(os_frame)
                    
                    # CPU Section
                    cpu_frame = QFrame()
                    cpu_frame.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 10px; padding: 5px;")
                    cpu_layout = QHBoxLayout(cpu_frame)
                    
                    cpu_icon = QLabel("⚙️")  # Gear icon
                    cpu_icon.setStyleSheet("font-size: 24px; padding: 5px;")
                    cpu_layout.addWidget(cpu_icon)
                    
                    cpu_info = QLabel(f"<b>Processor</b><br>{info.get('processor', 'Unknown')}")
                    cpu_info.setTextFormat(Qt.TextFormat.RichText)
                    cpu_info.setStyleSheet("font-size: 12px; line-height: 1.5;")
                    cpu_layout.addWidget(cpu_info)
                    cpu_layout.addStretch()
                    
                    info_layout.addWidget(cpu_frame)
                    
                    # Memory Section
                    memory_frame = QFrame()
                    memory_frame.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 10px; padding: 5px;")
                    memory_layout = QHBoxLayout(memory_frame)
                    
                    memory_icon = QLabel("🧠")  # Brain icon
                    memory_icon.setStyleSheet("font-size: 24px; padding: 5px;")
                    memory_layout.addWidget(memory_icon)
                    
                    # Create memory info label that will be updated
                    memory_info = QLabel()
                    memory_info.setTextFormat(Qt.TextFormat.RichText)
                    memory_info.setStyleSheet("font-size: 12px; line-height: 1.5;")
                    memory_layout.addWidget(memory_info)
                    memory_layout.addStretch()
                    
                    # Function to update memory info
                    def update_memory_info():
                        try:
                            if info.get('has_psutil', False):
                                import psutil
                                memory = psutil.virtual_memory()
                                memory_total = round(memory.total / (1024**3), 2)
                                memory_available = round(memory.available / (1024**3), 2)
                                memory_used = round(memory_total - memory_available, 2)
                                memory_percent = memory.percent
                                
                                # Create a progress bar style representation of memory usage
                                bar_width = 150
                                filled_width = int(bar_width * memory_percent / 100)
                                
                                memory_bar = f"""
                                <div style="background-color: #333344; width: {bar_width}px; height: 10px; border-radius: 5px; margin-top: 5px;">
                                    <div style="background-color: {'#4d79ff' if memory_percent < 80 else '#ff6666'}; width: {filled_width}px; height: 10px; border-radius: 5px;"></div>
                                </div>
                                """
                                
                                memory_info.setText(f"<b>Memory</b> (Live)<br>Total: {memory_total} GB<br>Used: {memory_used} GB ({memory_percent}%)<br>Available: {memory_available} GB{memory_bar}")
                            else:
                                memory_info.setText("<b>Memory</b><br>Install psutil for detailed memory information")
                        except Exception as e:
                            memory_info.setText(f"<b>Memory</b><br>Error updating: {str(e)}")
                    
                    # Initial update
                    update_memory_info()
                    
                    # Create timer to update memory info every half second
                    memory_timer = QTimer(dialog)
                    memory_timer.timeout.connect(update_memory_info)
                    memory_timer.start(500)  # Update every half second
                    
                    # Stop timer when dialog is closed
                    dialog.finished.connect(memory_timer.stop)
                    
                    info_layout.addWidget(memory_frame)
                    
                    # GPU Section
                    gpu_frame = QFrame()
                    gpu_frame.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 10px; padding: 5px;")
                    gpu_layout = QHBoxLayout(gpu_frame)
                    
                    gpu_icon = QLabel("🎮")  # Game controller icon
                    gpu_icon.setStyleSheet("font-size: 24px; padding: 5px;")
                    gpu_layout.addWidget(gpu_icon)
                    
                    # Create GPU info text with all detected GPUs
                    gpu_text = "<b>Graphics</b><br>"
                    for i, gpu_name in enumerate(info.get('gpu_names', ["Unknown"])):
                        if i > 0:
                            gpu_text += "<br>"
                        gpu_text += f"GPU {i+1}: {gpu_name}"
                    
                    gpu_text += f"<br>Vulkan Support: {'Yes' if info.get('vulkan_support', False) else 'No'}"
                    
                    gpu_info = QLabel(gpu_text)
                    gpu_info.setTextFormat(Qt.TextFormat.RichText)
                    gpu_info.setStyleSheet("font-size: 12px; line-height: 1.5;")
                    gpu_layout.addWidget(gpu_info)
                    gpu_layout.addStretch()
                    
                    info_layout.addWidget(gpu_frame)
                    
                    # Add the scroll area to the layout
                    scroll.setWidget(info_container)
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
                    
                    # Show the system info dialog
                    dialog.exec()
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Error showing system information: {str(e)}")
            
            self.worker.finished_signal.connect(update_system_info_ui)
            self.worker.start()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error showing system information: {str(e)}")
            

    def show_instructions(self):
        """Show detailed instructions dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Use PSD Converter")
        dialog.setMinimumSize(600, 500)  # Increased size for more content
        dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            dialog.setWindowIcon(QIcon(icon_path))
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("How to Use PSD Converter")
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
        • <b>Input Formats:</b> PSD, PNG, JPG, WEBP, BMP, GIF, TIFF, PDF<br>
        • <b>Output Formats:</b> PNG, JPG, WEBP, BMP, TIFF, PDF, GIF, ICO<br>
        • <b>AI Upscaling:</b> Available for PNG, JPG, WEBP (requires Vulkan support)<br>
        • <b>Batch Processing:</b> Convert multiple files at once<br>
        • <b>Drag & Drop:</b> Supported for easy file selection
        </p>
        """)
        panel_content.setTextFormat(Qt.TextFormat.RichText)
        panel_content.setWordWrap(True)
        info_panel_layout.addWidget(panel_content)
        instructions_layout.addWidget(info_panel)
        
        instructions_text = """
        <h2 style="font-size: 21px;">PSD Converter - Complete User Guide</h2>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Overview</h3>
        <p style="font-size: 14px; margin: 5px 0;">PSD Converter is a powerful tool designed to convert various image formats, including Adobe Photoshop (PSD) files, to other common formats. The application provides a user-friendly interface with advanced options for customizing your conversions.</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Getting Started</h3>
        <p style="font-size: 14px; margin: 5px 0;">The application has two main tabs:</p>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• <b>Home Tab</b>: Where you'll perform file conversions<br>• <b>Settings Tab</b>: Where you can customize application preferences</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 1: Select Files or Folder</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Select Files</b> to choose individual files for conversion<br>• Click <b>Select Folder</b> to convert all supported files in a folder<br>• Or Use Drag and Drop (Unsupported Files won't show up)<br>• Selected files will appear in the right panel, grouped by file type<br>• You can select/deselect individual files by clicking their checkboxes</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 2: Choose Output Format</h3>
        <p style="font-size: 14px; margin: 5px 0;">Select your desired output format from the dropdown menu. Supported output formats include:</p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>PNG</b>: Best for images requiring transparency and lossless quality</li>
            <li><b>JPG/JPEG</b>: Ideal for photographs and web images where file size is important</li>
            <li><b>WEBP</b>: Modern format with excellent compression and quality balance</li>
            <li><b>BMP</b>: Uncompressed format for maximum quality</li>
            <li><b>TIFF</b>: Professional format supporting layers and multiple pages</li>
            <li><b>PDF</b>: Document format that preserves image quality</li>
            <li><b>GIF</b>: Supports animation and is good for simple graphics</li>
            <li><b>ICO</b>: Windows icon format</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 3: Quality Settings</h3>
        <p style="font-size: 14px; margin: 5px 0;">Adjust quality settings based on your selected output format:</p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>JPEG Quality</b>: Higher values (70-100) provide better quality but larger file sizes</li>
            <li><b>PNG Compression</b>: Higher compression levels take longer but produce smaller files</li>
            <li><b>WEBP Quality</b>: Similar to JPEG, balances quality and file size</li>
            <li><b>PDF DPI</b>: Controls resolution of PDF output (72-300 DPI)</li>
            <li><b>PDF Quality</b>: Affects image quality within PDF documents</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 4: AI Upscaling (Optional)</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Enable AI Upscaling to enhance image quality and resolution<br>• Select an upscale factor from the dropdown (2x, 3x, 4x)<br>• Note: AI upscaling is only available for PNG, JPEG, and WEBP formats<br>• Upscaling will increase processing time and output file size<br>• Best results are achieved with clear source images</p>
        
        <p style="color: #FF9E9E; font-size: 14px; margin: 5px 0 10px 10px;"><span style="font-size: 18px;">⚠️</span> <b>Warning:</b> AI Upscaling requires Vulkan support on your system. If your GPU does not support Vulkan, this feature will be disabled.</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 5: Select Output Directory</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click <b>Output Directory</b> to choose where converted files will be saved<br>• If not selected, files will be saved in a subfolder of the source location<br>• The application will create the directory if it doesn't exist<br>• Original files are never modified or deleted</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Step 6: Convert</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Click the <b>Convert</b> button to start the conversion process<br>• A progress dialog will show conversion status, estimated time, and speed<br>• You can cancel the conversion at any time<br>• When complete, a summary dialog will show success/failure counts and size changes<br>• You can open the output folder or individual files directly from this dialog</p>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Supported Input Formats</h3>
        <p style="font-size: 14px; margin: 5px 0;"><b>Images:</b></p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>PNG</b> (.png): Portable Network Graphics</li>
            <li><b>JPEG</b> (.jpg, .jpeg): Joint Photographic Experts Group</li>
            <li><b>BMP</b> (.bmp): Bitmap Image File</li>
            <li><b>GIF</b> (.gif): Graphics Interchange Format</li>
            <li><b>TIFF</b> (.tif, .tiff): Tagged Image File Format</li>
            <li><b>WEBP</b> (.webp): Web Picture format</li>
        </ul>
        
        <p style="font-size: 14px; margin: 5px 0;"><b>Documents:</b></p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>PDF</b> (.pdf): Portable Document Format</li>
        </ul>
        
        <p style="font-size: 14px; margin: 5px 0;"><b>Design:</b></p>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>PSD</b> (.psd): Adobe Photoshop Document</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Advanced Tips</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li>Files that are already in the target format will be automatically disabled</li>
            <li>Use the "Select All" checkbox to quickly select or deselect all files</li>
            <li>You can select files by type using the checkboxes for each file format group</li>
            <li>The application preserves folder structure when converting entire folders</li>
            <li>For PSD files, all visible layers are flattened during conversion</li>
            <li>For batch processing, you can select multiple files or entire folders</li>
            <li>The application will remember your last used settings</li>
            <li>Right-click on files in the list for additional options</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">Troubleshooting</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li><b>Conversion fails</b>: Ensure the source file isn't corrupted or in use by another application</li>
            <li><b>Missing output files</b>: Check that you have write permissions for the output directory</li>
            <li><b>Application freezes</b>: For large files or batch operations, allow more time for processing</li>
            <li><b>Quality issues</b>: Adjust quality settings or try a different output format</li>
            <li><b>Upscaling problems</b>: Ensure your system meets the minimum requirements for AI processing</li>
        </ul>
        
        <h3 style="font-size: 18px; margin-top: 15px;">System Requirements</h3>
        <ul style="font-size: 14px; margin: 5px 0 10px 10px; padding-left: 15px;">
            <li>Windows 10 or later</li>
            <li>4GB RAM minimum (8GB+ recommended for AI upscaling)</li>
            <li>500MB free disk space</li>
            <li>1GHz processor (multi-core recommended)</li>
            <li>Dedicated GPU recommended for faster AI upscaling</li>
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

    def open_github_repo(self, url):
        import webbrowser
        webbrowser.open(url)

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
        self.denoiser_model_combo.addItems(["Anime/Manga Style", "Photo Style"])
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
        self.create_denoiser_action_buttons(layout)
        
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


    def format_size(self, size_bytes):
        """Format file size in bytes to human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        
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

    def update_denoise_button_state(self):
        """Update the state of the denoise button based on file selection and output directory"""
        # Check if any files are selected and output directory is set
        files_selected = False
        if self.denoiser_file_checkboxes:
            for checkbox in self.denoiser_file_checkboxes:
                if checkbox.isChecked():
                    files_selected = True
                    break
        
        # Enable the denoise button if files are selected and output directory is set
        self.denoise_btn.setEnabled(files_selected and bool(self.denoiser_output_dir))

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

    def start_denoising(self):
        """Start the denoising process"""
        # Get selected files
        selected_files = []
        for checkbox in self.denoiser_file_checkboxes:
            if checkbox.isChecked():
                selected_files.append(checkbox.file_path)
        
        if not selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to denoise.")
            return
        
        if not self.denoiser_output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select an output directory.")
            return
        
        # Check if this is a repeated denoising to the same output folder
        should_continue = True
        if hasattr(self, 'last_denoiser_output_dir') and self.last_denoiser_output_dir == self.denoiser_output_dir:
            # Show warning about potential file overwriting
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Warning: Same Output Folder")
            msg_box.setText("You are using the same output folder as your previous denoising.")
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
            elif clicked_button == change_folder_btn:
                # Open folder selection dialog
                self.set_denoiser_output_dir() 
                # Check if user actually selected a new folder
                if self.denoiser_output_dir != self.last_denoiser_output_dir:
                    # Make sure the folder icon is displayed
                    self.denoiser_output_dir_label.setText(f"📁 {self.denoiser_output_dir}")
                    should_continue = True
                else:
                    should_continue = False
        
        # Log the start of denoising
        self.log(f"Starting denoising of {len(selected_files)} files with strength {self.noise_level_combo.currentText()}", "INFO")

        # Store current output dir for future reference
        self.last_denoiser_output_dir = self.denoiser_output_dir
        
        # If user chose not to continue, exit the method
        if not should_continue:
            return

        # Get denoising options
        noise_level_text = self.noise_level_combo.currentText()
        noise_level = int(noise_level_text.split()[1].split("(")[0])  # Extract number from "Level X"
        model = "anime" if self.denoiser_model_combo.currentText() == "Anime/Manga Style" else "photo"
        keep_format = True
        output_format = "PNG"
        
        # Create and start the denoiser thread
        self.denoiser_thread = DenoiserThread(
            selected_files,
            self.denoiser_output_dir,
            noise_level=noise_level,
            model=model,
            keep_format=keep_format,
            output_format=output_format if output_format else "PNG"
        )
        
        # Connect signals
        self.denoiser_thread.progress_signal.connect(self.update_denoiser_progress)
        self.denoiser_thread.completion_signal.connect(self.denoising_completed)
        self.denoiser_thread.error_signal.connect(self.denoising_error)
        self.denoiser_thread.log_signal.connect(self.log)
        
        # Create progress dialog
        self.denoiser_progress_dialog = DenoiserProgressDialog(self)
        
        # Change the denoise button text and disable it
        self.denoise_btn.setText("Denoising...")
        self.denoise_btn.setEnabled(False)
        
        # Start thread and show dialog
        self.denoiser_thread.start()
        self.denoiser_progress_dialog.exec()

    def stop_denoising(self):
        """Stop the denoising thread"""
        if self.denoiser_thread:
            self.denoiser_thread.running = False
            self.denoiser_thread.cancelled = True
            
            # Close the progress dialog
            if hasattr(self, 'denoiser_progress_dialog') and self.denoiser_progress_dialog:
                self.denoiser_progress_dialog.close()
                self.denoiser_progress_dialog = None
            
            # Show cancellation message
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Denoising Cancelled")
            msg_box.setText("The denoising process has been cancelled.")
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
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['hover']};
                }}
            """)
            
            # Add buttons
            if self.denoiser_output_dir and os.path.exists(self.denoiser_output_dir):
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
            
            ok_btn = msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            ok_btn.setStyleSheet(f"""
                background-color: {COLORS['secondary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 150px;
            """)
            
            # Show dialog and handle response
            msg_box.exec()
            
            # Handle button clicks
            if hasattr(msg_box, 'clickedButton') and 'open_btn' in locals() and msg_box.clickedButton() == open_btn:
                if self.denoiser_output_dir and os.path.exists(self.denoiser_output_dir):
                    os.startfile(self.denoiser_output_dir)
            
            # Reset the denoise button
            self.denoise_btn.setText("✨ Denoise")
            self.update_denoise_button_state()

    def update_denoiser_progress(self, value, eta_text, speed_text):
        """Update the denoiser progress dialog"""
        if self.denoiser_progress_dialog:
            self.denoiser_progress_dialog.update_progress(value, eta_text, speed_text)

    def denoising_completed(self, last_output_path, input_size, output_size, success_count, failure_count):
        """Show a completion message for denoising with statistics"""
        # First close the progress dialog if it's still open
        if self.denoiser_progress_dialog and self.denoiser_progress_dialog.isVisible():
            self.denoiser_progress_dialog.accept()
            self.denoiser_progress_dialog = None
            
        # Don't show completion message if the operation was cancelled
        if hasattr(self, 'denoiser_thread') and self.denoiser_thread and self.denoiser_thread.cancelled:
            return
            
        # Format sizes in MB
        input_mb = input_size / (1024 * 1024)
        output_mb = output_size / (1024 * 1024)
        
        # Calculate size increase percentage (denoising usually increases size)
        if input_size > 0:
            increase = ((output_size - input_size) / input_size) * 100
            size_text = f"Size increased by {increase:.1f}%"
        else:
            size_text = "Size comparison not available"
        
        # Create message
        message = f"Denoising completed!\n\n"
        message += f"Files processed: {success_count} successful, {failure_count} failed\n"
        message += f"Input size: {input_mb:.2f} MB\n"
        message += f"Output size: {output_mb:.2f} MB\n"
        message += f"{size_text}"
        
        # Show styled message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Denoising Completed")
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
        
        # Show dialog and handle response
        msg_box.exec()
        
        # Handle button clicks
        if msg_box.clickedButton() == open_btn:
            # Open the output folder
            output_dir = os.path.dirname(last_output_path)
            if os.path.exists(output_dir):
                os.startfile(output_dir)

        # Reset the denoise button
        self.denoise_btn.setText("✨ Denoise")
        self.update_denoise_button_state()

        # Log completion
        self.log(f"Denoising completed: {success_count} succeeded, {failure_count} failed", 
                "SUCCESS" if failure_count == 0 else "INFO")

    def show_denoiser_instructions(self):
        """Show detailed instructions dialog for the Denoiser feature"""
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Use Image Denoiser")
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
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
        self.orientation_combo.addItems(["Vertical (Top to Bottom)", "Horizontal (Left to Right)"])
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
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
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
                direction = "→" if "Horizontal" in self.orientation_combo.currentText() else "↓"
                
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
                info_label = QLabel(f"Input : {files_text}\nOutput : {folder_name}_stitched.{format_text}\nInput Size :{input_size_str} → Output Size :{output_size_str}(approx.)\nStitching Direction {direction}")
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
        is_vertical = "Vertical" in self.orientation_combo.currentText()
        
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
            virtual_files=selected_files
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
            is_vertical = "Vertical" in orientation
            preview_text += f"<p><b>Stitch direction:</b> {'Vertical ↓' if is_vertical else 'Horizontal →'}</p>"
            
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

    def toggle_manual_spacing(self, state):
        """Toggle between preset spacing dropdown and manual spacing input"""
        if state == Qt.CheckState.Checked.value:
            # Enable manual input, disable dropdown
            self.manual_spacing_input.setEnabled(True)
            self.spacing_combo.setEnabled(False)
            
            # Store current value for transfer to manual input
            current_spacing = self.spacing_combo.currentText()
            
            # Apply disabled styling to the combo box
            self.spacing_combo.setStyleSheet("""
                QComboBox {
                    background-color: #3d3d4f;
                    color: #888888;
                    border: 1px solid #3d3d4f;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                }
            """)
            
            if not self.manual_spacing_input.text():
                self.manual_spacing_input.setText("0")
        else:
            # Enable dropdown, disable manual input
            self.manual_spacing_input.setEnabled(False)
            
            # Create a new AnimatedComboBox to replace the existing one
            current_index = self.spacing_combo.currentIndex()
            items = [self.spacing_combo.itemText(i) for i in range(self.spacing_combo.count())]
            
            # Find the parent layout
            parent_widget = self.spacing_combo.parent()
            for layout_item in parent_widget.children():
                if isinstance(layout_item, QHBoxLayout) and layout_item.indexOf(self.spacing_combo) != -1:
                    parent_layout = layout_item
                    position = parent_layout.indexOf(self.spacing_combo)
                    
                    # Remove old combo box
                    parent_layout.removeWidget(self.spacing_combo)
                    self.spacing_combo.deleteLater()
                    
                    # Create new combo box
                    self.spacing_combo = AnimatedComboBox()
                    self.spacing_combo.addItems(items)
                    self.spacing_combo.setCurrentIndex(current_index)
                    
                    # Add to layout
                    parent_layout.insertWidget(position, self.spacing_combo)
                    break
            else:
                # Fallback if layout not found
                self.spacing_combo.setEnabled(True)
                self.spacing_combo.setStyleSheet(f"""
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
            """)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    converter = ImageConverter()
    converter.show()
    sys.exit(app.exec())