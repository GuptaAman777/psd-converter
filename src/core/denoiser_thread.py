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


