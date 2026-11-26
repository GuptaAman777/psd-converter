import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Palette, RefreshCw, Terminal, BookOpen, Check, Trash2, Copy,
  Download, Github, Rocket, Search, Keyboard, Lightbulb, SlidersHorizontal, ListOrdered
} from "lucide-react";
import { LIQUID_THEMES } from "./LiquidBackdrop";
import { GlassCard, SettingRow, GlassSwitch } from "./GlassPrimitives";
import { apiGet, apiPost, openExternalUrl } from "../api/client";

const MANUAL_SECTIONS = [
  {
    id: "quickstart",
    title: "Quick Start & Queue",
    badge: "Workflow & Controls",
    jumpTab: "converter",
    jumpLabel: "Open Workspace",
    overview:
      "Every workspace shares the same high-speed asset queue and floating HUD. Drop files or entire folders anywhere on the window to begin.",
    steps: [
      "Drag & drop images, layered PSDs, multi-page PDFs, or folders into the Queue pane (or click + Add Files / Folder).",
      "Inspect predicted output filenames (shown as badges like → image_2x.webp) in List View, or switch to Thumbnail Cards for visual triage.",
      "Uncheck items to skip them, sort by Natural (1, 2, 10), Name A–Z, File Size, or Format, and pick an Output folder at the bottom.",
      "Click the primary Start / Upscale / Denoise / Stitch button. A centered, draggable Progress HUD tracks speed, ETA, and % completion.",
    ],
    controls: [
      { name: "Drag & Drop Overlay", desc: "Supports loose files and nested folders simultaneously. Dropping while on Settings automatically switches to Converter and queues items." },
      { name: "Moveable Progress HUD", desc: "Appears dead-center; drag its top Move grip anywhere in the window. Double-click the grip or click Recenter to snap back." },
      { name: "Output Bar & Auto-open", desc: "Choose a destination folder once per workspace. Enable Auto-open to open Explorer automatically when a batch finishes." },
      { name: "Quick Full Preview", desc: "Double-click any queued row or click the eye icon to inspect full artwork with 50%–800% scroll zoom and click-drag panning." },
    ],
    tips: [
      "Use Remove Unchecked to clean skipped items without clearing your active selection.",
      "Default JPEG, WEBP, PNG, EXIF, and PDF defaults live under Preferences & Themes and sync automatically into new Converter sessions.",
    ],
  },
  {
    id: "converter",
    title: "Converter Module",
    badge: "Formats, PDF & PSD",
    jumpTab: "converter",
    jumpLabel: "Open Converter",
    overview:
      "Batch-transcodes PNG, JPEG, WEBP, BMP, GIF, TIFF, multi-page PDF, and Photoshop PSD documents with optional inline Vulkan AI upscaling.",
    steps: [
      "Pick a 1-click Workflow Preset (Web WEBP, Archival PNG, PSD Layers, PDF Pages) or customize Output Format and quality sliders manually.",
      "Configure Resize Mode (25%–200%, Custom Bounds, Match Width Auto H, or Match Height Auto W) and Resampling filter.",
      "For documents: enable Extract Multi-Page PDFs (with optional 1-indexed page ranges like 1-4, 7) or Extract Visible PSD Layers.",
      "Expand Naming, Affixes & Conflict Policy for custom prefixes/suffixes, folder tree mirroring, EXIF preservation, or Overwrite/Skip/Auto-rename rules.",
    ],
    controls: [
      { name: "Workflow Presets", desc: "Web WEBP (85% WEBP, strips EXIF), Archival PNG (Lvl 6, keeps EXIF), PSD Layers (PNG + layer folders), and PDF Pages (PNG + all pages)." },
      { name: "Alpha Matte Flattening", desc: "When outputting JPEG, BMP, or PDF, pick White, Black, Neutral Gray, or a Custom Hex matte so transparent PNG/PSD pixels never turn black." },
      { name: "PSD Layer Extraction", desc: "Creates a subfolder per PSD and skips children inside hidden parent groups automatically. Toggle Include Composite and Keep Raw Names." },
      { name: "Inline AI Super-Resolution", desc: "Optionally chains Real-ESRGAN, Real-CUGAN, Waifu2x, or SRMD right after conversion (check Force if Vulkan probe needs manual override)." },
    ],
    tips: [
      "Nearest resampling preserves crisp pixel-art edges without blurring; Lanczos gives the sharpest downscaling for photos.",
      "Subfolder Tree Mirroring recreates nested folder hierarchies inside your chosen Output directory instead of flattening all outputs into one folder.",
    ],
  },
  {
    id: "upscaler",
    title: "AI Upscaler Module",
    badge: "Neural 1x–8x",
    jumpTab: "upscaler",
    jumpLabel: "Open Upscaler",
    overview:
      "Runs local NCNN neural super-resolution accelerated by your Vulkan GPU across anime/line-art, illustrations, scanned pages, and photography.",
    steps: [
      "Select an AI Engine matching your artwork type: Real-ESRGAN, Real-CUGAN, Waifu2x, or SRMD.",
      "Pick a Model Variant and Scale Factor (2x, 3x, 4x, plus 1x denoise on Waifu2x CUnet and up to multi-pass 8x workflows).",
      "Adjust Denoise Level (if supported by the chosen engine) and SyncGap (-c) on Real-CUGAN to prevent visible seams along large tile boundaries.",
      "Optionally choose 50% SSAA or a fixed Max Width target (1080p / 1440p / 4K), then set format, suffix, and hardware tile options.",
    ],
    controls: [
      { name: "Real-ESRGAN Variants", desc: "AnimeVideo V3 (fast 2x–4x video/anime), RealESRGAN+ (4x Photo), RealESRGAN+ Anime (4x crisp lines), RealESRNet+ (4x natural), Classic ESRGAN." },
      { name: "Real-CUGAN + SyncGap (-c)", desc: "SE, Pro, and Nose variants tuned for sharp line art. SyncGap 3 (default) or 2 (ultra-precise) synchronizes tile stats to avoid grid seams." },
      { name: "50% SSAA / Target Fit", desc: "Upscales at full neural scale then applies high-precision Lanczos downsampling to 50% SSAA (razor-sharp AA) or 1920/2560/3840px max width." },
      { name: "Keep Original Format", desc: "Saves outputs in each input image's original extension automatically unless you force PNG, JPG, or WEBP." },
    ],
    tips: [
      "For noisy manga scans or compressed web images, start with Real-CUGAN SE (Denoise 0 or 3) or SRMD before raising to 4x.",
      "RealESRGAN+ Anime and AnimeVideo V3 automatically skip extra denoise selectors because noise suppression is baked into the weights.",
    ],
  },
  {
    id: "denoiser",
    title: "AI Denoiser Module",
    badge: "1x Grain Cleanup",
    jumpTab: "denoiser",
    jumpLabel: "Open Denoiser",
    overview:
      "Removes JPEG ringing, mosquito noise, and high-ISO grain at native 1x resolution while letting you blend back original natural texture.",
    steps: [
      "Choose a Denoiser AI: Waifu2x CUnet (anime/digital art), Waifu2x Upconv Photo, Real-CUGAN SE (fast), or SRMD (scans/photos).",
      "Pick a Strength level matched to artifact severity (Levels 0–3 on Waifu2x/Real-CUGAN; -1 to 10 on SRMD).",
      "Dial Grain Preserve from 100% AI down toward 60%–85% AI to blend subtle original grain back and prevent waxy skin or flat skies.",
      "Keep default _denoised suffix or customize naming, format, and conflict handling before launching.",
    ],
    controls: [
      { name: "Waifu2x CUnet / Photo", desc: "CUnet excels at clean cel-shaded lines and gradients; Upconv Photo preserves natural camera detail." },
      { name: "Real-CUGAN Fast SE", desc: "Very fast GPU 1x cleanup with Levels 1–3 for compressed screenshots, CG art, and web comics." },
      { name: "SRMD (Level -1 to 10)", desc: "Fine-grained continuous strength scaling for grainy scanned film, archival prints, and DSLR shadows." },
      { name: "Grain Preserve Slider", desc: "Alpha-blends between original noisy input and AI-cleaned output (10%–100% AI) per pixel cleanly." },
    ],
    tips: [
      "Setting Grain Preserve around 75%–85% AI gives remarkably natural photo noise reduction without sacrificing sharp micro-contrast.",
      "Running Denoiser before a separate Stitch or JPEG/WEBP export keeps compression sizes smaller because random noise no longer wastes bitrate.",
    ],
  },
  {
    id: "janai",
    title: "JaNai AI (Manga & Art)",
    badge: "SPAN / FDAT / ESRGAN",
    jumpTab: "janai",
    jumpLabel: "Open JaNai AI",
    overview:
      "Runs 22 specialized MangaJaNai V1 and IllustrationJaNai V3 Vulkan models (SPAN, FDAT, ESRGAN 2x/4x) via native NCNN with zero CPU fallbacks.",
    steps: [
      "Pick a Model Family matching your artwork: FDAT (transformers for rich illustration), SPAN (ultra-fast 2x illustration), or MangaJaNai ESRGAN (2x/4x screentone & ink scans).",
      "Choose a specific Detail/Denoise or scan resolution preset (1200p–2048p). Models present in local `ncnn/` load immediately; others can be downloaded from GitHub on demand.",
      "Optionally adjust VRAM Tile Size (Auto handles large pages safely), FP16 Vulkan Compute, or 50% SSAA target scaling.",
      "Queue your artwork or manga chapters and launch.",
    ],
    controls: [
      { name: "IllustrationJaNai V3 (FDAT & SPAN)", desc: "FDAT-M / FDAT-XL transformers and compact SPAN-S models tailored for crisp anime illustrations and digital paintings." },
      { name: "MangaJaNai V1 (ESRGAN 2x/4x)", desc: "Resolution-tuned weights (1200p to 2048p) preserving halftone screentones, blacks, and speech-bubble text." },
      { name: "FP16 Vulkan & Smart Alignment", desc: "Automatically applies model-specific reflect padding (2px, 8px, 16px) and falls back to FP32 automatically if a GPU lacks FP16 compute." },
      { name: "On-Demand GitHub Downloads", desc: "Install individual packs directly inside the JaNai AI card or Model Packs manager whenever local copies are absent." },
    ],
    tips: [
      "For FDAT-XL on 4GB–6GB GPUs, keep VRAM Tile Size at Auto (0) or 256px to prevent out-of-memory errors.",
      "Match MangaJaNai 1200p–2048p weights roughly to your source page height for the cleanest screentone preservation.",
    ],
  },
  {
    id: "stitcher",
    title: "Image Stitcher Module",
    badge: "Strips & Grids",
    jumpTab: "stitcher",
    jumpLabel: "Open Stitcher",
    overview:
      "Assembles ordered batches of folders or custom image sets into seamless webtoon vertical strips, horizontal panoramas, or NxM grid sheets.",
    steps: [
      "Click Folder Tree (to auto-group every subfolder into its own stitched output) or drop chapter folders / loose images directly onto the Stitcher pane.",
      "Review live estimated output canvas dimensions & file counts per group; click any thumbnail in a group's filmstrip to preview full-res.",
      "Choose Stitch Direction (Vertical, Horizontal, or Grid 2–20 columns), Alignment, Resize Mode (e.g., Match First / Largest / Smallest), and Stacking Order.",
      "Adjust Panel Gap (negative values down to -200px overlap panels seamlessly), Outer Margin, Canvas Matte, and Output Encoding, then click Stitch.",
    ],
    controls: [
      { name: "Natural vs Alpha Sort", desc: "Natural Order keeps page_2 before page_10 cleanly; also supports Alphabetical A–Z, Modified Time, and Reverse Sequence." },
      { name: "Panel Gap & Outer Margin", desc: "Add crisp gutters (+px), overlap stitched tiles cleanly (negative px), and pad the outer canvas border uniformly (0–200px)." },
      { name: "Canvas Matte", desc: "Fill extra margins or alignment gaps with Transparent PNG alpha, White, Black, or a Custom Hex color picker." },
      { name: "Pixel Limit Safe Chunking", desc: "Automatically splits ultra-tall strips safely when dimensions exceed JPEG (65,500px) or WEBP (16,383px) encoder limits." },
    ],
    tips: [
      "For webtoon episodes split across slices, use Vertical (Top to Bottom), Match Width/Match First, Natural Order, and 0px gap.",
      "If WEBP splits tall strips into multiple parts unexpectedly and you want one unbroken image file, switch Output Format to PNG.",
    ],
  },
  {
    id: "inspector",
    title: "Compare & Preview",
    badge: "Zoom & Pan Inspector",
    jumpTab: "converter",
    jumpLabel: "Open Workspace",
    overview:
      "Inspect subtle upscaling, denoising, compression, and color-matte differences pixel-for-pixel in the Before / After Visual Inspector or Quick Preview.",
    steps: [
      "Open the inspector via Compare Before / After on a finished job capsule, the top dock Compare button, or shortcut Ctrl + B.",
      "Use the mouse scroll wheel over any spot to zoom from 50% up to 800% anchored directly under your cursor.",
      "Click and drag anywhere on the image canvas to pan both Before and After layers in lockstep.",
      "Grab the center ⇄ divider handle to sweep across Before vs After at any zoom/pan offset; double-click the divider to center it, or double-click the image to reset.",
    ],
    controls: [
      { name: "Scroll Wheel Zoom", desc: "Smooth cursor-anchored 50%–800% magnification across both Before / After Compare and Quick Full Preview." },
      { name: "Click-Drag Picture Pan", desc: "Drag the canvas freely with left-mouse button to inspect edges, eyes, typography, or film grain while zoomed." },
      { name: "Split Divider ⇄", desc: "Drag left/right independently of image pan; stage-level clipping keeps the split exact at every magnification." },
      { name: "Batch Pair Stepper", desc: "Use top ← / → buttons to step through all processed pairs from your latest batch, and Reset to snap back to 100% centered." },
    ],
    tips: [
      "Zoom to 300%–400% over fine hair, halftone dots, or text to compare Real-ESRGAN vs Real-CUGAN edge crispness.",
      "Need to compare outputs from an older batch? Queue the files again or run a single test image to populate the Compare buffer.",
    ],
  },
  {
    id: "hardware",
    title: "GPU, Shortcuts & FAQ",
    badge: "Tuning & Keys",
    jumpTab: "hardware",
    jumpLabel: "Inspect GPUs",
    overview:
      "Tune Vulkan NCNN GPU memory, threading, and TTA ensemble passes, or use keyboard shortcuts to switch tools quickly.",
    steps: [
      "Click the top-right GPU status pill (or Inspect GPUs here) to verify detected physical Vulkan GPUs and bundled AI engine binaries.",
      "Under Hardware, Threads & Naming in Upscaler/Denoiser, keep VRAM Tile Size at Auto (0) unless experiencing GPU memory pressure, then lower to 200, 100, or 64.",
      "Choose Thread Spec (-j): 1:2:2 (balanced default), 2:4:4 (fast NVMe + high VRAM), or 1:1:1 (lowest RAM/VRAM footprint).",
      "Toggle TTA 8-Pass Ensemble only for hero stills requiring maximum noise/aliasing suppression (~8× slower than single-pass).",
    ],
    controls: [
      { name: "Keyboard Shortcuts", desc: "Ctrl+1 Converter • Ctrl+2 AI Upscaler • Ctrl+3 AI Denoiser • Ctrl+4 JaNai AI • Ctrl+5 Stitcher • Ctrl+6 Settings & Manuals • Ctrl+B Before/After Compare." },
      { name: "Multi-GPU & CPU (-1)", desc: "Select GPU 0, GPU 1, etc. for laptops with dual iGPU/dGPU setups, or force CPU Fallback (-1) for compatibility debugging." },
      { name: "Preferences & Themes", desc: "Switch between 6 color themes and persist default JPEG/WEBP/PNG/EXIF/PDF settings in local settings.json." },
      { name: "Activity Logs & Updates", desc: "Filter live INFO/SUCCESS/WARNING/ERROR/TERMINAL logs, export imagetool_logs.txt, and check GitHub releases for GuptaAman777/psd-converter." },
    ],
    tips: [
      "If an AI upscale fails on an enormous input (>8000px), reduce VRAM Tile Size from Auto (0) down to 100 or 64 and retry.",
      "100% local & offline: zero images, PSDs, PDFs, or filenames ever leave your machine.",
    ],
  },
];

export default function SettingsWorkspace({
  bootstrap,
  activeTheme,
  onChangeTheme,
  onSaveSettings,
  logs,
  onClearLogs,
  onJumpToTab,
  onOpenGpuInfo,
  onOpenModelManager,
}) {
  const [subTab, setSubTab] = useState("prefs");
  const [guideIdx, setGuideIdx] = useState(0);
  const [manualQuery, setManualQuery] = useState("");
  const [logLevel, setLogLevel] = useState("ALL");
  const [logSearch, setLogSearch] = useState("");
  const [updateInfo, setUpdateInfo] = useState(null);
  const [checkingUpdates, setCheckingUpdates] = useState(false);

  const saved = bootstrap?.settings || {};
  const [jpegQ, setJpegQ] = useState(saved.jpeg_quality || "High");
  const [webpQ, setWebpQ] = useState(saved.webp_quality || "High");
  const [pngC, setPngC] = useState(saved.png_compression || "Normal");
  const [exifDefault, setExifDefault] = useState(saved.preserve_exif !== false);
  const [pdfDpi, setPdfDpi] = useState(saved.pdf_dpi || "150 DPI");
  const [pdfQ, setPdfQ] = useState(saved.pdf_quality || "High");
  const [confirmInstall, setConfirmInstall] = useState(saved.confirm_model_install !== false);
  const [confirmDelete, setConfirmDelete] = useState(saved.confirm_model_delete !== false);
  const [progressLiquidGlass, setProgressLiquidGlass] = useState(saved.progress_liquid_glass !== false);

  useEffect(() => {
    if (!bootstrap?.settings) return;
    const s = bootstrap.settings;
    if (s.jpeg_quality) setJpegQ(s.jpeg_quality);
    if (s.webp_quality) setWebpQ(s.webp_quality);
    if (s.png_compression) setPngC(s.png_compression);
    if (typeof s.preserve_exif === "boolean") setExifDefault(s.preserve_exif);
    if (s.pdf_dpi) setPdfDpi(s.pdf_dpi);
    if (s.pdf_quality) setPdfQ(s.pdf_quality);
    if (typeof s.confirm_model_install === "boolean") setConfirmInstall(s.confirm_model_install);
    if (typeof s.confirm_model_delete === "boolean") setConfirmDelete(s.confirm_model_delete);
    if (typeof s.progress_liquid_glass === "boolean") setProgressLiquidGlass(s.progress_liquid_glass);
  }, [bootstrap?.settings]);

  const savePref = (patch) => {
    onSaveSettings(patch);
  };

  const checkUpdates = async () => {
    setCheckingUpdates(true);
    try {
      const res = await apiGet("/api/updates/check");
      setUpdateInfo(res);
    } catch (e) {
      setUpdateInfo({ error: e.message });
    } finally {
      setCheckingUpdates(false);
    }
  };

  useEffect(() => {
    if (subTab === "updates" && !updateInfo) {
      checkUpdates();
    }
  }, [subTab]);

  const filteredLogs = (logs || []).filter((l) => {
    if (logLevel !== "ALL" && l.level !== logLevel) return false;
    if (logSearch.trim()) {
      const q = logSearch.trim().toLowerCase();
      return (
        String(l.message || "").toLowerCase().includes(q) ||
        String(l.level || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const exportLogsTxt = () => {
    const content = filteredLogs.map((l) => `[${l.timestamp}] [${l.level}] ${l.message}`).join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "imagetool_logs.txt";
    a.click();
  };

  const matchedManualIndices = useMemo(() => {
    const q = manualQuery.trim().toLowerCase();
    if (!q) return new Set(MANUAL_SECTIONS.map((_, i) => i));
    const hits = new Set();
    MANUAL_SECTIONS.forEach((sec, idx) => {
      const hay = [
        sec.title,
        sec.badge,
        sec.overview,
        ...sec.steps,
        ...sec.controls.flatMap((c) => [c.name, c.desc]),
        ...sec.tips,
      ]
        .join(" ")
        .toLowerCase();
      if (hay.includes(q)) hits.add(idx);
    });
    return hits;
  }, [manualQuery]);

  useEffect(() => {
    if (manualQuery.trim() && !matchedManualIndices.has(guideIdx) && matchedManualIndices.size > 0) {
      setGuideIdx(Array.from(matchedManualIndices)[0]);
    }
  }, [manualQuery, matchedManualIndices, guideIdx]);

  const activeGuide = MANUAL_SECTIONS[guideIdx] || MANUAL_SECTIONS[0];

  return (
    <div className="liquid-panel rounded-2xl sm:rounded-3xl p-3 sm:p-5 lg:h-full flex flex-col gap-3 sm:gap-4 overflow-hidden">
      {/* Sub-navigation Segmented Pill */}
      <div className="flex flex-wrap items-center gap-1 p-1 rounded-2xl sm:rounded-full bg-black/30 border border-white/10 w-full sm:w-fit">
        {[
          { id: "prefs", label: "Preferences & Themes", Icon: Palette },
          { id: "updates", label: "Updates", Icon: RefreshCw },
          { id: "logs", label: "Activity Logs", Icon: Terminal },
          { id: "about", label: "Manual & About", Icon: BookOpen },
        ].map(({ id, label, Icon }) => {
          const active = subTab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setSubTab(id)}
              className={`relative px-3 sm:px-4 py-1.5 rounded-full text-[11.5px] sm:text-[12px] font-semibold flex items-center gap-1.5 cursor-pointer ${
                active ? "text-white" : "text-white/60 hover:text-white"
              }`}
            >
              {active && (
                <motion.div
                  layoutId="settingsSubTabPill"
                  transition={{ type: "spring", stiffness: 450, damping: 32 }}
                  className="absolute inset-0 rounded-full bg-[var(--accent)] shadow"
                />
              )}
              <Icon className="w-3.5 h-3.5 relative z-10" />
              <span className="relative z-10">{label}</span>
            </button>
          );
        })}
      </div>

      {/* Body */}
      <div className="lg:flex-1 lg:min-h-0 lg:overflow-y-auto lg:pr-1 space-y-3 sm:space-y-3.5">
        {subTab === "prefs" && (
          <>
            <GlassCard title="Appearance & Themes">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
                {Object.entries(LIQUID_THEMES).map(([name, pal]) => {
                  const active = activeTheme === name;
                  return (
                    <button
                      key={name}
                      type="button"
                      onClick={() => onChangeTheme(name)}
                      className={`liquid-card rounded-2xl p-3 text-left flex items-center justify-between gap-2 cursor-pointer ${
                        active ? "ring-2 ring-[var(--accent)]" : ""
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span
                          className="w-5 h-5 rounded-full shrink-0 border border-white/30 shadow-md"
                          style={{
                            background: `linear-gradient(135deg, ${pal.heroStart || pal.accentHover}, ${pal.heroEnd || pal.accent})`,
                            boxShadow: `0 0 12px ${pal.accentSoft}`,
                          }}
                        />
                        <span className="text-[12.5px] font-semibold text-white truncate">{name}</span>
                      </div>
                      {active && <Check className="w-4 h-4 text-[var(--accent-hover)] shrink-0" />}
                    </button>
                  );
                })}
              </div>

              <div className="pt-2.5 mt-1 border-t border-white/10">
                <GlassSwitch
                  checked={progressLiquidGlass}
                  onChange={(val) => {
                    setProgressLiquidGlass(val);
                    savePref({ progress_liquid_glass: val });
                  }}
                  label="Progress Bar Liquid Glass Effect"
                  sublabel="Use translucent frosted glass on floating progress & completion cards (disable for solid opaque)"
                />
              </div>
            </GlassCard>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              <GlassCard title="Default Image Encoding">
                <SettingRow label="JPEG Preset">
                  <select
                    value={jpegQ}
                    onChange={(e) => {
                      setJpegQ(e.target.value);
                      savePref({ jpeg_quality: e.target.value });
                    }}
                    className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
                  >
                    {["Maximum", "High", "Medium", "Low"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </SettingRow>
                <SettingRow label="WEBP Preset">
                  <select
                    value={webpQ}
                    onChange={(e) => {
                      setWebpQ(e.target.value);
                      savePref({ webp_quality: e.target.value });
                    }}
                    className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
                  >
                    {["Maximum", "High", "Medium", "Low"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </SettingRow>
                <SettingRow label="PNG Compress">
                  <select
                    value={pngC}
                    onChange={(e) => {
                      setPngC(e.target.value);
                      savePref({ png_compression: e.target.value });
                    }}
                    className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
                  >
                    {["Maximum", "Normal", "Fast", "None"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </SettingRow>
                <GlassSwitch
                  checked={exifDefault}
                  onChange={(val) => {
                    setExifDefault(val);
                    savePref({ preserve_exif: val });
                  }}
                  label="Auto-Orient & Preserve EXIF by Default"
                />
              </GlassCard>

              <GlassCard title="PDF Rasterizer Defaults">
                <SettingRow label="PDF DPI">
                  <select
                    value={pdfDpi}
                    onChange={(e) => {
                      setPdfDpi(e.target.value);
                      savePref({ pdf_dpi: e.target.value });
                    }}
                    className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
                  >
                    {["72 DPI", "150 DPI", "300 DPI", "600 DPI"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </SettingRow>
                <SettingRow label="PDF Quality">
                  <select
                    value={pdfQ}
                    onChange={(e) => {
                      setPdfQ(e.target.value);
                      savePref({ pdf_quality: e.target.value });
                    }}
                    className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
                  >
                    {["High", "Medium", "Low"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </SettingRow>
              </GlassCard>
            </div>

            {onOpenModelManager && (
              <GlassCard
                title="Downloadable AI Model Packs & Confirmations"
                rightHeader={
                  <button
                    type="button"
                    onClick={onOpenModelManager}
                    className="liquid-hero-btn rounded-full px-3.5 py-1 text-[11.5px] font-semibold flex items-center gap-1.5 cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Manage Extra Models</span>
                  </button>
                }
              >
                <div className="text-[12px] text-white/70 leading-relaxed">
                  Download optional NCNN models on demand (4x-UltraSharp, 4x-Remacri, Digital Art 4x, 4x-Nomos8kSC,
                  Real-ESRGAN General v3, 4x-NMKD Siax, Uniscale Restore) directly into your local models folder for instant use in
                  the AI Upscaler and Converter.{" "}
                  <span className="text-white font-semibold">
                    {(bootstrap?.model_catalog || []).filter((m) => m.installed).length} of{" "}
                    {(bootstrap?.model_catalog || []).length} optional packs currently installed.
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-white/10">
                  <GlassSwitch
                    checked={confirmInstall}
                    onChange={(val) => {
                      setConfirmInstall(val);
                      savePref({ confirm_model_install: val });
                    }}
                    label="Confirm Before Installing Models"
                    sublabel="Show confirmation prompt when downloading"
                  />
                  <GlassSwitch
                    checked={confirmDelete}
                    onChange={(val) => {
                      setConfirmDelete(val);
                      savePref({ confirm_model_delete: val });
                    }}
                    label="Confirm Before Deleting Models"
                    sublabel="Show confirmation prompt when removing"
                  />
                </div>
              </GlassCard>
            )}
          </>
        )}

        {subTab === "updates" && (
          <GlassCard title="Software Updates & GitHub Releases">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[14px] font-bold text-white">
                  Current Version: v{bootstrap?.version}
                </div>
                <div className="text-[12px] text-white/60 mt-0.5">
                  {checkingUpdates
                    ? "Checking GuptaAman777/psd-converter releases..."
                    : updateInfo?.update_available
                    ? `Update available: v${updateInfo.latest_version}`
                    : `Latest on GitHub: v${updateInfo?.latest_version || bootstrap?.version} (Up to date)`}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={checkUpdates}
                  className="liquid-hero-btn rounded-full px-4 py-1.5 text-[12px] font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${checkingUpdates ? "animate-spin" : ""}`} />
                  <span>Check Now</span>
                </button>
                <button
                  type="button"
                  onClick={() => openExternalUrl("https://github.com/GuptaAman777/psd-converter/releases")}
                  className="liquid-pill-btn rounded-full px-4 py-1.5 text-[12px] font-semibold cursor-pointer"
                >
                  Open Releases
                </button>
              </div>
            </div>

            {updateInfo?.release_notes && (
              <pre className="rounded-2xl bg-black/40 border border-white/10 p-3.5 text-[12px] text-white/75 whitespace-pre-wrap max-h-64 overflow-y-auto font-mono">
                {updateInfo.release_notes}
              </pre>
            )}
          </GlassCard>
        )}

        {subTab === "logs" && (
          <GlassCard title="Streaming Activity Console">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                {["ALL", "INFO", "SUCCESS", "WARNING", "ERROR", "TERMINAL"].map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => setLogLevel(lvl)}
                    className={`px-2.5 py-1 rounded-full text-[11px] font-semibold cursor-pointer ${
                      logLevel === lvl
                        ? "bg-[var(--accent)] text-white"
                        : "liquid-pill-btn text-white/65"
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Search logs..."
                  value={logSearch}
                  onChange={(e) => setLogSearch(e.target.value)}
                  className="liquid-input rounded-full px-3 py-1 text-[12px] w-44"
                />
                <button
                  type="button"
                  onClick={() => navigator.clipboard?.writeText(filteredLogs.map((l) => `[${l.timestamp}] [${l.level}] ${l.message}`).join("\n"))}
                  className="liquid-pill-btn rounded-full px-2.5 py-1 text-[11px] flex items-center gap-1 cursor-pointer"
                >
                  <Copy className="w-3 h-3" /> Copy
                </button>
                <button
                  type="button"
                  onClick={exportLogsTxt}
                  className="liquid-pill-btn rounded-full px-2.5 py-1 text-[11px] flex items-center gap-1 cursor-pointer"
                >
                  <Download className="w-3 h-3" /> TXT
                </button>
                <button
                  type="button"
                  onClick={() => {
                    apiPost("/api/logs/clear", {});
                    onClearLogs();
                  }}
                  className="liquid-pill-btn rounded-full px-2.5 py-1 text-[11px] text-rose-300 flex items-center gap-1 cursor-pointer"
                >
                  <Trash2 className="w-3 h-3" /> Clear
                </button>
              </div>
            </div>

            <div className="rounded-2xl bg-black/45 border border-white/10 p-3 h-80 overflow-y-auto font-mono text-[11.5px] space-y-1">
              {filteredLogs.length === 0 ? (
                <div className="text-white/40 py-10 text-center">No log events match filter.</div>
              ) : (
                filteredLogs.map((l, i) => (
                  <div key={i} className="leading-snug">
                    <span className="text-white/40">[{l.timestamp}]</span>{" "}
                    <span
                      className={`font-bold ${
                        l.level === "ERROR"
                          ? "text-rose-400"
                          : l.level === "WARNING"
                          ? "text-amber-300"
                          : l.level === "SUCCESS"
                          ? "text-emerald-400"
                          : "text-sky-300"
                      }`}
                    >
                      [{l.level}]
                    </span>{" "}
                    <span className="text-white/85">{l.message}</span>
                  </div>
                ))
              )}
            </div>
          </GlassCard>
        )}

        {subTab === "about" && (
          <>
            <GlassCard>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-1.5 max-w-2xl">
                  <div className="flex items-center gap-2.5">
                    <span className="text-[20px] font-extrabold text-white tracking-tight">
                      ImageTool — PSD & AI Image Suite
                    </span>
                    <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[var(--accent)] text-white">
                      v{bootstrap?.version}
                    </span>
                  </div>
                  <p className="text-[12.5px] text-white/70 leading-relaxed">
                    Open-source desktop batch image processor from{" "}
                    <span className="text-white font-semibold">GuptaAman777/psd-converter</span>. Combines Photoshop{" "}
                    <code>.psd</code> layer extraction, multi-page <code>.pdf</code> rasterization, GPU-accelerated
                    Vulkan NCNN AI Super-Resolution & Denoising, strip/grid image stitching, and split-screen visual
                    comparison inside a hardware-accelerated desktop interface.
                  </p>
                  <div className="text-[14px] font-bold text-white pt-1">Made by GuptaAman777</div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => openExternalUrl("https://github.com/GuptaAman777/psd-converter")}
                    className="liquid-pill-btn rounded-full px-3.5 py-1.5 text-[12px] font-semibold flex items-center gap-1.5 cursor-pointer"
                  >
                    <Github className="w-3.5 h-3.5" />
                    <span>Repository</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => openExternalUrl("https://github.com/GuptaAman777/psd-converter/releases")}
                    className="liquid-pill-btn rounded-full px-3.5 py-1.5 text-[12px] font-semibold flex items-center gap-1.5 cursor-pointer"
                  >
                    <Rocket className="w-3.5 h-3.5" />
                    <span>Releases (v5.1–v7.5)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => openExternalUrl("https://github.com/GuptaAman777")}
                    className="liquid-hero-btn rounded-full px-4 py-1.5 text-[12px] font-semibold cursor-pointer"
                  >
                    @GuptaAman777
                  </button>
                </div>
              </div>
            </GlassCard>

            <GlassCard title="Project Architecture & Stack">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px]">
                <div className="rounded-xl bg-black/25 border border-white/10 p-3">
                  <div className="font-bold text-[var(--accent-hover)] mb-1">GPU UI & Server</div>
                  <div className="text-white/75">
                    React 19 • Vite • Tailwind CSS v4 • Framer Motion • Edge WebView2 GPU • FastAPI
                  </div>
                </div>
                <div className="rounded-xl bg-black/25 border border-white/10 p-3">
                  <div className="font-bold text-[var(--accent-hover)] mb-1">Neural NCNN Engines</div>
                  <div className="text-white/75">
                    Real-ESRGAN (x4plus, AnimeVideoV3) • Real-CUGAN • Waifu2x • SRMD • MangaJaNai / IllustrationJaNai (FDAT, SPAN)
                  </div>
                </div>
                <div className="rounded-xl bg-black/25 border border-white/10 p-3">
                  <div className="font-bold text-[var(--accent-hover)] mb-1">Imaging Core</div>
                  <div className="text-white/75">
                    Python 3.13 • Pillow • ncnn • numpy • psd-tools • PyMuPDF • psutil
                  </div>
                </div>
              </div>
            </GlassCard>

            <GlassCard
              title="Manuals & User Guide"
              rightHeader={
                <div className="relative w-44 sm:w-56">
                  <Search className="w-3.5 h-3.5 text-white/45 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Search manual..."
                    value={manualQuery}
                    onChange={(e) => setManualQuery(e.target.value)}
                    className="liquid-input w-full rounded-full pl-8 pr-3 py-1 text-[11.5px]"
                  />
                </div>
              }
            >
              <div className="flex flex-wrap gap-1.5 mb-3">
                {MANUAL_SECTIONS.map((m, idx) => {
                  const isMatch = matchedManualIndices.has(idx);
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setGuideIdx(idx)}
                      className={`rounded-full px-3 sm:px-3.5 py-1.5 text-[11.5px] sm:text-[12px] font-semibold cursor-pointer transition-opacity ${
                        guideIdx === idx
                          ? "bg-[var(--accent)] text-white shadow"
                          : "liquid-pill-btn text-white/75"
                      } ${!isMatch ? "opacity-35" : ""}`}
                    >
                      {m.title}
                    </button>
                  );
                })}
              </div>

              {manualQuery.trim() && matchedManualIndices.size === 0 ? (
                <div className="rounded-2xl bg-black/30 border border-white/10 p-5 text-center text-[12.5px] text-white/55">
                  No manual sections matched &ldquo;{manualQuery}&rdquo;. Try keywords like{" "}
                  <span className="text-white/80 font-semibold">SSAA</span>,{" "}
                  <span className="text-white/80 font-semibold">PSD</span>,{" "}
                  <span className="text-white/80 font-semibold">zoom</span>, or{" "}
                  <span className="text-white/80 font-semibold">Ctrl</span>.
                </div>
              ) : (
                <div className="rounded-2xl bg-black/30 border border-white/10 p-3.5 sm:p-5 space-y-4">
                  {/* Section Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[15.5px] sm:text-[16px] font-bold text-white">{activeGuide.title}</span>
                        <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent-hover)] border border-white/10">
                          {activeGuide.badge}
                        </span>
                      </div>
                      <p className="text-[12px] sm:text-[12.5px] text-white/75 mt-1.5 leading-relaxed">
                        {activeGuide.overview}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        if (activeGuide.jumpTab === "hardware") onOpenGpuInfo();
                        else onJumpToTab(activeGuide.jumpTab);
                      }}
                      className="liquid-hero-btn rounded-full px-4 py-1.5 text-[12px] font-semibold shrink-0 cursor-pointer self-start sm:self-center"
                    >
                      {activeGuide.jumpLabel || "Open"}
                    </button>
                  </div>

                  {/* Step-by-Step Workflow + Key Controls Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-[11.5px] font-bold uppercase tracking-wider text-[var(--accent-hover)]">
                        <ListOrdered className="w-3.5 h-3.5" />
                        <span>Step-by-Step Workflow</span>
                      </div>
                      <div className="space-y-2">
                        {activeGuide.steps.map((step, i) => (
                          <div
                            key={i}
                            className="flex items-start gap-2.5 rounded-xl bg-white/[0.04] border border-white/[0.07] p-2.5 text-[12px] text-white/85 leading-relaxed"
                          >
                            <span className="w-5 h-5 rounded-full bg-[var(--accent)] text-white text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                              {i + 1}
                            </span>
                            <span>{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-[11.5px] font-bold uppercase tracking-wider text-[var(--accent-hover)]">
                        <SlidersHorizontal className="w-3.5 h-3.5" />
                        <span>Parameters & Options Reference</span>
                      </div>
                      <div className="space-y-2">
                        {activeGuide.controls.map((ctrl) => (
                          <div
                            key={ctrl.name}
                            className="rounded-xl bg-white/[0.04] border border-white/[0.07] p-2.5"
                          >
                            <div className="text-[12px] font-bold text-white">{ctrl.name}</div>
                            <div className="text-[11.5px] text-white/70 mt-0.5 leading-relaxed">{ctrl.desc}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Pro Tips & Keyboard Shortcuts Strip */}
                  <div className="rounded-xl bg-[var(--accent-soft)]/50 border border-[var(--accent)]/25 p-3 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-[var(--accent-hover)]">
                      <Lightbulb className="w-3.5 h-3.5" />
                      <span>Pro Tips & Troubleshooting</span>
                    </div>
                    <ul className="space-y-1 text-[11.5px] text-white/80 list-disc pl-4">
                      {activeGuide.tips.map((tip, i) => (
                        <li key={i} className="leading-relaxed">{tip}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Always-handy Global Shortcut Strip */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-white/65 border-t border-white/10">
                    <span className="flex items-center gap-1 font-semibold text-white/80">
                      <Keyboard className="w-3.5 h-3.5 text-[var(--accent-hover)]" /> Shortcuts:
                    </span>
                    {[
                      ["Ctrl+1", "Converter"],
                      ["Ctrl+2", "Upscaler"],
                      ["Ctrl+3", "Denoiser"],
                      ["Ctrl+4", "JaNai AI"],
                      ["Ctrl+5", "Stitcher"],
                      ["Ctrl+6", "Settings"],
                      ["Ctrl+B", "Compare"],
                    ].map(([k, lbl]) => (
                      <span
                        key={k}
                        className="px-2 py-0.5 rounded-md bg-white/[0.07] border border-white/10 text-white/80"
                      >
                        <code className="font-bold text-[var(--accent-hover)]">{k}</code> {lbl}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </GlassCard>
          </>
        )}
      </div>
    </div>
  );
}
