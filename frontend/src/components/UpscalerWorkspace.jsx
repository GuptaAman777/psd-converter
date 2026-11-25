import React, { useEffect, useMemo, useState } from "react";
import { Wand2, Download } from "lucide-react";
import { GlassCard, CollapsibleGlassCard, SettingRow, GlassSwitch } from "./GlassPrimitives";
import { AI_ENGINES, getGroupedModelOptions } from "../utils/aiModels";

const MODEL_META = {
  realesr: {
    styles: [
      { label: "AnimeVideo V3 (2x/3x/4x)", value: "realesr-animevideov3" },
      { label: "RealESRGAN+ (4x Photo)", value: "realesrgan-x4plus" },
      { label: "RealESRGAN+ Anime (4x)", value: "realesrgan-x4plus-anime" },
      { label: "RealESRNet+ (4x Natural)", value: "realesrnet-x4plus" },
      { label: "Classic ESRGAN (4x)", value: "esrgan-x4" },
    ],
  },
  realcugan: {
    styles: [
      { label: "SE (Standard)", value: "models-se" },
      { label: "Pro (Advanced)", value: "models-pro" },
      { label: "Nose (Retain Details)", value: "models-nose" },
    ],
  },
  waifu2x: {
    styles: [
      { label: "CUnet (Best Quality)", value: "models-cunet" },
      { label: "Upconv (Anime/Art)", value: "models-upconv_7_anime_style_art_rgb" },
      { label: "Upconv (Photo)", value: "models-upconv_7_photo" },
    ],
  },
  srmd: {
    styles: [{ label: "SRMD (Photo Super-Resolution)", value: "models-srmd" }],
  },
};

export default function UpscalerWorkspace({
  bootstrap,
  selectedCount,
  outputDir,
  isBusy,
  onStart,
  onPreviewRuleChange,
  onOpenModelManager,
  externalModelSelection,
}) {
  const [model, setModel] = useState("realesr");
  const [styleModel, setStyleModel] = useState("realesr-animevideov3");
  const [scale, setScale] = useState("2x");
  const [noiseLevel, setNoiseLevel] = useState(0);
  const [syncgapMode, setSyncgapMode] = useState(3);
  const [postResizeMode, setPostResizeMode] = useState("Native");
  const [outputFormat, setOutputFormat] = useState("Keep Original");
  const [customSuffix, setCustomSuffix] = useState("");
  const [conflictPolicy, setConflictPolicy] = useState("overwrite");
  const [tileSize, setTileSize] = useState("Auto (0)");
  const [gpuId, setGpuId] = useState("auto");
  const [threadSpec, setThreadSpec] = useState("1:2:2");
  const [ttaMode, setTtaMode] = useState(false);

  const modelGroups = useMemo(
    () => getGroupedModelOptions(model, bootstrap?.model_catalog || []),
    [model, bootstrap?.model_catalog]
  );

  useEffect(() => {
    if (externalModelSelection?.style_model) {
      setModel(externalModelSelection.model || "realesr");
      setStyleModel(externalModelSelection.style_model);
      setScale("4x");
    }
  }, [externalModelSelection]);

  const scaleChoices = (() => {
    if (model === "realesr") {
      return ["2x", "3x", "4x", "8x"];
    }
    if (model === "realcugan") {
      return styleModel === "models-nose" ? ["2x"] : ["2x", "3x", "4x", "8x"];
    }
    if (model === "waifu2x") {
      return styleModel.includes("upconv") ? ["2x", "4x"] : ["1x", "2x", "4x", "8x"];
    }
    return ["2x", "3x", "4x", "8x"];
  })();

  useEffect(() => {
    if (!scaleChoices.includes(scale)) {
      setScale(scaleChoices[0]);
    }
  }, [scaleChoices, scale]);

  useEffect(() => {
    const suf = customSuffix.trim() || `_${scale}`;
    const ext = outputFormat === "Keep Original" ? "" : outputFormat.toLowerCase();
    onPreviewRuleChange({ suffix: suf, ext });
  }, [customSuffix, scale, outputFormat, onPreviewRuleChange]);

  const handleModelChange = (nextModel) => {
    setModel(nextModel);
    const firstStyle = MODEL_META[nextModel].styles[0].value;
    setStyleModel(firstStyle);
    setNoiseLevel(nextModel === "srmd" ? 3 : nextModel === "realesr" ? -1 : 0);
  };

  const noiseOptions = (() => {
    if (model === "realesr") return null;
    if (model === "srmd") {
      return [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((v) => ({
        val: v,
        lbl: v === -1 ? "-1 (None)" : v === 3 ? "3 (Default)" : v === 10 ? "10 (Max)" : String(v),
      }));
    }
    if (model === "realcugan") {
      if (styleModel === "models-nose") return [{ val: 0, lbl: "0 (Low)" }];
      if (styleModel === "models-pro" || (styleModel === "models-se" && scale !== "2x")) {
        return [
          { val: -1, lbl: "-1 (None)" },
          { val: 0, lbl: "0 (Low)" },
          { val: 3, lbl: "3 (High)" },
        ];
      }
    }
    return [
      { val: -1, lbl: "-1 (None)" },
      { val: 0, lbl: "0 (Low)" },
      { val: 1, lbl: "1 (Light)" },
      { val: 2, lbl: "2 (Medium)" },
      { val: 3, lbl: "3 (High)" },
    ];
  })();

  const handleLaunch = () => {
    const keepOriginal = outputFormat === "Keep Original";
    onStart({
      model,
      style_model: styleModel,
      scale,
      noise_level: noiseOptions ? noiseLevel : -1,
      syncgap_mode: syncgapMode,
      post_resize_mode: postResizeMode,
      keep_format: keepOriginal,
      output_format: keepOriginal ? "PNG" : outputFormat,
      custom_suffix: customSuffix.trim(),
      conflict_policy: conflictPolicy,
      tile_size: tileSize,
      gpu_id: gpuId,
      thread_spec: threadSpec,
      tta_mode: ttaMode,
    });
  };

  return (
    <div className="liquid-panel rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col gap-2.5 sm:gap-3 w-full lg:w-[356px] xl:w-[404px] 2xl:w-[440px] shrink-0 lg:h-full overflow-hidden">
      <div className="lg:flex-1 lg:overflow-y-auto lg:pr-1 space-y-2.5 sm:space-y-3">
        <GlassCard
          title="Neural Architecture & Scale"
          rightHeader={
            onOpenModelManager && (
              <button
                type="button"
                onClick={onOpenModelManager}
                title="Download additional NCNN AI models"
                className="liquid-pill-btn rounded-full px-2.5 py-1 text-[10.5px] font-semibold text-[var(--accent-hover)] flex items-center gap-1 cursor-pointer"
              >
                <Download className="w-3 h-3" />
                <span>More Models</span>
              </button>
            )
          }
        >
          <SettingRow label="AI Engine">
            <select
              value={model}
              onChange={(e) => handleModelChange(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12px] sm:text-[12.5px] font-medium"
            >
              {AI_ENGINES.map((eng) => (
                <option key={eng.value} value={eng.value}>
                  {eng.label}
                </option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Model Variant">
            <select
              value={styleModel}
              onChange={(e) => setStyleModel(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
            >
              {modelGroups.map((grp) => (
                <optgroup key={grp.group} label={grp.group}>
                  {grp.items.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </SettingRow>

          {noiseOptions && (
            <SettingRow label="Denoise Level">
              <select
                value={noiseLevel}
                onChange={(e) => setNoiseLevel(Number(e.target.value))}
                className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
              >
                {noiseOptions.map((o) => (
                  <option key={o.val} value={o.val}>
                    {o.lbl}
                  </option>
                ))}
              </select>
            </SettingRow>
          )}

          {model === "realcugan" && (
            <SettingRow label="SyncGap (-c)" hint="Tile seam sync">
              <select
                value={syncgapMode}
                onChange={(e) => setSyncgapMode(Number(e.target.value))}
                className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
              >
                <option value={3}>3 — Balanced / Default</option>
                <option value={2}>2 — Ultra-Precise Sync</option>
                <option value={1}>1 — Light Sync</option>
                <option value={0}>0 — No SyncGap</option>
              </select>
            </SettingRow>
          )}

          <SettingRow label="Scale Factor">
            <div className="flex gap-1.5">
              {scaleChoices.map((s) => {
                const active = scale === s;
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setScale(s)}
                    className={`flex-1 py-1.5 rounded-xl text-[12px] font-bold transition-all cursor-pointer border ${
                      active
                        ? "bg-[var(--accent)] text-white border-white/30 shadow-[0_0_16px_var(--accent-soft)]"
                        : "liquid-pill-btn text-white/75"
                    }`}
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </SettingRow>

          <SettingRow label="SSAA / Target" hint="Post Lanczos fit">
            <select
              value={postResizeMode}
              onChange={(e) => setPostResizeMode(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
            >
              <option value="Native">Native Full Scale</option>
              <option value="50% SSAA">50% SSAA (Crisp Anti-Aliased)</option>
              <option value="1920px Max Width">1920px Max Width (1080p Fit)</option>
              <option value="2560px Max Width">2560px Max Width (1440p Fit)</option>
              <option value="3840px Max Width">3840px Max Width (4K Fit)</option>
            </select>
          </SettingRow>
        </GlassCard>

        <GlassCard title="Output Encoding">
          <SettingRow label="Output Format">
            <select
              value={outputFormat}
              onChange={(e) => setOutputFormat(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
            >
              <option value="Keep Original">Keep Original Format</option>
              <option value="PNG">PNG</option>
              <option value="JPG">JPG</option>
              <option value="WEBP">WEBP</option>
            </select>
          </SettingRow>
        </GlassCard>

        <CollapsibleGlassCard title="Hardware, Threads & Naming" defaultOpen={false}>
          <SettingRow label="Custom Suffix">
            <input
              type="text"
              placeholder={`Default (_${scale})`}
              value={customSuffix}
              onChange={(e) => setCustomSuffix(e.target.value)}
              className="liquid-input w-full rounded-xl px-3 py-1.5 text-[12px]"
            />
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

          <SettingRow label="VRAM Tile Size">
            <select
              value={tileSize}
              onChange={(e) => setTileSize(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
            >
              {(bootstrap?.formats?.tile_sizes || ["Auto (0)", "64", "100", "200", "400"]).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Compute GPU">
            <select
              value={gpuId}
              onChange={(e) => setGpuId(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
            >
              <option value="auto">Auto (Best Vulkan GPU)</option>
              {(bootstrap?.gpus || []).map((g, idx) => (
                <option key={g} value={String(idx)}>
                  GPU {idx}: {g}
                </option>
              ))}
              <option value="-1">CPU Fallback (-1)</option>
            </select>
          </SettingRow>

          <SettingRow label="Thread Spec (-j)">
            <select
              value={threadSpec}
              onChange={(e) => setThreadSpec(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
            >
              <option value="1:2:2">1:2:2 (Balanced Default)</option>
              <option value="2:4:4">2:4:4 (Fast NVMe / VRAM)</option>
              <option value="1:1:1">1:1:1 (Low Memory)</option>
            </select>
          </SettingRow>

          <GlassSwitch
            checked={ttaMode}
            onChange={setTtaMode}
            label="Enable TTA 8-Pass Ensemble"
            sublabel="Peak sharpness & detail, 8x slower"
          />
        </CollapsibleGlassCard>
      </div>

      <button
        type="button"
        disabled={isBusy || selectedCount === 0 || !outputDir}
        onClick={handleLaunch}
        className="liquid-hero-btn w-full rounded-2xl py-3 text-[14px] font-bold text-white flex items-center justify-center gap-2 cursor-pointer shrink-0"
      >
        <Wand2 className="w-4 h-4" />
        <span>{isBusy ? "Upscaling..." : `Upscale ${selectedCount || ""} Image${selectedCount === 1 ? "" : "s"} (${scale})`}</span>
      </button>
    </div>
  );
}
