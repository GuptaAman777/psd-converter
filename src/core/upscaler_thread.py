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

class UpscalerThread(QThread):
    progress_signal = pyqtSignal(int, str, str)
    completion_signal = pyqtSignal(str, int, int, int, int)
    error_signal = pyqtSignal(str, str)
    log_signal = pyqtSignal(str, str)
    
    def __init__(self, selected_files, output_dir, upscale_factor="2x", model="waifu2x", 
                 keep_format=True, output_format="PNG", noise_level=0, style_model="models-cunet"):
        super().__init__()
        self.files = selected_files
        self.output_dir = output_dir
        self.upscale_factor = upscale_factor
        self.model = model
        self.keep_format = keep_format
        self.output_format = output_format
        self.noise_level = noise_level
        self.style_model = style_model

        self.running = True
        self.cancelled = False
        self.total_files = len(selected_files)
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
            self.log_signal.emit(f"Error cleaning up temp directory: {str(e)}", "ERROR")
    
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
                
                # Use GPU (auto) unconditionally
                gpu_id = "auto"
                
                cmd = [
                    waifu2x_path,
                    "-i", input_path,
                    "-o", output_path,
                    "-n", str(self.noise_level),  # Use the noise level parameter
                    "-s", str(scale_factor),
                    "-m", self.style_model,  # Model path
                    "-f", os.path.splitext(output_path)[1].lower().lstrip('.'),
                    "-g", gpu_id  # Use CPU (-1) or GPU (auto)
                ]
                
                self.log_signal.emit(f"Running waifu2x with noise level {self.noise_level}, model {self.style_model}, using GPU", "INFO")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    timeout=300, 
                    startupinfo=startupinfo, 
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    cwd=waifu2x_dir
                )
            elif self.model.lower() == "realcugan":
                cugan_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "realcugan-ncnn-vulkan")
                cugan_path = os.path.join(cugan_dir, "realcugan-ncnn-vulkan.exe")
                
                cugan_noise = self.noise_level
                cugan_scale = scale_factor
                cugan_model = self.style_model
                
                # Enforce Real-CUGAN model constraints natively
                if cugan_model == "models-nose":
                    if cugan_scale != 2:
                        self.log_signal.emit(f"models-nose only supports 2x scale. Falling back to 2x.", "WARNING")
                        cugan_scale = 2
                elif cugan_model == "models-pro":
                    if cugan_scale == 4:
                        self.log_signal.emit(f"models-pro does not support 4x scale. Using models-se instead.", "WARNING")
                        cugan_model = "models-se"
                
                if cugan_model == "models-se":
                    if cugan_scale in [3, 4] and cugan_noise not in [-1, 0, 3]:
                        self.log_signal.emit(f"models-se {cugan_scale}x only supports noise levels -1, 0, 3. Falling back to noise level 3.", "WARNING")
                        cugan_noise = 3
                
                if not os.path.exists(cugan_dir):
                    os.makedirs(cugan_dir)
                    raise Exception(f"Real-CUGAN directory created at: {cugan_dir}. Please download and place realcugan-ncnn-vulkan.exe in this directory.")
                
                if not os.path.exists(cugan_path):
                    raise Exception(f"Real-CUGAN executable not found in realcugan-ncnn-vulkan directory. Please download and place it there.")
                
                gpu_id = "auto"
                
                cmd = [
                    cugan_path,
                    "-i", input_path,
                    "-o", output_path
                ]
                
                if cugan_model == "models-se":
                    cmd.extend(["-n", str(cugan_noise)])
                elif cugan_model == "models-nose":
                    cmd.extend(["-n", "0"])
                    
                cmd.extend([
                    "-s", str(cugan_scale),
                    "-m", cugan_model,
                    "-f", os.path.splitext(output_path)[1].lower().lstrip('.'),
                    "-g", "auto"
                ])
                
                device_type = "GPU"
                noise_log = f"with noise level {cugan_noise}" if cugan_model == "models-se" else "with default noise"
                self.log_signal.emit(f"Running Real-CUGAN {noise_log}, model {cugan_model}, using {device_type}", "INFO")
                
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
                
                # Use style_model for the actual ESRGAN model name (supports sub-models)
                esrgan_model_name = self.style_model if self.style_model and not self.style_model.startswith("models-") else self.model
                
                # Run realesrgan-ncnn-vulkan
                cmd = [
                    esr_path,
                    "-i", input_path,
                    "-o", output_path,
                    "-s", str(scale_factor),
                    "-n", esrgan_model_name,  # Use the actual ESRGAN model name
                    "-f", os.path.splitext(output_path)[1].lower().lstrip('.'),
                    "-g", "auto"
                ]
                
                self.log_signal.emit(f"Running ESRGAN with model {esrgan_model_name}, using GPU", "INFO")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    timeout=300, 
                    startupinfo=startupinfo, 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            # Check if the process crashed
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='ignore').strip()
                raise Exception(f"Upscaler process crashed (code {result.returncode}). Error output:\n{stderr}")
                
            # Check if the output file was created
            if not os.path.exists(output_path):
                stderr = result.stderr.decode('utf-8', errors='ignore').strip()
                raise Exception(f"Failed to create output file. Error: {stderr}")
            
            # Return the output path
            return output_path
            
        except subprocess.TimeoutExpired:
            raise Exception(f"Upscaling timed out after 5 minutes. The image may be too large.")
        except Exception as e:
            raise Exception(f"Error during upscaling: {str(e)}")
            

