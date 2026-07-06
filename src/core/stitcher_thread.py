import os
import re
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

class StitcherThread(QThread):
    """Thread for stitching images together"""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(int, int, str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, folders, output_dir, is_vertical, spacing, output_format, virtual_files=None, alignment="Center", bg_color="Transparent", resize_option="Don't Resize", reverse_order=False):
        super().__init__()
        self.folders = folders
        self.output_dir = output_dir
        self.is_vertical = is_vertical
        self.spacing = spacing
        self.output_format = output_format.lower()
        self.virtual_files = virtual_files or {}
        self.alignment = alignment
        self.bg_color = bg_color
        self.resize_option = resize_option
        self.reverse_order = reverse_order
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
            
        # Disable PIL's DecompressionBomb error for massive stitches
        Image.MAX_IMAGE_PIXELS = None
        
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
            
        if getattr(self, 'reverse_order', False):
            images.reverse()
        
        # Apply resize options if needed
        if len(images) > 0 and getattr(self, 'resize_option', "Don't Resize") != "Don't Resize":
            if self.is_vertical:
                # Vertical stitching: match widths
                if self.resize_option == "Match Smallest":
                    target_width = min(img.width for img in images)
                elif self.resize_option == "Match Largest":
                    target_width = max(img.width for img in images)
                else: # Match First
                    target_width = images[0].width
                
                for i in range(len(images)):
                    if images[i].width != target_width:
                        ratio = target_width / images[i].width
                        new_height = int(images[i].height * ratio)
                        resample = Image.Resampling.LANCZOS if ratio < 1 else Image.Resampling.BICUBIC
                        images[i] = images[i].resize((target_width, new_height), resample)
            else:
                # Horizontal stitching: match heights
                if self.resize_option == "Match Smallest":
                    target_height = min(img.height for img in images)
                elif self.resize_option == "Match Largest":
                    target_height = max(img.height for img in images)
                else: # Match First
                    target_height = images[0].height
                
                for i in range(len(images)):
                    if images[i].height != target_height:
                        ratio = target_height / images[i].height
                        new_width = int(images[i].width * ratio)
                        resample = Image.Resampling.LANCZOS if ratio < 1 else Image.Resampling.BICUBIC
                        images[i] = images[i].resize((new_width, target_height), resample)

        # Calculate dimensions of the stitched image
        if self.is_vertical:
            # Vertical stitching (top to bottom)
            width = max(img.width for img in images)
            height = sum(img.height for img in images) + self.spacing * (len(images) - 1)
        else:
            # Horizontal stitching (left to right)
            width = sum(img.width for img in images) + self.spacing * (len(images) - 1)
            height = max(img.height for img in images)
            
        # Parse background color
        bg_color_setting = getattr(self, 'bg_color', "Transparent")
        if bg_color_setting == "White":
            bg_color_rgba = (255, 255, 255, 255)
        elif bg_color_setting == "Black":
            bg_color_rgba = (0, 0, 0, 255)
        else: # Transparent
            bg_color_rgba = (0, 0, 0, 0)
        
        # Create a new image with the calculated dimensions
        mode = 'RGB' if self.output_format.lower() in ['jpg', 'jpeg'] else 'RGBA'
        
        # If output is JPEG and they chose transparent, force it to white
        if mode == 'RGB' and bg_color_rgba[3] == 0:
            bg_color_rgba = (255, 255, 255, 255)
            
        stitched = Image.new(mode, (width, height), bg_color_rgba)
        
        # Paste images into the stitched image
        x_offset = 0
        y_offset = 0
        
        alignment_setting = getattr(self, 'alignment', "Center")
        
        for img in images:
            if self.is_vertical:
                if alignment_setting == "Start (Left/Top)":
                    x_offset = 0
                elif alignment_setting == "End (Right/Bottom)":
                    x_offset = width - img.width
                else: # Center
                    x_offset = (width - img.width) // 2
                    
                stitched.paste(img, (x_offset, y_offset))
                y_offset += img.height + self.spacing
            else:
                if alignment_setting == "Start (Left/Top)":
                    y_offset = 0
                elif alignment_setting == "End (Right/Bottom)":
                    y_offset = height - img.height
                else: # Center
                    y_offset = (height - img.height) // 2
                    
                stitched.paste(img, (x_offset, y_offset))
                x_offset += img.width + self.spacing
        
        # Check limits and split into chunks if necessary to bypass WEBP/JPEG limitations
        max_dim = None
        if self.output_format.lower() == 'webp':
            max_dim = 16300
        elif self.output_format.lower() in ['jpg', 'jpeg']:
            max_dim = 65500
            
        def save_chunk(img_chunk, path):
            if self.output_format.lower() in ['jpg', 'jpeg']:
                img_chunk.save(path, 'JPEG', quality=95)
            elif self.output_format.lower() == 'png':
                img_chunk.save(path, 'PNG')
            elif self.output_format.lower() == 'webp':
                img_chunk.save(path, 'WEBP', quality=95)
            else:
                img_chunk.save(path)

        if max_dim and (width > max_dim or height > max_dim):
            import math
            base_path, ext = os.path.splitext(output_path)
            if self.is_vertical:
                num_chunks = math.ceil(height / max_dim)
                for i in range(num_chunks):
                    top = i * max_dim
                    bottom = min((i + 1) * max_dim, height)
                    chunk = stitched.crop((0, top, width, bottom))
                    save_chunk(chunk, f"{base_path}_part{i+1}{ext}")
            else:
                num_chunks = math.ceil(width / max_dim)
                for i in range(num_chunks):
                    left = i * max_dim
                    right = min((i + 1) * max_dim, width)
                    chunk = stitched.crop((left, 0, right, height))
                    save_chunk(chunk, f"{base_path}_part{i+1}{ext}")
        else:
            save_chunk(stitched, output_path)
        
        # Close all images to free memory
        for img in images:
            img.close()
            
