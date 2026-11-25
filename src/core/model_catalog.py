import os
import sys
import threading
import urllib.request
from typing import Callable, Optional

from src.utils.helpers import _is_dir_writable, get_app_user_data_dir, get_tool_info

_RAW_UPSCAYL = "https://raw.githubusercontent.com/upscayl/upscayl/main/resources/models"
_RAW_CUSTOM = "https://raw.githubusercontent.com/upscayl/custom-models/main/models"

MODEL_CATALOG = [
    {
        "id": "upscayl-lite-4x",
        "label": "Upscayl Lite 4x",
        "category": "Fast Compact",
        "size_mb": 2.3,
        "scale": 4,
        "engine": "realesr",
        "description": "Ultra-fast compact 4x general upscaler; great for batches and low-VRAM GPUs.",
        "param_url": f"{_RAW_UPSCAYL}/upscayl-lite-4x.param",
        "bin_url": f"{_RAW_UPSCAYL}/upscayl-lite-4x.bin",
    },
    {
        "id": "RealESRGAN_General_x4_v3",
        "label": "Real-ESRGAN General v3 (4x)",
        "category": "Fast Compact",
        "size_mb": 2.3,
        "scale": 4,
        "engine": "realesr",
        "description": "Official compact Real-ESRGAN v3 general architecture; fast & sharp on everyday photos.",
        "param_url": f"{_RAW_CUSTOM}/RealESRGAN_General_x4_v3.param",
        "bin_url": f"{_RAW_CUSTOM}/RealESRGAN_General_x4_v3.bin",
    },
    {
        "id": "RealESRGAN_General_WDN_x4_v3",
        "label": "Real-ESRGAN General WDN v3 (4x)",
        "category": "Fast Compact",
        "size_mb": 2.3,
        "scale": 4,
        "engine": "realesr",
        "description": "Weighted-denoise v3 model for slightly noisy or JPEG-compressed general images.",
        "param_url": f"{_RAW_CUSTOM}/RealESRGAN_General_WDN_x4_v3.param",
        "bin_url": f"{_RAW_CUSTOM}/RealESRGAN_General_WDN_x4_v3.bin",
    },
    {
        "id": "4xLSDIRCompactC3",
        "label": "4x-LSDIR Compact C3",
        "category": "Fast Compact",
        "size_mb": 1.2,
        "scale": 4,
        "engine": "realesr",
        "description": "Tiny 1.2 MB compact sharpener & noise remover suited for rapid previews.",
        "param_url": f"{_RAW_CUSTOM}/4xLSDIRCompactC3.param",
        "bin_url": f"{_RAW_CUSTOM}/4xLSDIRCompactC3.bin",
    },
    {
        "id": "digital-art-4x",
        "label": "Digital Art 4x",
        "category": "Anime & Art",
        "size_mb": 8.6,
        "scale": 4,
        "engine": "realesr",
        "description": "Tuned for digital paintings, illustrations, flat shading, and crisp anime linework.",
        "param_url": f"{_RAW_UPSCAYL}/digital-art-4x.param",
        "bin_url": f"{_RAW_UPSCAYL}/digital-art-4x.bin",
    },
    {
        "id": "ultrasharp-4x",
        "label": "4x-UltraSharp",
        "category": "Photo & Realism",
        "size_mb": 32.0,
        "scale": 4,
        "engine": "realesr",
        "description": "Community-favorite high-acutance 4x model delivering razor-sharp edges & textures.",
        "param_url": f"{_RAW_UPSCAYL}/ultrasharp-4x.param",
        "bin_url": f"{_RAW_UPSCAYL}/ultrasharp-4x.bin",
    },
    {
        "id": "remacri-4x",
        "label": "4x-Foolhardy Remacri",
        "category": "Photo & Realism",
        "size_mb": 32.0,
        "scale": 4,
        "engine": "realesr",
        "description": "Natural skin, foliage, and fabric restoration without plastic over-smoothing.",
        "param_url": f"{_RAW_UPSCAYL}/remacri-4x.param",
        "bin_url": f"{_RAW_UPSCAYL}/remacri-4x.bin",
    },
    {
        "id": "high-fidelity-4x",
        "label": "High Fidelity 4x (HFA2k)",
        "category": "Photo & Realism",
        "size_mb": 32.0,
        "scale": 4,
        "engine": "realesr",
        "description": "Faithful 4x photography restoration balancing crisp detail and natural tonal accuracy.",
        "param_url": f"{_RAW_UPSCAYL}/high-fidelity-4x.param",
        "bin_url": f"{_RAW_UPSCAYL}/high-fidelity-4x.bin",
    },
    {
        "id": "4xNomos8kSC",
        "label": "4x-Nomos8kSC",
        "category": "Photo & Realism",
        "size_mb": 32.0,
        "scale": 4,
        "engine": "realesr",
        "description": "Modern high-resolution photography cleaner removing blur, ringing, and web artifacts.",
        "param_url": f"{_RAW_CUSTOM}/4xNomos8kSC.param",
        "bin_url": f"{_RAW_CUSTOM}/4xNomos8kSC.bin",
    },
    {
        "id": "uniscale_restore",
        "label": "Uniscale Restore 4x",
        "category": "Restoration",
        "size_mb": 32.0,
        "scale": 4,
        "engine": "realesr",
        "description": "Heavy degradation & compression artifact recovery for old scans and web grabs.",
        "param_url": f"{_RAW_CUSTOM}/uniscale_restore.param",
        "bin_url": f"{_RAW_CUSTOM}/uniscale_restore.bin",
    },
    {
        "id": "4x_NMKD-Siax_200k",
        "label": "4x-NMKD Siax 200k",
        "category": "Restoration",
        "size_mb": 63.8,
        "scale": 4,
        "engine": "realesr",
        "description": "Rich texture-preserving RRDB upscaler ideal for archival prints and detailed artwork.",
        "param_url": f"{_RAW_CUSTOM}/4x_NMKD-Siax_200k.param",
        "bin_url": f"{_RAW_CUSTOM}/4x_NMKD-Siax_200k.bin",
    },
]

_CATALOG_MAP = {m["id"]: m for m in MODEL_CATALOG}
_ACTIVE_DOWNLOADS: set[str] = set()
_LOCK = threading.Lock()


def get_bundled_esr_models_dir() -> str:
    _, exe_dir = get_tool_info("esr")
    return os.path.join(exe_dir, "models")


def get_esr_models_dir() -> str:
    """Return writable models directory for extra downloaded NCNN model packs."""
    bundled = get_bundled_esr_models_dir()
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(exe_dir, ".installed")) or not _is_dir_writable(bundled):
            user_models = os.path.join(get_app_user_data_dir(), "models")
            os.makedirs(user_models, exist_ok=True)
            return user_models
    os.makedirs(bundled, exist_ok=True)
    return bundled


def resolve_esr_models_dir_for(model_name: str) -> str:
    """Locate whichever models directory contains `<model_name>.param` cleanly."""
    bundled = get_bundled_esr_models_dir()
    if model_name and os.path.isfile(os.path.join(bundled, f"{model_name}.param")):
        return bundled
    user_models = get_esr_models_dir()
    if model_name and os.path.isfile(os.path.join(user_models, f"{model_name}.param")):
        return user_models
    return bundled


def is_model_installed(model_id: str) -> bool:
    if model_id not in _CATALOG_MAP:
        return False
    models_dir = get_esr_models_dir()
    p_file = os.path.join(models_dir, f"{model_id}.param")
    b_file = os.path.join(models_dir, f"{model_id}.bin")
    return (
        os.path.isfile(p_file) and os.path.getsize(p_file) > 64
        and os.path.isfile(b_file) and os.path.getsize(b_file) > 1024
    )


def get_catalog_status() -> list[dict]:
    with _LOCK:
        active = set(_ACTIVE_DOWNLOADS)
    items = []
    for item in MODEL_CATALOG:
        items.append({
            **item,
            "installed": is_model_installed(item["id"]),
            "downloading": item["id"] in active,
        })
    return items


def _download_file(url: str, dest_path: str, on_chunk: Optional[Callable[[int, int], None]] = None):
    tmp_path = f"{dest_path}.part"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ImageTool-Liquid-Studio"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            with open(tmp_path, "wb") as out:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if on_chunk:
                        on_chunk(downloaded, total)
        os.replace(tmp_path, dest_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def download_model_pack(model_id: str, progress_cb: Optional[Callable[[int, str], None]] = None) -> dict:
    meta = _CATALOG_MAP.get(model_id)
    if not meta:
        raise ValueError(f"Unknown model pack: {model_id}")

    with _LOCK:
        if model_id in _ACTIVE_DOWNLOADS:
            raise RuntimeError(f"Model {model_id} is already downloading")
        _ACTIVE_DOWNLOADS.add(model_id)

    models_dir = get_esr_models_dir()
    param_dest = os.path.join(models_dir, f"{model_id}.param")
    bin_dest = os.path.join(models_dir, f"{model_id}.bin")

    try:
        if progress_cb:
            progress_cb(2, f"Fetching {meta['label']} config...")
        _download_file(meta["param_url"], param_dest)

        def _on_bin_chunk(done_b: int, total_b: int):
            if progress_cb:
                est_total = total_b or int(meta["size_mb"] * 1024 * 1024)
                pct = min(98, max(5, int((done_b / max(1, est_total)) * 95) + 3))
                progress_cb(pct, f"{done_b / (1024 * 1024):.1f} / {meta['size_mb']:.1f} MB")

        _download_file(meta["bin_url"], bin_dest, on_chunk=_on_bin_chunk)
        if progress_cb:
            progress_cb(100, "Installed")
        return {**meta, "installed": True, "downloading": False}
    finally:
        with _LOCK:
            _ACTIVE_DOWNLOADS.discard(model_id)


def remove_model_pack(model_id: str) -> bool:
    if model_id not in _CATALOG_MAP:
        raise ValueError(f"Unknown or built-in model cannot be deleted: {model_id}")
    models_dir = get_esr_models_dir()
    removed = False
    for ext in (".param", ".bin"):
        fp = os.path.join(models_dir, f"{model_id}{ext}")
        if os.path.isfile(fp):
            os.remove(fp)
            removed = True
    return removed
