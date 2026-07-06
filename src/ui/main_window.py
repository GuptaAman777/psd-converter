import os
import subprocess
import sys
import time
import re
import threading
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from src.constants import *
from src.config import *
from src.utils.helpers import *
from src.utils.logger import logger
from src.utils.updater import UpdateCheckerThread
from src.managers.file_list_manager import FileListManager
from src.ui.styles import *
from src.ui.widgets.progress_dialog import ProcessingProgressDialog
from src.ui.widgets.update_notification import UpdateNotification
from src.ui.widgets.animated_combobox import AnimatedComboBox
from src.ui.widgets.upscale_settings import UpscaleSettingsDialog
from src.core.converter_thread import ConverterThread
from src.core.upscaler_thread import UpscalerThread
from src.core.denoiser_thread import DenoiserThread
from src.core.stitcher_thread import StitcherThread

from src.ui.panels.converter_panel import ConverterPanelMixin
from src.ui.panels.upscaler_panel import UpscalerPanelMixin
from src.ui.panels.denoiser_panel import DenoiserPanelMixin
from src.ui.panels.stitcher_panel import StitcherPanelMixin
from src.ui.panels.settings_panel import SettingsPanelMixin
from src.ui.panels.footer import FooterMixin

class ImageConverter(QWidget, ConverterPanelMixin, UpscalerPanelMixin, DenoiserPanelMixin, StitcherPanelMixin, SettingsPanelMixin, FooterMixin):
    def __init__(self):
        super().__init__()
        self.vulkan_support = False  # Add this line to track Vulkan support

        # Initialize logger
        self.log_messages = []
        
        # Redirect stdout to capture terminal output
        self.setup_stdout_redirect()

        # Set window icon
        icon_path = get_icon_path("icon.ico")
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
        
        # Initialize file managers
        self.converter_fm = FileListManager(self, INPUT_FORMATS, self.update_convert_button_state, "")
        self.upscaler_fm = FileListManager(self, UPSCALE_FORMATS, self.update_upscale_button_state, "upscaler_")
        self.denoiser_fm = FileListManager(self, DENOISE_FORMATS, self.update_denoise_button_state, "denoiser_")
        
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
            from src.utils.helpers import get_data_path
            settings_path = get_data_path("settings.json")
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
                    from src.utils.helpers import get_data_path
                    settings_path = get_data_path("settings.json")
                    
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

    def check_gpu_compatibility(self):
        """Check if GPU supports upscaling using ESRGAN-style detection"""
        try:
            if os.name == 'nt':  # Windows
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                    result = subprocess.run(
                        ['powershell', '-Command', 'Get-WmiObject win32_VideoController | Select-Object -ExpandProperty Name'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        startupinfo=startupinfo,
                        text=True,
                        timeout=5
                    )
                    
                    output = result.stdout.strip().lower()
                    gpu_lines = [line.strip() for line in output.split('\n') if line.strip()]
                    
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
        from src.utils.helpers import get_data_path
        settings_path = get_data_path("settings.json")
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
                    from src.utils.helpers import get_data_path
                    settings_path = get_data_path("settings.json")
                    
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
            # Handle check.png path
            check_icon_path = get_icon_path('check.png')
            
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
        file_panel = self.converter_fm.create_right_panel()
        home_layout.addWidget(converter_panel, 2)
        home_layout.addWidget(file_panel, 3)

        # Create Upscaler tab
        upscaler_tab = QWidget()
        upscaler_layout = QHBoxLayout(upscaler_tab)
        upscaler_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        upscaler_layout.setSpacing(0)
        
        # Add upscaler settings and file panel to Upscaler tab
        upscaler_panel = self.create_upscaler_panel()
        upscaler_file_panel = self.upscaler_fm.create_right_panel()
        upscaler_layout.addWidget(upscaler_panel, 2)
        upscaler_layout.addWidget(upscaler_file_panel, 3)

        # In the initUI method, after creating the tab widget
        denoiser_tab = QWidget()
        denoiser_layout = QHBoxLayout(denoiser_tab)
        denoiser_layout.setContentsMargins(0, 0, 0, 0)
        denoiser_layout.setSpacing(0)

        # Add denoiser settings and file panel
        denoiser_panel = self.create_denoiser_panel()
        denoiser_file_panel = self.denoiser_fm.create_right_panel()
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
        if hasattr(self, 'upscaler_noise_level_combo'):
            self.upscaler_noise_level_combo.setVisible(visible)
            
        # Find the noise level label (it's usually next to the combo)
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLabel) and "Noise Level:" in item.widget().text():
                item.widget().setVisible(visible)
                break

    def on_style_changed(self, style_name):
        """Handle changes to the upscaler style selection"""
        if not hasattr(self, 'upscaler_noise_level_combo'):
            return
            
        model_name = self.upscaler_model_combo.currentText().lower()
        if model_name == "realcugan":
            self._update_cugan_panel_options()
        elif model_name == "realesr":
            self.upscaler_noise_level_combo.setEnabled(False)
            self.upscaler_noise_level_combo.setToolTip("Noise level is not supported by ESRGAN models.")
            if hasattr(self, 'upscaler_noise_level_label'):
                self.upscaler_noise_level_label.setEnabled(False)
                self.upscaler_noise_level_label.setStyleSheet("color: #777777;")
            
            # Adjust scale factors for x4plus models (4x only)
            model_mapping = self.style_combo.property("modelMapping") if hasattr(self, 'style_combo') else None
            if model_mapping:
                actual_model = model_mapping.get(style_name, "")
                if "x4plus" in actual_model:
                    self.upscaler_factor_combo.blockSignals(True)
                    self.upscaler_factor_combo.clear()
                    self.upscaler_factor_combo.addItems(["4x"])
                    self.upscaler_factor_combo.blockSignals(False)
                else:
                    current_factor = self.upscaler_factor_combo.currentText()
                    self.upscaler_factor_combo.blockSignals(True)
                    self.upscaler_factor_combo.clear()
                    self.upscaler_factor_combo.addItems(["2x", "3x", "4x"])
                    idx = self.upscaler_factor_combo.findText(current_factor)
                    if idx >= 0:
                        self.upscaler_factor_combo.setCurrentIndex(idx)
                    self.upscaler_factor_combo.blockSignals(False)
        elif model_name == "waifu2x":
            self.upscaler_noise_level_combo.setEnabled(True)
            self.upscaler_noise_level_combo.setToolTip("")
            if hasattr(self, 'upscaler_noise_level_label'):
                self.upscaler_noise_level_label.setEnabled(True)
                self.upscaler_noise_level_label.setStyleSheet("")
            
            # Handle Upconv constraint for 1x scaling
            model_mapping = self.style_combo.property("modelMapping") if hasattr(self, 'style_combo') else None
            if model_mapping:
                actual_model = model_mapping.get(style_name, "")
                is_upconv = "upconv" in actual_model
                if is_upconv:
                    current_factor = self.upscaler_factor_combo.currentText()
                    self.upscaler_factor_combo.blockSignals(True)
                    self.upscaler_factor_combo.clear()
                    self.upscaler_factor_combo.addItems(["2x", "4x"])
                    idx = self.upscaler_factor_combo.findText(current_factor)
                    if idx >= 0:
                        self.upscaler_factor_combo.setCurrentIndex(idx)
                    else:
                        self.upscaler_factor_combo.setCurrentIndex(0)
                    self.upscaler_factor_combo.blockSignals(False)
                else:
                    current_factor = self.upscaler_factor_combo.currentText()
                    self.upscaler_factor_combo.blockSignals(True)
                    self.upscaler_factor_combo.clear()
                    self.upscaler_factor_combo.addItems(["1x", "2x", "4x"])
                    idx = self.upscaler_factor_combo.findText(current_factor)
                    if idx >= 0:
                        self.upscaler_factor_combo.setCurrentIndex(idx)
                    self.upscaler_factor_combo.blockSignals(False)

    def on_scale_changed(self, scale_text):
        if not hasattr(self, 'upscaler_model_combo'): return
        model_name = self.upscaler_model_combo.currentText().lower()
        if model_name == "waifu2x":
            if scale_text == "1x" and hasattr(self, 'style_combo'):
                # 1x scale only supports CUnet model
                idx = self.style_combo.findText("CUnet (Best Quality)")
                if idx >= 0 and self.style_combo.currentIndex() != idx:
                    self.style_combo.setCurrentIndex(idx)
        if model_name == "realcugan":
            self._update_cugan_panel_options()

    def _update_cugan_panel_options(self):
        style_name = self.style_combo.currentText()
        is_se = "SE" in style_name
        is_pro = "Pro" in style_name
        is_nose = "Nose" in style_name
        
        current_scale = self.upscaler_factor_combo.currentText()
        current_noise = self.upscaler_noise_level_combo.currentText()
        
        # Valid scales
        if is_nose:
            valid_scales = ["2x"]
        else:
            valid_scales = ["2x", "3x", "4x"]
            
        self.upscaler_factor_combo.blockSignals(True)
        self.upscaler_factor_combo.clear()
        self.upscaler_factor_combo.addItems(valid_scales)
        if current_scale in valid_scales:
            self.upscaler_factor_combo.setCurrentText(current_scale)
        self.upscaler_factor_combo.blockSignals(False)
        current_scale = self.upscaler_factor_combo.currentText()
        
        # Valid noise levels
        if is_nose:
            valid_noise = ["0 (Low)"]
        elif is_pro:
            valid_noise = ["-1 (None)", "0 (Low)", "3 (High)"]
        elif is_se:
            if current_scale == "2x":
                valid_noise = ["-1 (None)", "0 (Low)", "1 (Light)", "2 (Medium)", "3 (High)"]
            else:
                valid_noise = ["-1 (None)", "0 (Low)", "3 (High)"]
        else:
            valid_noise = ["-1 (None)", "0 (Low)", "1 (Light)", "2 (Medium)", "3 (High)"]
            
        self.upscaler_noise_level_combo.blockSignals(True)
        self.upscaler_noise_level_combo.clear()
        self.upscaler_noise_level_combo.addItems(valid_noise)
        if current_noise in valid_noise:
            self.upscaler_noise_level_combo.setCurrentText(current_noise)
        elif current_noise == "1 (Light)" and "0 (Low)" in valid_noise:
            self.upscaler_noise_level_combo.setCurrentText("0 (Low)")
        elif current_noise == "2 (Medium)" and "3 (High)" in valid_noise:
            self.upscaler_noise_level_combo.setCurrentText("3 (High)")
        elif current_noise not in valid_noise and valid_noise:
            self.upscaler_noise_level_combo.setCurrentText(valid_noise[0])
        self.upscaler_noise_level_combo.blockSignals(False)
        
        has_noise_options = len(valid_noise) > 1
        self.upscaler_noise_level_combo.setEnabled(has_noise_options)
        if hasattr(self, 'upscaler_noise_level_label'):
            self.upscaler_noise_level_label.setEnabled(has_noise_options)
            self.upscaler_noise_level_label.setStyleSheet("" if has_noise_options else "color: #777777;")
        self.upscaler_noise_level_combo.setToolTip("" if has_noise_options else "Noise level is fixed for this model.")

    def natural_sort_key(self, s):
        """Natural sort key function for sorting filenames with numbers correctly"""
        import re
        return [int(text) if text.isdigit() else text.lower() 
                for text in re.split('([0-9]+)', os.path.basename(s))]

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
        selected_files = self.upscaler_fm.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to upscale.")
            return
        
        if not self.upscaler_fm.output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select an output directory.")
            return
        
        # Check if this is a repeated upscaling to the same output folder
        should_continue = True
        if hasattr(self, 'last_upscaler_output_dir') and self.last_upscaler_output_dir == self.upscaler_fm.output_dir:
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
                self.upscaler_fm.set_output_dir()
                # Check if user actually selected a new folder
                if self.upscaler_fm.output_dir != self.last_upscaler_output_dir:
                    should_continue = True
                else:
                    should_continue = False
        
        # Log the start of upscaling
        self.log(f"Starting upscaling of {len(selected_files)} files with {self.upscaler_factor_combo.currentText()} factor", "INFO")

        # Store current output dir for future reference
        self.last_upscaler_output_dir = self.upscaler_fm.output_dir
        
        # If user chose not to continue, exit the method
        if not should_continue:
            return

        # Get upscaling options
        upscale_factor = self.upscaler_factor_combo.currentText()
        model = self.upscaler_model_combo.currentText()

        # For waifu2x, realcugan, and esrgan, get the actual model value from the display name
        style_model = "models-cunet"  # Default model
        if model.lower() in ["waifu2x", "realcugan", "realesr"]:
            display_name = self.style_combo.currentText()
            model_mapping = self.style_combo.property("modelMapping")
            if model_mapping:
                style_model = model_mapping.get(display_name, list(model_mapping.values())[0])
        
        # Get noise level if waifu2x or realcugan is selected
        noise_level = 1  # Default to medium noise reduction
        if model.lower() in ["waifu2x", "realcugan", "realesr"] and hasattr(self, 'upscaler_noise_level_combo'):
            # For realcugan pro/nose models, noise level is not supported - skip reading it
            if model.lower() == "realcugan" and not self.upscaler_noise_level_combo.isEnabled():
                noise_level = -1  # Default to no noise reduction for unsupported models
            else:
                noise_level_text = self.upscaler_noise_level_combo.currentText().split()[0]
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
            self.upscaler_fm.output_dir,
            upscale_factor=upscale_factor,
            model=model,
            keep_format=keep_format,
            output_format=output_format if output_format else "PNG",
            noise_level=noise_level,
            style_model=style_model
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
        
        self.upscaler_progress_dialog = ProcessingProgressDialog(self, title="Upscaling Images", label="Upscaling Files...", cancel_callback=self.stop_upscaling)
        
        # Update button text
        self.upscale_btn.setText("Upscaling...")
        self.upscale_btn.setEnabled(False)
        
        # Start thread and show dialog
        self.upscaler_thread.start()
        self.upscaler_progress_dialog.exec()

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
        core_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
        realesrgan_path = os.path.join(core_dir, "esr", "realesrgan-ncnn-vulkan.exe")
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
        
        # Force enable overrides Vulkan check
        force_enabled = hasattr(self, 'force_upscale_check') and self.force_upscale_check.isChecked()
        
        if self.vulkan_support or force_enabled:
            self.upscale_check.setEnabled(True)
            self.upscale_check.setStyleSheet("font-size: 13px; color: #ffffff;")
        else:
            # Disable upscaling if Vulkan is not supported
            self.upscale_check.setEnabled(False)
            self.upscale_check.setChecked(False)
            self.upscale_check.setStyleSheet("font-size: 13px; color: #888888;")
            self.upscale_check.setToolTip("AI Upscaling requires Vulkan support")
            
        # Update file checkboxes based on new format
        if hasattr(self, 'converter_fm') and hasattr(self.converter_fm, 'file_checkboxes'):
            current_output_format = format_text.lower()
            
            for checkbox in self.converter_fm.file_checkboxes:
                try:
                    file_ext = os.path.splitext(checkbox.file_path)[1].lower()[1:]
                    
                    # Disable checkbox if file format matches output format
                    if file_ext == current_output_format:
                        checkbox.setChecked(False)
                        checkbox.setEnabled(False)
                        checkbox.setStyleSheet(f"QCheckBox::indicator {{ background-color: #555555; }}")
                    else:
                        checkbox.setEnabled(True)
                        checkbox.setStyleSheet("")
                        # If "Select All" is checked, check this box too
                        if hasattr(self.converter_fm, 'select_all_checkbox') and self.converter_fm.select_all_checkbox.isChecked():
                            checkbox.setChecked(True)
                except RuntimeError:
                    pass
            
            self.converter_fm.update_file_type_checkbox_state()
            self.converter_fm.update_button_callback()

    def select_output_dir(self):
        dir_dialog = QFileDialog()
        dir_dialog.setFileMode(QFileDialog.FileMode.Directory)
        dir_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if dir_dialog.exec():
            self.output_dir = dir_dialog.selectedFiles()[0]
            self.output_dir_label.setText(f"📁 {self.output_dir}")
            self.output_dir_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
            self.update_convert_button_state()

    def start_conversion(self):
        if not self.converter_fm.files or not self.converter_fm.output_dir:
            return
        
        # Get only selected files before starting conversion
        files_to_convert = self.converter_fm.get_selected_files()
        if not files_to_convert:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to convert.")
            return
        
        # Check if this is a repeated conversion to the same output folder
        should_continue = True
        if hasattr(self, 'last_output_dir') and self.last_output_dir == self.converter_fm.output_dir:
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
                self.converter_fm.set_output_dir()
                # Check if user actually selected a new folder
                if self.converter_fm.output_dir != self.last_output_dir:
                    should_continue = True
                else:
                    should_continue = False
        
        self.log("Starting conversion process", "INFO")

        # Store current output dir for future reference
        self.last_output_dir = self.converter_fm.output_dir
        
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
            
        # Determine if we should force GPU via upscale_check (if applicable)
        force_enabled = hasattr(self, 'force_upscale_check') and self.force_upscale_check.isChecked()
        upscale_settings = getattr(self, 'converter_upscale_settings', {})
        
        # Create and configure the converter thread
        self.thread = ConverterThread(
            files_to_convert,
            self.converter_fm.output_dir,
            self.format_combo.currentText().lower(),
            current_settings,
            self.upscale_check.isChecked(),
            upscale_settings=upscale_settings
        )
        
        # Connect signals
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.completion_signal.connect(self.conversion_complete)
        self.thread.error_signal.connect(self.handle_error)
        
        # Show progress dialog
        self.progress_dialog = ProcessingProgressDialog(self, title="Converting Images", label="Converting Files...", cancel_callback=self.stop_conversion)
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
            icon_path = get_icon_path("icon.ico")
            if os.path.exists(icon_path):
                dialog.setWindowIcon(QIcon(icon_path))
            
            # Create a worker thread to gather system info
            class SystemInfoWorker(QThread):
                finished_signal = pyqtSignal(dict)
                log_signal = pyqtSignal(str, str)
                
                
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
                                self.log_signal.emit(f"DXDIAG method failed: {str(e)}", "WARNING")
                            
                            # Method 2: Fallback to WMI
                            if not info['gpu_names']:
                                try:
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
                                except Exception as e:
                                    self.log_signal.emit(f"WMIC method failed: {str(e)}", "WARNING")
                            
                            # Method 3: PowerShell fallback
                            if not info['gpu_names']:
                                try:
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
                                except Exception as e:
                                    self.log_signal.emit(f"PowerShell method failed: {str(e)}", "WARNING")
                            
                            # If no GPUs were found, add "Unknown"
                            if not info['gpu_names']:
                                info['gpu_names'].append("Unknown")
                            
                            import shutil
                            
                            # Check for Vulkan support
                            info['vulkan_support'] = shutil.which('vulkaninfo') is not None or shutil.which('vulkaninfo.exe') is not None
                            
                            if not info['vulkan_support']:
                                info['vulkan_support'] = shutil.which('vulkan-1.dll') is not None
                            
                            if not info['vulkan_support']:
                                system32_path = os.path.join(os.environ['SystemRoot'], 'System32')
                                info['vulkan_support'] = os.path.exists(os.path.join(system32_path, 'vulkan-1.dll'))
                                
                        except Exception as e:
                            self.log_signal.emit(f"GPU detection error: {str(e)}", "WARNING")
                        
                        self.finished_signal.emit(info)
                    except Exception as e:
                        self.log_signal.emit(f"Worker thread error: {str(e)}", "ERROR")
                        self.finished_signal.emit({})
            
            # Create and start the worker thread
            self.worker = SystemInfoWorker()
            self.worker.log_signal.connect(self.log)
            
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
        icon_path = get_icon_path("icon.ico")
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
        </ul>
        <h3 style="font-size: 18px; margin-top: 15px;">Step 4: AI Upscaling (Optional)</h3>
        <p style="font-size: 14px; margin: 5px 0 10px 10px;">• Enable AI Upscaling by clicking the gear icon to enhance image quality and resolution<br>• Select an upscale factor from the dropdown (1x, 2x, 4x for Waifu2x, and 2x, 3x, 4x for others)<br>• We feature <b>Waifu2x</b>, <b>RealCUGAN</b>, and <b>RealESRGAN</b> models for different art styles.<br>• <b>GPU STRICT MODE:</b> For maximum stability, all AI processing runs strictly on your dedicated GPU (Vulkan). CPU fallback is intentionally disabled.<br>• Upscaling will increase processing time and output file size</p>
        
        <p style="color: #FF9E9E; font-size: 14px; margin: 5px 0 10px 10px;"><span style="font-size: 18px;">⚠️</span> <b>Warning:</b> AI Upscaling requires a dedicated Vulkan-compatible GPU (e.g. NVIDIA, AMD). Using unsupported hardware will result in failed conversions.</p>
        
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

    def start_denoising(self):
        """Start the denoising process"""
        # Get selected files
        selected_files = self.denoiser_fm.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to denoise.")
            return
        
        if not self.denoiser_fm.output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select an output directory.")
            return
        
        # Check if this is a repeated denoising to the same output folder
        should_continue = True
        if hasattr(self, 'last_denoiser_output_dir') and self.last_denoiser_output_dir == self.denoiser_fm.output_dir:
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
                self.denoiser_fm.set_output_dir() 
                # Check if user actually selected a new folder
                if self.denoiser_fm.output_dir != self.last_denoiser_output_dir:
                    should_continue = True
                else:
                    should_continue = False
        
        # Log the start of denoising
        self.log(f"Starting denoising of {len(selected_files)} files with strength {self.noise_level_combo.currentText()}", "INFO")

        # Store current output dir for future reference
        self.last_denoiser_output_dir = self.denoiser_fm.output_dir
        
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
            self.denoiser_fm.output_dir,
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
        self.denoiser_progress_dialog = ProcessingProgressDialog(self, title="Denoising Images", label="Denoising Files...", cancel_callback=self.stop_denoising)
        
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

