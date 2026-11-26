import os
import subprocess
import time
import uuid
from src.core.signals import WorkerThread, Signal
from PIL import Image

from src.core.ncnn_runner import (
    cleanup_stage_files, prepare_ncnn_stage, run_ncnn_process,
    sanitize_ncnn_gpu_args, save_high_quality_image
)
from src.utils.helpers import calculate_progress_info, EtaTracker, get_tool_info, normalize_ncnn_format, resolve_conflict_path


class DenoiserThread(WorkerThread):
    """Thread for multi-engine image denoising with natural grain blending support."""
    progress_signal = Signal(int, str, str)
    completion_signal = Signal(str, float, float, int, int)
    error_signal = Signal(str, str)
    log_signal = Signal(str, str)

    def __init__(self, files, output_dir, noise_level=1, model="anime", keep_format=True, output_format="PNG",
                 engine="waifu2x", tile_size=0, tta_mode=False, gpu_id="auto",
                 custom_suffix="_denoised", conflict_policy="overwrite", thread_spec="1:2:2", blend_pct=100):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.noise_level = noise_level
        self.model_preset = model
        self.engine = engine.lower() if engine else "waifu2x"
        self.keep_format = keep_format
        self.output_format = output_format.lower()
        self.tile_size = int(tile_size or 0)
        self.tta_mode = bool(tta_mode)
        self.gpu_id = str(gpu_id or "auto")
        self.custom_suffix = str(custom_suffix or "_denoised")
        self.conflict_policy = str(conflict_policy or "overwrite")
        self.thread_spec = str(thread_spec or "1:2:2")
        self.blend_pct = max(10, min(100, int(blend_pct if blend_pct is not None else 100)))

        self.running = True
        self.cancelled = False
        self.total_files = len(files)
        self.processed_files = 0
        self.start_time = 0
        self.total_input_size = 0
        self.total_output_size = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_output_path = ""
        self.processed_pairs = []
        self.process = None

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

    def run(self):
        self.start_time = time.time()
        self._eta_tracker = EtaTracker(self.total_files)

        for file_path in self.files:
            try:
                self.total_input_size += os.path.getsize(file_path)
            except Exception:
                pass

        for idx, file_path in enumerate(self.files):
            if self._is_cancelled():
                break

            try:
                file_ext = os.path.splitext(file_path)[1].lower()
                base_name = os.path.basename(file_path)
                base_name_without_ext = os.path.splitext(base_name)[0]

                output_ext = file_ext if self.keep_format else f".{normalize_ncnn_format(self.output_format)}"
                if not output_ext.startswith('.'):
                    output_ext = f".{output_ext}"

                raw_output_path = os.path.join(self.output_dir, f"{base_name_without_ext}{self.custom_suffix}{output_ext}")
                output_path = resolve_conflict_path(raw_output_path, self.conflict_policy)
                if output_path is None:
                    self.processed_files += 1
                    self.log_signal.emit(f"Skipped existing: {os.path.basename(raw_output_path)}", "INFO")
                    continue

                self.log_signal.emit(
                    f"Denoising {base_name} (engine={self.engine.upper()}, noise={self.noise_level}, blend={self.blend_pct}%)",
                    "INFO"
                )

                self._denoise_image(file_path, output_path, file_index=idx)

                if self._is_cancelled():
                    break

                self.processed_files += 1
                self.success_count += 1
                self.last_output_path = output_path
                self.processed_pairs.append((file_path, output_path))

                if os.path.exists(output_path):
                    self.total_output_size += os.path.getsize(output_path)

                progress = int((self.processed_files / max(1, self.total_files)) * 100)
                eta_text, speed_text = calculate_progress_info(
                    self.processed_files, self.total_files, self.start_time, tracker=getattr(self, "_eta_tracker", None)
                )
                self.progress_signal.emit(progress, eta_text, speed_text)

            except Exception as e:
                if self._is_cancelled():
                    break
                self.failure_count += 1
                error_message = f"Error denoising {file_path}: {str(e)}"
                self.error_signal.emit(error_message, "denoising_error")
                self.log_signal.emit(error_message, "ERROR")

                self.processed_files += 1
                progress = int((self.processed_files / max(1, self.total_files)) * 100)
                self.progress_signal.emit(progress, "Processing...", "Error occurred on last file")

        if not self._is_cancelled():
            self.completion_signal.emit(
                self.last_output_path,
                self.total_input_size,
                self.total_output_size,
                self.success_count,
                self.failure_count
            )

    def _apply_grain_blend(self, orig_path, denoised_path, final_path, exif_bytes=None, icc_profile=None):
        alpha = self.blend_pct / 100.0
        with Image.open(orig_path) as orig_im, Image.open(denoised_path) as den_im:
            if orig_im.size != den_im.size:
                orig_im = orig_im.resize(den_im.size, Image.Resampling.LANCZOS)
            orig_conv = orig_im.convert(den_im.mode)
            blended = Image.blend(orig_conv, den_im, alpha)
            save_high_quality_image(blended, final_path, exif_bytes=exif_bytes, icc_profile=icc_profile)

    def _denoise_image(self, input_path, output_path, file_index=0):
        if not os.path.exists(input_path):
            raise Exception(f"Input file not found: {input_path}")

        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        needs_post = (self.engine == "srmd") or (self.blend_pct < 100)
        stage = prepare_ncnn_stage(
            input_path, output_path, output_dir,
            tag=f"den_{uuid.uuid4().hex[:8]}",
            force_png_output=needs_post,
        )

        try:
            in_for_cmd = stage["ncnn_input"]
            out_for_cmd = stage["ncnn_output"]
            out_format = stage["ncnn_format"]

            if self.engine == "realcugan":
                exe_path, exe_dir = get_tool_info("realcugan")
                if not os.path.exists(exe_path):
                    raise Exception(f"Real-CUGAN binary not found at: {exe_path}")
                cmd = [
                    exe_path, "-i", in_for_cmd, "-o", out_for_cmd,
                    "-n", str(self.noise_level if self.noise_level in [1, 2, 3] else 1),
                    "-s", "1", "-m", "models-se", "-f", out_format,
                ]
                cmd.extend(sanitize_ncnn_gpu_args("realcugan", self.gpu_id, self.log_signal.emit))

            elif self.engine == "srmd":
                exe_path, exe_dir = get_tool_info("srmd")
                if not os.path.exists(exe_path):
                    raise Exception(f"SRMD binary not found at: {exe_path}")
                cmd = [
                    exe_path, "-i", in_for_cmd, "-o", out_for_cmd,
                    "-n", str(self.noise_level if self.noise_level >= 0 else 3),
                    "-s", "2", "-m", "models-srmd", "-f", "png",
                ]
                cmd.extend(sanitize_ncnn_gpu_args("srmd", self.gpu_id, self.log_signal.emit))

            else:
                exe_path, exe_dir = get_tool_info("waifu2x")
                if not os.path.exists(exe_path):
                    raise Exception(f"Waifu2x binary not found at: {exe_path}")
                model_folder = "models-cunet" if self.model_preset == "anime" else "models-upconv_7_photo"
                cmd = [
                    exe_path, "-i", in_for_cmd, "-o", out_for_cmd,
                    "-n", str(self.noise_level), "-s", "1", "-m", model_folder,
                    "-f", out_format,
                ]
                cmd.extend(sanitize_ncnn_gpu_args("waifu2x", self.gpu_id, self.log_signal.emit))

            if self.tile_size > 0:
                cmd.extend(["-t", str(self.tile_size)])
            if self.thread_spec and self.thread_spec != "1:2:2":
                cmd.extend(["-j", self.thread_spec])
            if self.tta_mode:
                cmd.append("-x")

            if self._is_cancelled():
                return

            def _on_sub_progress(sub_pct):
                units_done = file_index + (sub_pct / 100.0)
                overall = int((units_done / max(1, self.total_files)) * 100)
                eta_text, speed_text = calculate_progress_info(
                    units_done, self.total_files, self.start_time, tracker=getattr(self, "_eta_tracker", None)
                )
                extra = f"Current image: {sub_pct:.0f}%"
                spd = extra if "Calculating" in speed_text else f"{speed_text} • {extra}"
                self.progress_signal.emit(min(99, overall), eta_text, spd)

            returncode, err_text = run_ncnn_process(
                cmd, exe_dir, self._is_cancelled,
                progress_callback=_on_sub_progress,
                process_setter=self._set_process,
                timeout=600
            )
            if self._is_cancelled():
                return
            if returncode != 0:
                raise Exception(f"Denoising process error (code {returncode}): {err_text}")
            if not os.path.exists(out_for_cmd):
                raise Exception("Denoising failed: Intermediate output file was not created")

            if self.engine == "srmd":
                ow, oh = stage["orig_size"]
                if ow <= 0 or oh <= 0:
                    with Image.open(in_for_cmd) as orig_img:
                        ow, oh = orig_img.size
                with Image.open(out_for_cmd) as up_img:
                    down_img = up_img.resize((ow, oh), Image.Resampling.LANCZOS)
                    down_img.save(out_for_cmd, format="PNG")

            if self.blend_pct < 100:
                self._apply_grain_blend(
                    in_for_cmd, out_for_cmd, output_path,
                    exif_bytes=stage["exif_bytes"], icc_profile=stage["icc_profile"],
                )
            elif stage["needs_finalize"]:
                with Image.open(out_for_cmd) as final_im:
                    save_high_quality_image(
                        final_im, output_path,
                        exif_bytes=stage["exif_bytes"], icc_profile=stage["icc_profile"],
                    )

            if not os.path.exists(output_path):
                raise Exception("Denoising failed: Output file was not created")

        except subprocess.TimeoutExpired:
            raise Exception("Denoising timed out after 10 minutes")
        except Exception as e:
            if self._is_cancelled():
                return
            raise Exception(f"Denoising error: {str(e)}")
        finally:
            cleanup_stage_files(stage["temp_files"])
