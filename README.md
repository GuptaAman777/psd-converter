# ImageTool v7.5 — PSD & AI Upscaler and Denoiser 

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![UI Stack](https://img.shields.io/badge/UI-React%2019%20%2B%20FastAPI%20%2B%20WebView2-0a84ff.svg)](https://github.com/GuptaAman777/psd-converter)
[![AI Engines](https://img.shields.io/badge/AI%20Engines-JaNai%20NCNN%20%7C%20Upscayl%20%7C%20Real--CUGAN%20%7C%20Waifu2x%202025%20%7C%20SRMD-orange.svg)](https://github.com/nihui)
[![Hardware Acceleration](https://img.shields.io/badge/Acceleration-Vulkan%20%7C%20Multi--GPU%20%7C%20CPU-purple.svg)](https://www.vulkan.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An offline, hardware-accelerated desktop application for batch format conversion, Photoshop `.psd` layer extraction, multi-page `.pdf` rasterization, local Vulkan NCNN AI super-resolution (`1x–8x`) with MangaJaNai & IllustrationJaNai auto-routing, multi-engine AI denoising, continuous strip/grid stitching, and multi-batch split-screen comparison — built on **FastAPI + React 19 + Tailwind CSS v4 + Edge WebView2**.

---

## What's New in v7.5

* **JaNai AI Workspace (`Ctrl+4`)**: Dedicated Manga & Illustration NCNN Vulkan upscaler (`ncnn` Python runtime + `numpy`) supporting 22 curated models across `SPAN`, `FDAT`, `ESRGAN 4x`, and `ESRGAN 2x`, with reflect-padded tile inference, overlap blending, alpha channel preservation, and 16-bit PNG normalization.
* **On-Demand MangaJaNai & IllustrationJaNai Downloads**: Weights (`~.param` + `.bin`) are no longer bundled in the installer or repository; install only the models you use directly inside **Additional AI Model Packs** from GitHub Releases (`v1.0.0`).
* **Smart Auto Detect & Custom 2-Pass Workflows**:
  * **MangaJaNai Auto Detect**: Analyzes grayscale vs. color artwork per file, snaps to resolution tiers (`1200p`–`2048p`), and pairs with `IllustrationJaNai V3` (`SPAN-S`, `FDAT-M`, `FDAT-XL`) and `2x`/`4x` scale options.
  * **Workflow Presets & Builder**: Five built-in presets plus a persistent Custom Workflow editor supporting 2-pass chained upscaling/denoising.
  * **Queue Routing Inspector**: Click any queued item to inspect its detected resolution, color classification, and exact pass-by-pass model routing before or after analysis.
* **Multi-Batch Before/After Compare**: Retains comparison sets across multiple conversion/upscale batches with a batch switcher, automatic missing-file detection, and one-click removal for deleted outputs.
* **Smoothed ETA & Progress HUD Appearance**: Unified fractional-progress ETA smoothing across all workers, plus a **Settings** toggle between translucent and opaque Progress HUD backgrounds.

---

## Core Capabilities

* **Modern Desktop Interface**: Hardware-accelerated Edge WebView2 host with 6 live themes (`Blue`, `Red Crimson`, `Black (OLED Dark)`, `Purple Cyberpunk`, `Green Emerald`, `Amber Sunset`), native drag-and-drop, and per-tab keyboard shortcuts (`Ctrl+1` to `Ctrl+6`).
* **Neural NCNN Super-Resolution & Denoising**:
  * **JaNai NCNN (`Ctrl+4`)**: 22 MangaJaNai & IllustrationJaNai Vulkan models (`SPAN`, `FDAT`, `ESRGAN`) with single-model, auto-routing, and 2-pass chained workflows.
  * **Upscayl / Real-ESRGAN (`upscayl-bin` 2025-12-07 + `realesrgan-ncnn-vulkan`)**: Built-in `AnimeVideoV3`, `RealESRGAN+`, `RealESRNet+`, `Classic ESRGAN`, plus 11 curated community packs (`4x-UltraSharp`, `4x-Remacri`, `Digital Art 4x`, `4x-Nomos8kSC`, `Uniscale Restore`, etc.).
  * **Real-CUGAN (`20220728`)**: Configurable **SyncGap (`-c`)** tile seam synchronization across `models-se`, `models-pro`, and `models-nose`.
  * **Waifu2x (`20250915`)**: Updated NCNN + `libjpeg-turbo` + `zlib-ng` supporting `1x–8x` upscaling and `1x` denoising.
  * **SRMD (`20220728`)**: Parametric noise-aware super-resolution & denoising (`-1` to `10`) with Grain Preserve blending.
* **Image, PDF & Photoshop PSD Pipeline**:
  * Workflow presets (`Web WEBP`, `Archival PNG`, `PSD Layers`, `PDF Pages`), EXIF auto-orientation & metadata preservation, custom hex alpha matte flattening, subfolder tree mirroring, filename affixes, and `Overwrite` / `Skip` / `Auto-rename` policies.
  * PSD visible-layer extraction skipping hidden parent groups; PyMuPDF PDF rasterizer supporting `72–600 DPI` and 1-indexed page ranges (`1-4, 7`).
* **High-Capacity Image Stitcher**: Vertical strips, horizontal panoramas, and NxM grid matrices with negative overlap gaps, outer margins, custom hex mattes, natural/alpha/mtime sorting, live dimension estimation, and automatic `WebP` (`16,300px`) / `JPEG` (`65,500px`) chunk splitting.
* **Before / After Inspector & Moveable Progress HUD**: Cursor-anchored `50%–800%` scroll zoom, click-drag synchronized panning, independent `⇄` split slider, multi-batch history, and a draggable Progress HUD.

---

## Comprehensive AI Model Matrix

| Engine | Models | Scale Factors | Noise Levels | Best For |
|---|---|---|---|---|
| **JaNai NCNN** | 22 downloadable MangaJaNai & IllustrationJaNai models (`SPAN`, `FDAT`, `ESRGAN`) | `2x`, `4x` (or 2-pass chained) | Built-in / Auto-routed | Manga pages, screentones, digital illustrations, CGs |
| **Upscayl / Real-ESRGAN** | `realesr-animevideov3`, `realesrgan-x4plus`, `realesrgan-x4plus-anime`, `realesrnet-x4plus`, `esrgan-x4` + 11 packs | `2x`, `3x`, `4x`, `8x` | Built-in | General photography, anime, illustrations, custom NCNN packs |
| **Real-CUGAN** | `models-se`, `models-pro`, `models-nose` | `2x`, `3x`, `4x`, `8x` | `-1`, `0`, `1`, `2`, `3` | Clean line art, manga, cel-shaded artwork (`SyncGap -c`) |
| **Waifu2x (2025)** | `models-cunet`, `models-upconv_7_anime_style_art_rgb`, `models-upconv_7_photo` | `1x`, `2x`, `4x`, `8x` | `-1`, `0`, `1`, `2`, `3` | Classic `1x` denoise & `2x–8x` illustration/photo scaling |
| **SRMD** | `models-srmd` | `2x`, `3x`, `4x`, `8x` | `-1` to `10` | Noisy captures, vintage scans, high-ISO photography |

---

## Project Architecture

```text
psd-converter/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies (pywebview, fastapi, uvicorn, ncnn, numpy, Pillow, psd-tools, PyMuPDF)
├── frontend/
│   ├── src/                     # React 19 + Tailwind CSS v4 + Framer Motion UI
│   └── dist/                    # Prebuilt production bundle served by FastAPI
├── src/
│   ├── constants.py             # Version, formats, themes, GitHub URLs
│   ├── desktop/bridge.py        # Edge WebView2 host, Windows 11 DWM frame, native DnD & file dialogs
│   ├── server/app.py            # FastAPI REST + WebSocket backend, JaNai analysis & model catalog endpoints
│   ├── core/
│   │   ├── ncnn_runner.py       # Subprocess runner, EXIF/BMP staging, HQ saves, GPU fallback
│   │   ├── janai_catalog.py     # Registry & on-demand downloader for 22 JaNai NCNN models
│   │   ├── janai_router.py      # Grayscale/color classifier, tier router & 2-pass workflow resolver
│   │   ├── janai_thread.py      # Python NCNN Vulkan tiled upscaler & worker thread
│   │   ├── model_catalog.py     # Unified Upscayl + JaNai model pack registry & installer
│   │   ├── converter_thread.py  # Batch image/PSD/PDF conversion & inline upscaling
│   │   ├── upscaler_thread.py   # Multi-engine super-resolution & SSAA post-resize
│   │   ├── denoiser_thread.py   # Multi-engine 1x denoising & Grain Preserve blending
│   │   └── stitcher_thread.py   # Vertical/horizontal/grid stitcher & safe chunking
│   └── utils/                   # Thread-safe settings, ETA tracker, hardware diagnostics, logger, updater
└── tests/test_app_suite.py      # Automated 33-test unit, API & engine verification suite
```

---

## Getting Started (From Source)

1. **Install Python dependencies** (`Python 3.10–3.13`):
   ```bash
   pip install -r requirements.txt
   ```
2. **Run ImageTool**:
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

Prebuilt **Portable (`.zip`)** and **Windows Setup Installer (`Setup.exe`)** builds are published on the [GitHub Releases](https://github.com/GuptaAman777/psd-converter/releases) page. When installed via `Setup.exe`, user preferences (`settings.json`) and optional downloaded models automatically store in `%LOCALAPPDATA%\ImageTool`; when extracted as Portable, data stays self-contained beside the executable.

---

## Author & License

Developed and maintained by **GuptaAman777** ([GitHub: @GuptaAman777](https://github.com/GuptaAman777)).
Released under the MIT License. Bundled NCNN runtimes and neural weights belong to their respective open-source authors (`nihui`, `xinntao`, `upscayl`, `nagadomi`, `the-database / MangaJaNai`).
