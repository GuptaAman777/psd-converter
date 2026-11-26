import asyncio
from contextlib import asynccontextmanager
import io
import os
import re
import threading
import time
import urllib.parse
import uuid
import webbrowser
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps
from pydantic import BaseModel

try:
    import pymupdf as fitz
except ImportError:
    fitz = None

from src.constants import (
    APP_VERSION, DENOISE_FORMATS, GITHUB_PROFILE_URL, GITHUB_RELEASES_URL,
    GITHUB_REPO_URL, INPUT_FORMATS, OUTPUT_FORMATS, RESIZE_PRESETS, THEMES,
    TILE_SIZES, UPSCALE_FORMATS, UPSCALE_MODELS, get_current_theme_name, set_theme
)
from src.core.converter_thread import ConverterThread
from src.core.denoiser_thread import DenoiserThread
from src.core.janai_router import BUILTIN_JANAI_WORKFLOWS, select_janai_route
from src.core.janai_thread import JanaiUpscalerThread
from src.core.model_catalog import (
    download_model_pack, get_catalog_status, is_model_downloading, remove_model_pack
)
from src.core.stitcher_thread import StitcherThread
from src.core.upscaler_thread import UpscalerThread
from src.utils.helpers import (
    detect_gpus, detect_vulkan_support, format_size, get_gpu_combo_items,
    get_resource_path, get_tool_info, load_user_settings, natural_sort_key,
    parse_tile_size, save_user_settings
)
from src.utils.logger import logger
from src.utils.updater import compare_versions


class _Hub:
    """Thread-safe WebSocket broadcaster and active job registry."""

    def __init__(self):
        self.clients: set[WebSocket] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.lock = threading.Lock()
        self.active_jobs: dict[str, dict[str, Any]] = {}
        self.preview_cache: dict[tuple[str, float, int], bytes] = {}
        self.meta_cache: dict[tuple[str, float], dict[str, Any]] = {}

    def broadcast(self, payload: dict[str, Any]):
        loop = self.loop
        if not loop or loop.is_closed():
            return
        with self.lock:
            targets = list(self.clients)
        for ws in targets:
            try:
                asyncio.run_coroutine_threadsafe(ws.send_json(payload), loop)
            except Exception:
                pass


hub = _Hub()


def _wire_logger_to_hub():
    def _on_log(ts: str, level: str, msg: str):
        hub.broadcast({
            "type": "log",
            "timestamp": ts,
            "level": level,
            "message": msg,
        })
    logger.log_signal.connect(_on_log)


_wire_logger_to_hub()


def _probe_single_file(fp: str) -> dict[str, Any]:
    if not fp or not os.path.exists(fp):
        return {
            "path": fp,
            "name": os.path.basename(fp),
            "ext": os.path.splitext(fp)[1].lower().lstrip("."),
            "size_bytes": 0,
            "size_str": "0 B",
            "width": 0,
            "height": 0,
            "dims": "",
            "mode": "",
            "layers": 0,
            "exists": False,
        }

    st = os.stat(fp)
    cache_key = (fp, st.st_mtime_ns, st.st_size)
    if cache_key in hub.meta_cache:
        return hub.meta_cache[cache_key]

    ext = os.path.splitext(fp)[1].lower().lstrip(".")
    size_bytes = st.st_size
    size_str = format_size(size_bytes)
    w, h, mode, layers = 0, 0, ext.upper(), 0
    dims = ""

    try:
        if ext == "psd":
            from psd_tools import PSDImage
            psd = PSDImage.open(fp)
            w, h = psd.width, psd.height
            layers = sum(1 for l in psd.descendants() if not l.is_group())
            dims = f"{w}×{h}"
            mode = f"PSD • {layers} layers"
        elif ext == "pdf":
            if fitz is not None:
                doc = fitz.open(fp)
                pages = doc.page_count
                if pages > 0:
                    rect = doc.load_page(0).rect
                    w, h = int(rect.width), int(rect.height)
                doc.close()
                mode = f"PDF • {pages} pages"
                dims = f"{pages} pg"
            else:
                mode = "PDF"
                dims = "Document"
        else:
            with Image.open(fp) as im:
                w, h = im.size
                dims = f"{w}×{h}"
                mode = str(im.mode)
    except Exception:
        pass

    info = {
        "path": fp,
        "name": os.path.basename(fp),
        "ext": ext,
        "size_bytes": size_bytes,
        "size_str": size_str,
        "width": w,
        "height": h,
        "dims": dims,
        "mode": mode,
        "layers": layers,
        "exists": True,
    }
    if len(hub.meta_cache) > 1500:
        hub.meta_cache.clear()
    hub.meta_cache[cache_key] = info
    return info


def _render_preview_bytes(fp: str, max_size: int = 420) -> bytes:
    if not fp or not os.path.exists(fp):
        raise FileNotFoundError(fp)
    st = os.stat(fp)
    max_size = max(64, min(2400, int(max_size)))
    key = (fp, st.st_mtime_ns, st.st_size, max_size)
    if key in hub.preview_cache:
        return hub.preview_cache[key]

    ext = os.path.splitext(fp)[1].lower().lstrip(".")
    pil_img = None
    try:
        if ext == "psd":
            from psd_tools import PSDImage
            psd = PSDImage.open(fp)
            comp = psd.composite()
            pil_img = comp.copy() if comp else Image.new("RGBA", (max(1, psd.width), max(1, psd.height)), (30, 30, 45, 255))
        elif ext == "pdf" and fitz is not None:
            doc = fitz.open(fp)
            if doc.page_count > 0:
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=120)
                pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
        else:
            with Image.open(fp) as im:
                pil_img = ImageOps.exif_transpose(im)
                if pil_img.mode not in ("RGBA", "RGB"):
                    pil_img = pil_img.convert("RGBA")
                elif pil_img is im:
                    pil_img = im.copy()

        if pil_img is None:
            raise ValueError("Unable to decode preview")

        if max(pil_img.size) > max_size:
            pil_img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)
        if pil_img.mode not in ("RGBA", "RGB"):
            pil_img = pil_img.convert("RGBA")

        buf = io.BytesIO()
        pil_img.save(buf, format="WEBP", quality=86, method=4)
        data = buf.getvalue()
        if len(hub.preview_cache) > 600:
            hub.preview_cache.clear()
        hub.preview_cache[key] = data
        return data
    finally:
        if pil_img is not None:
            try:
                pil_img.close()
            except Exception:
                pass


class ProbeRequest(BaseModel):
    paths: list[str]
    allowed_exts: Optional[list[str]] = None


class ScanFolderRequest(BaseModel):
    folder: str
    allowed_exts: Optional[list[str]] = None
    stitcher_mode: bool = False


class StitchEstimateRequest(BaseModel):
    groups: list[dict[str, Any]]
    layout_mode: str = "Vertical (Top to Bottom)"
    grid_columns: int = 2
    spacing: int = 0
    outer_padding: int = 0
    output_format: str = "PNG"
    sort_mode: str = "natural"
    reverse_order: bool = False


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any]


class PathActionRequest(BaseModel):
    path: str


class JobStartRequest(BaseModel):
    workspace: str
    payload: dict[str, Any]


class JobCancelRequest(BaseModel):
    job_id: str


class ModelInstallRequest(BaseModel):
    model_id: str


class CheckPathsRequest(BaseModel):
    paths: list[str]


class AnalyzeJanaiRequest(BaseModel):
    paths: list[str]
    mode: str = "auto"
    model_id: str = ""
    auto_config: Optional[dict[str, Any]] = None
    workflow: Optional[dict[str, Any]] = None


def create_app(frontend_dist: Optional[str] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        hub.loop = asyncio.get_running_loop()
        yield

    app = FastAPI(title="ImageTool API", version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket):
        await websocket.accept()
        with hub.lock:
            hub.clients.add(websocket)
        try:
            await websocket.send_json({"type": "hello", "version": APP_VERSION})
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            with hub.lock:
                hub.clients.discard(websocket)

    @app.get("/api/bootstrap")
    def api_bootstrap():
        user_settings = load_user_settings()
        if user_settings.get("theme") in THEMES:
            set_theme(user_settings["theme"])

        tools = {}
        for k in ("esr", "waifu2x", "realcugan", "srmd"):
            exe_p, _ = get_tool_info(k)
            tools[k] = bool(exe_p and os.path.exists(exe_p))
        try:
            import ncnn as _ncnn_mod
            import numpy as _np_mod
            tools["janai_ncnn"] = bool(_ncnn_mod and _np_mod)
        except Exception:
            tools["janai_ncnn"] = False

        return {
            "version": APP_VERSION,
            "themes": THEMES,
            "current_theme": get_current_theme_name(),
            "settings": user_settings,
            "gpus": detect_gpus(),
            "gpu_items": get_gpu_combo_items(),
            "vulkan_support": detect_vulkan_support(),
            "tools": tools,
            "model_catalog": get_catalog_status(),
            "builtin_janai_workflows": BUILTIN_JANAI_WORKFLOWS,
            "formats": {
                "input": INPUT_FORMATS,
                "output": OUTPUT_FORMATS,
                "upscale": UPSCALE_FORMATS,
                "denoise": DENOISE_FORMATS,
                "resize_presets": RESIZE_PRESETS,
                "tile_sizes": TILE_SIZES,
                "upscale_models": UPSCALE_MODELS,
            },
            "github": {
                "repo": GITHUB_REPO_URL,
                "profile": GITHUB_PROFILE_URL,
                "releases_api": GITHUB_RELEASES_URL,
            },
            "logs": logger.log_messages[-250:],
        }

    @app.post("/api/probe")
    def api_probe(req: ProbeRequest):
        allowed = {e.lower().lstrip(".") for e in (req.allowed_exts or INPUT_FORMATS)}
        results = []
        for raw_path in req.paths:
            if not raw_path:
                continue
            if os.path.isdir(raw_path):
                for root, _, filenames in os.walk(raw_path):
                    for fn in filenames:
                        ext = os.path.splitext(fn)[1].lower().lstrip(".")
                        if ext in allowed:
                            results.append(_probe_single_file(os.path.join(root, fn)))
            elif os.path.isfile(raw_path):
                ext = os.path.splitext(raw_path)[1].lower().lstrip(".")
                if not allowed or ext in allowed:
                    results.append(_probe_single_file(raw_path))
        return {"files": results}

    @app.post("/api/scan-folders")
    def api_scan_folders(req: ScanFolderRequest):
        folder = req.folder
        if not folder or not os.path.isdir(folder):
            return {"files": [], "groups": []}

        allowed = {e.lower().lstrip(".") for e in (req.allowed_exts or INPUT_FORMATS)}
        if not req.stitcher_mode:
            found = []
            for root, _, filenames in os.walk(folder):
                for fn in filenames:
                    if os.path.splitext(fn)[1].lower().lstrip(".") in allowed:
                        found.append(_probe_single_file(os.path.join(root, fn)))
            found.sort(key=lambda item: natural_sort_key(item["path"]))
            return {"files": found, "groups": []}

        # Stitcher subfolder scanning
        subfolders = [f.path for f in os.scandir(folder) if f.is_dir()]
        targets = subfolders if subfolders else [folder]
        groups = []
        img_exts = {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif"}
        for tgt in targets:
            files_in_dir = []
            for entry in os.scandir(tgt):
                if entry.is_file() and os.path.splitext(entry.name)[1].lower().lstrip(".") in img_exts:
                    files_in_dir.append(entry.path)
            if files_in_dir:
                files_in_dir.sort(key=natural_sort_key)
                total_b = sum(os.path.getsize(p) for p in files_in_dir if os.path.exists(p))
                groups.append({
                    "id": tgt,
                    "name": os.path.basename(tgt),
                    "is_virtual": False,
                    "files": files_in_dir,
                    "count": len(files_in_dir),
                    "total_bytes": total_b,
                    "size_str": format_size(total_b),
                })
        return {"files": [], "groups": groups}

    @app.post("/api/stitch-estimate")
    def api_stitch_estimate(req: StitchEstimateRequest):
        img_exts = {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif"}
        out_fmt = req.output_format.lower()
        estimates = []
        for grp in req.groups:
            gid = grp.get("id", "")
            raw_files = list(grp.get("files") or [])
            if not gid.startswith("virtual:") and os.path.isdir(gid) and not raw_files:
                raw_files = [
                    e.path for e in os.scandir(gid)
                    if e.is_file() and os.path.splitext(e.name)[1].lower().lstrip(".") in img_exts
                ]

            if req.sort_mode == "alpha":
                raw_files.sort(key=lambda p: os.path.basename(p).lower(), reverse=req.reverse_order)
            elif req.sort_mode == "mtime":
                raw_files.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=req.reverse_order)
            else:
                raw_files.sort(key=natural_sort_key, reverse=req.reverse_order)

            dims = []
            for fp in raw_files[:40]:
                try:
                    with Image.open(fp) as im:
                        dims.append(im.size)
                except Exception:
                    pass

            est_text = ""
            if dims:
                scale = len(raw_files) / len(dims)
                pad = max(0, req.outer_padding) * 2
                sp = req.spacing
                if "Grid" in req.layout_mode:
                    cols = max(1, req.grid_columns)
                    rows = (len(raw_files) + cols - 1) // cols
                    cw = max(w for w, _ in dims)
                    ch = max(h for _, h in dims)
                    ew = pad + cw * cols + max(0, sp) * (cols - 1)
                    eh = pad + ch * rows + max(0, sp) * (rows - 1)
                elif "Vertical" in req.layout_mode:
                    ew = pad + max(w for w, _ in dims)
                    eh = pad + int(sum(h for _, h in dims) * scale) + max(-200, sp) * (len(raw_files) - 1)
                else:
                    ew = pad + int(sum(w for w, _ in dims) * scale) + max(-200, sp) * (len(raw_files) - 1)
                    eh = pad + max(h for _, h in dims)
                ew, eh = max(1, ew), max(1, eh)
                chunks = ""
                if out_fmt == "webp" and (ew > 16383 or eh > 16383):
                    chunks = f" • ~{max(1, -(-max(ew, eh) // 16383))} WebP chunks"
                elif out_fmt in ("jpg", "jpeg") and (ew > 65500 or eh > 65500):
                    chunks = f" • ~{max(1, -(-max(ew, eh) // 65500))} JPEG chunks"
                est_text = f"Est. ~{ew:,}×{eh:,} px{chunks}"

            total_b = sum(os.path.getsize(p) for p in raw_files if os.path.exists(p))
            estimates.append({
                "id": gid,
                "sorted_files": raw_files,
                "count": len(raw_files),
                "total_bytes": total_b,
                "size_str": format_size(total_b),
                "estimate": est_text,
            })
        return {"estimates": estimates}

    @app.get("/api/preview")
    def api_preview(path: str = Query(...), max_size: int = Query(420)):
        decoded = urllib.parse.unquote(path)
        if not os.path.exists(decoded):
            raise HTTPException(status_code=404, detail="File not found")
        try:
            data = _render_preview_bytes(decoded, max_size=max_size)
            return Response(
                content=data,
                media_type="image/webp",
                headers={"Cache-Control": "no-store, max-age=0"},
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))

    @app.post("/api/check-paths")
    def api_check_paths(req: CheckPathsRequest):
        exists_map = {}
        for fp in req.paths or []:
            if fp:
                exists_map[fp] = bool(os.path.isfile(fp))
        return {"exists": exists_map}

    @app.get("/api/models/catalog")
    def api_model_catalog():
        return {"models": get_catalog_status()}

    @app.post("/api/janai/analyze")
    def api_janai_analyze(req: AnalyzeJanaiRequest):
        routes = []
        missing_set = set()
        for fp in (req.paths or [])[:250]:
            if not fp or not os.path.isfile(fp):
                continue
            try:
                r = select_janai_route(
                    fp,
                    mode=req.mode,
                    model_id=req.model_id,
                    auto_config=req.auto_config,
                    workflow=req.workflow,
                )
                for mid in r.get("missing_models") or []:
                    missing_set.add(mid)
                routes.append({
                    "path": fp,
                    "name": os.path.basename(fp),
                    **r,
                })
            except Exception as exc:
                routes.append({
                    "path": fp,
                    "name": os.path.basename(fp),
                    "error": str(exc),
                })
        return {"routes": routes, "missing_models": sorted(missing_set)}

    @app.post("/api/models/install")
    def api_model_install(req: ModelInstallRequest):
        model_id = req.model_id.strip()
        if is_model_downloading(model_id):
            return {"started": False, "already_downloading": True, "model_id": model_id}

        def _worker():
            try:
                last_pct = [-1]

                def _on_prog(pct: int, detail: str):
                    if pct < 100 and pct != last_pct[0] and pct - last_pct[0] >= 4:
                        last_pct[0] = pct
                        hub.broadcast({
                            "type": "model_download",
                            "model_id": model_id,
                            "status": "downloading",
                            "percent": pct,
                            "detail": detail,
                        })

                info = download_model_pack(model_id, progress_cb=_on_prog)
                logger.log(f"Downloaded AI model pack: {info['label']}", "SUCCESS")
                hub.broadcast({
                    "type": "model_download",
                    "model_id": model_id,
                    "status": "installed",
                    "percent": 100,
                    "detail": "Ready",
                    "catalog": get_catalog_status(),
                })
            except Exception as e:
                logger.log(f"Model pack download failed ({model_id}): {e}", "ERROR")
                hub.broadcast({
                    "type": "model_download",
                    "model_id": model_id,
                    "status": "error",
                    "percent": 0,
                    "detail": str(e),
                    "catalog": get_catalog_status(),
                })

        threading.Thread(target=_worker, daemon=True).start()
        return {"started": True, "model_id": model_id}

    @app.delete("/api/models/{model_id}")
    def api_model_remove(model_id: str):
        if is_model_downloading(model_id):
            raise HTTPException(status_code=409, detail="Cannot delete model while it is currently downloading")
        try:
            remove_model_pack(model_id)
            logger.log(f"Removed custom AI model pack: {model_id}", "INFO")
            return {"ok": True, "models": get_catalog_status()}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/api/logs")
    def api_logs():
        return {"logs": logger.log_messages[-300:]}

    @app.post("/api/logs/clear")
    def api_logs_clear():
        logger.log_messages.clear()
        return {"ok": True}

    @app.post("/api/settings")
    def api_save_settings(req: SettingsUpdateRequest):
        save_user_settings(req.settings)
        saved = load_user_settings()
        if "theme" in req.settings and req.settings["theme"] in THEMES:
            set_theme(req.settings["theme"])
        logger.log(f"Settings updated: {', '.join(req.settings.keys())}", "INFO")
        return {"settings": saved, "current_theme": get_current_theme_name()}

    @app.get("/api/updates/check")
    def api_check_updates():
        try:
            import requests
            resp = requests.get(GITHUB_RELEASES_URL, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            latest = data.get("tag_name", "").lstrip("v") or APP_VERSION
            notes = data.get("body", "No release notes available.")
            url = data.get("html_url", f"{GITHUB_REPO_URL}/releases")
            avail = compare_versions(APP_VERSION, latest) < 0
            return {
                "current_version": APP_VERSION,
                "latest_version": latest,
                "release_notes": notes,
                "release_url": url,
                "update_available": avail,
            }
        except Exception as e:
            return {
                "current_version": APP_VERSION,
                "latest_version": APP_VERSION,
                "release_notes": "",
                "release_url": GITHUB_REPO_URL,
                "update_available": False,
                "error": str(e),
            }

    @app.post("/api/open-folder")
    def api_open_folder(req: PathActionRequest):
        if req.path and os.path.exists(req.path):
            os.startfile(req.path)
            return {"ok": True}
        return {"ok": False}

    @app.post("/api/open-url")
    def api_open_url(req: PathActionRequest):
        if req.path and req.path.startswith(("http://", "https://")):
            webbrowser.open(req.path)
            return {"ok": True}
        return {"ok": False}

    @app.post("/api/jobs/start")
    def api_start_job(req: JobStartRequest):
        job_id = uuid.uuid4().hex[:10]
        ws = req.workspace
        p = req.payload
        out_dir = p.get("output_dir", "")

        if ws == "converter":
            files = p.get("files", [])
            if not files or not out_dir:
                raise HTTPException(status_code=400, detail="Missing files or output directory")
            out_fmt = str(p.get("output_format", "png")).lower()
            settings = dict(p.get("settings") or {})
            enable_upscale = bool(p.get("enable_upscale", False))
            upscale_settings = dict(p.get("upscale_settings") or {})

            worker = ConverterThread(files, out_dir, out_fmt, settings, enable_upscale, upscale_settings)
            hub.active_jobs[job_id] = {"worker": worker, "workspace": ws, "cancelled": False}

            worker.progress_signal.connect(lambda val, eta, spd: hub.broadcast({
                "type": "progress", "job_id": job_id, "workspace": ws,
                "percent": val, "eta": eta, "speed": spd,
            }))
            worker.log_signal.connect(lambda msg, lvl: logger.log(msg, lvl))
            worker.error_signal.connect(lambda msg, _t: _emit_job_error(job_id, ws, msg))
            worker.completion_signal.connect(
                lambda last_p, in_b, out_b, ok_c, fail_c: _emit_job_complete(
                    job_id, ws, last_p or out_dir, out_dir, in_b, out_b, ok_c, fail_c,
                    getattr(worker, "skipped_count", 0), getattr(worker, "processed_pairs", [])
                )
            )
            worker.start()

        elif ws == "upscaler":
            files = p.get("files", [])
            if not files or not out_dir:
                raise HTTPException(status_code=400, detail="Missing files or output directory")
            worker = UpscalerThread(
                files,
                out_dir,
                upscale_factor=str(p.get("scale", "2x")),
                model=str(p.get("model", "realesr")),
                keep_format=bool(p.get("keep_format", True)),
                output_format=str(p.get("output_format", "PNG")),
                noise_level=int(p.get("noise_level", -1)),
                style_model=str(p.get("style_model", "realesr-animevideov3")),
                tile_size=parse_tile_size(str(p.get("tile_size", "0"))),
                tta_mode=bool(p.get("tta_mode", False)),
                gpu_id=str(p.get("gpu_id", "auto")),
                custom_suffix=str(p.get("custom_suffix", "")),
                conflict_policy=str(p.get("conflict_policy", "overwrite")),
                syncgap_mode=int(p.get("syncgap_mode", 3)),
                thread_spec=str(p.get("thread_spec", "1:2:2")),
                post_resize_mode=str(p.get("post_resize_mode", "Native")),
            )
            hub.active_jobs[job_id] = {"worker": worker, "workspace": ws, "cancelled": False}

            worker.progress_signal.connect(lambda val, eta, spd: hub.broadcast({
                "type": "progress", "job_id": job_id, "workspace": ws,
                "percent": val, "eta": eta, "speed": spd,
            }))
            worker.log_signal.connect(lambda msg, lvl: logger.log(msg, lvl))
            worker.error_signal.connect(lambda msg, _t: _emit_job_error(job_id, ws, msg))
            worker.completion_signal.connect(
                lambda last_p, in_b, out_b, ok_c, fail_c: _emit_job_complete(
                    job_id, ws, os.path.dirname(last_p) if last_p else out_dir, out_dir,
                    in_b, out_b, ok_c, fail_c, 0, getattr(worker, "processed_pairs", [])
                )
            )
            worker.start()

        elif ws == "denoiser":
            files = p.get("files", [])
            if not files or not out_dir:
                raise HTTPException(status_code=400, detail="Missing files or output directory")
            worker = DenoiserThread(
                files,
                out_dir,
                noise_level=int(p.get("noise_level", 2)),
                model=str(p.get("model", "anime")),
                keep_format=bool(p.get("keep_format", True)),
                output_format=str(p.get("output_format", "PNG")),
                engine=str(p.get("engine", "waifu2x")),
                tile_size=parse_tile_size(str(p.get("tile_size", "0"))),
                tta_mode=bool(p.get("tta_mode", False)),
                gpu_id=str(p.get("gpu_id", "auto")),
                custom_suffix=str(p.get("custom_suffix", "_denoised")),
                conflict_policy=str(p.get("conflict_policy", "overwrite")),
                thread_spec=str(p.get("thread_spec", "1:2:2")),
                blend_pct=int(p.get("blend_pct", 100)),
            )
            hub.active_jobs[job_id] = {"worker": worker, "workspace": ws, "cancelled": False}

            worker.progress_signal.connect(lambda val, eta, spd: hub.broadcast({
                "type": "progress", "job_id": job_id, "workspace": ws,
                "percent": val, "eta": eta, "speed": spd,
            }))
            worker.log_signal.connect(lambda msg, lvl: logger.log(msg, lvl))
            worker.error_signal.connect(lambda msg, _t: _emit_job_error(job_id, ws, msg))
            worker.completion_signal.connect(
                lambda last_p, in_b, out_b, ok_c, fail_c: _emit_job_complete(
                    job_id, ws, os.path.dirname(last_p) if last_p else out_dir, out_dir,
                    in_b, out_b, ok_c, fail_c, 0, getattr(worker, "processed_pairs", [])
                )
            )
            worker.start()

        elif ws == "janai":
            files = p.get("files", [])
            if not files or not out_dir:
                raise HTTPException(status_code=400, detail="Missing files or output directory")
            raw_tile = str(p.get("tile_size", "0")).strip().lower()
            tile_val = -1 if raw_tile in ("full", "none", "-1") else parse_tile_size(raw_tile)
            worker = JanaiUpscalerThread(
                files,
                out_dir,
                model_id=str(p.get("model_id", "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16")),
                keep_format=bool(p.get("keep_format", True)),
                output_format=str(p.get("output_format", "PNG")),
                tile_size=tile_val,
                use_fp16=bool(p.get("use_fp16", True)),
                gpu_id=str(p.get("gpu_id", "auto")),
                custom_suffix=str(p.get("custom_suffix", "")),
                conflict_policy=str(p.get("conflict_policy", "overwrite")),
                post_resize_mode=str(p.get("post_resize_mode", "Native")),
                mode=str(p.get("mode", "single")),
                auto_config=p.get("auto_config") or {},
                workflow=p.get("workflow") or {},
            )
            hub.active_jobs[job_id] = {"worker": worker, "workspace": ws, "cancelled": False}

            worker.progress_signal.connect(lambda val, eta, spd: hub.broadcast({
                "type": "progress", "job_id": job_id, "workspace": ws,
                "percent": val, "eta": eta, "speed": spd,
            }))
            worker.log_signal.connect(lambda msg, lvl: logger.log(msg, lvl))
            worker.error_signal.connect(lambda msg, _t: _emit_job_error(job_id, ws, msg))
            worker.completion_signal.connect(
                lambda last_p, in_b, out_b, ok_c, fail_c: _emit_job_complete(
                    job_id, ws, os.path.dirname(last_p) if last_p else out_dir, out_dir,
                    in_b, out_b, ok_c, fail_c, 0, getattr(worker, "processed_pairs", [])
                )
            )
            worker.start()

        elif ws == "stitcher":
            groups = p.get("groups", [])
            if not groups or not out_dir:
                raise HTTPException(status_code=400, detail="Missing stitch groups or output directory")
            folders = [g["id"] for g in groups]
            virtual_files = {g["id"]: g["files"] for g in groups if str(g["id"]).startswith("virtual:")}
            layout_mode = str(p.get("layout_mode", "Vertical (Top to Bottom)"))
            is_vertical = "Vertical" in layout_mode
            rev_dir = ("Bottom to Top" in layout_mode) or ("Right to Left" in layout_mode)
            rev_extra = bool(p.get("reverse_order", False))
            reverse_order = (rev_dir != rev_extra)
            total_groups = max(1, len(folders))

            worker = StitcherThread(
                folders,
                out_dir,
                is_vertical=is_vertical,
                spacing=int(p.get("spacing", 0)),
                output_format=str(p.get("output_format", "PNG")),
                virtual_files=virtual_files,
                alignment=str(p.get("alignment", "Center")),
                bg_color=str(p.get("bg_color", "Transparent")),
                resize_option=str(p.get("resize_option", "Don't Resize")),
                reverse_order=reverse_order,
                layout_mode=layout_mode,
                grid_columns=int(p.get("grid_columns", 2)),
                quality=int(p.get("quality", 95)),
                outer_padding=int(p.get("outer_padding", 0)),
                sort_mode=str(p.get("sort_mode", "natural")),
            )
            hub.active_jobs[job_id] = {"worker": worker, "workspace": ws, "cancelled": False}

            worker.progress_signal.connect(lambda idx, fname: hub.broadcast({
                "type": "progress",
                "job_id": job_id,
                "workspace": ws,
                "percent": int(((idx) / total_groups) * 100),
                "eta": f"Group {idx + 1} / {total_groups}",
                "speed": fname,
            }))
            worker.error_signal.connect(lambda msg: _emit_job_error(job_id, ws, msg))
            worker.finished_signal.connect(
                lambda ok_c, fail_c, outp: _emit_job_complete(
                    job_id, ws, outp or out_dir, out_dir, 0, 0, ok_c, fail_c, 0, []
                )
            )
            worker.start()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown workspace: {ws}")

        logger.log(f"Started {ws} job ({job_id})", "INFO")
        return {"job_id": job_id, "workspace": ws}

    @app.post("/api/jobs/cancel")
    def api_cancel_job(req: JobCancelRequest):
        entry = hub.active_jobs.get(req.job_id)
        if not entry:
            return {"ok": False}
        entry["cancelled"] = True
        worker = entry["worker"]
        try:
            worker.error_signal.disconnect()
        except Exception:
            pass
        if hasattr(worker, "cancelled"):
            worker.cancelled = True
        if hasattr(worker, "running"):
            worker.running = False
        if hasattr(worker, "stop"):
            worker.stop()
        logger.log(f"Cancelled {entry['workspace']} job ({req.job_id})", "WARNING")
        hub.broadcast({"type": "cancelled", "job_id": req.job_id, "workspace": entry["workspace"]})
        return {"ok": True}

    def _emit_job_error(job_id: str, ws: str, message: str):
        entry = hub.active_jobs.get(job_id)
        if entry and entry.get("cancelled"):
            return
        logger.log(f"{ws.title()} error: {message}", "ERROR")
        hub.broadcast({"type": "error", "job_id": job_id, "workspace": ws, "message": message})

    def _emit_job_complete(job_id: str, ws: str, open_dir: str, out_dir: str, in_b: float, out_b: float, ok_c: int, fail_c: int, skip_c: int, pairs: list):
        entry = hub.active_jobs.pop(job_id, None)
        if entry and entry.get("cancelled"):
            return
        pair_dicts = [{"before": a, "after": b} for a, b in (pairs or []) if os.path.exists(a) and os.path.exists(b)]
        logger.log(f"{ws.title()} completed: {ok_c} ok, {fail_c} failed, {skip_c} skipped", "SUCCESS" if fail_c == 0 else "INFO")
        hub.broadcast({
            "type": "completed",
            "job_id": job_id,
            "workspace": ws,
            "output_dir": out_dir or open_dir,
            "input_size": in_b,
            "output_size": out_b,
            "success_count": ok_c,
            "failure_count": fail_c,
            "skipped_count": skip_c,
            "pairs": pair_dicts,
        })

    # Serve compiled Vite React UI cleanly
    dist_dir = frontend_dist or get_resource_path("frontend", "dist")
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        index_file = os.path.join(dist_dir, "index.html")
        candidate = os.path.join(dist_dir, full_path) if full_path else index_file
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return JSONResponse({"status": "API ready — run npm run build in frontend/"}, status_code=200)

    return app
