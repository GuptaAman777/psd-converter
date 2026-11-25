import os
import time
import gc
from pathlib import Path
from src.core.signals import WorkerThread, Signal
from PIL import Image, ImageFile, ImageOps
from psd_tools import PSDImage

try:
    import pymupdf as fitz
    PDF_CONVERTER = "pymupdf"
except ImportError:
    try:
        import fitz
        PDF_CONVERTER = "pymupdf"
    except ImportError:
        PDF_CONVERTER = None
        fitz = None

from src.core.ncnn_runner import (
    build_esr_command, cleanup_stage_files, prepare_ncnn_stage,
    run_ncnn_process, sanitize_ncnn_gpu_args, save_high_quality_image
)
from src.utils.helpers import (
    calculate_progress_info, get_tool_info, normalize_ncnn_format,
    parse_color_spec, parse_page_range, resolve_conflict_path
)

_RESAMPLE_MAP = {
    "lanczos": Image.Resampling.LANCZOS,
    "bicubic": Image.Resampling.BICUBIC,
    "bilinear": Image.Resampling.BILINEAR,
    "nearest": Image.Resampling.NEAREST,
}


def _flatten_to_rgb(img, bg_rgb=(255, 255, 255)):
    """Composite transparent images cleanly onto a solid RGB background."""
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        rgba = img.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, bg_rgb + (255,))
        composited = Image.alpha_composite(bg, rgba)
        return composited.convert('RGB')
    if img.mode != 'RGB':
        return img.convert('RGB')
    return img


def _iter_visible_psd_layers(group):
    """Yield visible leaf layers from a PSD, skipping hidden parent groups."""
    for layer in group:
        if not layer.is_visible():
            continue
        if layer.is_group():
            yield from _iter_visible_psd_layers(layer)
        elif layer.width > 0 and layer.height > 0:
            yield layer


class ConverterThread(WorkerThread):
    progress_signal = Signal(int, str, str)
    completion_signal = Signal(str, float, float, int, int)
    error_signal = Signal(str, str)
    log_signal = Signal(str, str)

    def __init__(self, files, output_dir, output_format, settings, enable_upscale=False, upscale_settings=None):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.output_format = output_format.lower()
        self.settings = settings or {}
        self.enable_upscale = enable_upscale
        self.upscale_settings = upscale_settings or {}
        self.running = True
        self.cancelled = False
        self.total_files = len(files)
        self.processed_files = 0
        self.start_time = 0
        self.total_input_size = 0
        self.total_output_size = 0
        self.success_count = 0
        self.failure_count = 0
        self.skipped_count = 0
        self.last_output_path = ""
        self.processed_pairs = []
        self.process = None

        # Precompute common root when mirroring subfolder structure
        self._common_root = None
        if self.settings.get('mirror_folders') and len(files) > 0:
            try:
                dirs = [os.path.dirname(os.path.abspath(f)) for f in files]
                self._common_root = os.path.commonpath(dirs)
            except Exception:
                self._common_root = None

    def stop(self):
        self.running = False
        self.cancelled = True
        proc = self.process
        if proc:
            for fn in (proc.terminate, proc.kill):
                try:
                    fn()
                except Exception:
                    pass

    def _is_cancelled(self):
        return self.cancelled or not self.running

    def _set_process(self, proc):
        self.process = proc

    def _build_target_dir(self, input_path):
        if self.settings.get('mirror_folders') and self._common_root:
            try:
                rel = os.path.relpath(os.path.dirname(os.path.abspath(input_path)), self._common_root)
                if rel and rel != '.':
                    return os.path.join(self.output_dir, rel)
            except Exception:
                pass
        return self.output_dir

    def _build_output_stem(self, input_path):
        stem = os.path.splitext(os.path.basename(input_path))[0]
        prefix = str(self.settings.get('filename_prefix', '') or '')
        suffix = str(self.settings.get('filename_suffix', '') or '')
        return f"{prefix}{stem}{suffix}"

    def run(self):
        self.start_time = time.time()

        for file_path in self.files:
            try:
                self.total_input_size += os.path.getsize(file_path)
            except Exception:
                pass

        conflict_policy = self.settings.get('conflict_policy', 'overwrite')

        for idx, file_path in enumerate(self.files):
            if self._is_cancelled():
                break

            try:
                file_ext = os.path.splitext(file_path)[1].lower()
                dest_dir = self._build_target_dir(file_path)
                out_stem = self._build_output_stem(file_path)
                raw_output_path = os.path.join(dest_dir, f"{out_stem}.{self.output_format}")

                # Conflict resolution for single-file outputs
                if file_ext not in ('.psd', '.pdf'):
                    resolved = resolve_conflict_path(raw_output_path, conflict_policy)
                    if resolved is None:
                        self.skipped_count += 1
                        self.processed_files += 1
                        self.log_signal.emit(f"Skipped existing: {os.path.basename(raw_output_path)}", "INFO")
                        continue
                    output_path = resolved
                else:
                    output_path = raw_output_path

                created_paths = []

                if file_ext == '.psd':
                    created = self._convert_psd(file_path, output_path, dest_dir, out_stem)
                    created_paths.extend(created if isinstance(created, list) else [])
                elif file_ext == '.pdf' and self.output_format != 'pdf':
                    created = self._convert_pdf(file_path, output_path, dest_dir, out_stem)
                    created_paths.extend(created if isinstance(created, list) else [])
                else:
                    self._convert_image(file_path, output_path)
                    created_paths.append(output_path)

                if self._is_cancelled():
                    break

                if self.enable_upscale and self.output_format in ['png', 'jpg', 'jpeg', 'webp']:
                    for p in created_paths:
                        if self._is_cancelled():
                            break
                        if os.path.exists(p):
                            self._apply_ai_upscale(p, file_index=idx)

                if self._is_cancelled():
                    break

                self.processed_files += 1
                self.success_count += 1
                if created_paths:
                    self.last_output_path = created_paths[-1]
                    if os.path.exists(created_paths[0]):
                        self.processed_pairs.append((file_path, created_paths[0]))

                for p in created_paths:
                    if os.path.exists(p):
                        self.total_output_size += os.path.getsize(p)

                progress = int((self.processed_files / max(1, self.total_files)) * 100)
                eta_text, speed_text = calculate_progress_info(self.processed_files, self.total_files, self.start_time)
                self.progress_signal.emit(progress, eta_text, speed_text)

            except Exception as e:
                if self._is_cancelled():
                    break
                self.failure_count += 1
                error_message = f"Error converting {file_path}: {str(e)}"
                self.error_signal.emit(error_message, "conversion_error")
                self.log_signal.emit(error_message, "ERROR")

                self.processed_files += 1
                progress = int((self.processed_files / max(1, self.total_files)) * 100)
                self.progress_signal.emit(progress, "Processing...", "Error occurred on last file")

        self.cleanup_temp_directory()

        if not self._is_cancelled():
            self.completion_signal.emit(
                self.last_output_path,
                self.total_input_size,
                self.total_output_size,
                self.success_count,
                self.failure_count
            )

    def _apply_ai_upscale(self, target_image_path, file_index=0):
        if self._is_cancelled():
            return

        scale_str = str(self.upscale_settings.get('scale', '2x'))
        scale_factor = int(scale_str.lower().replace('x', '').strip()) if scale_str.lower().replace('x', '').strip().isdigit() else 2
        model_name = self.upscale_settings.get('model', 'realesr').lower()
        style_model = self.upscale_settings.get('style_model', 'realesr-animevideov3')
        noise_level = self.upscale_settings.get('noise_level', -1)
        tile_size = int(self.upscale_settings.get('tile_size', 0))
        tta_mode = bool(self.upscale_settings.get('tta_mode', False))
        gpu_id = str(self.upscale_settings.get('gpu_id', 'auto'))
        syncgap_mode = int(self.upscale_settings.get('syncgap_mode', 3) or 3)
        thread_spec = str(self.upscale_settings.get('thread_spec', '1:2:2') or '1:2:2')

        tool_key = "esr"
        if model_name == "waifu2x":
            tool_key = "waifu2x"
        elif model_name == "realcugan":
            tool_key = "realcugan"
        elif model_name == "srmd":
            tool_key = "srmd"

        exe_path, exe_dir = get_tool_info(tool_key)
        if not os.path.exists(exe_path):
            raise Exception(f"AI upscaler not found at: {exe_path}")

        dir_name = os.path.dirname(target_image_path)
        stage = prepare_ncnn_stage(
            target_image_path, target_image_path, dir_name,
            tag=f"c_up_{os.getpid()}_{file_index}",
            force_png_output=(scale_factor < 4 and tool_key == "esr") or (scale_factor == 8 and tool_key != "waifu2x"),
        )
        w, h = stage["orig_size"]
        if 0 < w < 16 or 0 < h < 16:
            if scale_factor > 1:
                with Image.open(stage["ncnn_input"]) as chk_img:
                    upscaled_tiny = chk_img.resize((max(1, w * scale_factor), max(1, h * scale_factor)), Image.Resampling.LANCZOS)
                    save_high_quality_image(upscaled_tiny, target_image_path, exif_bytes=stage["exif_bytes"], icc_profile=stage["icc_profile"])
            cleanup_stage_files(stage["temp_files"])
            return

        if stage["ncnn_output"] == target_image_path:
            temp_upscaled = os.path.join(dir_name, f"upscale_tmp_{os.path.splitext(os.path.basename(target_image_path))[0]}.{stage['ncnn_format']}")
            stage["temp_files"].append(temp_upscaled)
        else:
            temp_upscaled = stage["ncnn_output"]

        pass1_scale = 4 if (scale_factor == 8 and tool_key != "waifu2x") else scale_factor

        if tool_key == "waifu2x":
            cmd = [exe_path, "-i", stage["ncnn_input"], "-o", temp_upscaled, "-s", str(pass1_scale), "-n", str(noise_level), "-m", style_model, "-f", stage["ncnn_format"]]
            cmd.extend(sanitize_ncnn_gpu_args("waifu2x", gpu_id, self.log_signal.emit))
        elif tool_key == "realcugan":
            cmd = [exe_path, "-i", stage["ncnn_input"], "-o", temp_upscaled]
            if style_model == "models-se":
                cmd.extend(["-n", str(noise_level)])
            elif style_model == "models-nose":
                cmd.extend(["-n", "0"])
            cmd.extend(["-s", str(pass1_scale), "-m", style_model, "-c", str(syncgap_mode), "-f", stage["ncnn_format"]])
            cmd.extend(sanitize_ncnn_gpu_args("realcugan", gpu_id, self.log_signal.emit))
        elif tool_key == "srmd":
            cmd = [exe_path, "-i", stage["ncnn_input"], "-o", temp_upscaled, "-s", str(pass1_scale), "-n", str(noise_level), "-m", "models-srmd", "-f", stage["ncnn_format"]]
            cmd.extend(sanitize_ncnn_gpu_args("srmd", gpu_id, self.log_signal.emit))
        else:
            cmd = build_esr_command(
                exe_path, exe_dir, stage["ncnn_input"], temp_upscaled,
                style_model, pass1_scale, stage["ncnn_format"], gpu_id
            )

        if tile_size > 0:
            cmd.extend(["-t", str(tile_size)])
        if thread_spec and thread_spec != "1:2:2":
            cmd.extend(["-j", thread_spec])
        if tta_mode:
            cmd.append("-x")

        self.log_signal.emit(f"Upscaling converted output with {tool_key.upper()} ({scale_factor}x)", "INFO")

        def _on_sub_progress(sub_pct):
            overall = int(((file_index + (sub_pct / 100.0)) / max(1, self.total_files)) * 100)
            eta_text, speed_text = calculate_progress_info(self.processed_files, self.total_files, self.start_time)
            self.progress_signal.emit(min(99, overall), eta_text, f"{speed_text} • Upscaling {sub_pct:.0f}%")

        try:
            returncode, err_text = run_ncnn_process(
                cmd, exe_dir, self._is_cancelled,
                progress_callback=_on_sub_progress,
                process_setter=self._set_process,
                timeout=600
            )
            if self._is_cancelled():
                return
            if returncode != 0:
                raise Exception(f"Upscaler process error (code {returncode}): {err_text}")
            if not os.path.exists(temp_upscaled):
                raise Exception("Upscaler finished but output image was not created")

            if stage["needs_finalize"]:
                with Image.open(temp_upscaled) as out_im:
                    if w > 0 and scale_factor in (2, 3, 8) and out_im.size[0] != w * scale_factor:
                        out_im = out_im.resize((w * scale_factor, h * scale_factor), Image.Resampling.LANCZOS)
                    save_high_quality_image(out_im, target_image_path, exif_bytes=stage["exif_bytes"], icc_profile=stage["icc_profile"])
            else:
                if os.path.exists(target_image_path):
                    os.remove(target_image_path)
                os.rename(temp_upscaled, target_image_path)
        finally:
            cleanup_stage_files(stage["temp_files"])

    def cleanup_temp_directory(self):
        try:
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception:
                        pass
        except Exception:
            pass

    def _apply_resizing(self, img):
        preset = self.settings.get('resize_preset', 'Original (100%)')
        if preset == 'Original (100%)':
            return img

        w, h = img.size
        new_w, new_h = w, h

        if preset.endswith('%'):
            pct_val = int(preset.rstrip('%'))
            ratio = pct_val / 100.0
            new_w = max(1, int(w * ratio))
            new_h = max(1, int(h * ratio))
        elif preset in ('Custom Bounds', 'Fit Bounding Box', 'Match Width (Auto H)', 'Match Height (Auto W)'):
            max_w = int(self.settings.get('custom_max_width', 0))
            max_h = int(self.settings.get('custom_max_height', 0))
            if preset == 'Match Width (Auto H)' and max_w > 0:
                ratio = max_w / w
                new_w, new_h = max_w, max(1, int(h * ratio))
            elif preset == 'Match Height (Auto W)' and max_h > 0:
                ratio = max_h / h
                new_w, new_h = max(1, int(w * ratio)), max_h
            elif max_w > 0 and max_h > 0:
                ratio = min(max_w / w, max_h / h)
                new_w, new_h = max(1, int(w * ratio)), max(1, int(h * ratio))
            elif max_w > 0:
                ratio = max_w / w
                new_w, new_h = max_w, max(1, int(h * ratio))
            elif max_h > 0:
                ratio = max_h / h
                new_w, new_h = max(1, int(w * ratio)), max_h

        if (new_w, new_h) != (w, h):
            filter_key = str(self.settings.get('resample_filter', 'lanczos')).lower().split()[0]
            resample = _RESAMPLE_MAP.get(filter_key, Image.Resampling.LANCZOS)
            img = img.resize((new_w, new_h), resample)
            self.log_signal.emit(f"Resized image from {w}x{h} to {new_w}x{new_h} ({filter_key})", "INFO")

        return img

    def _prepare_color_mode(self, img):
        if self.output_format in ['jpg', 'jpeg', 'bmp', 'pdf']:
            bg_rgb = parse_color_spec(self.settings.get('alpha_bg_color', 'White'))
            return _flatten_to_rgb(img, bg_rgb=bg_rgb)
        if self.output_format == 'png' and img.mode == 'P':
            return img.convert('RGBA')
        return img

    def _convert_psd(self, input_path, output_path, dest_dir=None, out_stem=None):
        try:
            if self._is_cancelled():
                return []

            psd = PSDImage.open(input_path)
            psd_image = psd.composite()
            if psd_image is None:
                raise Exception("Failed to generate composite image from PSD.")

            extract_layers = self.settings.get('extract_layers', False)
            include_composite = self.settings.get('psd_include_composite', True)
            raw_layer_names = self.settings.get('psd_raw_layer_names', False)
            conflict_policy = self.settings.get('conflict_policy', 'overwrite')
            base_stem = out_stem or Path(input_path).stem
            target_root = dest_dir or self.output_dir
            created = []

            if extract_layers:
                img_folder = os.path.join(target_root, base_stem)
                os.makedirs(img_folder, exist_ok=True)
                if not os.access(img_folder, os.W_OK):
                    raise Exception(f"Output directory is not writable: {img_folder}")

                if include_composite:
                    composite_path = resolve_conflict_path(os.path.join(img_folder, f"{base_stem}.{self.output_format}"), conflict_policy)
                    if composite_path:
                        comp_img = self._prepare_color_mode(psd_image)
                        comp_img = self._apply_resizing(comp_img)
                        self._save_image_with_settings(comp_img, composite_path)
                        created.append(composite_path)

                layer_idx = 1
                for layer in _iter_visible_psd_layers(psd):
                    if self._is_cancelled():
                        break
                    try:
                        layer_img = layer.composite()
                    except Exception:
                        layer_img = None

                    if layer_img:
                        clean_name = "".join(c for c in layer.name if c.isalnum() or c in (' ', '_', '-')).strip()
                        layer_name = clean_name if clean_name else f"layer_{layer_idx:02d}"
                        fname = f"{layer_name}.{self.output_format}" if raw_layer_names else f"layer_{layer_idx:02d}_{layer_name}.{self.output_format}"
                        raw_lpath = os.path.join(img_folder, fname)
                        lpath = resolve_conflict_path(raw_lpath, "rename" if raw_layer_names and os.path.exists(raw_lpath) else conflict_policy)
                        if lpath:
                            layer_img = self._prepare_color_mode(layer_img)
                            layer_img = self._apply_resizing(layer_img)
                            self._save_image_with_settings(layer_img, lpath)
                            created.append(lpath)
                        layer_idx += 1
            else:
                resolved = resolve_conflict_path(output_path, conflict_policy)
                if resolved:
                    output_dir = os.path.dirname(resolved)
                    os.makedirs(output_dir, exist_ok=True)
                    if not os.access(output_dir, os.W_OK):
                        raise Exception(f"Output directory is not writable: {output_dir}")
                    psd_image = self._prepare_color_mode(psd_image)
                    psd_image = self._apply_resizing(psd_image)
                    self._save_image_with_settings(psd_image, resolved)
                    created.append(resolved)

            del psd, psd_image
            gc.collect()
            return created

        except Exception as e:
            if self._is_cancelled():
                return []
            raise Exception(f"PSD conversion error: {str(e)}")

    def _convert_pdf(self, input_path, output_path, dest_dir=None, out_stem=None):
        try:
            if self._is_cancelled():
                return []

            if PDF_CONVERTER != "pymupdf" or fitz is None:
                raise Exception("PyMuPDF is not available. Please install PyMuPDF.")

            pdf_document = fitz.open(input_path)
            dpi_setting = str(self.settings.get('pdf_dpi', '150 DPI'))
            dpi = int(dpi_setting.split()[0])

            quality_setting = self.settings.get('pdf_quality', 'High')
            quality_factor = 2.0 if quality_setting == 'High' else (1.5 if quality_setting == 'Medium' else 1.0)
            zoom_factor = (dpi / 72.0) * quality_factor
            matrix = fitz.Matrix(zoom_factor, zoom_factor)

            extract_all = self.settings.get('pdf_extract_all', False)
            page_range_str = self.settings.get('pdf_page_range', '')
            conflict_policy = self.settings.get('conflict_policy', 'overwrite')
            created_files = []
            base_stem = out_stem or Path(input_path).stem
            target_root = dest_dir or self.output_dir

            if not extract_all:
                target_pages = [0] if pdf_document.page_count > 0 else []
            else:
                target_pages = parse_page_range(page_range_str, pdf_document.page_count)

            if len(target_pages) <= 1 and not extract_all:
                if target_pages:
                    resolved = resolve_conflict_path(output_path, conflict_policy)
                    if resolved:
                        os.makedirs(os.path.dirname(resolved), exist_ok=True)
                        page = pdf_document.load_page(target_pages[0])
                        pix = page.get_pixmap(matrix=matrix)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        img = self._apply_resizing(img)
                        self._save_image_with_settings(img, resolved)
                        created_files.append(resolved)
            else:
                pdf_folder = os.path.join(target_root, base_stem)
                os.makedirs(pdf_folder, exist_ok=True)
                for page_idx in target_pages:
                    if self._is_cancelled():
                        break
                    page = pdf_document.load_page(page_idx)
                    pix = page.get_pixmap(matrix=matrix)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img = self._apply_resizing(img)
                    page_path = resolve_conflict_path(os.path.join(pdf_folder, f"page_{page_idx + 1:03d}.{self.output_format}"), conflict_policy)
                    if page_path:
                        self._save_image_with_settings(img, page_path)
                        created_files.append(page_path)

            pdf_document.close()
            return created_files

        except Exception as e:
            if self._is_cancelled():
                return []
            raise Exception(f"PDF conversion error: {str(e)}")

    def _convert_image(self, input_path, output_path):
        try:
            if self._is_cancelled():
                return
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            preserve_exif = bool(self.settings.get('preserve_exif', True))

            with Image.open(input_path) as raw_img:
                exif_bytes = raw_img.info.get('exif') if preserve_exif else None
                icc_profile = raw_img.info.get('icc_profile') if preserve_exif else None

                if preserve_exif:
                    try:
                        orient = raw_img.getexif().get(0x0112, 1)
                        img = ImageOps.exif_transpose(raw_img)
                        if exif_bytes and orient in (2, 3, 4, 5, 6, 7, 8):
                            ex = raw_img.getexif()
                            ex[0x0112] = 1
                            exif_bytes = ex.tobytes()
                    except Exception:
                        img = raw_img.copy()
                else:
                    img = raw_img.copy()

                img = self._prepare_color_mode(img)
                img = self._apply_resizing(img)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                self._save_image_with_settings(img, output_path, exif_bytes=exif_bytes, icc_profile=icc_profile)
        except Exception as e:
            if self._is_cancelled():
                return
            raise Exception(f"Image conversion error: {str(e)}")

    def _save_image_with_settings(self, img, output_path, exif_bytes=None, icc_profile=None):
        out_fmt = self.output_format
        extra_kwargs = {}
        if icc_profile and out_fmt in ('jpg', 'jpeg', 'png', 'webp', 'tiff'):
            extra_kwargs['icc_profile'] = icc_profile
        if exif_bytes and out_fmt in ('jpg', 'jpeg', 'webp', 'png', 'tiff'):
            extra_kwargs['exif'] = exif_bytes

        if out_fmt in ['jpg', 'jpeg']:
            quality = int(self.settings.get('jpeg_quality_num') or self._get_quality_value(self.settings.get('jpeg_quality', 'High')))
            img.save(output_path, quality=quality, optimize=True, **extra_kwargs)

        elif out_fmt == 'png':
            compression = self.settings.get('png_compression_num')
            if compression is None:
                compression = self._get_compression_level(self.settings.get('png_compression', 'Normal'))
            img.save(output_path, format='PNG', compress_level=int(compression), optimize=False, **extra_kwargs)

        elif out_fmt == 'webp':
            lossless = bool(self.settings.get('webp_lossless', False))
            quality = int(self.settings.get('webp_quality_num') or self._get_quality_value(self.settings.get('webp_quality', 'High')))
            img.save(output_path, quality=quality, lossless=lossless, method=6, **extra_kwargs)

        elif out_fmt == 'tiff':
            img.save(output_path, format='TIFF', compression='tiff_deflate', **extra_kwargs)

        elif out_fmt == 'bmp':
            img.save(output_path, format='BMP')

        elif out_fmt == 'gif':
            if img.mode != 'P':
                img = img.convert('P')
            img.save(output_path, format='GIF')

        elif out_fmt == 'pdf':
            bg_rgb = parse_color_spec(self.settings.get('alpha_bg_color', 'White'))
            img_rgb = _flatten_to_rgb(img, bg_rgb=bg_rgb)
            quality_setting = self.settings.get('pdf_quality', 'High')
            dpi_setting = str(self.settings.get('pdf_dpi', '150 DPI'))
            dpi = int(dpi_setting.split()[0])
            quality_factor = 1.0 if quality_setting == 'High' else (0.8 if quality_setting == 'Medium' else 0.6)
            img_rgb.save(output_path, format='PDF', resolution=dpi, quality=int(95 * quality_factor))

        else:
            img.save(output_path)

    def _get_quality_value(self, quality_setting):
        quality_map = {"Maximum": 95, "High": 85, "Medium": 70, "Low": 50}
        return quality_map.get(quality_setting, 85)

    def _get_compression_level(self, compression_setting):
        compression_map = {"None": 0, "Fast": 1, "Normal": 6, "Maximum": 9}
        return compression_map.get(compression_setting, 6)
