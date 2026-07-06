import os
import time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from src.constants import COLORS, APP_VERSION, GITHUB_RELEASES_URL
from src.ui.styles import STYLES
from src.utils.helpers import natural_sort_key, get_file_icon, format_size, get_icon_path

class FileListManager:
    """Unified file list, checkbox, and drag-drop management for Converter / Upscaler / Denoiser.

    Each tab creates its own FileListManager instance with its supported format list.
    The manager owns all file list state and provides UI factory methods.
    """

    def __init__(self, parent, supported_formats, update_button_callback, file_attr_prefix=""):
        """
        Args:
            parent: The ImageConverter QWidget.
            supported_formats: List of uppercase format strings e.g. ["PNG", "JPEG", ...].
            update_button_callback: Callable to update the tab's main action button state.
            file_attr_prefix: Prefix for attribute names to avoid collisions (e.g. "upscaler_", "denoiser_").
        """
        self.parent = parent
        self.supported_formats = supported_formats
        self.update_button_callback = update_button_callback
        self.prefix = file_attr_prefix

        # State
        self.files = []
        self.file_checkboxes = []
        self.output_dir = ""
        self.selected_folder = None

        # UI widgets (set during create_right_panel / create_action_buttons)
        self.file_container = None
        self.scroll_area = None
        self.output_dir_label = None
        self.select_all_checkbox = None
        self.file_count_label = None

    # ─── File Operations ────────────────────────────────────────────────

    def add_files(self):
        """Open a file dialog to add files."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(f"Supported Files (*.{' *.'.join(f.lower() for f in self.supported_formats)})")
        if file_dialog.exec():
            new_files = file_dialog.selectedFiles()
            skipped = self._add_new_files(new_files)
            self.files.sort(key=natural_sort_key)
            if not self.selected_folder and self.files:
                self.selected_folder = os.path.dirname(self.files[0])
            if skipped:
                self.parent.show_duplicate_warning(skipped)
            self.refresh_file_list()
            self.update_button_callback()

    def add_folder(self):
        """Open a folder dialog to add all supported files in a folder."""
        folder = QFileDialog.getExistingDirectory(self.parent, "Select Folder Containing Images")
        if folder:
            supported_extensions = tuple(f'.{ext.lower()}' for ext in self.supported_formats)
            new_files = []
            for root, _, filenames in os.walk(folder):
                for f in filenames:
                    if f.lower().endswith(supported_extensions):
                        new_files.append(os.path.join(root, f))
            skipped = self._add_new_files(new_files)
            self.files.sort(key=natural_sort_key)
            if not self.selected_folder and self.files:
                self.selected_folder = folder
            if skipped:
                self.parent.show_duplicate_warning(skipped)
            self.refresh_file_list()
            self.update_button_callback()

    def clear_files(self):
        """Clear all files from the list."""
        self.files.clear()
        self.file_checkboxes.clear()
        self.selected_folder = None
        self.refresh_file_list()
        self.update_button_callback()

    def get_selected_files(self):
        """Return list of file paths that are currently checked."""
        selected = []
        for cb in self.file_checkboxes:
            try:
                if cb.isChecked() and cb.isEnabled():
                    selected.append(cb.file_path)
            except RuntimeError:
                continue
        return selected

    def set_output_dir(self):
        """Open a folder dialog to set the output directory."""
        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.FileMode.Directory)
        folder_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if folder_dialog.exec():
            self.output_dir = folder_dialog.selectedFiles()[0]
            if self.output_dir_label:
                self.output_dir_label.setText(f"📁 {self.output_dir}")
                self.output_dir_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
            self.update_button_callback()

    # ─── Internal helpers ───────────────────────────────────────────────

    def _add_new_files(self, new_paths):
        """Add new paths avoiding duplicates. Returns list of skipped paths."""
        existing = set(self.files)
        existing_pairs = set()
        for fp in self.files:
            name, ext = os.path.splitext(os.path.basename(fp))
            existing_pairs.add((name.lower(), ext.lower()))
        skipped = []
        for fp in new_paths:
            if fp not in existing:
                name, ext = os.path.splitext(os.path.basename(fp))
                key = (name.lower(), ext.lower())
                if key in existing_pairs:
                    skipped.append(fp)
                else:
                    self.files.append(fp)
                    existing_pairs.add(key)
        return skipped

    def process_dropped_folder(self, folder_path):
        """Extract all supported files from a dropped folder."""
        supported_extensions = tuple(f'.{ext.lower()}' for ext in self.supported_formats)
        for root, _, filenames in os.walk(folder_path):
            for f in filenames:
                if f.lower().endswith(supported_extensions):
                    self.files.append(os.path.join(root, f))
        if not self.selected_folder:
            self.selected_folder = folder_path

    def process_dropped_folder_keep_existing(self, folder_path, existing_files):
        """Extract supported files from a dropped folder, skipping existing ones."""
        supported_extensions = tuple(f'.{ext.lower()}' for ext in self.supported_formats)
        for root, _, filenames in os.walk(folder_path):
            for f in filenames:
                if f.lower().endswith(supported_extensions):
                    file_path = os.path.join(root, f)
                    if file_path not in existing_files:
                        self.files.append(file_path)
        if not self.selected_folder:
            self.selected_folder = folder_path

    # ─── Checkbox Logic ─────────────────────────────────────────────────

    def toggle_select_all(self, state):
        """Toggle all file checkboxes."""
        for cb in list(self.file_checkboxes):
            try:
                if cb.isEnabled():
                    cb.setChecked(state == Qt.CheckState.Checked.value)
            except RuntimeError:
                if cb in self.file_checkboxes:
                    self.file_checkboxes.remove(cb)
        self.update_file_type_checkbox_state()

    def toggle_file_type(self, state, file_ext):
        """Toggle all checkboxes for a specific file type."""
        for cb in list(self.file_checkboxes):
            try:
                if hasattr(cb, 'file_ext') and cb.file_ext == file_ext and cb.isEnabled():
                    cb.setChecked(state == Qt.CheckState.Checked.value)
            except RuntimeError:
                if cb in self.file_checkboxes:
                    self.file_checkboxes.remove(cb)

    def update_select_all_checkbox_state(self):
        """Update 'Select All' checkbox to reflect current selection state."""
        if not self.select_all_checkbox:
            return
        checked = 0
        enabled = 0
        for cb in self.file_checkboxes:
            try:
                if cb.isEnabled():
                    enabled += 1
                    if cb.isChecked():
                        checked += 1
            except RuntimeError:
                continue
        if enabled > 0:
            self.select_all_checkbox.blockSignals(True)
            self.select_all_checkbox.setChecked(checked == enabled)
            self.select_all_checkbox.setText(f"Select All ({checked}/{enabled} selected)")
            self.select_all_checkbox.blockSignals(False)
            if self.file_count_label:
                self.file_count_label.setText(f"Total: {len(self.files)} files, {checked} selected")

    def update_file_type_checkbox_state(self, _state=None):
        """Update per-type checkboxes and Select All based on individual checkbox states."""
        # Group checkboxes by extension
        groups = {}
        for cb in self.file_checkboxes:
            try:
                if hasattr(cb, 'file_ext') and cb.isEnabled():
                    groups.setdefault(cb.file_ext, []).append(cb)
            except RuntimeError:
                continue

        # Find file-type header checkboxes in the UI
        if self.file_container and self.file_container.layout():
            for i in range(self.file_container.layout().count()):
                widget = self.file_container.layout().itemAt(i).widget()
                if isinstance(widget, QScrollArea):
                    scroll_widget = widget.widget()
                    if scroll_widget:
                        for j in range(scroll_widget.layout().count()):
                            item = scroll_widget.layout().itemAt(j)
                            if item.widget() and isinstance(item.widget(), QFrame):
                                frame = item.widget()
                                if frame.layout() is not None:
                                    for k in range(frame.layout().count()):
                                        item2 = frame.layout().itemAt(k)
                                        if item2 and item2.layout():
                                            for l_idx in range(item2.layout().count()):
                                                w = item2.layout().itemAt(l_idx).widget()
                                                if isinstance(w, QCheckBox) and hasattr(w, 'file_ext'):
                                                    ext = w.file_ext
                                                    if ext in groups:
                                                        checked_ct = sum(1 for c in groups[ext] if c.isChecked())
                                                        total_ct = len(groups[ext])
                                                        w.blockSignals(True)
                                                        w.setChecked(checked_ct == total_ct)
                                                        if hasattr(w, 'original_text'):
                                                            w.setText(f"{w.original_text} ({checked_ct}/{total_ct} selected)")
                                                        w.blockSignals(False)
        self.update_select_all_checkbox_state()

    def add_files(self):
        """Open file dialog to add files."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        format_filter = " ".join(f"*.{fmt.lower()}" for fmt in self.supported_formats)
        file_dialog.setNameFilter(f"Supported Files ({format_filter})")
        
        if file_dialog.exec():
            new_paths = file_dialog.selectedFiles()
            skipped = self._add_new_files(new_paths)
            self.files.sort(key=self.parent.natural_sort_key)
            if not self.selected_folder and self.files:
                self.selected_folder = os.path.dirname(self.files[0])
            self.refresh_file_list()
            if skipped:
                self.parent.show_duplicate_warning(skipped)

    def add_folder(self):
        """Open dialog to add a folder of files."""
        folder = QFileDialog.getExistingDirectory(self.parent, "Select Folder Containing Images")
        if folder:
            existing = set(self.files)
            self.process_dropped_folder_keep_existing(folder, existing)
            self.files.sort(key=self.parent.natural_sort_key)
            self.refresh_file_list()

    def clear_files(self):
        """Clear the file list."""
        self.files = []
        self.selected_folder = None
        self.refresh_file_list()

    # ─── UI Construction ────────────────────────────────────────────────

    def create_action_buttons(self, layout):
        """Create Add Files / Add Folder / Clear Files / Set Output buttons."""
        btn_layout = QGridLayout()
        btn_layout.setSpacing(10)

        add_files_btn = QPushButton("📁 Add Files")
        add_files_btn.setFont(QFont("Segoe UI", 10))
        add_files_btn.setFixedHeight(40)
        add_files_btn.clicked.connect(self.add_files)
        add_files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_files_btn.setStyleSheet(STYLES['action_button'])
        btn_layout.addWidget(add_files_btn, 0, 0)

        add_folder_btn = QPushButton("📂 Add Folder")
        add_folder_btn.setFont(QFont("Segoe UI", 10))
        add_folder_btn.setFixedHeight(40)
        add_folder_btn.clicked.connect(self.add_folder)
        add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder_btn.setStyleSheet(STYLES['action_button'])
        btn_layout.addWidget(add_folder_btn, 0, 1)

        clear_btn = QPushButton("🚫 Clear Files")
        clear_btn.setFont(QFont("Segoe UI", 10))
        clear_btn.setFixedHeight(40)
        clear_btn.clicked.connect(self.clear_files)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(STYLES['action_button_red'])
        btn_layout.addWidget(clear_btn, 1, 0)

        output_btn = QPushButton("📂 Set Output")
        output_btn.setFont(QFont("Segoe UI", 10))
        output_btn.setFixedHeight(40)
        output_btn.clicked.connect(self.set_output_dir)
        output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        output_btn.setStyleSheet(STYLES['action_button_yellow'])
        btn_layout.addWidget(output_btn, 1, 1)

        layout.addLayout(btn_layout)

    def create_right_panel(self):
        """Create the right panel with file list and output directory display."""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 0px; border-top-right-radius: 10px; border-bottom-right-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        file_header = QLabel("Selected Files:")
        file_header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 5px;")
        layout.addWidget(file_header)

        scroll_container = QFrame()
        scroll_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 10px;")
        sc_layout = QVBoxLayout(scroll_container)
        sc_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(200)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(STYLES['scroll_area_hv'])

        self.file_container = QWidget()
        self.file_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 8px;")
        fc_layout = QVBoxLayout(self.file_container)
        fc_layout.setContentsMargins(10, 10, 10, 10)
        fc_layout.setSpacing(8)

        # Enable drag and drop
        self.file_container.setAcceptDrops(True)
        self._original_container_style = self.file_container.styleSheet()

        # Placeholder
        placeholder = QLabel("No files selected")
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("color: #888888; padding: 10px;")
        fc_layout.addWidget(placeholder)

        self.scroll_area.setWidget(self.file_container)
        sc_layout.addWidget(self.scroll_area)
        layout.addWidget(scroll_container)

        # Output directory
        output_header = QLabel("Output Directory:")
        output_header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 5px;")
        layout.addWidget(output_header)

        output_container = QWidget()
        output_container.setMinimumHeight(40)
        output_container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 8px;")
        out_layout = QVBoxLayout(output_container)

        self.output_dir_label = QLabel("No output directory selected")
        self.output_dir_label.setWordWrap(True)
        self.output_dir_label.setStyleSheet("color: #888888; padding: 10px;")
        out_layout.addWidget(self.output_dir_label)
        output_container.setLayout(out_layout)
        layout.addWidget(output_container)

        return panel

    def refresh_file_list(self):
        """Rebuild the file list UI from current self.files."""
        # Save existing checkbox states
        checkbox_states = {}
        for cb in self.file_checkboxes:
            try:
                if hasattr(cb, 'file_path'):
                    checkbox_states[cb.file_path] = cb.isChecked()
            except RuntimeError:
                pass

        # Clear file container
        for i in reversed(range(self.file_container.layout().count())):
            w = self.file_container.layout().itemAt(i).widget()
            if w:
                w.deleteLater()
        self.file_checkboxes = []

        if not self.files:
            lbl = QLabel("No files selected")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #888888; padding: 10px;")
            self.file_container.layout().addWidget(lbl)
        else:
            file_scroll = QScrollArea()
            file_scroll.setWidgetResizable(True)
            file_scroll.setFrameShape(QFrame.Shape.NoFrame)
            file_scroll.setStyleSheet(STYLES['scroll_area'])

            list_widget = QWidget()
            list_layout = QVBoxLayout(list_widget)
            list_layout.setContentsMargins(5, 5, 5, 5)
            list_layout.setSpacing(10)

            # Folder label
            if self.selected_folder:
                folder_lbl = QLabel(f"📁 Selected Folder: {self.selected_folder}")
                folder_lbl.setStyleSheet(f"color: {COLORS['text']}; padding: 5px; font-weight: bold;")
                list_layout.addWidget(folder_lbl)
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
                list_layout.addWidget(sep)

            # Select All
            sa_layout = QHBoxLayout()
            self.select_all_checkbox = QCheckBox("Select All")
            self.select_all_checkbox.setChecked(True)
            self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
            sa_layout.addWidget(self.select_all_checkbox)

            self.file_count_label = QLabel(f"Total: {len(self.files)} files")
            self.file_count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9pt;")
            sa_layout.addWidget(self.file_count_label, alignment=Qt.AlignmentFlag.AlignRight)
            list_layout.addLayout(sa_layout)

            sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
            sep2.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
            list_layout.addWidget(sep2)

            # Group by extension
            file_groups = {}
            for fp in self.files:
                ext = os.path.splitext(fp)[1].lower()[1:]
                file_groups.setdefault(ext, []).append(fp)

            for ext, ext_files in file_groups.items():
                group_frame = QFrame()
                group_frame.setStyleSheet(f"background-color: {COLORS['panel']}; border-radius: 8px;")
                group_layout = QVBoxLayout(group_frame)
                group_layout.setContentsMargins(10, 10, 10, 10)
                group_layout.setSpacing(5)

                # Type header
                header_layout = QHBoxLayout()
                original_text = f"{ext.upper()} Files ({len(ext_files)})"
                type_cb = QCheckBox(original_text)
                type_cb.setStyleSheet("font-weight: bold; font-size: 11pt;")
                type_cb.file_ext = ext
                type_cb.original_text = original_text
                all_checked = all(checkbox_states.get(fp, True) for fp in ext_files)
                type_cb.setChecked(all_checked)
                type_cb.stateChanged.connect(lambda state, e=ext: self.toggle_file_type(state, e))
                header_layout.addWidget(type_cb)
                header_layout.addStretch()
                group_layout.addLayout(header_layout)

                type_sep = QFrame(); type_sep.setFrameShape(QFrame.Shape.HLine)
                type_sep.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 0px;")
                group_layout.addWidget(type_sep)

                grid = QGridLayout()
                grid.setSpacing(5)
                num_columns = 4

                for i, fp in enumerate(ext_files):
                    fname = os.path.basename(fp)
                    item = QWidget()
                    item_layout = QHBoxLayout(item)
                    item_layout.setContentsMargins(2, 2, 2, 2)
                    item_layout.setSpacing(5)

                    cb = QCheckBox()
                    initial = checkbox_states.get(fp, True)
                    cb.file_path = fp
                    cb.file_ext = ext
                    cb.setChecked(initial)
                    cb.stateChanged.connect(self.update_file_type_checkbox_state)
                    cb.stateChanged.connect(lambda _: self.update_button_callback())
                    self.file_checkboxes.append(cb)
                    item_layout.addWidget(cb)

                    icon_lbl = QLabel(get_file_icon(ext))
                    item_layout.addWidget(icon_lbl)

                    max_len = 15
                    display_name = fname if len(fname) <= max_len else fname[:max_len-3] + "..."
                    name_lbl = QLabel(display_name)
                    name_lbl.setToolTip(fname)
                    name_lbl.setStyleSheet(f"color: {COLORS['text']};")
                    item_layout.addWidget(name_lbl, 1)

                    grid.addWidget(item, i // num_columns, i % num_columns)

                group_layout.addLayout(grid)
                list_layout.addWidget(group_frame)

            file_scroll.setWidget(list_widget)
            self.file_container.layout().addWidget(file_scroll)
            self.update_select_all_checkbox_state()

        self.update_button_callback()

    # ─── Drag and Drop Handlers ─────────────────────────────────────────

    def handle_drag_enter(self, event):
        """Handle drag enter on the file container."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            supported_extensions = tuple(f'.{ext.lower()}' for ext in self.supported_formats)
            has_valid = any(
                url.toLocalFile().lower().endswith(supported_extensions) or os.path.isdir(url.toLocalFile())
                for url in urls
            )
            if has_valid:
                event.acceptProposedAction()
                if self.file_container:
                    self.file_container.setStyleSheet(
                        f"background-color: {COLORS['background']}; border-radius: 8px; border: 2px dashed {COLORS['primary']};"
                    )
                return
        event.ignore()

    def handle_drag_leave(self, event):
        """Handle drag leave on the file container."""
        if self.file_container:
            self.file_container.setStyleSheet(
                self._original_container_style if hasattr(self, '_original_container_style')
                else f"background-color: {COLORS['background']}; border-radius: 8px;"
            )

    def handle_drag_move(self, event):
        """Handle drag move on the file container."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def handle_drop(self, event):
        """Handle drop on the file container."""
        if self.file_container:
            self.file_container.setStyleSheet(
                self._original_container_style if hasattr(self, '_original_container_style')
                else f"background-color: {COLORS['background']}; border-radius: 8px;"
            )
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            existing_files = set(self.files)
            existing_pairs = set()
            for fp in self.files:
                name, ext = os.path.splitext(os.path.basename(fp))
                existing_pairs.add((name.lower(), ext.lower()))

            new_files_added = []
            skipped_files = []
            supported_extensions = tuple(f'.{ext.lower()}' for ext in self.supported_formats)

            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):
                    for root, _, filenames in os.walk(path):
                        for f in filenames:
                            if f.lower().endswith(supported_extensions):
                                fp = os.path.join(root, f)
                                if fp not in existing_files:
                                    name, ext = os.path.splitext(os.path.basename(fp))
                                    key = (name.lower(), ext.lower())
                                    if key in existing_pairs:
                                        skipped_files.append(fp)
                                    else:
                                        self.files.append(fp)
                                        new_files_added.append(fp)
                                        existing_files.add(fp)
                                        existing_pairs.add(key)
                    if not self.selected_folder:
                        self.selected_folder = path
                elif path.lower().endswith(supported_extensions):
                    if path not in existing_files:
                        name, ext = os.path.splitext(os.path.basename(path))
                        key = (name.lower(), ext.lower())
                        if key in existing_pairs:
                            skipped_files.append(path)
                        else:
                            self.files.append(path)
                            new_files_added.append(path)
                            existing_files.add(path)
                            existing_pairs.add(key)

            self.files.sort(key=natural_sort_key)

            if new_files_added and not self.selected_folder:
                self.selected_folder = os.path.dirname(new_files_added[0])

            self.refresh_file_list()

            if new_files_added and skipped_files:
                msg_box = QMessageBox(self.parent)
                msg_box.setWindowTitle("Files Added with Duplicates")
                msg_box.setText(f"Added {len(new_files_added)} new file(s).\n{len(skipped_files)} duplicate file(s) were skipped.")
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setStyleSheet(STYLES['message_box'])
                msg_box.exec()
            elif skipped_files:
                self.parent.show_duplicate_warning(skipped_files)

            self.update_button_callback()
            event.accept()
        else:
            event.ignore()


