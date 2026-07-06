from src.constants import *
from src.config import *
from src.ui.widgets.animated_combobox import AnimatedComboBox
import os
import time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from src.constants import COLORS, APP_VERSION, GITHUB_RELEASES_URL
from src.ui.styles import STYLES
from src.utils.helpers import natural_sort_key, get_file_icon, format_size, get_icon_path

class UpscaleSettingsDialog(QDialog):
    """Dialog for configuring upscale model settings in the converter tab."""
    
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Upscale Settings")
        self.setFixedSize(420, 350)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['background']}; color: {COLORS['text']}; border-radius: 10px; }}
            QLabel {{ color: {COLORS['text']}; font-size: 12px; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("⚙️ Upscale Model Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title)
        
        note = QLabel("These settings will be used when upscaling in the Converter tab.")
        note.setStyleSheet(f"font-size: 10px; color: {COLORS['text_secondary']}; margin-bottom: 8px;")
        note.setWordWrap(True)
        layout.addWidget(note)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("AI Model:")
        model_label.setFixedWidth(100)
        model_layout.addWidget(model_label)
        self.model_combo = AnimatedComboBox()
        self.model_combo.addItems(UPSCALE_MODELS)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        # Style selection
        style_layout = QHBoxLayout()
        self.style_label = QLabel("Style:")
        self.style_label.setFixedWidth(100)
        style_layout.addWidget(self.style_label)
        self.style_combo = AnimatedComboBox()
        self.style_combo.currentTextChanged.connect(self._on_style_changed)
        style_layout.addWidget(self.style_combo)
        layout.addLayout(style_layout)
        
        # Noise level
        noise_layout = QHBoxLayout()
        self.noise_label = QLabel("Noise Level:")
        self.noise_label.setFixedWidth(100)
        noise_layout.addWidget(self.noise_label)
        self.noise_combo = AnimatedComboBox()
        self.noise_combo.addItems(["-1 (None)", "0 (Low)", "1 (Light)", "2 (Medium)", "3 (High)"])
        self.noise_combo.setCurrentIndex(1)
        noise_layout.addWidget(self.noise_combo)
        layout.addLayout(noise_layout)
        
        # Scale factor
        scale_layout = QHBoxLayout()
        scale_label = QLabel("Scale Factor:")
        scale_label.setFixedWidth(100)
        scale_layout.addWidget(scale_label)
        self.scale_combo = AnimatedComboBox()
        self.scale_combo.addItems(["2x", "3x", "4x"])
        self.scale_combo.currentTextChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.scale_combo)
        layout.addLayout(scale_layout)
        
        layout.addStretch()
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setFixedHeight(38)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['primary']}; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 13px; }}
            QPushButton:hover {{ background-color: {COLORS['hover']}; }}
        """)
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)
        
        # Initialize model state
        if current_settings:
            idx = self.model_combo.findText(current_settings.get('model', 'realesr'))
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
        self._on_model_changed(self.model_combo.currentText())
        
        # Restore saved style/noise/scale after model init
        if current_settings:
            style_idx = self.style_combo.findText(current_settings.get('style_display', ''))
            if style_idx >= 0:
                self.style_combo.setCurrentIndex(style_idx)
            noise_idx = self.noise_combo.findText(current_settings.get('noise_display', ''))
            if noise_idx >= 0:
                self.noise_combo.setCurrentIndex(noise_idx)
            scale_idx = self.scale_combo.findText(current_settings.get('scale', '2x'))
            if scale_idx >= 0:
                self.scale_combo.setCurrentIndex(scale_idx)
    
    def _on_model_changed(self, model_name):
        model_lower = model_name.lower()
        self.style_combo.clear()
        
        if model_lower == "waifu2x":
            style_options = {
                "CUnet (Best Quality)": "models-cunet",
                "Upconv (Anime/Art)": "models-upconv_7_anime_style_art_rgb",
                "Upconv (Photo)": "models-upconv_7_photo"
            }
            self.scale_combo.clear()
            self.scale_combo.addItems(["1x", "2x", "4x"])
        elif model_lower == "realcugan":
            style_options = {
                "SE (Standard)": "models-se",
                "Pro (Advanced)": "models-pro",
                "Nose (Retain Details)": "models-nose"
            }
            self.scale_combo.clear()
            self.scale_combo.addItems(["2x", "3x", "4x"])
        elif model_lower == "realesr":
            style_options = {
                "AnimeVideo V3 (2x/3x/4x)": "realesr-animevideov3",
                "RealESRGAN+ (4x only)": "realesrgan-x4plus",
                "RealESRGAN+ Anime (4x only)": "realesrgan-x4plus-anime"
            }
            self.scale_combo.clear()
            self.scale_combo.addItems(["2x", "3x", "4x"])
        else:
            style_options = {}
        
        self.style_combo.addItems(list(style_options.keys()))
        self.style_combo.setProperty("modelMapping", style_options)
        
        show_style = bool(style_options)
        self.style_label.setVisible(show_style)
        self.style_combo.setVisible(show_style)
        self._on_style_changed(self.style_combo.currentText() if self.style_combo.count() > 0 else "")
    
    def _on_style_changed(self, style_name):
        model_lower = self.model_combo.currentText().lower()
        
        if model_lower == "waifu2x":
            mapping = self.style_combo.property("modelMapping") or {}
            actual = mapping.get(style_name, "")
            is_upconv = "upconv" in actual
            if is_upconv:
                cur = self.scale_combo.currentText()
                self.scale_combo.blockSignals(True)
                self.scale_combo.clear()
                self.scale_combo.addItems(["2x", "4x"])
                idx = self.scale_combo.findText(cur)
                if idx >= 0:
                    self.scale_combo.setCurrentIndex(idx)
                else:
                    self.scale_combo.setCurrentIndex(0)
                self.scale_combo.blockSignals(False)
            else:
                cur = self.scale_combo.currentText()
                self.scale_combo.blockSignals(True)
                self.scale_combo.clear()
                self.scale_combo.addItems(["1x", "2x", "4x"])
                idx = self.scale_combo.findText(cur)
                if idx >= 0:
                    self.scale_combo.setCurrentIndex(idx)
                self.scale_combo.blockSignals(False)
                
            self.noise_combo.setEnabled(True)
            self.noise_label.setEnabled(True)
            self.noise_label.setStyleSheet("")
            self.noise_combo.setToolTip("")
        elif model_lower == "realesr":
            self.noise_combo.setEnabled(False)
            self.noise_label.setEnabled(False)
            self.noise_label.setStyleSheet("color: #777777;")
            self.noise_combo.setToolTip("Noise level is not supported by ESRGAN models.")
            mapping = self.style_combo.property("modelMapping") or {}
            actual = mapping.get(style_name, "")
            if "x4plus" in actual:
                self.scale_combo.blockSignals(True)
                self.scale_combo.clear()
                self.scale_combo.addItems(["4x"])
                self.scale_combo.blockSignals(False)
            else:
                cur = self.scale_combo.currentText()
                self.scale_combo.blockSignals(True)
                self.scale_combo.clear()
                self.scale_combo.addItems(["2x", "3x", "4x"])
                idx = self.scale_combo.findText(cur)
                if idx >= 0:
                    self.scale_combo.setCurrentIndex(idx)
                self.scale_combo.blockSignals(False)
        elif model_lower == "realcugan":
            self._update_cugan_options()
        else:
            self.noise_combo.setEnabled(True)
            self.noise_label.setEnabled(True)
            self.noise_label.setStyleSheet("")
            self.noise_combo.setToolTip("")

    def _on_scale_changed(self, scale_text):
        model_lower = self.model_combo.currentText().lower()
        if model_lower == "waifu2x":
            if scale_text == "1x":
                # 1x scale only supports CUnet model
                idx = self.style_combo.findText("CUnet (Best Quality)")
                if idx >= 0 and self.style_combo.currentIndex() != idx:
                    self.style_combo.setCurrentIndex(idx)
        if model_lower == "realcugan":
            self._update_cugan_options()

    def _update_cugan_options(self):
        style_name = self.style_combo.currentText()
        is_se = "SE" in style_name
        is_pro = "Pro" in style_name
        is_nose = "Nose" in style_name
        
        current_scale = self.scale_combo.currentText()
        current_noise = self.noise_combo.currentText()
        
        # Valid scales
        if is_nose:
            valid_scales = ["2x"]
        else:
            valid_scales = ["2x", "3x", "4x"]
            
        self.scale_combo.blockSignals(True)
        self.scale_combo.clear()
        self.scale_combo.addItems(valid_scales)
        if current_scale in valid_scales:
            self.scale_combo.setCurrentText(current_scale)
        self.scale_combo.blockSignals(False)
        current_scale = self.scale_combo.currentText()
        
        # Valid noise levels
        if is_nose:
            valid_noise = ["-1 (None)"]
        elif is_pro:
            valid_noise = ["-1 (None)", "0 (Low)", "3 (High)"]
        elif is_se:
            if current_scale == "2x":
                valid_noise = ["-1 (None)", "0 (Low)", "1 (Light)", "2 (Medium)", "3 (High)"]
            else:
                valid_noise = ["-1 (None)", "0 (Low)", "3 (High)"]
        else:
            valid_noise = ["-1 (None)", "0 (Low)", "1 (Light)", "2 (Medium)", "3 (High)"]
            
        self.noise_combo.blockSignals(True)
        self.noise_combo.clear()
        self.noise_combo.addItems(valid_noise)
        if current_noise in valid_noise:
            self.noise_combo.setCurrentText(current_noise)
        elif current_noise == "1 (Light)" and "0 (Low)" in valid_noise:
            self.noise_combo.setCurrentText("0 (Low)")
        elif current_noise == "2 (Medium)" and "3 (High)" in valid_noise:
            self.noise_combo.setCurrentText("3 (High)")
        elif current_noise not in valid_noise and valid_noise:
            self.noise_combo.setCurrentText(valid_noise[0])
        self.noise_combo.blockSignals(False)
        
        has_noise_options = len(valid_noise) > 1
        self.noise_combo.setEnabled(has_noise_options)
        self.noise_label.setEnabled(has_noise_options)
        self.noise_label.setStyleSheet("" if has_noise_options else "color: #777777;")
        self.noise_combo.setToolTip("" if has_noise_options else "Noise level is fixed for this model.")

    def get_settings(self):
        mapping = self.style_combo.property("modelMapping") or {}
        style_display = self.style_combo.currentText()
        style_model = mapping.get(style_display, "")
        noise_text = self.noise_combo.currentText().split()[0]
        try:
            noise_level = int(noise_text)
        except ValueError:
            noise_level = -1
        
        return {
            'model': self.model_combo.currentText(),
            'style_display': style_display,
            'style_model': style_model,
            'noise_level': noise_level if self.noise_combo.isEnabled() else -1,
            'noise_display': self.noise_combo.currentText(),
            'scale': self.scale_combo.currentText(),
        }
