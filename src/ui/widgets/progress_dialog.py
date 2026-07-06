import os
import time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from src.constants import COLORS, APP_VERSION, GITHUB_RELEASES_URL
from src.ui.styles import STYLES
from src.utils.helpers import natural_sort_key, get_file_icon, format_size, get_icon_path

class ProcessingProgressDialog(QDialog):
    """Single progress dialog used for Converter, Upscaler, and Denoiser."""

    def __init__(self, parent=None, title="Processing...", label="Processing Files...", cancel_callback=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(450, 220)
        self.setModal(True)
        self._cancel_callback = cancel_callback

        # Window icon
        icon_path = get_icon_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(f"QDialog {{ background-color: {COLORS['background']}; color: {COLORS['text']}; border-radius: 10px; }}")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 25)
        layout.setSpacing(15)

        title_lbl = QLabel(label)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet(STYLES['progress_bar'])
        layout.addWidget(self.progress_bar)

        self.eta_label = QLabel("Preparing...")
        self.eta_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.eta_label)

        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.speed_label)

        layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(45)
        self.cancel_btn.setMinimumWidth(160)
        self.cancel_btn.setFont(QFont("Segoe UI", 10))
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['error']}; color: white; border: none; border-radius: 8px;
                          padding: 10px; font-weight: 600; margin-bottom: 5px; }}
            QPushButton:hover {{ background-color: #FF6B6B; }}
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self.cancel_btn)
        self.setLayout(layout)

    def _on_cancel(self):
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #d13438; border-radius: 8px; }")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelling...")
        if self._cancel_callback:
            self._cancel_callback()

    def update_progress(self, value, eta_text, speed_text):
        self.progress_bar.setValue(value)
        self.eta_label.setText(eta_text)
        self.speed_label.setText(speed_text)


# ── FileListManager ─────────────────────────────────────────────────────────────

