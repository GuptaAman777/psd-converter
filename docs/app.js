(() => {
  const THEMES = {
    blue: {
      name: "Blue (Default)",
      accent: "#0a84ff",
      accentHover: "#3ea0ff",
      accentSoft: "rgba(10, 132, 255, 0.22)",
      accentGlow: "rgba(10, 132, 255, 0.44)",
      heroStart: "#3ea0ff",
      heroEnd: "#0a84ff",
      bgDeep: "#060a14",
      orb1: "rgba(10, 132, 255, 0.36)",
      orb2: "rgba(94, 92, 230, 0.28)",
      orb3: "rgba(56, 189, 248, 0.18)",
      dockBg: "linear-gradient(155deg, rgba(34, 41, 64, 0.66), rgba(14, 18, 30, 0.56))",
      panelBg: "linear-gradient(165deg, rgba(28, 34, 54, 0.62), rgba(14, 17, 29, 0.52))",
      cardBg: "linear-gradient(160deg, rgba(255, 255, 255, 0.068), rgba(255, 255, 255, 0.024))",
      glassBorder: "rgba(255, 255, 255, 0.13)",
    },
    crimson: {
      name: "Red (Crimson)",
      accent: "#ff375f",
      accentHover: "#ff5c7c",
      accentSoft: "rgba(255, 55, 95, 0.22)",
      accentGlow: "rgba(255, 55, 95, 0.44)",
      heroStart: "#ff5c7c",
      heroEnd: "#ff375f",
      bgDeep: "#10060a",
      orb1: "rgba(255, 55, 95, 0.36)",
      orb2: "rgba(191, 90, 242, 0.24)",
      orb3: "rgba(255, 100, 130, 0.16)",
      dockBg: "linear-gradient(155deg, rgba(34, 41, 64, 0.66), rgba(14, 18, 30, 0.56))",
      panelBg: "linear-gradient(165deg, rgba(28, 34, 54, 0.62), rgba(14, 17, 29, 0.52))",
      cardBg: "linear-gradient(160deg, rgba(255, 255, 255, 0.068), rgba(255, 255, 255, 0.024))",
      glassBorder: "rgba(255, 255, 255, 0.13)",
    },
    oled: {
      name: "Black (OLED Dark)",
      accent: "#27272e",
      accentHover: "#d4d4d8",
      accentSoft: "rgba(255, 255, 255, 0.10)",
      accentGlow: "rgba(255, 255, 255, 0.18)",
      heroStart: "#32323c",
      heroEnd: "#16161b",
      bgDeep: "#000000",
      orb1: "rgba(255, 255, 255, 0.032)",
      orb2: "rgba(210, 210, 220, 0.02)",
      orb3: "rgba(150, 150, 165, 0.016)",
      dockBg: "linear-gradient(155deg, rgba(9, 9, 11, 0.90), rgba(0, 0, 0, 0.96))",
      panelBg: "linear-gradient(165deg, rgba(6, 6, 8, 0.90), rgba(0, 0, 0, 0.96))",
      cardBg: "linear-gradient(160deg, rgba(255, 255, 255, 0.022), rgba(0, 0, 0, 0.80))",
      glassBorder: "rgba(255, 255, 255, 0.10)",
    },
    purple: {
      name: "Purple (Cyberpunk)",
      accent: "#bf5af2",
      accentHover: "#d47fff",
      accentSoft: "rgba(191, 90, 242, 0.22)",
      accentGlow: "rgba(191, 90, 242, 0.46)",
      heroStart: "#d47fff",
      heroEnd: "#bf5af2",
      bgDeep: "#0a0614",
      orb1: "rgba(191, 90, 242, 0.38)",
      orb2: "rgba(10, 132, 255, 0.26)",
      orb3: "rgba(255, 55, 95, 0.18)",
      dockBg: "linear-gradient(155deg, rgba(34, 41, 64, 0.66), rgba(14, 18, 30, 0.56))",
      panelBg: "linear-gradient(165deg, rgba(28, 34, 54, 0.62), rgba(14, 17, 29, 0.52))",
      cardBg: "linear-gradient(160deg, rgba(255, 255, 255, 0.068), rgba(255, 255, 255, 0.024))",
      glassBorder: "rgba(255, 255, 255, 0.13)",
    },
    emerald: {
      name: "Green (Emerald)",
      accent: "#30d158",
      accentHover: "#52e378",
      accentSoft: "rgba(48, 209, 88, 0.22)",
      accentGlow: "rgba(48, 209, 88, 0.42)",
      heroStart: "#52e378",
      heroEnd: "#30d158",
      bgDeep: "#050f0a",
      orb1: "rgba(48, 209, 88, 0.34)",
      orb2: "rgba(100, 210, 255, 0.22)",
      orb3: "rgba(48, 176, 199, 0.16)",
      dockBg: "linear-gradient(155deg, rgba(34, 41, 64, 0.66), rgba(14, 18, 30, 0.56))",
      panelBg: "linear-gradient(165deg, rgba(28, 34, 54, 0.62), rgba(14, 17, 29, 0.52))",
      cardBg: "linear-gradient(160deg, rgba(255, 255, 255, 0.068), rgba(255, 255, 255, 0.024))",
      glassBorder: "rgba(255, 255, 255, 0.13)",
    },
    amber: {
      name: "Amber (Sunset)",
      accent: "#ff9f0a",
      accentHover: "#ffb340",
      accentSoft: "rgba(255, 159, 10, 0.22)",
      accentGlow: "rgba(255, 159, 10, 0.42)",
      heroStart: "#ffb340",
      heroEnd: "#ff9f0a",
      bgDeep: "#120b05",
      orb1: "rgba(255, 159, 10, 0.34)",
      orb2: "rgba(255, 69, 58, 0.24)",
      orb3: "rgba(255, 214, 10, 0.16)",
      dockBg: "linear-gradient(155deg, rgba(34, 41, 64, 0.66), rgba(14, 18, 30, 0.56))",
      panelBg: "linear-gradient(165deg, rgba(28, 34, 54, 0.62), rgba(14, 17, 29, 0.52))",
      cardBg: "linear-gradient(160deg, rgba(255, 255, 255, 0.068), rgba(255, 255, 255, 0.024))",
      glassBorder: "rgba(255, 255, 255, 0.13)",
    },
  };

  const WORKSPACES = {
    janai: {
      title: "JaNai AI (Manga & Illustration)",
      shortcut: "Shortcut: Ctrl + 4",
      summary:
        "Vulkan-accelerated Python NCNN super-resolution purpose-built for manga screentones, line art, and digital illustrations across 22 on-demand models.",
      bullets: [
        "Auto Detect analyzes grayscale vs. chroma fraction, snaps B&W manga pages to 1200p–2048p height tiers, and pairs color artwork with IllustrationJaNai V3.",
        "Queue Routing Inspector previews exact per-file analysis metrics and pass-by-pass model chains before running a batch.",
        "5 built-in presets + persistent 2-pass Custom Workflow builder with reflect-padded tile inference and 16-bit PNG normalization.",
      ],
    },
    converter: {
      title: "Batch Converter, PSD & PDF Suite",
      shortcut: "Shortcut: Ctrl + 1",
      summary:
        "Fast batch conversion between PNG, JPEG, WebP, BMP, TIFF, GIF, PSD, and multi-page PDF documents with strict color/alpha safety.",
      bullets: [
        "Extracts visible Photoshop PSD layers into organized per-document folders while automatically skipping hidden parent groups.",
        "Rasters multi-page PDFs at 72–600 DPI with custom 1-indexed page ranges (e.g. 1-4, 7).",
        "Workflow presets (Web WEBP, Archival PNG, PSD Layers, PDF Pages), hex alpha matte flattening, subfolder mirroring, and conflict policies.",
      ],
    },
    upscaler: {
      title: "Multi-Engine AI Upscaler",
      shortcut: "Shortcut: Ctrl + 2",
      summary:
        "Hardware-accelerated 2x to 8x super-resolution with Real-ESRGAN, Upscayl (2025-12-07), Real-CUGAN SyncGap, Waifu2x 2025, and SRMD.",
      bullets: [
        "Supports 11 optional downloadable community NCNN packs (4x-UltraSharp, 4x-Remacri, Digital Art 4x, Nomos8kSC, Uniscale Restore).",
        "Optional SSAA post-resize downsampling and lossless two-pass 8x scaling.",
        "EXIF auto-orientation staging, alpha preservation, multi-GPU selection, and safe automatic CPU fallback.",
      ],
    },
    denoiser: {
      title: "AI Denoiser & Grain Preserve",
      shortcut: "Shortcut: Ctrl + 3",
      summary:
        "1x compression-artifact and sensor-noise removal powered by Waifu2x 2025 (cunet/upconv7), Real-CUGAN, and SRMD.",
      bullets: [
        "Adjustable Grain Preserve blending mixes controlled original micro-texture back to prevent plastic over-smoothing.",
        "Tune noise levels independently (-1 to 10 on SRMD, -1 to 3 on Waifu2x/Real-CUGAN) without changing output resolution.",
        "Full batch queue support with live fractional-progress ETA smoothing.",
      ],
    },
    stitcher: {
      title: "High-Capacity Strip & Grid Stitcher",
      shortcut: "Shortcut: Ctrl + 5",
      summary:
        "Combine webtoon strips, manga chapters, or sprite sheets into seamless vertical strips, horizontal panoramas, or NxM grids.",
      bullets: [
        "Grouped folder scanner stages chapters independently with live output dimension estimates.",
        "Supports negative overlap gaps, outer margins, custom hex mattes, and natural / alpha / mtime sorting.",
        "Automatic WebP (16,300px) and JPEG (65,500px) chunk splitting avoids codec dimension failures.",
      ],
    },
    compare: {
      title: "Multi-Batch Compare & Settings",
      shortcut: "Shortcut: Ctrl + 6",
      summary:
        "Inspect output fidelity across multiple batches with 50%–800% cursor-anchored zoom and customizable translucent or opaque HUD surfaces.",
      bullets: [
        "Compare Inspector retains results across multiple conversion/upscale runs with instant batch switching and missing-file cleanup.",
        "Synchronized click-drag pan and independent split divider compare before/after at pixel level.",
        "Toggle translucent vs. opaque Progress HUD appearance alongside 6 live color themes.",
      ],
    },
  };

  function applyTheme(key) {
    const t = THEMES[key] || THEMES.blue;
    const root = document.documentElement.style;
    root.setProperty("--accent", t.accent);
    root.setProperty("--accent-hover", t.accentHover);
    root.setProperty("--accent-soft", t.accentSoft);
    root.setProperty("--accent-glow", t.accentGlow);
    root.setProperty("--hero-start", t.heroStart);
    root.setProperty("--hero-end", t.heroEnd);
    root.setProperty("--bg-deep", t.bgDeep);
    root.setProperty("--orb-1", t.orb1);
    root.setProperty("--orb-2", t.orb2);
    root.setProperty("--orb-3", t.orb3);
    root.setProperty("--dock-bg", t.dockBg);
    root.setProperty("--panel-bg", t.panelBg);
    root.setProperty("--card-bg", t.cardBg);
    root.setProperty("--glass-border", t.glassBorder);
    document.querySelectorAll(".theme-dot").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.theme === key);
    });
    try {
      localStorage.setItem("imagetool_showcase_theme", key);
    } catch (_) {}
  }

  // Init Theme Switcher
  let savedTheme = "blue";
  try {
    const s = localStorage.getItem("imagetool_showcase_theme");
    if (s && THEMES[s]) savedTheme = s;
  } catch (_) {}
  applyTheme(savedTheme);

  document.querySelectorAll(".theme-dot").forEach((btn) => {
    btn.addEventListener("click", () => applyTheme(btn.dataset.theme));
  });

  // Desktop-only radial pointer specular tracking (disabled on coarse/mobile pointers)
  const finePointer = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (finePointer) {
    document.querySelectorAll(".liquid-card").forEach((card) => {
      card.addEventListener("pointermove", (e) => {
        const rect = card.getBoundingClientRect();
        card.style.setProperty("--mx", `${e.clientX - rect.left}px`);
        card.style.setProperty("--my", `${e.clientY - rect.top}px`);
      });
    });
  }

  // Interactive Compare Slider
  const stage = document.getElementById("compareStage");
  const range = document.getElementById("compareRange");
  function setSplit(pct) {
    const clamped = Math.max(4, Math.min(96, Number(pct) || 50));
    if (stage) stage.style.setProperty("--split", `${clamped}%`);
    if (range) range.value = String(Math.round(clamped));
  }
  if (range) {
    range.addEventListener("input", () => setSplit(range.value));
  }
  if (stage) {
    let dragging = false;
    const updateFromClientX = (clientX) => {
      const rect = stage.getBoundingClientRect();
      if (rect.width <= 0) return;
      setSplit(((clientX - rect.left) / rect.width) * 100);
    };
    stage.addEventListener("pointerdown", (e) => {
      dragging = true;
      stage.setPointerCapture(e.pointerId);
      updateFromClientX(e.clientX);
    });
    stage.addEventListener("pointermove", (e) => {
      if (dragging) updateFromClientX(e.clientX);
    });
    stage.addEventListener("pointerup", () => { dragging = false; });
    stage.addEventListener("pointercancel", () => { dragging = false; });
  }
  document.querySelectorAll("[data-split-preset]").forEach((btn) => {
    btn.addEventListener("click", () => setSplit(btn.dataset.splitPreset));
  });

  // Workspace Tabs Switcher
  const wsTitle = document.getElementById("wsTitle");
  const wsShortcut = document.getElementById("wsShortcut");
  const wsSummary = document.getElementById("wsSummary");
  const wsBullets = document.getElementById("wsBullets");

  function renderWorkspace(key) {
    const info = WORKSPACES[key] || WORKSPACES.janai;
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.ws === key);
    });
    if (wsTitle) wsTitle.textContent = info.title;
    if (wsShortcut) wsShortcut.textContent = info.shortcut;
    if (wsSummary) wsSummary.textContent = info.summary;
    if (wsBullets) {
      wsBullets.innerHTML = info.bullets
        .map((txt) => `<li><span class="bullet-dot" aria-hidden="true"></span><span>${txt}</span></li>`)
        .join("");
    }
  }
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => renderWorkspace(btn.dataset.ws));
  });
  renderWorkspace("janai");

  // MangaJaNai Auto Detect Interactive Simulator
  const simType = document.getElementById("simType");
  const simScale = document.getElementById("simScale");
  const simTier = document.getElementById("simTier");
  const simFormat = document.getElementById("simFormat");
  const simModelEl = document.getElementById("simModel");
  const simReasonEl = document.getElementById("simReason");

  function nearestMangaTier(h) {
    const tiers = [1200, 1400, 1600, 1920, 2048];
    let best = 1200;
    let bestDiff = Infinity;
    for (const t of tiers) {
      const diff = Math.abs(t - h);
      if (diff < bestDiff) {
        bestDiff = diff;
        best = t;
      }
    }
    return best;
  }

  function updateRouterSim() {
    if (!simType || !simScale || !simTier || !simFormat) return;
    const isGray = simType.value.startsWith("bw");
    const height = Number(simType.value.split(":")[1] || 1400);
    const scale = simScale.value;
    const colorTier = simTier.value;
    const isJpeg = simFormat.value === "jpg";

    let modelId = "";
    let reason = "";

    if (isGray) {
      const tier = nearestMangaTier(height);
      const scalePrefix = scale === "4x" ? "4x" : "2x";
      modelId = `${scalePrefix}_MangaJaNai_${tier}p_V1_ESRGAN_70k_fp16`;
      reason = `Grayscale detected (${height}px height) -> snapped to ${tier}p screentone ESRGAN tier at ${scalePrefix}.`;
    } else {
      const op = isJpeg ? "V3denoise" : "V3detail";
      if (colorTier === "span") {
        modelId = isJpeg
          ? "2x_IllustrationJaNai_V3denoise_SPAN_S_30k_fp16"
          : "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16";
        reason = `Color illustration (${isJpeg ? "JPEG -> denoise" : "PNG -> detail"}) routed to ultra-fast SPAN-S (0.8 MB).`;
      } else if (colorTier === "fdat_xl") {
        modelId = isJpeg
          ? "4x_IllustrationJaNai_V3denoise_FDAT_XL_32k_fp16"
          : "4x_IllustrationJaNai_V3detail_FDAT_XL_27k_fp16";
        reason = `Color illustration routed to flagship FDAT-XL transformer (${op}, 45.6 MB, 4x native).`;
      } else {
        if (scale === "4x") {
          modelId = isJpeg
            ? "4x_IllustrationJaNai_V3denoise_FDAT_M_47k_fp16"
            : "4x_IllustrationJaNai_V3detail_FDAT_M_40k_fp16";
        } else {
          modelId = isJpeg
            ? "2x_IllustrationJaNai_V3denoise_FDAT_M_unshuffle_30k_fp16"
            : "2x_IllustrationJaNai_V3detail_FDAT_M_unshuffle_40k_fp16";
        }
        reason = `Color illustration (${isJpeg ? "JPEG -> denoise" : "PNG -> detail"}) routed to balanced FDAT-M (${scale}).`;
      }
    }

    if (simModelEl) simModelEl.textContent = modelId;
    if (simReasonEl) simReasonEl.textContent = reason;
  }

  [simType, simScale, simTier, simFormat].forEach((el) => {
    if (el) el.addEventListener("change", updateRouterSim);
  });
  updateRouterSim();

  // Progressive Enhancement: Refresh latest GitHub Release links & asset sizes
  function formatMiB(bytes) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function hydrateLatestRelease() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 4000);
    try {
      const resp = await fetch("https://api.github.com/repos/GuptaAman777/psd-converter/releases/latest", {
        signal: controller.signal,
        headers: { Accept: "application/vnd.github+json" },
      });
      if (!resp.ok) return;
      const rel = await resp.json();
      const tag = rel.tag_name || "7.5";
      const verBadge = document.getElementById("releaseBadge");
      const heroEyebrow = document.getElementById("heroEyebrow");
      if (verBadge) verBadge.textContent = `v${tag.replace(/^v/, "")}`;
      if (heroEyebrow) heroEyebrow.textContent = `v${tag.replace(/^v/, "")} Latest Release • Windows 10 / 11 (x64)`;

      const assets = Array.isArray(rel.assets) ? rel.assets : [];
      const setup = assets.find((a) => /setup.*\.exe$/i.test(a.name));
      const portable = assets.find((a) => /portable.*\.zip$/i.test(a.name));

      if (setup) {
        document.querySelectorAll("[data-dl-setup]").forEach((a) => {
          a.href = setup.browser_download_url;
        });
        const sz = document.getElementById("setupSize");
        if (sz && setup.size) sz.textContent = `${setup.name} • ${formatMiB(setup.size)}`;
      }
      if (portable) {
        document.querySelectorAll("[data-dl-portable]").forEach((a) => {
          a.href = portable.browser_download_url;
        });
        const sz = document.getElementById("portableSize");
        if (sz && portable.size) sz.textContent = `${portable.name} • ${formatMiB(portable.size)}`;
      }
    } catch (_) {
      // Static v7.5 URLs remain active on offline/rate-limited clients.
    } finally {
      clearTimeout(timer);
    }
  }
  hydrateLatestRelease();
})();
