import os
import sys
import time
import subprocess
import gc
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image, ImageFile
from psd_tools import PSDImage

try:
    import fitz
    PDF_CONVERTER = "pymupdf"
except ImportError:
    PDF_CONVERTER = None

class ConverterThread(QThread):
    progress_signal = pyqtSignal(int, str, str)
    completion_signal = pyqtSignal(str, float, float, int, int)
    error_signal = pyqtSignal(str, str)
    
    
    def __init__(self, files, output_dir, output_format, settings, enable_upscale=False, upscale_settings=None):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.output_format = output_format.lower()
        self.settings = settings 
        self.enable_upscale = enable_upscale

        self.upscale_settings = upscale_settings or {}
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
                self.log_signal.emit(f"Error terminating process: {str(e)}", "ERROR")
        
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
                    scale_factor = int(self.upscale_settings.get('scale', '2x')[0])
                    temp_output = output_path
                    
                    # Create a temporary filename for the upscaled version
                    temp_upscaled = os.path.join(
                        self.output_dir,
                        f"{base_name_without_ext}_temp.{self.output_format}"
                    )
                    
                    # Determine model and executable from upscale_settings
                    model_name = self.upscale_settings.get('model', 'realesr').lower()
                    style_model = self.upscale_settings.get('style_model', 'realesr-animevideov3')
                    noise_level = self.upscale_settings.get('noise_level', -1)
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    
                    if model_name == "waifu2x":
                        exe_dir = os.path.join(base_dir, "waifu2x-ncnn-vulkan")
                        exe_path = os.path.join(exe_dir, "waifu2x-ncnn-vulkan_waifu2xEX.exe")
                        if not os.path.exists(exe_path):
                            exe_path = os.path.join(exe_dir, "waifu2x-ncnn-vulkan.exe")
                    elif model_name == "realcugan":
                        exe_dir = os.path.join(base_dir, "realcugan-ncnn-vulkan")
                        exe_path = os.path.join(exe_dir, "realcugan-ncnn-vulkan.exe")
                    else:
                        exe_dir = os.path.join(base_dir, "esr")
                        exe_path = os.path.join(exe_dir, "realesrgan-ncnn-vulkan.exe")
                    
                    if not os.path.exists(exe_path):
                        raise Exception(f"AI upscaler not found at: {exe_path}")
                    
                    try:
                        startupinfo = None
                        if os.name == 'nt':
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            startupinfo.wShowWindow = 0
                        
                        # Build command based on model type
                        cmd = [exe_path, "-i", temp_output, "-o", temp_upscaled]
                        
                        if model_name == "waifu2x":
                            cmd.extend(["-s", str(scale_factor), "-n", str(noise_level), "-m", style_model])
                        elif model_name == "realcugan":
                            if style_model == "models-se":
                                cmd.extend(["-n", str(noise_level)])
                            elif style_model == "models-nose":
                                cmd.extend(["-n", "0"])
                            cmd.extend(["-s", str(scale_factor), "-m", style_model])
                        else:
                            # ESRGAN variants
                            esrgan_model = style_model if style_model and not style_model.startswith("models-") else "realesr-animevideov3"
                            cmd.extend(["-s", str(scale_factor), "-n", esrgan_model])
                        
                        cmd.extend(["-f", self.output_format])
                        
                        # Use GPU (auto) unconditionally
                        if model_name == "waifu2x":
                            cmd.extend(["-g", "auto"])
                        else:
                            cmd.extend(["-g", "auto"])
                            
                        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, 
                           stderr=subprocess.PIPE,
                           timeout=300, 
                           startupinfo=startupinfo, 
                           creationflags=subprocess.CREATE_NO_WINDOW,
                           cwd=exe_dir)
                        
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
                        self.log_signal.emit(f"Error deleting temporary file {file_path}: {str(e)}", "ERROR")
        except Exception as e:
            self.log_signal.emit(f"Error cleaning up temporary directory: {str(e)}", "ERROR")
    
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
            
            self._save_image_with_settings(psd_image, output_path)
            
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
                    
                    if self.output_format.lower() == 'pdf':
                        # Just copy the PDF file if output is also PDF
                        pdf_document.save(output_path, garbage=3, deflate=True)
                    else:
                        self._save_image_with_settings(img, output_path)
                else:
                    # For multi-page PDFs, convert only the first page
                    base_name = os.path.splitext(output_path)[0]
                    output_path = f"{base_name}_page1.{self.output_format}"
                    
                    page = pdf_document.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
                    
                    # Convert pixmap to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    if self.output_format.lower() == 'pdf':
                        # For PDF to PDF, extract just the first page
                        new_pdf = fitz.open()
                        new_pdf.insert_pdf(pdf_document, from_page=0, to_page=0)
                        new_pdf.save(output_path, garbage=3, deflate=True)
                        new_pdf.close()
                    else:
                        self._save_image_with_settings(img, output_path)
                
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
                
                self._save_image_with_settings(img, output_path)
                    
        except Exception as e:
            raise Exception(f"Image conversion error: {str(e)}")

    def _save_image_with_settings(self, img, output_path):
        """Save a PIL Image using the current format settings."""
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

