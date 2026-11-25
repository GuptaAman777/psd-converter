# ImageTool Liquid Studio v7.0 — PSD & AI Image Suite

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![UI Stack](https://img.shields.io/badge/UI-React%2019%20%2B%20FastAPI%20%2B%20WebView2-0a84ff.svg)](https://github.com/GuptaAman777/psd-converter)
[![AI Engines](https://img.shields.io/badge/AI%20Engines-Upscayl%20%7C%20Real--ESRGAN%20%7C%20Real--CUGAN%20%7C%20Waifu2x%202025%20%7C%20SRMD-orange.svg)](https://github.com/nihui)
[![Hardware Acceleration](https://img.shields.io/badge/Acceleration-Vulkan%20%7C%20Multi--GPU%20%7C%20CPU-purple.svg)](https://www.vulkan.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An offline, hardware-accelerated desktop image processing studio for batch format conversion, Photoshop `.psd` layer extraction, multi-page `.pdf` rasterization, local Vulkan NCNN AI super-resolution (`1x–8x`), multi-engine AI denoising with grain preservation, continuous strip/grid stitching, and split-screen visual inspection — built on a **FastAPI + React 19 + Tailwind CSS v4 + Framer Motion + Edge WebView2 Liquid Glass** architecture.

---

## Key Highlights

* **Apple Liquid Glass Studio (`v7.0`)**: Hardware-composited Edge WebView2 desktop shell with 6 live ambient themes (`Blue`, `Red Crimson`, true-black monochrome `Black (OLED Dark)`, `Purple Cyberpunk`, `Green Emerald`, `Amber Sunset`).
* **Upgraded 2025 Neural NCNN Backends**:
  * **Upscayl / Real-ESRGAN (`upscayl-bin` 2025-12-07 + `realesrgan-ncnn-vulkan`)** supporting `AnimeVideoV3`, `RealESRGAN+`, `RealESRNet+`, `Classic ESRGAN`, plus custom output scaling (`-z/-s`).
  * **Real-CUGAN (`20220728`)** with configurable **SyncGap (`-c`)** tile seam synchronization across `models-se`, `models-pro`, and `models-nose`.
  * **Waifu2x (`20250915`)** updated NCNN + `libjpeg-turbo` + `zlib-ng` supporting `1x–8x` upscaling and `1x` denoising.
  * **SRMD (`20220728`)** parametric noise-aware super-resolution & denoising (`-1` to `10`).
* **On-Demand Additional AI Model Packs**: Download and manage 11 community/curated NCNN model packs (`4x-UltraSharp`, `4x-Remacri`, `Digital Art 4x`, `4x-Nomos8kSC`, `Real-ESRGAN General v3 / WDN`, `4x-LSDIRCompactC3`, `4x-NMKD Siax`, `Uniscale Restore`, etc.) with persistent install/delete confirmation controls.
* **Image, PDF & Photoshop PSD Pipeline**:
  * Workflow presets (`Web WEBP`, `Archival PNG`, `PSD Layers`, `PDF Pages`), EXIF auto-orientation & metadata preservation, custom hex alpha matte flattening, subfolder tree mirroring, filename affixes, and `Overwrite` / `Skip` / `Auto-rename` policies.
  * PSD visible-layer extraction skipping hidden parent groups; PyMuPDF PDF rasterizer supporting `72–600 DPI` and 1-indexed page ranges (`1-4, 7`).
* **High-Capacity Image Stitcher**: Vertical strips, horizontal panoramas, and NxM grid matrices with negative overlap gaps, outer margins, custom hex mattes, natural/alpha/mtime sorting, live dimension estimation, and automatic `WebP` (`16,300px`) / `JPEG` (`65,500px`) chunk splitting.
* **Before / After Inspector & Centered Moveable HUD**: Cursor-anchored `50%–800%` scroll zoom, click-drag synchronized panning, independent `⇄` split slider, and a centered, draggable floating Progress HUD.

---

## Comprehensive AI Model Matrix

| Engine | Built-in Models | Scale Factors | Noise Levels | Best For |
|---|---|---|---|---|
| **Upscayl / Real-ESRGAN** | `realesr-animevideov3`, `realesrgan-x4plus`, `realesrgan-x4plus-anime`, `realesrnet-x4plus`, `esrgan-x4` + 11 downloadable packs | `2x`, `3x`, `4x`, `8x` | Built-in | General photography, anime, illustrations, custom NCNN packs |
| **Real-CUGAN** | `models-se`, `models-pro`, `models-nose` | `2x`, `3x`, `4x`, `8x` | `-1`, `0`, `1`, `2`, `3` | Clean line art, manga, cel-shaded artwork (`SyncGap -c`) |
| **Waifu2x (2025)** | `models-cunet`, `models-upconv_7_anime_style_art_rgb`, `models-upconv_7_photo` | `1x`, `2x`, `4x`, `8x` | `-1`, `0`, `1`, `2`, `3` | Classic `1x` denoise & `2x–8x` illustration/photo scaling |
| **SRMD** | `models-srmd` | `2x`, `3x`, `4x`, `8x` | `-1` to `10` | Noisy captures, vintage scans, high-ISO photography |

---

## Project Architecture

```text
psd-converter/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies (pywebview, fastapi, uvicorn, Pillow, psd-tools, PyMuPDF)
├── frontend/
│   ├── src/                     # React 19 + Tailwind CSS v4 + Framer Motion Liquid Glass UI
│   └── dist/                    # Prebuilt production bundle served by FastAPI
├── src/
│   ├── constants.py             # Version, formats, themes, GitHub URLs
│   ├── desktop/bridge.py        # Edge WebView2 host, Windows 11 DWM frame, native DnD & file dialogs
│   ├── server/app.py            # FastAPI REST + WebSocket backend & model catalog endpoints
│   ├── core/
│   │   ├── ncnn_runner.py       # Subprocess runner, EXIF/BMP staging, HQ saves, GPU fallback
│   │   ├── model_catalog.py     # Curated downloadable NCNN model registry & installer
│   │   ├── converter_thread.py  # Batch image/PSD/PDF conversion & inline upscaling
│   │   ├── upscaler_thread.py   # Multi-engine super-resolution & SSAA post-resize
│   │   ├── denoiser_thread.py   # Multi-engine 1x denoising & Grain Preserve blending
│   │   └── stitcher_thread.py   # Vertical/horizontal/grid stitcher & safe chunking
│   └── utils/                   # Thread-safe settings, hardware diagnostics, logger, updater
└── tests/test_app_suite.py      # Automated 29-test unit, API & engine verification suite
```

---

## Getting Started (From Source)

1. **Install Python dependencies** (`Python 3.10–3.13`):
   ```bash
   pip install -r requirements.txt
   ```
2. **Run ImageTool Liquid Studio**:
   ```bash
   python main.py
   ```
3. *(Optional, only if modifying UI under `frontend/src/`)*:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

---

## Packaging (Windows Portable & Installer)

Prebuilt **Portable (`.zip`)** and **Windows Setup Installer (`Setup.exe`)** builds are published on the [GitHub Releases](https://github.com/GuptaAman777/psd-converter/releases) page. When installed to `Program Files`, user preferences (`settings.json`) and optional downloaded models automatically store in `%LOCALAPPDATA%\ImageTool`; when extracted as Portable, data stays self-contained beside the executable.

---

## Author & License

Developed and maintained by **GuptaAman777** ([GitHub: @GuptaAman777](https://github.com/GuptaAman777)).
Released under the MIT License. Bundled NCNN executables and neural weights belong to their respective open-source authors (`nihui`, `xinntao`, `upscayl`, `nagadomi`).
