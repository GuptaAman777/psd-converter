import os
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageOps

from src.core.janai_catalog import JANAI_MODEL_MAP, resolve_janai_model_paths

MANGA_HEIGHT_TIERS = (1200, 1300, 1400, 1500, 1600, 1920, 2048)
_ANALYSIS_CACHE: dict[tuple[str, float], dict[str, Any]] = {}

MANGA_2X_MODELS = {
    1200: "2x_MangaJaNai_1200p_V1_ESRGAN_70k_fp16",
    1300: "2x_MangaJaNai_1300p_V1_ESRGAN_75k_fp16",
    1400: "2x_MangaJaNai_1400p_V1_ESRGAN_70k_fp16",
    1500: "2x_MangaJaNai_1500p_V1_ESRGAN_90k_fp16",
    1600: "2x_MangaJaNai_1600p_V1_ESRGAN_90k_fp16",
    1920: "2x_MangaJaNai_1920p_V1_ESRGAN_70k_fp16",
    2048: "2x_MangaJaNai_2048p_V1_ESRGAN_95k_fp16",
}

MANGA_4X_MODELS = {
    1200: "4x_MangaJaNai_1200p_V1_ESRGAN_70k_fp16",
    1300: "4x_MangaJaNai_1300p_V1_ESRGAN_75k_fp16",
    1400: "4x_MangaJaNai_1400p_V1_ESRGAN_105k_fp16",
    1500: "4x_MangaJaNai_1500p_V1_ESRGAN_105k_fp16",
    1600: "4x_MangaJaNai_1600p_V1_ESRGAN_70k_fp16",
    1920: "4x_MangaJaNai_1920p_V1_ESRGAN_105k_fp16",
    2048: "4x_MangaJaNai_2048p_V1_ESRGAN_70k_fp16",
}

ILLUSTRATION_MODELS = {
    ("span", 2, "detail"): "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16",
    ("span", 2, "denoise"): "2x_IllustrationJaNai_V3denoise_SPAN_S_30k_fp16",
    ("fdat_m", 2, "detail"): "2x_IllustrationJaNai_V3detail_FDAT_M_unshuffle_40k_fp16",
    ("fdat_m", 2, "denoise"): "2x_IllustrationJaNai_V3denoise_FDAT_M_unshuffle_30k_fp16",
    ("fdat_m", 4, "detail"): "4x_IllustrationJaNai_V3detail_FDAT_M_40k_fp16",
    ("fdat_m", 4, "denoise"): "4x_IllustrationJaNai_V3denoise_FDAT_M_47k_fp16",
    ("fdat_xl", 4, "detail"): "4x_IllustrationJaNai_V3detail_FDAT_XL_27k_fp16",
    ("fdat_xl", 4, "denoise"): "4x_IllustrationJaNai_V3denoise_FDAT_XL_32k_fp16",
    # FDAT-XL only ships 4x weights; honor user's explicit FDAT-XL choice at 4x instead of silently switching to FDAT-M.
    ("fdat_xl", 2, "detail"): "4x_IllustrationJaNai_V3detail_FDAT_XL_27k_fp16",
    ("fdat_xl", 2, "denoise"): "4x_IllustrationJaNai_V3denoise_FDAT_XL_32k_fp16",
}

BUILTIN_JANAI_WORKFLOWS = [
    {
        "id": "preset_mangajanai_2x",
        "name": "MangaJaNai 2x Balanced (B&W Tiers + FDAT-M 2x Color)",
        "builtin": True,
        "description": "Fast daily driver: auto-matches B&W pages to nearest 1200p–2048p 2x tier and color pages to FDAT-M 2x.",
        "grayscale_strategy": "auto_tier",
        "grayscale_scale": "2x",
        "grayscale_model_id": MANGA_2X_MODELS[1400],
        "grayscale_chain_id": "",
        "color_model_id": "2x_IllustrationJaNai_V3detail_FDAT_M_unshuffle_40k_fp16",
        "color_denoise_model_id": "2x_IllustrationJaNai_V3denoise_FDAT_M_unshuffle_30k_fp16",
        "color_auto_denoise": True,
        "color_chain_id": "",
    },
    {
        "id": "preset_mangajanai_4x",
        "name": "MangaJaNai 4x High-Res (B&W Tiers + FDAT-M 4x Color)",
        "builtin": True,
        "description": "Auto-matches B&W pages to nearest 1200p–2048p 4x tier and routes color art/covers to FDAT-M 4x V3.",
        "grayscale_strategy": "auto_tier",
        "grayscale_scale": "4x",
        "grayscale_model_id": MANGA_4X_MODELS[1400],
        "grayscale_chain_id": "",
        "color_model_id": "4x_IllustrationJaNai_V3detail_FDAT_M_40k_fp16",
        "color_denoise_model_id": "4x_IllustrationJaNai_V3denoise_FDAT_M_47k_fp16",
        "color_auto_denoise": True,
        "color_chain_id": "",
    },
    {
        "id": "preset_fast_span",
        "name": "High Speed Batch (Manga 2x + SPAN 2x Color)",
        "builtin": True,
        "description": "Fastest throughput for whole manga volumes: 2x MangaJaNai on B&W + 0.8 MB SPAN-S 2x on color.",
        "grayscale_strategy": "auto_tier",
        "grayscale_scale": "2x",
        "grayscale_model_id": MANGA_2X_MODELS[1400],
        "grayscale_chain_id": "",
        "color_model_id": "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16",
        "color_denoise_model_id": "2x_IllustrationJaNai_V3denoise_SPAN_S_30k_fp16",
        "color_auto_denoise": True,
        "color_chain_id": "",
    },
    {
        "id": "preset_archival_xl",
        "name": "Archival Maximum Quality (4x Manga + FDAT-XL 4x Color)",
        "builtin": True,
        "description": "Maximum 4x restoration for scans and flagship FDAT-XL 4x detail/denoise on color plates.",
        "grayscale_strategy": "auto_tier",
        "grayscale_scale": "4x",
        "grayscale_model_id": MANGA_4X_MODELS[1200],
        "grayscale_chain_id": "",
        "color_model_id": "4x_IllustrationJaNai_V3detail_FDAT_XL_27k_fp16",
        "color_denoise_model_id": "4x_IllustrationJaNai_V3denoise_FDAT_XL_32k_fp16",
        "color_auto_denoise": True,
        "color_chain_id": "",
    },
    {
        "id": "preset_denoise_chain_illustration",
        "name": "Color Print Restore (SPAN Denoise 2x → FDAT Detail 4x)",
        "builtin": True,
        "description": "Two-pass chain on color pages (cleans halftone/JPEG first via SPAN, then adds crisp detail via FDAT-M 4x); 2x auto-tiers B&W.",
        "grayscale_strategy": "auto_tier",
        "grayscale_scale": "2x",
        "grayscale_model_id": MANGA_2X_MODELS[1400],
        "grayscale_chain_id": "",
        "color_model_id": "2x_IllustrationJaNai_V3denoise_SPAN_S_30k_fp16",
        "color_denoise_model_id": "2x_IllustrationJaNai_V3denoise_SPAN_S_30k_fp16",
        "color_auto_denoise": False,
        "color_chain_id": "4x_IllustrationJaNai_V3detail_FDAT_M_40k_fp16",
    },
]


def nearest_manga_tier(height: int) -> int:
    """Snap source page height to the closest trained MangaJaNai tier (1200p..2048p)."""
    h = max(1, int(height or 1200))
    return min(MANGA_HEIGHT_TIERS, key=lambda t: (abs(h - t), -t))


def analyze_image_properties(image_path: str) -> dict[str, Any]:
    """Inspect image dimensions, grayscale vs color content, and compression heuristic."""
    try:
        mtime = os.path.getmtime(image_path)
    except OSError:
        mtime = 0.0
    cache_key = (image_path, mtime)
    if cache_key in _ANALYSIS_CACHE:
        return dict(_ANALYSIS_CACHE[cache_key])

    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    is_lossy_ext = ext in ("jpg", "jpeg", "webp")

    with Image.open(image_path) as raw:
        im = ImageOps.exif_transpose(raw)
        w, h = im.size
        mode = im.mode

        if mode in ("1", "L", "LA"):
            is_gray = True
            chroma_ratio = 0.0
        else:
            probe = im.convert("RGB")
            if max(w, h) > 384:
                probe.thumbnail((384, 384), Image.Resampling.BILINEAR)
            arr = np.asarray(probe, dtype=np.int16)
            # Channel spread max(|R-G|, |G-B|, |R-B|) accurately detects B&W scans even with minor JPEG chroma tint
            rg = np.abs(arr[:, :, 0] - arr[:, :, 1])
            gb = np.abs(arr[:, :, 1] - arr[:, :, 2])
            rb = np.abs(arr[:, :, 0] - arr[:, :, 2])
            spread = np.maximum(np.maximum(rg, gb), rb)
            colored_frac = float(np.mean(spread > 16))
            mean_spread = float(np.mean(spread))
            p98_5 = float(np.percentile(spread, 98.5))
            is_gray = (colored_frac < 0.015) and (mean_spread < 4.5) and (p98_5 <= 22.0)
            chroma_ratio = round(colored_frac, 4)

    result = {
        "width": int(w),
        "height": int(h),
        "ext": ext,
        "is_grayscale": bool(is_gray),
        "likely_compressed": bool(is_lossy_ext),
        "chroma_ratio": chroma_ratio,
        "nearest_tier": nearest_manga_tier(h),
    }
    if len(_ANALYSIS_CACHE) > 2000:
        _ANALYSIS_CACHE.clear()
    _ANALYSIS_CACHE[cache_key] = result
    return dict(result)


def _pick_auto_manga_scale(height: int, scale_pref: str) -> int:
    pref = str(scale_pref or "2x").lower().strip()
    if pref in ("4", "4x"):
        return 4
    return 2


def select_janai_route(
    image_path: str,
    mode: str = "auto",
    model_id: str = "",
    auto_config: Optional[dict[str, Any]] = None,
    workflow: Optional[dict[str, Any]] = None,
    props: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Resolve primary (and optional chained) JaNai NCNN model(s) for a specific image."""
    norm_mode = str(mode or "auto").lower().strip()

    if norm_mode == "single":
        chosen_id = model_id or "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16"
        meta = JANAI_MODEL_MAP.get(chosen_id, {})
        resolved = resolve_janai_model_paths(chosen_id)
        return {
            "mode": "single",
            "model_id": chosen_id,
            "model_label": meta.get("label", chosen_id),
            "chain_model_id": "",
            "chain_model_label": "",
            "scale": int(meta.get("scale", 2)),
            "installed": bool(resolved["installed"]),
            "source": resolved["source"],
            "reason": f"Manual selection ({meta.get('family', 'NCNN')})",
            "analysis": props,
        }

    info = props or analyze_image_properties(image_path)
    tier = info["nearest_tier"]
    is_gray = info["is_grayscale"]

    chain_id = ""
    if norm_mode == "workflow" and isinstance(workflow, dict):
        wf = workflow
        if is_gray:
            strat = str(wf.get("grayscale_strategy", "auto_tier")).lower()
            if strat == "specific" and wf.get("grayscale_model_id") in JANAI_MODEL_MAP:
                chosen_id = wf["grayscale_model_id"]
                reason = f"Workflow B&W fixed model"
            else:
                g_scale = _pick_auto_manga_scale(info["height"], wf.get("grayscale_scale", "auto"))
                chosen_id = (MANGA_2X_MODELS if g_scale == 2 else MANGA_4X_MODELS)[tier]
                reason = f"Workflow B&W {info['height']}px → {tier}p ({g_scale}x)"
            chain_id = str(wf.get("grayscale_chain_id") or "")
        else:
            auto_dn = bool(wf.get("color_auto_denoise", True))
            if auto_dn and info["likely_compressed"] and wf.get("color_denoise_model_id") in JANAI_MODEL_MAP:
                chosen_id = wf["color_denoise_model_id"]
                reason = f"Workflow Color ({info['ext'].upper()} denoise)"
            elif wf.get("color_model_id") in JANAI_MODEL_MAP:
                chosen_id = wf["color_model_id"]
                reason = f"Workflow Color ({info['ext'].upper()} detail)"
            else:
                chosen_id = "4x_IllustrationJaNai_V3detail_FDAT_M_40k_fp16"
                reason = "Workflow Color default (FDAT-M 4x)"
            chain_id = str(wf.get("color_chain_id") or "")
    else:
        # Built-in Auto Detect (MangaJaNai + IllustrationJaNai V3 rules)
        cfg = auto_config or {}
        req_scale = str(cfg.get("scale") or cfg.get("manga_scale_mode") or "2x").lower().strip()
        if is_gray:
            g_scale = _pick_auto_manga_scale(info["height"], cfg.get("manga_scale_mode") or req_scale)
            chosen_id = (MANGA_2X_MODELS if g_scale == 2 else MANGA_4X_MODELS)[tier]
            reason = f"Auto B&W Manga ({info['width']}×{info['height']} → {tier}p • {g_scale}x)"
        else:
            color_tier = str(cfg.get("color_tier", "fdat_m")).lower()
            if color_tier not in ("span", "fdat_m", "fdat_xl"):
                color_tier = "fdat_m"

            dn_pref = str(cfg.get("color_denoise_mode", "auto")).lower()
            if dn_pref == "detail":
                style_kind = "detail"
            elif dn_pref == "denoise":
                style_kind = "denoise"
            else:
                style_kind = "denoise" if info["likely_compressed"] else "detail"

            if color_tier == "span":
                target_c_scale = 2
            else:
                c_scale_pref = str(cfg.get("color_scale_mode") or req_scale).lower().strip()
                target_c_scale = 4 if c_scale_pref in ("4", "4x") else 2

            chosen_id = ILLUSTRATION_MODELS.get(
                (color_tier, target_c_scale, style_kind),
                "2x_IllustrationJaNai_V3detail_FDAT_M_unshuffle_40k_fp16",
            )
            c_meta = JANAI_MODEL_MAP[chosen_id]
            reason = (
                f"Auto Color ({info['width']}×{info['height']} • "
                f"{'Denoise' if style_kind == 'denoise' else 'Detail'} → {c_meta['family']} {c_meta['scale']}x)"
            )

    if chain_id and chain_id not in JANAI_MODEL_MAP:
        chain_id = ""

    meta = JANAI_MODEL_MAP.get(chosen_id, {})
    resolved = resolve_janai_model_paths(chosen_id)
    chain_meta = JANAI_MODEL_MAP.get(chain_id, {}) if chain_id else {}
    chain_resolved = resolve_janai_model_paths(chain_id) if chain_id else {"installed": True}

    total_scale = int(meta.get("scale", 2)) * (int(chain_meta.get("scale", 1)) if chain_id else 1)

    return {
        "mode": norm_mode,
        "model_id": chosen_id,
        "model_label": meta.get("label", chosen_id),
        "chain_model_id": chain_id,
        "chain_model_label": chain_meta.get("label", "") if chain_id else "",
        "scale": total_scale,
        "installed": bool(resolved["installed"] and chain_resolved["installed"]),
        "missing_models": [
            mid for mid, ok in ((chosen_id, resolved["installed"]), (chain_id, chain_resolved["installed"]))
            if mid and not ok
        ],
        "source": resolved["source"],
        "reason": reason + (f" → Chain: {chain_meta.get('label', chain_id)}" if chain_id else ""),
        "analysis": info,
    }
