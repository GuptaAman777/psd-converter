import os
import re
import subprocess
import threading
import time
from PIL import Image, ImageOps

from src.utils.helpers import normalize_ncnn_format

_PROGRESS_RE = re.compile(r'(\d{1,3}(?:\.\d+)?)\s*%')
_NCNN_NATIVE_EXTS = {'.png', '.jpg', '.jpeg', '.webp'}


def run_ncnn_process(cmd, cwd, is_cancelled_fn, progress_callback=None, process_setter=None, timeout=600):
    """Execute an NCNN Vulkan CLI subprocess with live progress parsing and clean cancellation.

    Returns:
        tuple[int, str]: (returncode, collected_stderr_text)
    Raises:
        subprocess.TimeoutExpired: If process exceeds `timeout` seconds while active.
    """
    if is_cancelled_fn():
        return -1, ""

    startupinfo = None
    creationflags = 0
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        startupinfo=startupinfo,
        creationflags=creationflags,
        cwd=cwd,
    )
    if process_setter:
        process_setter(proc)

    stderr_chunks = []

    def _read_stderr():
        buf = ""
        try:
            fd = proc.stderr.fileno()
            while True:
                raw = os.read(fd, 512)
                if not raw:
                    break
                text = raw.decode('utf-8', errors='ignore')
                stderr_chunks.append(text)
                if progress_callback:
                    buf += text
                    if '\r' in buf or '\n' in buf:
                        parts = re.split(r'[\r\n]+', buf)
                        buf = parts[-1]
                        for part in parts[:-1]:
                            matches = _PROGRESS_RE.findall(part)
                            if matches:
                                try:
                                    pct = min(100.0, max(0.0, float(matches[-1])))
                                    progress_callback(pct)
                                except ValueError:
                                    pass
        except Exception:
            pass
        finally:
            try:
                proc.stderr.close()
            except Exception:
                pass

    reader = threading.Thread(target=_read_stderr, daemon=True)
    reader.start()

    start_time = time.monotonic()
    try:
        while proc.poll() is None:
            if is_cancelled_fn():
                for fn in (proc.terminate, proc.kill):
                    try:
                        fn()
                    except Exception:
                        pass
                break
            if time.monotonic() - start_time > timeout:
                try:
                    proc.kill()
                except Exception:
                    pass
                raise subprocess.TimeoutExpired(cmd, timeout)
            time.sleep(0.05)

        reader.join(timeout=2.0)
        return proc.returncode if proc.returncode is not None else -1, "".join(stderr_chunks).strip()
    finally:
        if process_setter:
            process_setter(None)


def sanitize_ncnn_gpu_args(tool_key, gpu_id, log_fn=None):
    """Build safe `-g <gpu_id>` CLI args without crashing engines that disallow CPU (-1)."""
    gid = str(gpu_id or "auto").strip()
    if not gid or gid.lower() == "auto":
        return []
    if gid == "-1" and tool_key in ("esr", "realesrgan", "srmd"):
        if log_fn:
            log_fn(f"{tool_key.upper()} does not support CPU (-1); using default Vulkan GPU.", "WARNING")
        return []
    return ["-g", gid]


def save_high_quality_image(img, output_path, exif_bytes=None, icc_profile=None):
    """Save PIL image cleanly at high quality with EXIF/ICC preservation and safe alpha flattening."""
    ext = os.path.splitext(output_path)[1].lower()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    out_im = img
    if ext in ('.jpg', '.jpeg', '.bmp'):
        if out_im.mode in ('RGBA', 'LA') or (out_im.mode == 'P' and 'transparency' in out_im.info):
            rgba = out_im.convert('RGBA')
            bg = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
            out_im = Image.alpha_composite(bg, rgba).convert('RGB')
        elif out_im.mode != 'RGB':
            out_im = out_im.convert('RGB')
    elif ext == '.png' and out_im.mode == 'P':
        out_im = out_im.convert('RGBA')

    save_kwargs = {}
    if ext in ('.jpg', '.jpeg'):
        save_kwargs = {"format": "JPEG", "quality": 95, "optimize": True}
    elif ext == '.webp':
        save_kwargs = {"format": "WEBP", "quality": 92, "method": 6}
    elif ext == '.png':
        save_kwargs = {"format": "PNG", "compress_level": 6}
    elif ext in ('.tif', '.tiff'):
        save_kwargs = {"format": "TIFF", "compression": "tiff_deflate"}
    elif ext == '.bmp':
        save_kwargs = {"format": "BMP"}
    elif ext == '.gif':
        if out_im.mode != 'P':
            out_im = out_im.convert('P')
        save_kwargs = {"format": "GIF"}

    if exif_bytes and ext in ('.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'):
        save_kwargs['exif'] = exif_bytes
    if icc_profile and ext in ('.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'):
        save_kwargs['icc_profile'] = icc_profile

    try:
        out_im.save(output_path, **save_kwargs)
    except Exception:
        save_kwargs.pop('exif', None)
        save_kwargs.pop('icc_profile', None)
        out_im.save(output_path, **save_kwargs)


def prepare_ncnn_stage(input_path, final_output_path, temp_dir, tag="stage", force_png_output=False):
    """Prepare NCNN-compatible oriented PNG input and decide whether output needs intermediate PNG staging.

    Returns:
        dict with keys: ncnn_input, ncnn_output, ncnn_format, temp_files, exif_bytes, icc_profile, final_output, needs_finalize, orig_size
    """
    os.makedirs(temp_dir, exist_ok=True)
    in_ext = os.path.splitext(input_path)[1].lower()
    out_ext = os.path.splitext(final_output_path)[1].lower()

    exif_bytes = None
    icc_profile = None
    orientation = 1
    orig_size = (0, 0)
    needs_in_stage = in_ext not in _NCNN_NATIVE_EXTS

    try:
        with Image.open(input_path) as im:
            orig_size = im.size
            icc_profile = im.info.get('icc_profile')
            raw_exif = im.info.get('exif')
            try:
                orientation = im.getexif().get(0x0112, 1)
            except Exception:
                orientation = 1

            # Drop orientation tag once transposed so viewers don't rotate twice
            if raw_exif:
                if orientation in (2, 3, 4, 5, 6, 7, 8):
                    ex = im.getexif()
                    ex[0x0112] = 1
                    exif_bytes = ex.tobytes()
                else:
                    exif_bytes = raw_exif

            if orientation != 1 or im.mode in ('P', '1', 'CMYK', 'LA'):
                needs_in_stage = True
    except Exception:
        pass

    temp_files = []
    ncnn_input = input_path
    if needs_in_stage:
        ncnn_input = os.path.join(temp_dir, f"{tag}_in.png")
        with Image.open(input_path) as raw:
            oriented = ImageOps.exif_transpose(raw)
            if oriented.mode in ('RGBA', 'LA') or (oriented.mode == 'P' and 'transparency' in oriented.info):
                oriented = oriented.convert('RGBA')
            elif oriented.mode != 'RGB':
                oriented = oriented.convert('RGB')
            oriented.save(ncnn_input, format="PNG")
            orig_size = oriented.size
        temp_files.append(ncnn_input)

    needs_finalize = bool(
        force_png_output
        or (out_ext not in _NCNN_NATIVE_EXTS)
        or (out_ext in ('.jpg', '.jpeg', '.webp') and (exif_bytes or icc_profile))
    )

    if needs_finalize:
        ncnn_output = os.path.join(temp_dir, f"{tag}_out.png")
        ncnn_format = "png"
        temp_files.append(ncnn_output)
    else:
        ncnn_output = final_output_path
        ncnn_format = normalize_ncnn_format(out_ext)

    return {
        "ncnn_input": ncnn_input,
        "ncnn_output": ncnn_output,
        "ncnn_format": ncnn_format,
        "temp_files": temp_files,
        "exif_bytes": exif_bytes,
        "icc_profile": icc_profile,
        "final_output": final_output_path,
        "needs_finalize": needs_finalize,
        "orig_size": orig_size,
    }


def cleanup_stage_files(temp_files):
    for fp in temp_files or ():
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass


def build_esr_command(exe_path, exe_dir, in_path, out_path, style_model, scale_factor, out_format, gpu_id, model_scale_hint=None):
    """Build command list for either modern `upscayl-bin` (2025) or legacy `realesrgan-ncnn-vulkan`."""
    exe_name = os.path.basename(exe_path).lower()
    raw_model = style_model if style_model and not style_model.startswith("models-") else "realesr-animevideov3"

    if exe_name.startswith("upscayl-bin"):
        from src.core.model_catalog import resolve_esr_models_dir_for
        if raw_model == "realesr-animevideov3":
            ms = scale_factor if scale_factor in (2, 3, 4) else 4
            model_name = f"realesr-animevideov3-x{ms}"
            out_scale = ms
        else:
            model_name = raw_model
            if model_scale_hint in (2, 3, 4):
                ms = int(model_scale_hint)
            elif "x2" in raw_model.lower() or "2x" in raw_model.lower():
                ms = 2
            elif "x3" in raw_model.lower() or "3x" in raw_model.lower():
                ms = 3
            else:
                ms = 4
            out_scale = scale_factor if scale_factor in (2, 3, 4) else ms

        models_dir = resolve_esr_models_dir_for(model_name)
        cmd = [
            exe_path, "-i", in_path, "-o", out_path,
            "-m", models_dir, "-n", model_name,
            "-z", str(ms), "-s", str(out_scale),
            "-f", out_format,
        ]
    else:
        effective_scale = 4 if ("x4" in raw_model and "animevideov3" not in raw_model) else min(4, max(2, scale_factor))
        cmd = [
            exe_path, "-i", in_path, "-o", out_path,
            "-s", str(effective_scale), "-n", raw_model,
            "-f", out_format,
        ]

    cmd.extend(sanitize_ncnn_gpu_args("esr", gpu_id))
    return cmd
