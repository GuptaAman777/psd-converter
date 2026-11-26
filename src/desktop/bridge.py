import ctypes
import os
import socket
import threading
import time
import uvicorn
import webview
from webview.dom import DOMEventHandler

from src.constants import APP_VERSION, INPUT_FORMATS
from src.server.app import create_app, hub


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _apply_win11_dark_glass_frame(hwnd: int):
    """Apply native Windows 11 DWM immersive dark titlebar & obsidian caption tint cleanly."""
    if not hwnd or os.name != "nt":
        return
    try:
        dwmapi = ctypes.windll.dwmapi
        dark_val = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_val), ctypes.sizeof(dark_val))
        # Caption color RGB(7, 10, 20) in COLORREF (0x00BBGGRR) -> 0x00140A07
        caption_color = ctypes.c_int(0x00140A07)
        dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))
        border_color = ctypes.c_int(0x002D241E)
        dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), ctypes.sizeof(border_color))
    except Exception:
        pass


class DesktopBridge:
    """Exposed JS API (`window.pywebview.api`) for native file/folder pickers and OS integration."""

    def __init__(self):
        self._window = None

    def bind_window(self, win):
        self._window = win

    def browse_files(self, allowed_exts=None):
        if not self._window:
            return []
        exts = [e.lower().lstrip(".") for e in (allowed_exts or INPUT_FORMATS)]
        pattern = ";".join(f"*.{e}" for e in exts)
        file_types = (f"Supported Files ({pattern})", "All Files (*.*)")
        res = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=True,
            file_types=file_types,
        )
        return list(res) if res else []

    def browse_folder(self):
        if not self._window:
            return ""
        res = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if res and len(res) > 0:
            return str(res[0])
        return ""

    def open_folder(self, folder_path: str):
        if folder_path and os.path.exists(folder_path):
            os.startfile(folder_path)
            return True
        return False


def launch_liquid_studio():
    """Start in-process FastAPI server and open GPU-accelerated Edge WebView2 Liquid Glass UI."""
    port = _find_free_port()
    fastapi_app = create_app()
    config = uvicorn.Config(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    srv_thread = threading.Thread(target=server.run, daemon=True)
    srv_thread.start()

    # Wait briefly until uvicorn binds port cleanly
    deadline = time.time() + 6.0
    while not server.started and time.time() < deadline:
        time.sleep(0.03)

    bridge = DesktopBridge()
    win = webview.create_window(
        title=f"ImageTool — PSD & AI Image Suite (v{APP_VERSION})",
        url=f"http://127.0.0.1:{port}/",
        js_api=bridge,
        width=1320,
        height=840,
        min_size=(460, 560),
        background_color="#070a14",
        resizable=True,
        text_select=False,
    )
    bridge.bind_window(win)

    def _on_drop(event):
        try:
            files = event.get("dataTransfer", {}).get("files", [])
            paths = []
            seen = set()
            for f in files:
                fp = f.get("pywebviewFullPath") or f.get("path") or f.get("name") or ""
                if fp and os.path.exists(fp) and fp not in seen:
                    seen.add(fp)
                    paths.append(fp)
            if paths:
                hub.broadcast({"type": "dnd_drop", "paths": paths})
        except Exception:
            pass

    drop_handler = DOMEventHandler(_on_drop, prevent_default=True, stop_propagation=False)

    def _on_loaded():
        try:
            hwnd = int(getattr(win.native, "Handle", 0).ToInt64()) if hasattr(win.native, "Handle") else 0
            _apply_win11_dark_glass_frame(hwnd)
        except Exception:
            pass
        try:
            drop_event = win.dom.document.events.drop
            if drop_handler not in getattr(drop_event, "_items", ()):
                win.dom.document.events.drop += drop_handler
        except Exception:
            pass

    win.events.loaded += _on_loaded
    webview.start(gui="edgechromium", debug=False)
    server.should_exit = True
