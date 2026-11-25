import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Sparkles, Globe, Archive, Layers, FileText, Check } from "lucide-react";
import { GlassCard, CollapsibleGlassCard, SettingRow, GlassSwitch } from "./GlassPrimitives";
import { AI_ENGINES, getGroupedModelOptions } from "../utils/aiModels";

const ESRGAN_STYLES = [
  { label: "AnimeVideo V3 (2x/3x/4x)", value: "realesr-animevideov3" },
  { label: "RealESRGAN+ (4x Photo)", value: "realesrgan-x4plus" },
  { label: "RealESRGAN+ Anime (4x Anime)", value: "realesrgan-x4plus-anime" },
  { label: "RealESRNet+ (4x Natural)", value: "realesrnet-x4plus" },
  { label: "Classic ESRGAN (4x)", value: "esrgan-x4" },
];

const WAIFU_STYLES = [
  { label: "CUnet (Best Quality)", value: "models-cunet" },
  { label: "Upconv (Anime/Art)", value: "models-upconv_7_anime_style_art_rgb" },
  { label: "Upconv (Photo)", value: "models-upconv_7_photo" },
];

const CUGAN_STYLES = [
  { label: "SE (Standard)", value: "models-se" },
  { label: "Pro (Advanced)", value: "models-pro" },
  { label: "Nose (Retain Details)", value: "models-nose" },
];

export default function ConverterWorkspace({
  bootstrap,
  selectedCount,
  outputDir,
  isBusy,
  onStart,
  onPreviewRuleChange,
}) {
  const saved = bootstrap?.settings || {};
  const qMap = { Maximum: 95, High: 85, Medium: 70, Low: 50 };
  const cMap = { None: 0, Fast: 1, Normal: 6, Maximum: 9 };

  const [activePreset, setActivePreset] = useState("");
  const [outputFormat, setOutputFormat] = useState("PNG");
  const [jpegQuality, setJpegQuality] = useState(qMap[saved.jpeg_quality] || 85);
  const [webpQuality, setWebpQuality] = useState(qMap[saved.webp_quality] || 85);
  const [webpLossless, setWebpLossless] = useState(false);
  const [pngCompression, setPngCompression] = useState(cMap[saved.png_compression] ?? 6);
  const [alphaChoice, setAlphaChoice] = useState("White");
  const [alphaHex, setAlphaHex] = useState("#FFFFFF");

  const [resizePreset, setResizePreset] = useState("Original (100%)");
  const [customMaxW, setCustomMaxW] = useState("");
  const [customMaxH, setCustomMaxH] = useState("");
  const [resampleFilter, setResampleFilter] = useState("lanczos");

  const [pdfExtractAll, setPdfExtractAll] = useState(false);
  const [pdfPageRange, setPdfPageRange] = useState("");
  const [psdExtractLayers, setPsdExtractLayers] = useState(false);
  const [psdIncludeComposite, setPsdIncludeComposite] = useState(true);
  const [psdRawNames, setPsdRawNames] = useState(false);

  const [enableUpscale, setEnableUpscale] = useState(false);
  const [forceUpscale, setForceUpscale] = useState(false);
  const [upscaleModel, setUpscaleModel] = useState("realesr");
  const [upscaleStyle, setUpscaleStyle] = useState("realesr-animevideov3");
  const [upscaleScale, setUpscaleScale] = useState("2x");
  const [upscaleNoise, setUpscaleNoise] = useState(-1);
  const [upscaleTile, setUpscaleTile] = useState("Auto (0)");
  const [upscaleGpu, setUpscaleGpu] = useState("auto");
  const [upscaleTta, setUpscaleTta] = useState(false);

  const [prefix, setPrefix] = useState("");
  const [suffix, setSuffix] = useState("");
  const [conflictPolicy, setConflictPolicy] = useState("overwrite");
  const [preserveExif, setPreserveExif] = useState(saved.preserve_exif !== false);
  const [mirrorFolders, setMirrorFolders] = useState(false);

  // Sync saved Settings encoding/EXIF defaults once async /api/bootstrap resolves or Settings change
  const lastSettingsJson = useRef("");
  useEffect(() => {
    if (!bootstrap?.settings) return;
    const serialized = JSON.stringify(bootstrap.settings);
    if (serialized === lastSettingsJson.current) return;
    lastSettingsJson.current = serialized;
    const s = bootstrap.settings;
    if (s.jpeg_quality && qMap[s.jpeg_quality] != null) setJpegQuality(qMap[s.jpeg_quality]);
    if (s.webp_quality && qMap[s.webp_quality] != null) setWebpQuality(qMap[s.webp_quality]);
    if (s.png_compression && cMap[s.png_compression] != null) setPngCompression(cMap[s.png_compression]);
    if (typeof s.preserve_exif === "boolean") setPreserveExif(s.preserve_exif);
  }, [bootstrap?.settings]);

  useEffect(() => {
    onPreviewRuleChange({ suffix: suffix.trim(), ext: outputFormat.toLowerCase() });
  }, [suffix, outputFormat, onPreviewRuleChange]);

  const vulkanReady = Boolean(bootstrap?.vulkan_support) || forceUpscale;
  const isCustomW = resizePreset === "Custom Bounds" || resizePreset === "Match Width (Auto H)";
  const isCustomH = resizePreset === "Custom Bounds" || resizePreset === "Match Height (Auto W)";

  const inlineModelGroups = getGroupedModelOptions(upscaleModel, bootstrap?.model_catalog || []);

  const handleUpscaleModelSwitch = (m) => {
    setUpscaleModel(m);
    if (m === "waifu2x") {
      setUpscaleStyle("models-cunet");
      setUpscaleScale("2x");
      setUpscaleNoise(0);
    } else if (m === "realcugan") {
      setUpscaleStyle("models-se");
      setUpscaleScale("2x");
      setUpscaleNoise(0);
    } else if (m === "srmd") {
      setUpscaleStyle("models-srmd");
      setUpscaleScale("2x");
      setUpscaleNoise(3);
    } else {
      setUpscaleStyle("realesr-animevideov3");
      setUpscaleScale("2x");
      setUpscaleNoise(-1);
    }
  };

  const handleLaunch = () => {
    onStart({
      output_format: outputFormat.toLowerCase(),
      settings: {
        jpeg_quality: saved.jpeg_quality || "High",
        jpeg_quality_num: jpegQuality,
        webp_quality: saved.webp_quality || "High",
        webp_quality_num: webpQuality,
        webp_lossless: webpLossless,
        png_compression: saved.png_compression || "Normal",
        png_compression_num: pngCompression,
        pdf_dpi: saved.pdf_dpi || "150 DPI",
        pdf_quality: saved.pdf_quality || "High",
        pdf_extract_all: pdfExtractAll,
        pdf_page_range: pdfPageRange.trim(),
        extract_layers: psdExtractLayers,
        psd_include_composite: psdIncludeComposite,
        psd_raw_layer_names: psdRawNames,
        resize_preset: resizePreset,
        custom_max_width: parseInt(customMaxW || "0", 10) || 0,
        custom_max_height: parseInt(customMaxH || "0", 10) || 0,
        resample_filter: resampleFilter,
        alpha_bg_color: alphaChoice === "Custom" ? alphaHex : alphaChoice,
        filename_prefix: prefix.trim(),
        filename_suffix: suffix.trim(),
        conflict_policy: conflictPolicy,
        preserve_exif: preserveExif,
        mirror_folders: mirrorFolders,
      },
      enable_upscale: enableUpscale && ["PNG", "JPEG", "WEBP"].includes(outputFormat),
      upscale_settings: {
        model: upscaleModel,
        style_model: upscaleStyle,
        scale: upscaleScale,
        noise_level: upscaleNoise,
        tile_size: upscaleTile.includes("Auto") ? 0 : parseInt(upscaleTile, 10) || 0,
        gpu_id: upscaleGpu,
        tta_mode: upscaleTta,
      },
    });
  };

  return (
    <div className="liquid-panel rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col gap-2.5 sm:gap-3 w-full lg:w-[356px] xl:w-[404px] 2xl:w-[440px] shrink-0 lg:h-full overflow-hidden">
      <div className="lg:flex-1 lg:overflow-y-auto lg:pr-1 space-y-2.5 sm:space-y-3">
        {/* Workflow Presets */}
        <GlassCard
          title="Workflow Presets"
          badge={activePreset ? `${activePreset} active` : null}
        >
          <div className="grid grid-cols-2 gap-2">
            {[
              {
                label: "Web WEBP",
                Icon: Globe,
                onClick: () => {
                  setActivePreset("Web WEBP");
                  setOutputFormat("WEBP");
                  setWebpLossless(false);
                  setWebpQuality(85);
                  setResizePreset("Original (100%)");
                  setPsdExtractLayers(false);
                  setPdfExtractAll(false);
                  setPreserveExif(false);
                },
              },
              {
                label: "Archival PNG",
                Icon: Archive,
                onClick: () => {
                  setActivePreset("Archival PNG");
                  setOutputFormat("PNG");
                  setPngCompression(6);
                  setResizePreset("Original (100%)");
                  setPsdExtractLayers(false);
                  setPdfExtractAll(false);
                  setPreserveExif(true);
                },
              },
              {
                label: "PSD Layers",
                Icon: Layers,
                onClick: () => {
                  setActivePreset("PSD Layers");
                  setOutputFormat("PNG");
                  setPsdExtractLayers(true);
                  setPsdIncludeComposite(true);
                  setPsdRawNames(false);
                  setPdfExtractAll(false);
                  setResizePreset("Original (100%)");
                },
              },
              {
                label: "PDF Pages",
                Icon: FileText,
                onClick: () => {
                  setActivePreset("PDF Pages");
                  setOutputFormat("PNG");
                  setPdfExtractAll(true);
                  setPdfPageRange("");
                  setPsdExtractLayers(false);
                  setResizePreset("Original (100%)");
                },
              },
            ].map(({ label, Icon, onClick }) => {
              const isSelected = activePreset === label;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={onClick}
                  className={`rounded-xl px-3 py-2 text-[12px] font-semibold flex items-center justify-center gap-1.5 cursor-pointer transition-all ${
                    isSelected
                      ? "bg-[var(--accent-soft)] text-white border border-[var(--accent)] shadow-[0_0_16px_var(--accent-soft)]"
                      : "liquid-pill-btn text-white/90"
                  }`}
                >
                  {isSelected ? (
                    <Check className="w-3.5 h-3.5 text-[var(--accent-hover)]" />
                  ) : (
                    <Icon className="w-3.5 h-3.5 text-[var(--accent-hover)]" />
                  )}
                  <span>{label}</span>
                </button>
              );
            })}
          </div>
        </GlassCard>

        {/* Output Format & Contextual Sliders */}
        <GlassCard title="Output Format & Encoding">
          <SettingRow label="Output Format">
            <select
              value={outputFormat}
              onChange={(e) => {
                setActivePreset("");
                setOutputFormat(e.target.value);
              }}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px] font-medium cursor-pointer"
            >
              {(bootstrap?.formats?.output || ["PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP", "PDF"]).map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </SettingRow>

          {outputFormat === "JPEG" && (
            <SettingRow label="JPEG Quality">
              <div className="flex items-center gap-2.5">
                <input
                  type="range"
                  min={10}
                  max={100}
                  value={jpegQuality}
                  onChange={(e) => setJpegQuality(Number(e.target.value))}
                  className="liquid-slider flex-1"
                />
                <span className="text-[12px] font-bold w-10 text-right tabular-nums">{jpegQuality}%</span>
              </div>
            </SettingRow>
          )}

          {outputFormat === "WEBP" && (
            <>
              <SettingRow label="WEBP Quality">
                <div className="flex items-center gap-2.5">
                  <input
                    type="range"
                    min={10}
                    max={100}
                    disabled={webpLossless}
                    value={webpQuality}
                    onChange={(e) => setWebpQuality(Number(e.target.value))}
                    className="liquid-slider flex-1 disabled:opacity-40"
                  />
                  <span className="text-[12px] font-bold w-10 text-right tabular-nums">{webpQuality}%</span>
                </div>
              </SettingRow>
              <GlassSwitch
                checked={webpLossless}
                onChange={setWebpLossless}
                label="Lossless WEBP Encoding"
                sublabel="Bit-exact transparency & lines"
              />
            </>
          )}

          {outputFormat === "PNG" && (
            <SettingRow label="Compression">
              <div className="flex items-center gap-2.5">
                <input
                  type="range"
                  min={0}
                  max={9}
                  value={pngCompression}
                  onChange={(e) => setPngCompression(Number(e.target.value))}
                  className="liquid-slider flex-1"
                />
                <span className="text-[12px] font-bold w-10 text-right tabular-nums">Lvl {pngCompression}</span>
              </div>
            </SettingRow>
          )}

          {["JPEG", "BMP", "PDF"].includes(outputFormat) && (
            <SettingRow label="Alpha Matte">
              <div className="flex items-center gap-2">
                <select
                  value={alphaChoice}
                  onChange={(e) => setAlphaChoice(e.target.value)}
                  className="liquid-select flex-1 rounded-xl px-3 py-1.5 text-[12px]"
                >
                  <option value="White">White (#FFFFFF)</option>
                  <option value="Black">Black (#000000)</option>
                  <option value="Gray">Neutral Gray</option>
                  <option value="Custom">Custom Color</option>
                </select>
                {alphaChoice === "Custom" && (
                  <input
                    type="color"
                    value={alphaHex}
                    onChange={(e) => setAlphaHex(e.target.value)}
                    className="w-8 h-8 rounded-lg bg-transparent border border-white/20 cursor-pointer"
                  />
                )}
              </div>
            </SettingRow>
          )}
        </GlassCard>

        {/* Dimensions & Resampling */}
        <GlassCard title="Dimensions & Resampling">
          <SettingRow label="Resize Mode">
            <select
              value={resizePreset}
              onChange={(e) => setResizePreset(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
            >
              {[
                ...(bootstrap?.formats?.resize_presets || ["Original (100%)", "25%", "50%", "75%", "150%", "200%", "Custom Bounds"]),
                "Match Width (Auto H)",
                "Match Height (Auto W)",
              ].map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </SettingRow>

          <AnimatePresence initial={false}>
            {(isCustomW || isCustomH) && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden flex items-center gap-2"
              >
                {isCustomW && (
                  <input
                    type="number"
                    min={1}
                    placeholder="Max W px"
                    value={customMaxW}
                    onChange={(e) => setCustomMaxW(e.target.value)}
                    className="liquid-input flex-1 rounded-xl px-3 py-1.5 text-[12px]"
                  />
                )}
                {isCustomH && (
                  <input
                    type="number"
                    min={1}
                    placeholder="Max H px"
                    value={customMaxH}
                    onChange={(e) => setCustomMaxH(e.target.value)}
                    className="liquid-input flex-1 rounded-xl px-3 py-1.5 text-[12px]"
                  />
                )}
              </motion.div>
            )}
          </AnimatePresence>

          <SettingRow label="Resampling">
            <select
              value={resampleFilter}
              onChange={(e) => setResampleFilter(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
            >
              <option value="lanczos">Lanczos (Sharp)</option>
              <option value="bicubic">Bicubic (Balanced)</option>
              <option value="bilinear">Bilinear (Fast)</option>
              <option value="nearest">Nearest (Pixel Art)</option>
            </select>
          </SettingRow>
        </GlassCard>

        {/* PSD & PDF Extraction */}
        <GlassCard title="PSD & PDF Extraction">
          <GlassSwitch
            checked={pdfExtractAll}
            onChange={setPdfExtractAll}
            label="Extract Multi-Page PDFs"
            sublabel="Rasterizes selected pages into document folder"
          />

          <AnimatePresence initial={false}>
            {pdfExtractAll && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden pl-2 border-l-2 border-[var(--accent)]/40"
              >
                <SettingRow label="Page Range">
                  <input
                    type="text"
                    placeholder="All (or e.g. 1-4, 7)"
                    value={pdfPageRange}
                    onChange={(e) => setPdfPageRange(e.target.value)}
                    className="liquid-input w-full rounded-xl px-3 py-1.5 text-[12px]"
                  />
                </SettingRow>
              </motion.div>
            )}
          </AnimatePresence>

          <GlassSwitch
            checked={psdExtractLayers}
            onChange={setPsdExtractLayers}
            label="Extract Visible PSD Layers"
            sublabel="Saves each layer cleanly per PSD folder"
          />

          <AnimatePresence initial={false}>
            {psdExtractLayers && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden pl-2 border-l-2 border-[var(--accent)]/40 space-y-2"
              >
                <GlassSwitch
                  checked={psdIncludeComposite}
                  onChange={setPsdIncludeComposite}
                  label="Include Flattened Composite"
                />
                <GlassSwitch
                  checked={psdRawNames}
                  onChange={setPsdRawNames}
                  label="Keep Raw Photoshop Filenames"
                />
              </motion.div>
            )}
          </AnimatePresence>
        </GlassCard>

        {/* Inline AI Super-Resolution */}
        <GlassCard
          title="Inline AI Super-Resolution"
          rightHeader={
            <label className="flex items-center gap-1.5 text-[11px] text-amber-300 cursor-pointer">
              <input
                type="checkbox"
                checked={forceUpscale}
                onChange={(e) => setForceUpscale(e.target.checked)}
                className="accent-amber-400"
              />
              Force
            </label>
          }
        >
          <GlassSwitch
            checked={enableUpscale && vulkanReady}
            disabled={!vulkanReady}
            onChange={setEnableUpscale}
            label="Run AI Upscaler After Convert"
            sublabel={vulkanReady ? "Vulkan Neural Pipeline Ready" : "Requires Vulkan GPU or Force"}
          />

          <AnimatePresence initial={false}>
            {enableUpscale && vulkanReady && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden pt-2 border-t border-white/10 space-y-2"
              >
                <SettingRow label="Engine">
                  <select
                    value={upscaleModel}
                    onChange={(e) => handleUpscaleModelSwitch(e.target.value)}
                    className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[12px]"
                  >
                    {AI_ENGINES.map((eng) => (
                      <option key={eng.value} value={eng.value}>
                        {eng.label}
                      </option>
                    ))}
                  </select>
                </SettingRow>
                <SettingRow label="Variant">
                  <select
                    value={upscaleStyle}
                    onChange={(e) => setUpscaleStyle(e.target.value)}
                    className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[12px]"
                  >
                    {inlineModelGroups.map((grp) => (
                      <optgroup key={grp.group} label={grp.group}>
                        {grp.items.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </SettingRow>
                <SettingRow label="Scale / Device">
                  <div className="flex gap-2">
                    <select
                      value={upscaleScale}
                      onChange={(e) => setUpscaleScale(e.target.value)}
                      className="liquid-select w-20 rounded-xl px-2 py-1.5 text-[12px]"
                    >
                      {(upscaleStyle.includes("x4") && !upscaleStyle.includes("animevideov3")
                        ? ["4x"]
                        : upscaleModel === "waifu2x"
                        ? ["1x", "2x", "4x", "8x"]
                        : ["2x", "3x", "4x"]
                      ).map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    <select
                      value={upscaleGpu}
                      onChange={(e) => setUpscaleGpu(e.target.value)}
                      className="liquid-select flex-1 rounded-xl px-2 py-1.5 text-[12px]"
                    >
                      <option value="auto">Auto GPU</option>
                      {(bootstrap?.gpus || []).map((g, idx) => (
                        <option key={g} value={String(idx)}>
                          GPU {idx}: {g.slice(0, 18)}
                        </option>
                      ))}
                      <option value="-1">CPU (-1)</option>
                    </select>
                  </div>
                </SettingRow>
                <SettingRow label="Tile Size">
                  <select
                    value={upscaleTile}
                    onChange={(e) => setUpscaleTile(e.target.value)}
                    className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[12px]"
                  >
                    {(bootstrap?.formats?.tile_sizes || ["Auto (0)", "64", "100", "200", "400"]).map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </SettingRow>
                <GlassSwitch checked={upscaleTta} onChange={setUpscaleTta} label="8-Pass TTA Mode" />
              </motion.div>
            )}
          </AnimatePresence>
        </GlassCard>

        {/* Advanced Pipeline Accordion */}
        <CollapsibleGlassCard title="Advanced Naming & Pipeline" defaultOpen={false}>
          <SettingRow label="Name Affixes">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Prefix"
                value={prefix}
                onChange={(e) => setPrefix(e.target.value)}
                className="liquid-input flex-1 rounded-xl px-2.5 py-1.5 text-[12px]"
              />
              <input
                type="text"
                placeholder="Suffix"
                value={suffix}
                onChange={(e) => setSuffix(e.target.value)}
                className="liquid-input flex-1 rounded-xl px-2.5 py-1.5 text-[12px]"
              />
            </div>
          </SettingRow>

          <SettingRow label="If File Exists">
            <select
              value={conflictPolicy}
              onChange={(e) => setConflictPolicy(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
            >
              <option value="overwrite">Overwrite existing</option>
              <option value="skip">Skip existing</option>
              <option value="rename">Auto-rename (_1, _2)</option>
            </select>
          </SettingRow>

          <GlassSwitch
            checked={preserveExif}
            onChange={setPreserveExif}
            label="Preserve EXIF & ICC Color Profile"
          />
          <GlassSwitch
            checked={mirrorFolders}
            onChange={setMirrorFolders}
            label="Mirror Source Subfolder Hierarchy"
          />
        </CollapsibleGlassCard>
      </div>

      {/* Hero Button */}
      <button
        type="button"
        disabled={isBusy || selectedCount === 0 || !outputDir}
        onClick={handleLaunch}
        className="liquid-hero-btn w-full rounded-2xl py-3 text-[14px] font-bold text-white flex items-center justify-center gap-2 cursor-pointer shrink-0"
      >
        <Sparkles className="w-4 h-4" />
        <span>{isBusy ? "Processing Batch..." : `Convert ${selectedCount || ""} File${selectedCount === 1 ? "" : "s"}`}</span>
      </button>
    </div>
  );
}
