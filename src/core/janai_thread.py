from collections import OrderedDict
import math
import os
import time
from PIL import Image, ImageOps

from src.core.janai_catalog import JANAI_MODEL_MAP, resolve_janai_model_paths
from src.core.janai_router import select_janai_route
from src.core.ncnn_runner import save_high_quality_image
from src.core.signals import Signal, WorkerThread
from src.utils.helpers import EtaTracker, normalize_ncnn_format, resolve_conflict_path


class JanaiUpscalerThread(WorkerThread):
    """Run Vulkan-capable JaNai NCNN models (single, auto-detect MangaJaNai, or chained workflows)."""

    progress_signal = Signal(int, str, str)
    completion_signal = Signal(str, int, int, int, int)
    error_signal = Signal(str, str)
    log_signal = Signal(str, str)

    def __init__(
        self,
        selected_files,
        output_dir,
        model_id="2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16",
        keep_format=True,
        output_format="PNG",
        tile_size=0,
        use_fp16=True,
        gpu_id="auto",
        custom_suffix="",
        conflict_policy="overwrite",
        post_resize_mode="Native",
        mode="single",
        auto_config=None,
        workflow=None,
    ):
        super().__init__()
        self.files = list(selected_files or [])
        self.output_dir = output_dir
        self.model_id = str(model_id or "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16")
        self.keep_format = bool(keep_format)
        self.output_format = str(output_format or "PNG").lower()
        self.tile_size = int(tile_size) if tile_size is not None else 0
        self.use_fp16 = bool(use_fp16)
        self.gpu_id = str(gpu_id or "auto")
        self.custom_suffix = str(custom_suffix or "")
        self.conflict_policy = str(conflict_policy or "overwrite")
        self.post_resize_mode = str(post_resize_mode or "Native")
        self.mode = str(mode or "single").lower().strip()
        self.auto_config = dict(auto_config or {})
        self.workflow = dict(workflow or {}) if isinstance(workflow, dict) else {}

        self.running = True
        self.cancelled = False
        self.total_files = len(self.files)
        self.processed_files = 0
        self.start_time = 0.0
        self.total_input_size = 0
        self.total_output_size = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_output_path = ""
        self.processed_pairs = []
        self.failed_files = {}
        self.routed_models = []
        self._net_cache: OrderedDict[tuple[str, bool], object] = OrderedDict()
        self._eta_tracker = None

    def stop(self):
        self.running = False
        self.cancelled = True

    def _is_cancelled(self):
        return self.cancelled or not self.running

    def _get_network(self, model_id: str, meta: dict, resolved: dict, use_fp16: bool):
        key = (model_id, bool(use_fp16))
        if key in self._net_cache:
            self._net_cache.move_to_end(key)
            return self._net_cache[key]

        import ncnn

        net = ncnn.Net()
        gpu_count = ncnn.get_gpu_count()
        gid_str = self.gpu_id.strip().lower()
        use_vulkan = gpu_count > 0 and gid_str != "-1"
        net.opt.use_vulkan_compute = use_vulkan

        if use_vulkan:
            gpu_idx = 0
            if gid_str not in ("", "auto"):
                try:
                    cand = int(gid_str)
                    if 0 <= cand < gpu_count:
                        gpu_idx = cand
                except ValueError:
                    gpu_idx = 0
            net.set_vulkan_device(gpu_idx)
            net.opt.use_fp16_packed = bool(use_fp16)
            net.opt.use_fp16_storage = bool(use_fp16)
            net.opt.use_fp16_arithmetic = bool(use_fp16)
        else:
            if gid_str != "-1" and gpu_count == 0:
                self.log_signal.emit("No Vulkan GPU found for ncnn; running on CPU.", "WARNING")

        if net.load_param(resolved["param_path"]) != 0:
            raise RuntimeError(f"Failed to load NCNN param: {resolved['param_path']}")
        if net.load_model(resolved["bin_path"]) != 0:
            raise RuntimeError(f"Failed to load NCNN bin: {resolved['bin_path']}")

        self._net_cache[key] = net
        while len(self._net_cache) > 3:
            self._net_cache.popitem(last=False)
        return net

    def _infer_patch(self, net, arr_hwc, align, scale, np_mod, ncnn_mod):
        """Run aligned reflect-padded single patch `(H, W, 3)` float32 [0,1] -> `(H*scale, W*scale, 3)`."""
        h, w, _ = arr_hwc.shape
        pad_h = (math.ceil(h / align) * align) - h
        pad_w = (math.ceil(w / align) * align) - w
        padded = np_mod.pad(arr_hwc, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect") if (pad_h or pad_w) else arr_hwc

        chw = np_mod.transpose(padded, (2, 0, 1))[None, ...].copy()
        with net.create_extractor() as ex:
            ex.input("in0", ncnn_mod.Mat(chw, batch_index=0).clone())
            ret, out_mat = ex.extract("out0")
            if ret != 0:
                raise RuntimeError(f"NCNN extractor failed with code {ret}")
        out_chw = out_mat.numpy(batch_index=0)[0]
        out_chw = out_chw[:, : h * scale, : w * scale]
        return np_mod.transpose(out_chw, (1, 2, 0))

    def _run_model_pass(self, arr_hwc, model_id: str, file_index: int, pass_label: str = "", pass_offset: float = 0.0, pass_span: float = 1.0):
        import ncnn
        import numpy as np

        meta = JANAI_MODEL_MAP.get(model_id)
        if not meta:
            raise RuntimeError(f"Unknown JaNai NCNN model: {model_id}")

        resolved = resolve_janai_model_paths(model_id)
        if not resolved["installed"]:
            raise RuntimeError(
                f"Model '{meta['label']}' is not installed locally. Download it first from JaNai AI or Model Packs."
            )

        scale = int(meta["scale"])
        align = max(1, int(meta["align"]))
        h, w, _ = arr_hwc.shape

        if self.tile_size < 0:
            effective_tile = 0
        elif self.tile_size > 0:
            effective_tile = max(64, int(self.tile_size))
        else:
            limit = 384 if meta["family"] == "FDAT" else 512
            effective_tile = 256 if max(h, w) > limit else 0

        def _execute(fp16_flag: bool):
            active_net = self._get_network(model_id, meta, resolved, fp16_flag)
            if effective_tile <= 0 or (h <= effective_tile and w <= effective_tile):
                return self._infer_patch(active_net, arr_hwc, align, scale, np, ncnn)

            overlap = 16
            step = effective_tile
            out_canvas = np.zeros((h * scale, w * scale, 3), dtype=np.float32)

            xs = list(range(0, w, step))
            ys = list(range(0, h, step))
            total_tiles = max(1, len(xs) * len(ys))
            done_tiles = 0

            for y0 in ys:
                for x0 in xs:
                    if self._is_cancelled():
                        return out_canvas
                    y1 = min(h, y0 + step)
                    x1 = min(w, x0 + step)

                    ey0 = max(0, y0 - overlap)
                    ex0 = max(0, x0 - overlap)
                    ey1 = min(h, y1 + overlap)
                    ex1 = min(w, x1 + overlap)

                    patch = arr_hwc[ey0:ey1, ex0:ex1, :]
                    patch_out = self._infer_patch(active_net, patch, align, scale, np, ncnn)

                    cy0 = (y0 - ey0) * scale
                    cx0 = (x0 - ex0) * scale
                    cy1 = cy0 + (y1 - y0) * scale
                    cx1 = cx0 + (x1 - x0) * scale

                    out_canvas[y0 * scale : y1 * scale, x0 * scale : x1 * scale, :] = patch_out[cy0:cy1, cx0:cx1, :]
                    done_tiles += 1
                    tile_frac = done_tiles / total_tiles
                    file_frac = pass_offset + (tile_frac * pass_span)
                    units_done = file_index + file_frac
                    overall = int((units_done / max(1, self.total_files)) * 100)
                    eta_text, speed_text = (
                        self._eta_tracker.update(units_done)
                        if self._eta_tracker is not None
                        else ("Calculating ETA...", "Calculating speed...")
                    )
                    prefix = f"{pass_label} " if pass_label else ""
                    sub_str = f"{prefix}Tile {done_tiles}/{total_tiles} ({tile_frac * 100:.0f}%)"
                    speed_label = sub_str if "Calculating" in speed_text else f"{speed_text} • {sub_str}"
                    self.progress_signal.emit(min(99, overall), eta_text, speed_label)
            return out_canvas

        try:
            return _execute(self.use_fp16)
        except Exception as exc:
            if self.use_fp16 and self.gpu_id.strip().lower() != "-1":
                self.log_signal.emit(f"FP16 Vulkan inference failed ({exc}); retrying in FP32 mode.", "WARNING")
                return _execute(False)
            raise

    def _apply_post_resize(self, img):
        mode = self.post_resize_mode
        if not mode or mode == "Native":
            return img
        w, h = img.size
        target = (w, h)
        if "50% SSAA" in mode:
            target = (max(1, w // 2), max(1, h // 2))
        elif "Height Fit" in mode:
            for th in (2160, 3200, 4096):
                if str(th) in mode and h > th:
                    ratio = th / max(1, h)
                    target = (max(1, int(round(w * ratio))), th)
                    break
        elif "Max Width" in mode:
            for mw in (1920, 2560, 3840):
                if str(mw) in mode and max(w, h) > mw:
                    ratio = mw / max(1, max(w, h))
                    target = (max(1, int(w * ratio)), max(1, int(h * ratio)))
                    break

        if target != (w, h):
            resized = img.resize(target, Image.Resampling.LANCZOS)
            self.log_signal.emit(f"Applied SSAA / target fit to {target[0]}x{target[1]}", "INFO")
            return resized
        return img

    def _process_single(self, input_path, output_path, route, file_index):
        import numpy as np

        exif_bytes = None
        icc_profile = None

        with Image.open(input_path) as raw:
            icc_profile = raw.info.get("icc_profile")
            raw_exif = raw.info.get("exif")
            try:
                orientation = raw.getexif().get(0x0112, 1)
            except Exception:
                orientation = 1
            if raw_exif:
                if orientation in (2, 3, 4, 5, 6, 7, 8):
                    ex = raw.getexif()
                    ex[0x0112] = 1
                    exif_bytes = ex.tobytes()
                else:
                    exif_bytes = raw_exif

            oriented = ImageOps.exif_transpose(raw)
            has_alpha = oriented.mode in ("RGBA", "LA") or (
                oriented.mode == "P" and "transparency" in oriented.info
            )
            alpha_band = oriented.convert("RGBA").getchannel("A") if has_alpha else None
            if oriented.mode in ("I", "I;16", "I;16L", "I;16B", "F"):
                scale_div = 1.0 if oriented.mode == "F" else 65535.0
                norm = np.clip(np.asarray(oriented, dtype=np.float32) / scale_div, 0.0, 1.0)
                if norm.ndim == 2:
                    arr = np.repeat(norm[:, :, None], 3, axis=2)
                else:
                    arr = norm[:, :, :3]
            else:
                rgb_img = oriented.convert("RGB")
                arr = np.asarray(rgb_img, dtype=np.float32) / 255.0

        primary_id = route["model_id"]
        chain_id = route.get("chain_model_id") or ""

        out_arr = self._run_model_pass(
            arr,
            primary_id,
            file_index,
            pass_label="Pass 1" if chain_id else "",
            pass_offset=0.0,
            pass_span=0.5 if chain_id else 1.0,
        )
        if self._is_cancelled():
            return

        if chain_id:
            out_arr = np.clip(out_arr, 0.0, 1.0).astype(np.float32)
            out_arr = self._run_model_pass(
                out_arr,
                chain_id,
                file_index,
                pass_label="Pass 2",
                pass_offset=0.5,
                pass_span=0.5,
            )
            if self._is_cancelled():
                return

        out_u8 = np.clip(out_arr * 255.0 + 0.5, 0, 255).astype(np.uint8)
        out_img = Image.fromarray(out_u8, mode="RGB")

        if alpha_band is not None:
            up_alpha = alpha_band.resize(out_img.size, Image.Resampling.BICUBIC)
            out_img.putalpha(up_alpha)

        out_img = self._apply_post_resize(out_img)
        save_high_quality_image(out_img, output_path, exif_bytes=exif_bytes, icc_profile=icc_profile)

    def run(self):
        self.start_time = time.time()
        self._eta_tracker = EtaTracker(self.total_files)
        os.makedirs(self.output_dir, exist_ok=True)

        for fp in self.files:
            try:
                self.total_input_size += os.path.getsize(fp)
            except Exception as e:
                self.failed_files[fp] = f"Failed to get file size: {e}"
                self.failure_count += 1

        try:
            for idx, file_path in enumerate(self.files):
                if self._is_cancelled():
                    break
                try:
                    route = select_janai_route(
                        file_path,
                        mode=self.mode,
                        model_id=self.model_id,
                        auto_config=self.auto_config,
                        workflow=self.workflow,
                    )
                    if not route["installed"]:
                        missing = ", ".join(route.get("missing_models") or [route["model_id"]])
                        raise RuntimeError(f"Required model(s) not installed: {missing}")

                    in_ext = os.path.splitext(file_path)[1].lower()
                    base = os.path.basename(file_path)
                    stem = os.path.splitext(base)[0]

                    out_ext = in_ext if self.keep_format else f".{normalize_ncnn_format(self.output_format)}"
                    if not out_ext.startswith("."):
                        out_ext = f".{out_ext}"

                    scale = int(route.get("scale") or 2)
                    suffix_str = self.custom_suffix if self.custom_suffix else f"_janai{scale}x"
                    raw_out = os.path.join(self.output_dir, f"{stem}{suffix_str}{out_ext}")
                    output_path = resolve_conflict_path(raw_out, self.conflict_policy)
                    if output_path is None:
                        self.processed_files += 1
                        self.log_signal.emit(f"Skipped existing: {os.path.basename(raw_out)}", "INFO")
                        continue

                    self.routed_models.append((file_path, route["model_id"], route.get("chain_model_id", "")))
                    self.log_signal.emit(
                        f"Upscaling {base} ({scale}x) → {route['reason']}",
                        "INFO",
                    )
                    self._process_single(file_path, output_path, route, idx)
                    if self._is_cancelled():
                        break

                    self.processed_files += 1
                    self.success_count += 1
                    self.last_output_path = output_path
                    self.processed_pairs.append((file_path, output_path))
                    if os.path.exists(output_path):
                        self.total_output_size += os.path.getsize(output_path)

                    progress = int((self.processed_files / max(1, self.total_files)) * 100)
                    eta_text, speed_text = self._eta_tracker.update(self.processed_files)
                    self.progress_signal.emit(progress, eta_text, speed_text)

                except Exception as e:
                    if self._is_cancelled():
                        break
                    self.failure_count += 1
                    self.failed_files[file_path] = str(e)
                    msg = f"Error upscaling {file_path}: {e}"
                    self.error_signal.emit(msg, "janai_error")
                    self.log_signal.emit(msg, "ERROR")
                    self.processed_files += 1
                    progress = int((self.processed_files / max(1, self.total_files)) * 100)
                    self.progress_signal.emit(progress, "Processing...", "Error occurred on last file")
        finally:
            self._net_cache.clear()

        if not self._is_cancelled():
            self.completion_signal.emit(
                self.last_output_path,
                self.total_input_size,
                self.total_output_size,
                self.success_count,
                self.failure_count,
            )
