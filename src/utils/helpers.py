import os
import re
import sys
import time
import json
import shutil
import subprocess
import threading

_CACHED_GPUS = None
_SETTINGS_LOCK = threading.RLock()


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
        remaining = max(0, total - processed)
        eta_seconds = avg * remaining
        if eta_seconds < 60:
            eta_text = f"ETA: {int(eta_seconds)} seconds"
        elif eta_seconds < 3600:
            eta_text = f"ETA: {int(eta_seconds / 60)} minutes {int(eta_seconds % 60)} seconds"
        else:
            eta_text = f"ETA: {eta_seconds / 3600:.1f} hours"
    else:
        eta_text = "Calculating ETA..."
    if elapsed > 0 and processed > 0:
        speed_text = f"Speed: {processed / elapsed:.2f} files/second"
    else:
        speed_text = "Calculating speed..."
    return eta_text, speed_text


def detect_vulkan_support():
    """Fast, non-blocking check for Vulkan runtime availability."""
    if shutil.which('vulkaninfo') or shutil.which('vulkaninfo.exe') or shutil.which('vulkan-1.dll'):
        return True
    if os.name == 'nt':
        sys_root = os.environ.get('SystemRoot', r'C:\Windows')
        for sub in ('System32', 'SysWOW64'):
            if os.path.exists(os.path.join(sys_root, sub, 'vulkan-1.dll')):
                return True
    else:
        for p in ('/usr/lib/libvulkan.so.1', '/usr/lib/x86_64-linux-gnu/libvulkan.so.1'):
            if os.path.exists(p):
                return True
    return False


def detect_gpus(force_refresh=False):
    """Return a cached list of detected GPU adapter names."""
    global _CACHED_GPUS
    if _CACHED_GPUS is not None and not force_refresh:
        return list(_CACHED_GPUS)

    gpus = []
    if os.name == 'nt':
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                timeout=4
            )
            if result.returncode == 0 and result.stdout.strip():
                gpus = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception:
            gpus = []
    _CACHED_GPUS = gpus
    return list(gpus)


def get_gpu_combo_items():
    """Build display labels for compute device dropdowns using detected GPUs."""
    items = ["Auto (GPU)"]
    gpus = detect_gpus()
    if gpus:
        for idx, name in enumerate(gpus):
            short_name = name if len(name) <= 28 else name[:25] + "..."
            items.append(f"GPU {idx}: {short_name}")
    else:
        items.extend(["GPU 0", "GPU 1"])
    items.append("CPU (-1)")
    return items


def parse_gpu_id(gpu_choice):
    """Extract NCNN -g gpu-id argument from a compute device combo string."""
    text = str(gpu_choice or "")
    if "CPU" in text or "-1" in text:
        return "-1"
    m = re.search(r'\bGPU\s+(\d+)\b', text)
    if m:
        return m.group(1)
    return "auto"


def parse_tile_size(tile_choice):
    """Extract integer tile size from combo label such as 'Auto (0)' or '200'."""
    parts = str(tile_choice or "0").split()
    return int(parts[0]) if parts and parts[0].isdigit() else 0


def normalize_ncnn_format(fmt):
    """Normalize image format string for NCNN Vulkan CLI -f argument (jpg/png/webp)."""
    cleaned = str(fmt or "png").lower().lstrip('.')
    if cleaned in ('jpg', 'jpeg'):
        return 'jpg'
    if cleaned in ('png', 'webp'):
        return cleaned
    return 'png'


def parse_color_spec(spec, default_rgb=(255, 255, 255)):
    """Convert a color label ('White', 'Black', 'Gray', '#RRGGBB') into an (R, G, B) tuple."""
    s = str(spec or "").strip()
    low = s.lower()
    if low == "white":
        return (255, 255, 255)
    if low == "black":
        return (0, 0, 0)
    if low in ("gray", "grey", "neutral gray"):
        return (128, 128, 128)
    if s.startswith("#") and len(s) in (4, 7):
        try:
            hex_part = s[1:]
            if len(hex_part) == 3:
                hex_part = "".join(ch * 2 for ch in hex_part)
            return tuple(int(hex_part[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    return default_rgb


def parse_page_range(range_str, total_pages):
    """Parse 1-based PDF page range expression (e.g. '1-3, 5') into sorted 0-based indices."""
    txt = str(range_str or "").strip()
    if not txt or txt.lower() in ("all", "*"):
        return list(range(total_pages))
    indices = set()
    for token in txt.split(","):
        part = token.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-", 1)
            try:
                start = max(1, int(bounds[0].strip())) if bounds[0].strip() else 1
                end = min(total_pages, int(bounds[1].strip())) if bounds[1].strip() else total_pages
                for p in range(start, end + 1):
                    if 1 <= p <= total_pages:
                        indices.add(p - 1)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    indices.add(p - 1)
            except ValueError:
                continue
    return sorted(indices)


def resolve_conflict_path(target_path, policy="overwrite"):
    """Resolve destination path against conflict policy ('overwrite', 'skip', 'rename').

    Returns:
        str | None: Final destination path, or None if policy is 'skip' and file already exists.
    """
    norm_policy = str(policy or "overwrite").lower()
    if not os.path.exists(target_path) or norm_policy == "overwrite":
        return target_path
    if norm_policy == "skip":
        return None
    if norm_policy == "rename":
        base, ext = os.path.splitext(target_path)
        idx = 1
        while True:
            cand = f"{base}_{idx}{ext}"
            if not os.path.exists(cand):
                return cand
            idx += 1
    return target_path


def get_icon_path(icon_name):
    """Resolve path to an icon, handling PyInstaller environment."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
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
        src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(src_path, "assets", "icons", icon_name)


def _is_dir_writable(dir_path):
    try:
        os.makedirs(dir_path, exist_ok=True)
        probe = os.path.join(dir_path, f".write_probe_{os.getpid()}")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def get_app_user_data_dir():
    """Return per-user writable application data folder (LocalAppData/ImageTool on Windows)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    data_dir = os.path.join(base, "ImageTool")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_resource_path(*parts):
    """Resolve bundled read-only asset paths in both dev and PyInstaller frozen modes."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        meipass = getattr(sys, '_MEIPASS', exe_dir)
        for root in (meipass, exe_dir, os.path.join(exe_dir, "_internal")):
            cand = os.path.join(root, *parts)
            if os.path.exists(cand):
                return cand
        return os.path.join(meipass, *parts)
    src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_path = os.path.dirname(src_path)
    return os.path.join(base_path, *parts)


def get_data_path(filename):
    """Get writable path for data files like settings.json (portable beside exe when writable, else LocalAppData)."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        if not os.path.exists(os.path.join(exe_dir, ".installed")) and _is_dir_writable(exe_dir):
            base_path = exe_dir
        else:
            base_path = get_app_user_data_dir()
    else:
        src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_path = os.path.dirname(src_path)
    return os.path.join(base_path, filename)


def load_user_settings():
    """Load settings dictionary from settings.json."""
    settings_path = get_data_path("settings.json")
    with _SETTINGS_LOCK:
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def save_user_settings(new_settings):
    """Merge and save settings dictionary atomically to settings.json."""
    settings_path = get_data_path("settings.json")
    with _SETTINGS_LOCK:
        data = load_user_settings()
        data.update(new_settings)
        try:
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            tmp_path = f"{settings_path}.tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, settings_path)
            return True
        except Exception:
            return False


def get_tool_path(tool_name):
    """Resolve path to an external tool binary, handling PyInstaller and development environments."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        meipass_path = getattr(sys, '_MEIPASS', base_path)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        meipass_path = base_path

    tool_map = {
        "esr": [
            os.path.join("esr", "upscayl-bin.exe"),
            os.path.join("esr", "realesrgan-ncnn-vulkan.exe")
        ],
        "realesrgan": [
            os.path.join("esr", "realesrgan-ncnn-vulkan.exe")
        ],
        "waifu2x": [
            os.path.join("waifu2x-ncnn-vulkan", "waifu2x-ncnn-vulkan.exe"),
            os.path.join("waifu2x-ncnn-vulkan", "waifu2x-ncnn-vulkan_waifu2xEX.exe")
        ],
        "realcugan": [
            os.path.join("realcugan-ncnn-vulkan", "realcugan-ncnn-vulkan.exe")
        ],
        "srmd": [
            os.path.join("srmd-ncnn-vulkan", "srmd-ncnn-vulkan.exe")
        ]
    }

    subpaths = tool_map.get(tool_name.lower(), [os.path.join(tool_name, f"{tool_name}.exe")])

    roots_to_check = [
        os.path.join(base_path, "src", "core"),
        os.path.join(meipass_path, "src", "core"),
        os.path.join(base_path, "core"),
        os.path.join(meipass_path, "core"),
        base_path,
        meipass_path
    ]

    for rel in subpaths:
        for root in roots_to_check:
            cand = os.path.normpath(os.path.join(root, rel))
            if os.path.exists(cand):
                return cand

    fallback_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
    return os.path.normpath(os.path.join(fallback_dir, subpaths[0]))


def get_tool_info(tool_name):
    """Returns (exe_path, exe_dir) for the given tool."""
    exe_path = get_tool_path(tool_name)
    exe_dir = os.path.dirname(exe_path)
    return exe_path, exe_dir
