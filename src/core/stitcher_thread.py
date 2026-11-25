import os
import re
import math
from pathlib import Path
from src.core.signals import WorkerThread, Signal
from PIL import Image, ImageOps

from src.utils.helpers import parse_color_spec


class StitcherThread(WorkerThread):
    """Thread for stitching images together in vertical, horizontal, or grid layouts with outer padding."""
    progress_signal = Signal(int, str)
    finished_signal = Signal(int, int, str)
    error_signal = Signal(str)

    def __init__(self, folders, output_dir, is_vertical, spacing, output_format, virtual_files=None,
                 alignment="Center", bg_color="Transparent", resize_option="Don't Resize", reverse_order=False,
                 layout_mode="Vertical", grid_columns=2, quality=95, outer_padding=0, sort_mode="natural"):
        super().__init__()
        self.folders = folders
        self.output_dir = output_dir
        self.is_vertical = is_vertical
        self.spacing = int(spacing or 0)
        self.outer_padding = max(0, int(outer_padding or 0))
        self.output_format = output_format.lower()
        self.virtual_files = virtual_files or {}
        self.alignment = alignment
        self.bg_color = bg_color
        self.resize_option = resize_option
        self.reverse_order = reverse_order
        self.layout_mode = layout_mode
        self.grid_columns = max(1, int(grid_columns or 2))
        self.quality = int(quality or 95)
        self.sort_mode = str(sort_mode or "natural").lower()
        self.running = True
        self.cancelled = False
        self.last_output_path = ""

    def stop(self):
        self.running = False
        self.cancelled = True

    def _sort_paths(self, paths):
        if "alpha" in self.sort_mode:
            return sorted(paths, key=lambda s: os.path.basename(s).lower())
        if "time" in self.sort_mode or "date" in self.sort_mode:
            return sorted(paths, key=lambda s: os.path.getmtime(s) if os.path.exists(s) else 0)
        return sorted(paths, key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', os.path.basename(s))])

    def run(self):
        success_count = 0
        error_count = 0
        os.makedirs(self.output_dir, exist_ok=True)

        for i, folder_path in enumerate(self.folders):
            if not self.running or self.cancelled:
                break

            try:
                folder_name = folder_path.split(":", 1)[1] if folder_path.startswith("virtual:") else os.path.basename(folder_path)
                self.progress_signal.emit(i, folder_name)

                files_to_stitch = []
                if folder_path.startswith("virtual:"):
                    files_to_stitch = list(self.virtual_files.get(folder_path, []))
                else:
                    for ext in ('*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.gif', '*.tiff', '*.tif'):
                        files_to_stitch.extend([str(f) for f in Path(folder_path).glob(ext)])

                files_to_stitch = self._sort_paths(files_to_stitch)
                if not files_to_stitch:
                    raise ValueError(f"No images found in {folder_name}")

                output_path = os.path.join(self.output_dir, f"{folder_name}_stitched.{self.output_format}")
                self._stitch_images(files_to_stitch, output_path)
                self.last_output_path = output_path
                success_count += 1

            except Exception as e:
                if not self.running or self.cancelled:
                    break
                error_count += 1
                self.error_signal.emit(f"Error stitching {folder_path}: {str(e)}")

        if self.running and not self.cancelled:
            self.finished_signal.emit(success_count, error_count, self.output_dir)

    def _paste_image(self, canvas, img, pos):
        if img.mode == 'RGBA':
            canvas.paste(img, pos, img.split()[3])
        else:
            canvas.paste(img, pos)

    def _stitch_images(self, image_paths, output_path):
        if not image_paths:
            raise ValueError("No images to stitch")

        Image.MAX_IMAGE_PIXELS = None
        images = []
        stitched = None

        try:
            for path in image_paths:
                try:
                    with Image.open(path) as raw:
                        raw_oriented = ImageOps.exif_transpose(raw)
                        if raw_oriented.mode in ('RGBA', 'LA') or (raw_oriented.mode == 'P' and 'transparency' in raw_oriented.info):
                            img = raw_oriented.convert('RGBA')
                        elif raw_oriented.mode != 'RGB':
                            img = raw_oriented.convert('RGB')
                        else:
                            img = raw_oriented.copy()
                        images.append(img)
                except Exception as e:
                    self.error_signal.emit(f"Error opening image {path}: {str(e)}")

            if not images:
                raise ValueError("No valid images to stitch")

            if self.reverse_order:
                images.reverse()

            is_grid = "grid" in self.layout_mode.lower()

            if self.resize_option != "Don't Resize":
                if is_grid:
                    if self.resize_option == "Match Smallest":
                        tw, th = min(im.width for im in images), min(im.height for im in images)
                    elif self.resize_option == "Match Largest":
                        tw, th = max(im.width for im in images), max(im.height for im in images)
                    else:
                        tw, th = images[0].width, images[0].height
                    for idx in range(len(images)):
                        resized = images[idx].resize((tw, th), Image.Resampling.LANCZOS)
                        images[idx].close()
                        images[idx] = resized
                elif self.is_vertical:
                    target_width = (
                        min(img.width for img in images) if self.resize_option == "Match Smallest" else
                        (max(img.width for img in images) if self.resize_option == "Match Largest" else images[0].width)
                    )
                    for i in range(len(images)):
                        if images[i].width != target_width:
                            ratio = target_width / images[i].width
                            new_height = max(1, int(images[i].height * ratio))
                            resample = Image.Resampling.LANCZOS if ratio < 1 else Image.Resampling.BICUBIC
                            resized = images[i].resize((target_width, new_height), resample)
                            images[i].close()
                            images[i] = resized
                else:
                    target_height = (
                        min(img.height for img in images) if self.resize_option == "Match Smallest" else
                        (max(img.height for img in images) if self.resize_option == "Match Largest" else images[0].height)
                    )
                    for i in range(len(images)):
                        if images[i].height != target_height:
                            ratio = target_height / images[i].height
                            new_width = max(1, int(images[i].width * ratio))
                            resample = Image.Resampling.LANCZOS if ratio < 1 else Image.Resampling.BICUBIC
                            resized = images[i].resize((new_width, target_height), resample)
                            images[i].close()
                            images[i] = resized

            if str(self.bg_color).lower() == "transparent":
                bg_color_rgba = (0, 0, 0, 0)
            else:
                rgb = parse_color_spec(self.bg_color, default_rgb=(255, 255, 255))
                bg_color_rgba = rgb + (255,)

            mode = 'RGB' if self.output_format in ['jpg', 'jpeg'] else 'RGBA'
            if mode == 'RGB' and bg_color_rgba[3] == 0:
                bg_color_rgba = (255, 255, 255, 255)

            pad = self.outer_padding
            alignment = self.alignment

            if is_grid:
                cols = self.grid_columns
                num_imgs = len(images)
                rows = math.ceil(num_imgs / cols)
                col_widths = [0] * cols
                row_heights = [0] * rows
                for idx, img in enumerate(images):
                    c, r = idx % cols, idx // cols
                    col_widths[c] = max(col_widths[c], img.width)
                    row_heights[r] = max(row_heights[r], img.height)

                inner_w = max(1, sum(col_widths) + self.spacing * max(0, cols - 1))
                inner_h = max(1, sum(row_heights) + self.spacing * max(0, rows - 1))
                width, height = inner_w + 2 * pad, inner_h + 2 * pad
                stitched = Image.new(mode, (width, height), bg_color_rgba)

                col_x_offsets = [pad] * cols
                for c in range(1, cols):
                    col_x_offsets[c] = max(pad, col_x_offsets[c - 1] + col_widths[c - 1] + self.spacing)

                row_y_offsets = [pad] * rows
                for r in range(1, rows):
                    row_y_offsets[r] = max(pad, row_y_offsets[r - 1] + row_heights[r - 1] + self.spacing)

                for idx, img in enumerate(images):
                    c, r = idx % cols, idx // cols
                    cell_w, cell_h = col_widths[c], row_heights[r]
                    if alignment == "Start (Left/Top)":
                        ox, oy = col_x_offsets[c], row_y_offsets[r]
                    elif alignment == "End (Right/Bottom)":
                        ox, oy = col_x_offsets[c] + (cell_w - img.width), row_y_offsets[r] + (cell_h - img.height)
                    else:
                        ox, oy = col_x_offsets[c] + (cell_w - img.width) // 2, row_y_offsets[r] + (cell_h - img.height) // 2
                    self._paste_image(stitched, img, (ox, oy))

            elif self.is_vertical:
                inner_w = max(1, max(img.width for img in images))
                inner_h = max(1, sum(img.height for img in images) + self.spacing * max(0, len(images) - 1))
                width, height = inner_w + 2 * pad, inner_h + 2 * pad
                stitched = Image.new(mode, (width, height), bg_color_rgba)
                y_offset = pad
                for img in images:
                    if alignment == "Start (Left/Top)":
                        x_offset = pad
                    elif alignment == "End (Right/Bottom)":
                        x_offset = pad + (inner_w - img.width)
                    else:
                        x_offset = pad + (inner_w - img.width) // 2
                    self._paste_image(stitched, img, (x_offset, max(pad, y_offset)))
                    y_offset += img.height + self.spacing
            else:
                inner_w = max(1, sum(img.width for img in images) + self.spacing * max(0, len(images) - 1))
                inner_h = max(1, max(img.height for img in images))
                width, height = inner_w + 2 * pad, inner_h + 2 * pad
                stitched = Image.new(mode, (width, height), bg_color_rgba)
                x_offset = pad
                for img in images:
                    if alignment == "Start (Left/Top)":
                        y_offset = pad
                    elif alignment == "End (Right/Bottom)":
                        y_offset = pad + (inner_h - img.height)
                    else:
                        y_offset = pad + (inner_h - img.height) // 2
                    self._paste_image(stitched, img, (max(pad, x_offset), y_offset))
                    x_offset += img.width + self.spacing

            max_dim = None
            if self.output_format == 'webp':
                max_dim = 16300
            elif self.output_format in ['jpg', 'jpeg']:
                max_dim = 65500

            def save_chunk(img_chunk, path):
                if self.output_format in ['jpg', 'jpeg']:
                    img_chunk.convert('RGB').save(path, format='JPEG', quality=self.quality, optimize=True)
                elif self.output_format == 'png':
                    img_chunk.save(path, format='PNG')
                elif self.output_format == 'webp':
                    img_chunk.save(path, format='WEBP', quality=self.quality, method=6)
                else:
                    img_chunk.save(path)

            if max_dim and ((is_grid or self.is_vertical) and height > max_dim):
                num_parts = math.ceil(height / max_dim)
                base, ext = os.path.splitext(output_path)
                for p in range(num_parts):
                    chunk = stitched.crop((0, p * max_dim, width, min((p + 1) * max_dim, height)))
                    save_chunk(chunk, f"{base}_part{p + 1}{ext}")
                    chunk.close()
            elif max_dim and (not self.is_vertical and not is_grid) and width > max_dim:
                num_parts = math.ceil(width / max_dim)
                base, ext = os.path.splitext(output_path)
                for p in range(num_parts):
                    chunk = stitched.crop((p * max_dim, 0, min((p + 1) * max_dim, width), height))
                    save_chunk(chunk, f"{base}_part{p + 1}{ext}")
                    chunk.close()
            else:
                save_chunk(stitched, output_path)
        finally:
            for img in images:
                try:
                    img.close()
                except Exception:
                    pass
            if stitched is not None:
                try:
                    stitched.close()
                except Exception:
                    pass
