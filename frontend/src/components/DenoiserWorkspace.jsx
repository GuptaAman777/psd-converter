import React, { useEffect, useState } from "react";
import { Eraser } from "lucide-react";
import { GlassCard, CollapsibleGlassCard, SettingRow, GlassSwitch } from "./GlassPrimitives";

const ENGINES = [
  { id: "waifu2x_cunet", label: "Waifu2x (CUnet Anime)", engine: "waifu2x", model: "anime" },
  { id: "waifu2x_photo", label: "Waifu2x (Upconv Photo)", engine: "waifu2x", model: "photo" },
  { id: "realcugan", label: "Real-CUGAN (Fast SE)", engine: "realcugan", model: "models-se" },
  { id: "srmd", label: "SRMD (Photo & Scans)", engine: "srmd", model: "srmd" },
];

export default function DenoiserWorkspace({
  bootstrap,
  selectedCount,
  outputDir,
  isBusy,
  onStart,
  onPreviewRuleChange,
}) {
  const [engineKey, setEngineKey] = useState("waifu2x_cunet");
  const [noiseLevel, setNoiseLevel] = useState(2);
  const [blendPct, setBlendPct] = useState(100);
  const [outputFormat, setOutputFormat] = useState("Keep Original");
  const [customSuffix, setCustomSuffix] = useState("_denoised");
  const [conflictPolicy, setConflictPolicy] = useState("overwrite");
  const [tileSize, setTileSize] = useState("Auto (0)");
  const [gpuId, setGpuId] = useState("auto");
  const [threadSpec, setThreadSpec] = useState("1:2:2");
  const [ttaMode, setTtaMode] = useState(false);

  const engineMeta = ENGINES.find((e) => e.id === engineKey) || ENGINES[0];

  const handleEngineChange = (id) => {
    setEngineKey(id);
    if (id === "srmd") setNoiseLevel(3);
    else if (id === "realcugan") setNoiseLevel(1);
    else setNoiseLevel(2);
  };

  useEffect(() => {
    const suf = customSuffix.trim() || "_denoised";
    const ext = outputFormat === "Keep Original" ? "" : outputFormat.toLowerCase();
    onPreviewRuleChange({ suffix: suf, ext });
  }, [customSuffix, outputFormat, onPreviewRuleChange]);

  const noiseChoices = (() => {
    if (engineKey === "srmd") {
      return [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((v) => ({
        val: v,
        lbl: v === -1 ? "-1 (None)" : v === 3 ? "3 (Default)" : v === 10 ? "10 (Max)" : `Level ${v}`,
      }));
    }
    if (engineKey === "realcugan") {
      return [
        { val: 1, lbl: "Level 1 (Light)" },
        { val: 2, lbl: "Level 2 (Medium)" },
        { val: 3, lbl: "Level 3 (High)" },
      ];
    }
    return [
      { val: 0, lbl: "Level 0 (Light)" },
      { val: 1, lbl: "Level 1 (Low)" },
      { val: 2, lbl: "Level 2 (Medium)" },
      { val: 3, lbl: "Level 3 (Strong)" },
    ];
  })();

  const handleLaunch = () => {
    const keepOriginal = outputFormat === "Keep Original";
    onStart({
      engine: engineMeta.engine,
      model: engineMeta.model,
      noise_level: noiseLevel,
      blend_pct: blendPct,
      keep_format: keepOriginal,
      output_format: keepOriginal ? "PNG" : outputFormat,
      custom_suffix: customSuffix.trim() || "_denoised",
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
        <GlassCard title="Noise Suppression Engine">
          <SettingRow label="Denoiser AI">
            <select
              value={engineKey}
              onChange={(e) => handleEngineChange(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px] font-medium"
            >
              {ENGINES.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.label}
                </option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Strength">
            <select
              value={noiseLevel}
              onChange={(e) => setNoiseLevel(Number(e.target.value))}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
            >
              {noiseChoices.map((o) => (
                <option key={o.val} value={o.val}>
                  {o.lbl}
                </option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Grain Preserve" hint="Texture blend">
            <div className="flex items-center gap-2.5">
              <input
                type="range"
                min={10}
                max={100}
                value={blendPct}
                onChange={(e) => setBlendPct(Number(e.target.value))}
                className="liquid-slider flex-1"
              />
              <span className="text-[12px] font-bold w-14 text-right tabular-nums">
                {blendPct}% AI
              </span>
            </div>
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
          <SettingRow label="Suffix">
            <input
              type="text"
              placeholder="_denoised"
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

          <GlassSwitch checked={ttaMode} onChange={setTtaMode} label="Enable TTA 8-Pass Ensemble" />
        </CollapsibleGlassCard>
      </div>

      <button
        type="button"
        disabled={isBusy || selectedCount === 0 || !outputDir}
        onClick={handleLaunch}
        className="liquid-hero-btn w-full rounded-2xl py-3 text-[14px] font-bold text-white flex items-center justify-center gap-2 cursor-pointer shrink-0"
      >
        <Eraser className="w-4 h-4" />
        <span>{isBusy ? "Denoising..." : `Denoise ${selectedCount || ""} Image${selectedCount === 1 ? "" : "s"}`}</span>
      </button>
    </div>
  );
}
