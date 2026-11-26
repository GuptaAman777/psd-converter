import os
import subprocess
import time
import uuid
from src.core.signals import WorkerThread, Signal
from PIL import Image

from src.core.ncnn_runner import (
    build_esr_command, cleanup_stage_files, prepare_ncnn_stage,
    run_ncnn_process, sanitize_ncnn_gpu_args, save_high_quality_image
)
from src.utils.helpers import calculate_progress_info, EtaTracker, get_tool_info, normalize_ncnn_format, resolve_conflict_path


class UpscalerThread(WorkerThread):
    progress_signal = Signal(int, str, str)
    completion_signal = Signal(str, int, int, int, int)
    error_signal = Signal(str, str)
    log_signal = Signal(str, str)

    def __init__(self, selected_files, output_dir, upscale_factor="2x", model="waifu2x",
                 keep_format=True, output_format="PNG", noise_level=0, style_model="models-cunet",
                 tile_size=0, tta_mode=False, gpu_id="auto",
                 custom_suffix="", conflict_policy="overwrite", syncgap_mode=3,
                 thread_spec="1:2:2", post_resize_mode="Native"):
        super().__init__()
        self.files = selected_files
        self.output_dir = output_dir
        self.upscale_factor = upscale_factor
        self.model = model
        self.keep_format = keep_format
        self.output_format = output_format.lower()
        self.noise_level = noise_level
        self.style_model = style_model
        self.tile_size = int(tile_size or 0)
        self.tta_mode = bool(tta_mode)
        self.gpu_id = str(gpu_id or "auto")
        self.custom_suffix = custom_suffix
        self.conflict_policy = conflict_policy
        self.syncgap_mode = int(syncgap_mode if syncgap_mode is not None else 3)
        self.thread_spec = str(thread_spec or "1:2:2")
        self.post_resize_mode = str(post_resize_mode or "Native")

        self.running = True
        self.cancelled = False
        self.total_files = len(selected_files)
        self.processed_files = 0
        self.start_time = 0
        self.total_input_size = 0
        self.total_output_size = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_output_path = ""
        self.processed_pairs = []
        self.failed_files = {}
        self.process = None
        self.temp_dir = None

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

    def cleanup_temp_directory(self):
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    try:
                        os.remove(os.path.join(self.temp_dir, file))
                    except Exception:
                        pass
                try:
                    os.rmdir(self.temp_dir)
                except Exception:
                    pass
        except Exception as e:
            self.log_signal.emit(f"Error cleaning up temp directory: {str(e)}", "WARNING")

    def run(self):
        self.start_time = time.time()
        self._eta_tracker = EtaTracker(self.total_files)
        self.temp_dir = os.path.join(self.output_dir, "temp_upscale")
        os.makedirs(self.temp_dir, exist_ok=True)

        for file_path in self.files:
            try:
                self.total_input_size += os.path.getsize(file_path)
            except Exception as e:
                self.failed_files[file_path] = f"Failed to get file size: {str(e)}"
                self.failure_count += 1

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

                suffix_str = self.custom_suffix if self.custom_suffix else f"_upscaled{self.upscale_factor}"
                raw_output_path = os.path.join(self.output_dir, f"{base_name_without_ext}{suffix_str}{output_ext}")
                output_path = resolve_conflict_path(raw_output_path, self.conflict_policy)
                if output_path is None:
                    self.processed_files += 1
                    self.log_signal.emit(f"Skipped existing: {os.path.basename(raw_output_path)}", "INFO")
                    continue

                self.log_signal.emit(
                    f"Upscaling {base_name} ({self.upscale_factor}) using {self.model.upper()} ({self.style_model})",
                    "INFO"
                )

                self._upscale_image(file_path, output_path, file_index=idx)

                if self._is_cancelled():
                    break

                self.processed_files += 1
                self.success_count += 1
                self.last_output_path = output_path
                self.processed_pairs.append((file_path, output_path))

                if os.path.exists(output_path):
                    self.total_output_size += os.path.getsize(output_path)

                progress = int((self.processed_files / max(1, self.total_files)) * 100)
                self._update_progress_info(progress)

            except Exception as e:
                if self._is_cancelled():
                    break
                self.failure_count += 1
                self.failed_files[file_path] = str(e)
                error_message = f"Error upscaling {file_path}: {str(e)}"
                self.error_signal.emit(error_message, "upscaling_error")
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

    def _apply_post_resize(self, img):
        mode = self.post_resize_mode
        if not mode or mode == "Native":
            return img
        w, h = img.size
        if "50% SSAA" in mode:
            target = (max(1, w // 2), max(1, h // 2))
        elif "1920" in mode:
            ratio = min(1.0, 1920 / max(1, max(w, h)))
            target = (max(1, int(w * ratio)), max(1, int(h * ratio)))
        elif "2560" in mode:
            ratio = min(1.0, 2560 / max(1, max(w, h)))
            target = (max(1, int(w * ratio)), max(1, int(h * ratio)))
        elif "3840" in mode:
            ratio = min(1.0, 3840 / max(1, max(w, h)))
            target = (max(1, int(w * ratio)), max(1, int(h * ratio)))
        else:
            return img
        if target != (w, h):
            resized = img.resize(target, Image.Resampling.LANCZOS)
            self.log_signal.emit(f"Applied SSAA post-resize to {target[0]}x{target[1]}", "INFO")
            return resized
        return img

    def _update_progress_info(self, progress, sub_status=None, units=None):
        done = units if units is not None else self.processed_files
        eta_text, speed_text = calculate_progress_info(
            done, self.total_files, self.start_time, tracker=getattr(self, "_eta_tracker", None)
        )
        if sub_status:
            speed_text = sub_status if "Calculating" in speed_text else f"{speed_text} • {sub_status}"
        self.progress_signal.emit(progress, eta_text, speed_text)

    def _build_engine_cmd(self, model_type, in_path, out_path, out_format, scale_factor):
        if model_type == "waifu2x":
            exe_path, exe_dir = get_tool_info("waifu2x")
            if not os.path.exists(exe_path):
                raise Exception(f"Waifu2x binary not found at: {exe_path}")
            cmd = [
                exe_path, "-i", in_path, "-o", out_path,
                "-n", str(self.noise_level), "-s", str(scale_factor),
                "-m", self.style_model, "-f", out_format,
            ]
            cmd.extend(sanitize_ncnn_gpu_args("waifu2x", self.gpu_id, self.log_signal.emit))
            return cmd, exe_dir

        if model_type == "realcugan":
            exe_path, exe_dir = get_tool_info("realcugan")
            if not os.path.exists(exe_path):
                raise Exception(f"Real-CUGAN binary not found at: {exe_path}")

            cugan_noise = self.noise_level
            cugan_scale = scale_factor
            cugan_model = self.style_model

            if cugan_model == "models-nose" and cugan_scale != 2:
                cugan_scale = 2
            elif cugan_model == "models-pro" and cugan_scale == 4:
                cugan_model = "models-se"

            if cugan_model == "models-se" and cugan_scale in [3, 4] and cugan_noise not in [-1, 0, 3]:
                cugan_noise = 3

            cmd = [exe_path, "-i", in_path, "-o", out_path]
            if cugan_model == "models-se":
                cmd.extend(["-n", str(cugan_noise)])
            elif cugan_model == "models-nose":
                cmd.extend(["-n", "0"])

            cmd.extend(["-s", str(cugan_scale), "-m", cugan_model, "-c", str(self.syncgap_mode), "-f", out_format])
            cmd.extend(sanitize_ncnn_gpu_args("realcugan", self.gpu_id, self.log_signal.emit))
            return cmd, exe_dir

        if model_type == "srmd":
            exe_path, exe_dir = get_tool_info("srmd")
            if not os.path.exists(exe_path):
                raise Exception(f"SRMD binary not found at: {exe_path}")
            cmd = [
                exe_path, "-i", in_path, "-o", out_path,
                "-s", str(scale_factor), "-n", str(self.noise_level),
                "-m", "models-srmd", "-f", out_format,
            ]
            cmd.extend(sanitize_ncnn_gpu_args("srmd", self.gpu_id, self.log_signal.emit))
            return cmd, exe_dir

        exe_path, exe_dir = get_tool_info("esr")
        if not os.path.exists(exe_path):
            raise Exception(f"Real-ESRGAN / Upscayl binary not found at: {exe_path}")
        cmd = build_esr_command(
            exe_path, exe_dir, in_path, out_path, self.style_model, scale_factor, out_format, self.gpu_id
        )
        return cmd, exe_dir

    def _upscale_image(self, input_path, output_path, file_index=0):
        if not os.path.exists(input_path):
            raise Exception(f"Input file not found: {input_path}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        clean_factor_str = self.upscale_factor.lower().replace('x', '').strip()
        scale_factor = int(clean_factor_str) if clean_factor_str.isdigit() else 2
        model_type = self.model.lower()

        needs_post_resize = bool(self.post_resize_mode and self.post_resize_mode != "Native")
        needs_two_pass_8x = scale_factor == 8 and model_type != "waifu2x"
        stage = prepare_ncnn_stage(
            input_path,
            output_path,
            self.temp_dir,
            tag=f"up_{uuid.uuid4().hex[:8]}",
            force_png_output=needs_post_resize or needs_two_pass_8x or (scale_factor < 4 and model_type == "esr"),
        )

        # Tiny images (<16px) can crash Vulkan tile kernels; resize cleanly with Lanczos
        ow, oh = stage["orig_size"]
        if 0 < ow < 16 or 0 < oh < 16:
            with Image.open(stage["ncnn_input"]) as tiny_im:
                res = tiny_im.resize((max(1, ow * scale_factor), max(1, oh * scale_factor)), Image.Resampling.LANCZOS)
                res = self._apply_post_resize(res)
                save_high_quality_image(res, output_path, exif_bytes=stage["exif_bytes"], icc_profile=stage["icc_profile"])
            cleanup_stage_files(stage["temp_files"])
            return output_path

        try:
            def _on_sub_progress(sub_pct):
                units_done = file_index + (sub_pct / 100.0)
                overall = int((units_done / max(1, self.total_files)) * 100)
                self._update_progress_info(min(99, overall), sub_status=f"Current image: {sub_pct:.0f}%", units=units_done)

            pass1_scale = 4 if needs_two_pass_8x else scale_factor
            cmd, exe_dir = self._build_engine_cmd(
                model_type, stage["ncnn_input"], stage["ncnn_output"], stage["ncnn_format"], pass1_scale
            )
            if self.tile_size > 0:
                cmd.extend(["-t", str(self.tile_size)])
            if self.thread_spec and self.thread_spec != "1:2:2":
                cmd.extend(["-j", self.thread_spec])
            if self.tta_mode:
                cmd.append("-x")

            if self._is_cancelled():
                return None

            returncode, err_text = run_ncnn_process(
                cmd, exe_dir, self._is_cancelled,
                progress_callback=_on_sub_progress,
                process_setter=self._set_process,
                timeout=600
            )
            if self._is_cancelled():
                return None
            if returncode != 0:
                raise Exception(f"Upscaler process error (code {returncode}): {err_text}")
            if not os.path.exists(stage["ncnn_output"]):
                raise Exception(f"Upscaler did not produce output file: {err_text}")

            # 8x workflow on 4x-native engines: second neural 2x pass (or Lanczos if already huge)
            if needs_two_pass_8x:
                with Image.open(stage["ncnn_output"]) as mid_im:
                    mw, mh = mid_im.size
                if mw * mh <= 3200 * 3200:
                    pass2_out = os.path.join(self.temp_dir, f"up8x_{uuid.uuid4().hex[:8]}.png")
                    stage["temp_files"].append(pass2_out)
                    pass2_cmd, pass2_dir = self._build_engine_cmd(
                        model_type if model_type != "esr" else "esr",
                        stage["ncnn_output"], pass2_out, "png", 2
                    )
                    if self.tile_size > 0:
                        pass2_cmd.extend(["-t", str(self.tile_size)])
                    rc2, err2 = run_ncnn_process(
                        pass2_cmd, pass2_dir, self._is_cancelled,
                        progress_callback=_on_sub_progress,
                        process_setter=self._set_process,
                        timeout=600
                    )
                    if rc2 == 0 and os.path.exists(pass2_out):
                        stage["ncnn_output"] = pass2_out
                else:
                    stage["needs_finalize"] = True

            if stage["needs_finalize"]:
                with Image.open(stage["ncnn_output"]) as final_im:
                    out_im = final_im.copy()
                if needs_two_pass_8x and out_im.size[0] < ow * 8:
                    out_im = out_im.resize((ow * 8, oh * 8), Image.Resampling.LANCZOS)
                elif ow > 0 and scale_factor in (2, 3) and model_type == "esr" and out_im.size[0] > ow * scale_factor:
                    out_im = out_im.resize((ow * scale_factor, oh * scale_factor), Image.Resampling.LANCZOS)
                out_im = self._apply_post_resize(out_im)
                save_high_quality_image(
                    out_im, output_path,
                    exif_bytes=stage["exif_bytes"],
                    icc_profile=stage["icc_profile"],
                )
                out_im.close()

            return output_path

        except subprocess.TimeoutExpired:
            raise Exception("Upscaling timed out after 10 minutes. Reduce image size or increase tile size.")
        except Exception as e:
            if self._is_cancelled():
                return None
            raise Exception(f"Upscaling error: {str(e)}")
        finally:
            cleanup_stage_files(stage["temp_files"])
