import os
import re
import sys
import time

def natural_sort_key(s):
    """Key function for natural (human-friendly) sorting of strings."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def format_size(size_bytes):
    """Format file size in bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_file_icon(ext):
    ext = ext.lower().lstrip('.')
    if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'tif'):
        return '🖼️'
    if ext == 'pdf':
        return '📑'
    if ext == 'psd':
        return '🎨'
    return '📄'

def calculate_progress_info(processed, total, start_time):
    elapsed = time.time() - start_time
    if processed > 0:
        avg = elapsed / processed
        remaining = total - processed
        eta_seconds = avg * remaining
        if eta_seconds < 60:
            eta_text = f"ETA: {int(eta_seconds)} seconds"
        elif eta_seconds < 3600:
            eta_text = f"ETA: {int(eta_seconds / 60)} minutes {int(eta_seconds % 60)} seconds"
        else:
            eta_text = f"ETA: {eta_seconds / 3600:.1f} hours"
    else:
        eta_text = "Calculating ETA..."
    if elapsed > 0:
        speed_text = f"Speed: {processed / elapsed:.2f} files/second"
    else:
        speed_text = "Calculating speed..."
    return eta_text, speed_text

def get_icon_path(icon_name):
    """Resolve path to an icon, handling PyInstaller environment."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        # Check src/assets/icons first since we bundled it as src/assets
        src_test_path = os.path.join(base_path, "src", "assets", "icons", icon_name)
        test_path = os.path.join(base_path, "assets", "icons", icon_name)
        if os.path.exists(src_test_path):
            return src_test_path
        elif os.path.exists(test_path):
            return test_path
        elif os.path.exists(os.path.join(base_path, "icons", icon_name)):
            return os.path.join(base_path, "icons", icon_name)
        else:
            return os.path.join(base_path, icon_name)
    else:
        # Path during development (src/assets/icons)
        src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(src_path, "assets", "icons", icon_name)

def get_data_path(filename):
    """Get the path for data files like settings.json, handling PyInstaller onefile mode."""
    if getattr(sys, 'frozen', False):
        # In PyInstaller, save next to the executable
        base_path = os.path.dirname(sys.executable)
    else:
        # In development, save in the src/ui directory (where main_window.py is)
        src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_path = os.path.join(src_path, "ui")
    return os.path.join(base_path, filename)

def get_tool_path(tool_name):
    """Resolve path to an external tool binary, handling PyInstaller environment."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        meipass_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        meipass_path = base_path
    
    tool_map = {
        "esr": os.path.join("esr", "realesrgan-ncnn-vulkan.exe"),
        "waifu2x": os.path.join("waifu2x-ncnn-vulkan", "waifu2x-ncnn-vulkan_waifu2xEX.exe"),
        "waifu2x_alt": os.path.join("waifu2x-ncnn-vulkan", "waifu2x-ncnn-vulkan.exe"),
        "realcugan": os.path.join("realcugan-ncnn-vulkan", "realcugan-ncnn-vulkan.exe")
    }
    
    def find_existing_path(paths_to_try):
        for p in paths_to_try:
            if os.path.exists(p):
                return p
        return paths_to_try[-1] # Fallback to last tested path

    if tool_name == "waifu2x":
        paths = [
            os.path.join(base_path, tool_map["waifu2x"]),
            os.path.join(base_path, tool_map["waifu2x_alt"]),
            os.path.join(meipass_path, "src", "core", tool_map["waifu2x"]),
            os.path.join(meipass_path, "src", "core", tool_map["waifu2x_alt"])
        ]
        return find_existing_path(paths)
        
    mapped = tool_map.get(tool_name, "")
    paths = [
        os.path.join(base_path, mapped),
        os.path.join(meipass_path, "src", "core", mapped)
    ]
    return find_existing_path(paths)
