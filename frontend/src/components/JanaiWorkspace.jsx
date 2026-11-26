import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Cpu, Download, Loader2, CheckCircle2, Sparkles, Wand2, Workflow,
  Sliders, Plus, Save, Trash2, Copy, Eye, AlertCircle
} from "lucide-react";
import { GlassCard, CollapsibleGlassCard, SettingRow, GlassSwitch } from "./GlassPrimitives";
import QueueRoutingModal from "./QueueRoutingModal";
import { apiPost } from "../api/client";

const FAMILIES = [
  { value: "FDAT", label: "FDAT — IllustrationJaNai V3 (2x / 4x Transformer)" },
  { value: "SPAN", label: "SPAN — IllustrationJaNai V3 Fast (2x Line Art)" },
  { value: "ESRGAN_4x", label: "ESRGAN 4x — MangaJaNai V1 Scans (1200p–2048p)" },
  { value: "ESRGAN_2x", label: "ESRGAN 2x — MangaJaNai V1 Scans (1200p–2048p)" },
];

const EMPTY_DRAFT = {
  id: "",
  name: "My Custom Workflow",
  description: "Custom grayscale + color routing rules",
  grayscale_strategy: "auto_tier",
  grayscale_scale: "2x",
  grayscale_model_id: "2x_MangaJaNai_1400p_V1_ESRGAN_70k_fp16",
  grayscale_chain_id: "",
  color_model_id: "2x_IllustrationJaNai_V3detail_FDAT_M_unshuffle_40k_fp16",
  color_denoise_model_id: "2x_IllustrationJaNai_V3denoise_FDAT_M_unshuffle_30k_fp16",
  color_auto_denoise: true,
  color_chain_id: "",
};

export default function JanaiWorkspace({
  bootstrap,
  prefs,
  onChangePrefs,
  selectedFiles = [],
  selectedCount,
  outputDir,
  isBusy,
  onStart,
  onPreviewRuleChange,
  onOpenModelManager,
  onSaveSettings,
  externalModelSelection,
  downloadProgress = {},
  onInstallModel,
}) {
  const janaiModels = useMemo(
    () => (bootstrap?.model_catalog || []).filter((m) => m.engine === "janai_ncnn"),
    [bootstrap?.model_catalog]
  );
  const builtinWorkflows = bootstrap?.builtin_janai_workflows || [];
  const customWorkflows = bootstrap?.settings?.janai_workflows || [];
  const allWorkflows = useMemo(
    () => [...builtinWorkflows, ...customWorkflows],
    [builtinWorkflows, customWorkflows]
  );

  // Persisted workspace state via App `prefs` (falls back cleanly if omitted in tests)
  const [localPrefs, setLocalPrefs] = useState({
    mode: "auto",
    autoScale: "2x",
    colorTier: "fdat_m",
    colorDenoiseMode: "auto",
    selectedWfId: "preset_mangajanai_2x",
    family: "SPAN",
    modelId: "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16",
    postResizeMode: "Native",
    outputFormat: "Keep Original",
    customSuffix: "",
    conflictPolicy: "overwrite",
    tileSize: "Auto (0)",
    gpuId: "auto",
    useFp16: true,
  });
  const activePrefs = prefs || localPrefs;
  const setPref = useCallback(
    (patch) => {
      if (onChangePrefs) onChangePrefs(patch);
      else setLocalPrefs((p) => ({ ...p, ...patch }));
    },
    [onChangePrefs]
  );

  const mode = activePrefs.mode;
  const setMode = (v) => setPref({ mode: v });
  const autoScale = activePrefs.autoScale;
  const setAutoScale = (v) => setPref({ autoScale: v });
  const colorTier = activePrefs.colorTier;
  const setColorTier = (v) => setPref({ colorTier: v });
  const colorDenoiseMode = activePrefs.colorDenoiseMode;
  const setColorDenoiseMode = (v) => setPref({ colorDenoiseMode: v });
  const selectedWfId = activePrefs.selectedWfId;
  const setSelectedWfId = (v) => setPref({ selectedWfId: v });
  const [editingWf, setEditingWf] = useState(null);
  const family = activePrefs.family;
  const setFamily = (v) => setPref({ family: v });
  const modelId = activePrefs.modelId;
  const setModelId = (v) => setPref({ modelId: v });
  const postResizeMode = activePrefs.postResizeMode;
  const setPostResizeMode = (v) => setPref({ postResizeMode: v });
  const outputFormat = activePrefs.outputFormat;
  const setOutputFormat = (v) => setPref({ outputFormat: v });
  const customSuffix = activePrefs.customSuffix;
  const setCustomSuffix = (v) => setPref({ customSuffix: v });
  const conflictPolicy = activePrefs.conflictPolicy;
  const setConflictPolicy = (v) => setPref({ conflictPolicy: v });
  const tileSize = activePrefs.tileSize;
  const setTileSize = (v) => setPref({ tileSize: v });
  const gpuId = activePrefs.gpuId;
  const setGpuId = (v) => setPref({ gpuId: v });
  const useFp16 = activePrefs.useFp16;
  const setUseFp16 = (v) => setPref({ useFp16: v });

  // Live Queue Routing Inspection
  const [routeReport, setRouteReport] = useState(null);
  const [routeError, setRouteError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [routingModalOpen, setRoutingModalOpen] = useState(false);
  const analyzeSeqRef = useRef(0);
  const selectedFilesKey = useMemo(() => (selectedFiles || []).join("\n"), [selectedFiles]);

  const familyModels = useMemo(
    () => janaiModels.filter((m) => m.family === family),
    [janaiModels, family]
  );

  const selectedMeta = useMemo(
    () => janaiModels.find((m) => m.id === modelId) || familyModels[0] || null,
    [janaiModels, familyModels, modelId]
  );

  const activeWorkflow = useMemo(
    () => allWorkflows.find((w) => w.id === selectedWfId) || allWorkflows[0] || EMPTY_DRAFT,
    [allWorkflows, selectedWfId]
  );

  const lastAppliedExternalTickRef = useRef(0);

  useEffect(() => {
    if (
      externalModelSelection?.model_id &&
      externalModelSelection.tick &&
      externalModelSelection.tick !== lastAppliedExternalTickRef.current
    ) {
      const hit = janaiModels.find((m) => m.id === externalModelSelection.model_id);
      if (hit) {
        lastAppliedExternalTickRef.current = externalModelSelection.tick;
        setPref({ mode: "single", family: hit.family, modelId: hit.id });
      }
    }
  }, [externalModelSelection, janaiModels, setPref]);

  useEffect(() => {
    if (familyModels.length > 0 && !familyModels.some((m) => m.id === modelId)) {
      setPref({ modelId: familyModels[0].id });
    }
  }, [familyModels, modelId, setPref]);

  const previewScaleLabel = useMemo(() => {
    if (mode === "single") return `${selectedMeta?.scale || 2}x`;
    if (mode === "workflow") {
      return activeWorkflow.grayscale_scale === "4x" ? "4x" : "2x";
    }
    return autoScale;
  }, [mode, selectedMeta, activeWorkflow, autoScale]);

  useEffect(() => {
    const suf = customSuffix.trim() || `_janai${previewScaleLabel}`;
    const ext = outputFormat === "Keep Original" ? "" : outputFormat.toLowerCase();
    const perFileSuffixes = {};
    if (!customSuffix.trim() && mode !== "single" && routeReport?.routes?.length) {
      for (const r of routeReport.routes) {
        if (r.path && r.scale) {
          perFileSuffixes[r.path] = `_janai${r.scale}x`;
        }
      }
    }
    onPreviewRuleChange({ suffix: suf, ext, perFileSuffixes });
  }, [customSuffix, previewScaleLabel, outputFormat, mode, routeReport, onPreviewRuleChange]);

  const autoConfig = useMemo(
    () => ({
      scale: autoScale,
      manga_scale_mode: autoScale,
      color_scale_mode: autoScale,
      color_tier: colorTier,
      color_denoise_mode: colorDenoiseMode,
    }),
    [autoScale, colorTier, colorDenoiseMode]
  );

  const runRouteAnalysis = useCallback(async () => {
    if (!selectedFilesKey || mode === "single") {
      setRouteReport(null);
      setRouteError("");
      setAnalyzing(false);
      return;
    }
    const seq = ++analyzeSeqRef.current;
    setAnalyzing(true);
    setRouteError("");
    try {
      const wfPayload = editingWf || activeWorkflow;
      const paths = selectedFilesKey.split("\n").filter(Boolean);
      const res = await apiPost("/api/janai/analyze", {
        paths,
        mode,
        auto_config: autoConfig,
        workflow: wfPayload,
      });
      if (seq === analyzeSeqRef.current) {
        setRouteReport(res);
      }
    } catch (err) {
      if (seq === analyzeSeqRef.current) {
        setRouteReport(null);
        setRouteError(err?.message || "Failed to analyze queued files");
      }
    } finally {
      if (seq === analyzeSeqRef.current) {
        setAnalyzing(false);
      }
    }
  }, [selectedFilesKey, mode, autoConfig, activeWorkflow, editingWf]);

  useEffect(() => {
    runRouteAnalysis();
  }, [runRouteAnalysis, bootstrap?.model_catalog]);

  // Workflow CRUD helpers
  const startNewWorkflow = () => {
    setEditingWf({
      ...EMPTY_DRAFT,
      id: `custom_${Date.now()}`,
      name: `Custom Workflow ${customWorkflows.length + 1}`,
      builtin: false,
    });
  };

  const duplicateActiveWorkflow = () => {
    setEditingWf({
      ...activeWorkflow,
      id: `custom_${Date.now()}`,
      name: `${activeWorkflow.name} (Copy)`,
      builtin: false,
    });
  };

  const saveDraftWorkflow = async () => {
    if (!editingWf || !editingWf.name.trim()) return;
    const clean = { ...editingWf, name: editingWf.name.trim(), builtin: false };
    const exists = customWorkflows.some((w) => w.id === clean.id);
    const nextList = exists
      ? customWorkflows.map((w) => (w.id === clean.id ? clean : w))
      : [...customWorkflows, clean];
    await onSaveSettings?.({ janai_workflows: nextList });
    setSelectedWfId(clean.id);
    setEditingWf(null);
  };

  const deleteCustomWorkflow = async (wfId) => {
    const nextList = customWorkflows.filter((w) => w.id !== wfId);
    await onSaveSettings?.({ janai_workflows: nextList });
    setEditingWf(null);
    setSelectedWfId(builtinWorkflows[0]?.id || "preset_mangajanai_2x");
  };

  const prog = selectedMeta ? downloadProgress[selectedMeta.id] : null;
  const isDownloadingSingle = Boolean(selectedMeta?.downloading || prog?.status === "downloading");
  const isSingleReady = Boolean(selectedMeta?.installed);
  const missingFromReport = routeReport?.missing_models || [];
  const installedJanaiCount = useMemo(
    () => janaiModels.filter((m) => m.installed).length,
    [janaiModels]
  );
  const activeMissingDownloads = useMemo(
    () =>
      missingFromReport.filter(
        (mid) => downloadProgress[mid]?.status === "downloading"
      ),
    [missingFromReport, downloadProgress]
  );
  const runtimeReady = bootstrap?.tools?.janai_ncnn !== false;

  const canLaunch =
    !isBusy &&
    selectedCount > 0 &&
    Boolean(outputDir) &&
    runtimeReady &&
    (mode !== "single" || isSingleReady) &&
    (mode === "single" || missingFromReport.length === 0);

  const handleLaunch = () => {
    if (!canLaunch) return;
    const keepOriginal = outputFormat === "Keep Original";
    onStart({
      mode,
      model_id: selectedMeta?.id || modelId,
      auto_config: autoConfig,
      workflow: editingWf || activeWorkflow,
      keep_format: keepOriginal,
      output_format: keepOriginal ? "PNG" : outputFormat,
      post_resize_mode: postResizeMode,
      custom_suffix: customSuffix.trim(),
      conflict_policy: conflictPolicy,
      tile_size: tileSize,
      gpu_id: gpuId,
      use_fp16: useFp16,
    });
  };

  const routeSummary = useMemo(() => {
    const routes = routeReport?.routes || [];
    let grayCount = 0;
    let colorCount = 0;
    const modelGroups = {};
    for (const r of routes) {
      if (r.analysis?.is_grayscale) grayCount += 1;
      else if (r.analysis) colorCount += 1;

      if (r.model_id) {
        const key = r.chain_model_id ? `${r.model_id}__${r.chain_model_id}` : r.model_id;
        if (!modelGroups[key]) {
          modelGroups[key] = {
            key,
            label: r.model_label || r.model_id,
            chainLabel: r.chain_model_label || "",
            scale: r.scale,
            installed: r.installed,
            count: 0,
          };
        }
        modelGroups[key].count += 1;
      }
    }
    return {
      total: routes.length,
      grayCount,
      colorCount,
      models: Object.values(modelGroups).sort((a, b) => b.count - a.count),
      routes,
    };
  }, [routeReport]);

  return (
    <div className="liquid-panel rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col gap-2.5 sm:gap-3 w-full lg:w-[372px] xl:w-[420px] 2xl:w-[456px] shrink-0 lg:h-full overflow-hidden">
      <div className="lg:flex-1 lg:overflow-y-auto lg:pr-1 space-y-2.5 sm:space-y-3">
        {/* Mode Switcher Header Card */}
        <GlassCard
          title="JaNai Routing & Models"
          rightHeader={
            onOpenModelManager && (
              <button
                type="button"
                onClick={onOpenModelManager}
                title="Browse & Download JaNai / NCNN model packs"
                className="liquid-pill-btn rounded-full px-2.5 py-1 text-[10.5px] font-semibold text-[var(--accent-hover)] flex items-center gap-1 cursor-pointer"
              >
                <Download className="w-3 h-3" />
                <span>Model Packs</span>
              </button>
            )
          }
        >
          {/* 3-Mode Segmented Control */}
          <div className="grid grid-cols-3 gap-1 p-1 rounded-xl bg-black/35 border border-white/10">
            {[
              { id: "auto", label: "Auto Detect", icon: Wand2 },
              { id: "workflow", label: "Workflows", icon: Workflow },
              { id: "single", label: "Single Model", icon: Sliders },
            ].map((m) => {
              const Icon = m.icon;
              const active = mode === m.id;
              return (
                <button
                  key={m.id}
                  type="button"
                  data-testid={`janai-mode-${m.id}`}
                  onClick={() => setMode(m.id)}
                  className={`rounded-lg py-1.5 px-2 text-[11.5px] font-semibold flex items-center justify-center gap-1 cursor-pointer transition-all ${
                    active
                      ? "bg-[var(--accent)] text-white shadow-[0_2px_10px_var(--accent-soft)]"
                      : "text-white/65 hover:text-white"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{m.label}</span>
                </button>
              );
            })}
          </div>

          {/* MODE 1: AUTO DETECT */}
          {mode === "auto" && (
            <div className="space-y-2.5 pt-1">
              <SettingRow label="Scale Factor">
                <div className="flex gap-1.5">
                  {["2x", "4x"].map((s) => {
                    const active = autoScale === s;
                    return (
                      <button
                        key={s}
                        type="button"
                        data-testid={`janai-auto-scale-${s}`}
                        onClick={() => setAutoScale(s)}
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

              <div className="rounded-xl bg-[var(--accent-soft)]/35 border border-[var(--accent)]/25 p-2.5 text-[11.5px] text-white/80 leading-relaxed">
                Auto-matches each <strong className="text-white">Grayscale page</strong> height to its closest{" "}
                <span className="text-[var(--accent-hover)] font-semibold">1200p–2048p ({autoScale})</span> model tier, and routes{" "}
                <strong className="text-white">Color pages</strong> to IllustrationJaNai V3.
              </div>

              <SettingRow label="Color Model">
                <select
                  value={colorTier}
                  onChange={(e) => setColorTier(e.target.value)}
                  data-testid="janai-auto-color-tier"
                  className="liquid-select w-full rounded-xl px-3 py-2 text-[12px]"
                >
                  <option value="fdat_m">FDAT-M V3 (Balanced • {autoScale})</option>
                  <option value="fdat_xl">FDAT-XL V3 (Max Detail • 4x)</option>
                  <option value="span">SPAN-S V3 (Ultra Fast • 2x)</option>
                </select>
              </SettingRow>

              <SettingRow label="Color Style">
                <select
                  value={colorDenoiseMode}
                  onChange={(e) => setColorDenoiseMode(e.target.value)}
                  className="liquid-select w-full rounded-xl px-3 py-2 text-[12px]"
                >
                  <option value="auto">Auto (JPG/WebP→Denoise • PNG→Detail)</option>
                  <option value="detail">Always V3 Detail (Clean Digital Art)</option>
                  <option value="denoise">Always V3 Denoise (Halftone / Compression)</option>
                </select>
              </SettingRow>

              {installedJanaiCount === 0 && (
                <div className="rounded-xl bg-amber-500/12 border border-amber-400/25 p-2.5 flex items-center justify-between gap-2 text-[11px] text-amber-200">
                  <span>0 / {janaiModels.length} JaNai models downloaded yet.</span>
                  {onOpenModelManager && (
                    <button
                      type="button"
                      onClick={onOpenModelManager}
                      className="liquid-pill-btn rounded-full px-2.5 py-0.5 text-[10.5px] font-semibold text-white shrink-0 cursor-pointer"
                    >
                      Download Packs
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* MODE 2: CUSTOM WORKFLOWS */}
          {mode === "workflow" && (
            <div className="space-y-2.5 pt-1">
              {!editingWf ? (
                <>
                  <SettingRow label="Workflow">
                    <select
                      value={activeWorkflow.id}
                      onChange={(e) => setSelectedWfId(e.target.value)}
                      data-testid="janai-workflow-select"
                      className="liquid-select w-full rounded-xl px-3 py-2 text-[12px] font-medium"
                    >
                      {builtinWorkflows.length > 0 && (
                        <optgroup label="Built-in Presets">
                          {builtinWorkflows.map((w) => (
                            <option key={w.id} value={w.id}>
                              {w.name}
                            </option>
                          ))}
                        </optgroup>
                      )}
                      {customWorkflows.length > 0 && (
                        <optgroup label="Saved Custom Workflows">
                          {customWorkflows.map((w) => (
                            <option key={w.id} value={w.id}>
                              {w.name}
                            </option>
                          ))}
                        </optgroup>
                      )}
                    </select>
                  </SettingRow>

                  <div className="rounded-xl bg-black/30 border border-white/10 p-2.5 space-y-2 text-[11.5px]">
                    <p className="text-white/75 leading-relaxed">
                      {activeWorkflow.description || "Custom B&W + Color model chain"}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      <button
                        type="button"
                        onClick={startNewWorkflow}
                        data-testid="janai-new-workflow-btn"
                        className="liquid-pill-btn rounded-full px-2.5 py-1 text-[11px] font-semibold text-white flex items-center gap-1 cursor-pointer"
                      >
                        <Plus className="w-3 h-3" /> New Workflow
                      </button>
                      <button
                        type="button"
                        onClick={duplicateActiveWorkflow}
                        className="liquid-pill-btn rounded-full px-2.5 py-1 text-[11px] font-semibold text-white/80 flex items-center gap-1 cursor-pointer"
                      >
                        <Copy className="w-3 h-3" /> {activeWorkflow.builtin ? "Clone & Edit" : "Duplicate"}
                      </button>
                      {!activeWorkflow.builtin && (
                        <>
                          <button
                            type="button"
                            onClick={() => setEditingWf({ ...activeWorkflow })}
                            className="liquid-pill-btn rounded-full px-2.5 py-1 text-[11px] font-semibold text-[var(--accent-hover)] cursor-pointer"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteCustomWorkflow(activeWorkflow.id)}
                            className="liquid-pill-btn rounded-full px-2.5 py-1 text-[11px] font-semibold text-rose-300 hover:bg-rose-500/20 flex items-center gap-1 cursor-pointer"
                          >
                            <Trash2 className="w-3 h-3" /> Delete
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                /* Workflow Builder Form */
                <div className="rounded-xl bg-black/35 border border-white/15 p-3 space-y-2.5" data-testid="janai-workflow-editor">
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] font-bold text-[var(--accent-hover)]">Custom Workflow Builder</span>
                    <button
                      type="button"
                      onClick={() => setEditingWf(null)}
                      className="text-[11px] text-white/60 hover:text-white cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>

                  <SettingRow label="Name">
                    <input
                      type="text"
                      value={editingWf.name}
                      onChange={(e) => setEditingWf((p) => ({ ...p, name: e.target.value }))}
                      className="liquid-input w-full rounded-xl px-2.5 py-1.5 text-[12px]"
                    />
                  </SettingRow>

                  <SettingRow label="B&W Manga">
                    <select
                      value={editingWf.grayscale_strategy}
                      onChange={(e) => setEditingWf((p) => ({ ...p, grayscale_strategy: e.target.value }))}
                      className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[11.5px]"
                    >
                      <option value="auto_tier">Auto Height Tier (1200p–2048p)</option>
                      <option value="specific">Use Specific Fixed Model</option>
                    </select>
                  </SettingRow>

                  {editingWf.grayscale_strategy === "auto_tier" ? (
                    <SettingRow label="B&W Scale">
                      <select
                        value={editingWf.grayscale_scale === "4x" ? "4x" : "2x"}
                        onChange={(e) => setEditingWf((p) => ({ ...p, grayscale_scale: e.target.value }))}
                        className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[11.5px]"
                      >
                        <option value="2x">2x (Auto 1200p–2048p Tier)</option>
                        <option value="4x">4x (Auto 1200p–2048p Tier)</option>
                      </select>
                    </SettingRow>
                  ) : (
                    <SettingRow label="B&W Model">
                      <select
                        value={editingWf.grayscale_model_id}
                        onChange={(e) => setEditingWf((p) => ({ ...p, grayscale_model_id: e.target.value }))}
                        className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[11.5px]"
                      >
                        {janaiModels.map((m) => (
                          <option key={m.id} value={m.id}>{m.label}</option>
                        ))}
                      </select>
                    </SettingRow>
                  )}

                  <SettingRow label="B&W Chain 2">
                    <select
                      value={editingWf.grayscale_chain_id || ""}
                      onChange={(e) => setEditingWf((p) => ({ ...p, grayscale_chain_id: e.target.value }))}
                      className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[11.5px]"
                    >
                      <option value="">None (Single Pass)</option>
                      {janaiModels.map((m) => (
                        <option key={m.id} value={m.id}>+ {m.label}</option>
                      ))}
                    </select>
                  </SettingRow>

                  <SettingRow label="Color Model">
                    <select
                      value={editingWf.color_model_id}
                      onChange={(e) => setEditingWf((p) => ({ ...p, color_model_id: e.target.value }))}
                      className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[11.5px]"
                    >
                      {janaiModels.map((m) => (
                        <option key={m.id} value={m.id}>{m.label}</option>
                      ))}
                    </select>
                  </SettingRow>

                  <GlassSwitch
                    checked={editingWf.color_auto_denoise !== false}
                    onChange={(v) => setEditingWf((p) => ({ ...p, color_auto_denoise: v }))}
                    label="Use Denoise Variant on JPG/WebP"
                    sublabel="Applies separate denoise model to lossy color scans"
                  />

                  {editingWf.color_auto_denoise !== false && (
                    <SettingRow label="Color Denoise">
                      <select
                        value={editingWf.color_denoise_model_id}
                        onChange={(e) => setEditingWf((p) => ({ ...p, color_denoise_model_id: e.target.value }))}
                        className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[11.5px]"
                      >
                        {janaiModels.map((m) => (
                          <option key={m.id} value={m.id}>{m.label}</option>
                        ))}
                      </select>
                    </SettingRow>
                  )}

                  <SettingRow label="Color Chain 2">
                    <select
                      value={editingWf.color_chain_id || ""}
                      onChange={(e) => setEditingWf((p) => ({ ...p, color_chain_id: e.target.value }))}
                      className="liquid-select w-full rounded-xl px-2.5 py-1.5 text-[11.5px]"
                    >
                      <option value="">None (Single Pass)</option>
                      {janaiModels.map((m) => (
                        <option key={m.id} value={m.id}>+ {m.label}</option>
                      ))}
                    </select>
                  </SettingRow>

                  <button
                    type="button"
                    onClick={saveDraftWorkflow}
                    data-testid="janai-save-workflow-btn"
                    className="liquid-hero-btn w-full rounded-xl py-1.5 text-[12px] font-bold text-white flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>Save Custom Workflow</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* MODE 3: SINGLE MODEL */}
          {mode === "single" && (
            <div className="space-y-2.5 pt-1">
              <SettingRow label="Model Family">
                <select
                  value={family}
                  onChange={(e) => setFamily(e.target.value)}
                  data-testid="janai-family-select"
                  className="liquid-select w-full rounded-xl px-3 py-2 text-[12px] sm:text-[12.5px] font-medium"
                >
                  {FAMILIES.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </select>
              </SettingRow>

              <SettingRow label="Model Variant">
                <select
                  value={selectedMeta?.id || modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  data-testid="janai-model-select"
                  className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
                >
                  {familyModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label} ({m.scale}x • {m.installed ? (m.source === "local" ? "Local" : "Ready") : `${m.size_mb} MB`})
                    </option>
                  ))}
                </select>
              </SettingRow>

              {selectedMeta && (
                <div className="rounded-xl bg-black/30 border border-white/10 p-2.5 space-y-2 text-[11.5px]">
                  <div className="flex flex-wrap items-center justify-between gap-1.5">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="px-2 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent-hover)] font-bold text-[10.5px]">
                        {selectedMeta.scale}x Native
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-white/10 text-white/75 font-semibold text-[10.5px]">
                        Align {selectedMeta.align}px • {selectedMeta.size_mb} MB
                      </span>
                    </div>
                    {isSingleReady ? (
                      <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 font-bold text-[10.5px] flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        {selectedMeta.source === "local" ? "Local ncnn" : "Downloaded"}
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-400/30 font-semibold text-[10.5px]">
                        Not Installed
                      </span>
                    )}
                  </div>

                  <p className="text-white/70 leading-relaxed">{selectedMeta.description}</p>

                  {!isSingleReady && onInstallModel && (
                    <div className="pt-1 space-y-1.5">
                      {isDownloadingSingle && (
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10.5px] text-white/70">
                            <span>{prog?.detail || "Downloading..."}</span>
                            <span className="tabular-nums font-bold">{prog?.percent || 0}%</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                            <div
                              style={{
                                width: `${Math.max(4, prog?.percent || 0)}%`,
                                background: "linear-gradient(90deg, var(--accent), var(--accent-hover))",
                              }}
                              className="h-full rounded-full transition-all duration-150"
                            />
                          </div>
                        </div>
                      )}
                      <button
                        type="button"
                        disabled={isDownloadingSingle}
                        onClick={() => onInstallModel(selectedMeta.id)}
                        className="liquid-hero-btn w-full rounded-xl py-1.5 text-[11.5px] font-semibold text-white flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                      >
                        {isDownloadingSingle ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Download className="w-3.5 h-3.5" />
                        )}
                        <span>
                          {isDownloadingSingle
                            ? "Downloading from GitHub..."
                            : `Download Model (${selectedMeta.size_mb} MB)`}
                        </span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* LIVE QUEUE ROUTING PREVIEW (Auto Detect & Workflows) */}
          {mode !== "single" && selectedFiles.length > 0 && (
            <div className="rounded-xl bg-black/30 border border-white/10 p-2.5 space-y-2 text-[11.5px]">
              <div className="flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => setRoutingModalOpen(true)}
                  data-testid="janai-routing-eye-btn"
                  title="Open Queue Routing Inspector window"
                  className="font-bold text-white/90 hover:text-[var(--accent-hover)] flex items-center gap-1.5 cursor-pointer text-left min-w-0"
                >
                  {analyzing ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--accent-hover)] shrink-0" />
                  ) : (
                    <span className="w-6 h-6 rounded-lg bg-[var(--accent-soft)] border border-[var(--accent)]/30 flex items-center justify-center shrink-0">
                      <Eye className="w-3.5 h-3.5 text-[var(--accent-hover)]" />
                    </span>
                  )}
                  <span className="truncate">
                    {analyzing && routeSummary.total === 0
                      ? `Analyzing ${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"}...`
                      : `Queue Routing (${routeSummary.grayCount} B&W • ${routeSummary.colorCount} Color)`}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setRoutingModalOpen(true)}
                  className="liquid-pill-btn rounded-full px-2.5 py-0.5 text-[10.5px] font-semibold text-[var(--accent-hover)] flex items-center gap-1 shrink-0 cursor-pointer"
                >
                  <Eye className="w-3 h-3" />
                  <span>Details</span>
                </button>
              </div>

              {routeError && (
                <div className="rounded-lg bg-rose-500/15 border border-rose-400/30 px-2.5 py-1.5 text-[11px] text-rose-200 flex items-center justify-between gap-2">
                  <span className="truncate">{routeError}</span>
                  <button
                    type="button"
                    onClick={runRouteAnalysis}
                    className="text-[10.5px] font-bold underline shrink-0 cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              )}

              {routeSummary.models.length > 0 && (
                <div className="space-y-1">
                  {routeSummary.models.map((grp) => (
                    <div
                      key={grp.key}
                      className="rounded-lg bg-white/[0.05] border border-white/10 px-2.5 py-1.5 flex items-center justify-between gap-2 text-[11px]"
                    >
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span
                          className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                            grp.installed ? "bg-emerald-400" : "bg-amber-400"
                          }`}
                        />
                        <span className="truncate font-semibold text-white/90" title={grp.chainLabel ? `${grp.label} → ${grp.chainLabel}` : grp.label}>
                          {grp.label}
                          {grp.chainLabel ? ` → ${grp.chainLabel}` : ""}
                        </span>
                      </div>
                      <span className="shrink-0 text-[10.5px] font-bold px-2 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent-hover)]">
                        {grp.count} file{grp.count === 1 ? "" : "s"}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {routeSummary.routes.length > 0 && (
                <div className="max-h-36 overflow-y-auto space-y-1 pr-1 pt-0.5 border-t border-white/10">
                  {routeSummary.routes.slice(0, 6).map((r) => {
                    const dimLabel = r.analysis
                      ? `${r.analysis.width}×${r.analysis.height}`
                      : "";
                    const kindBadge = r.analysis?.is_grayscale
                      ? `B&W ${dimLabel} → ${r.analysis.nearest_tier}p`
                      : `Color ${dimLabel}`;
                    const modelText = r.chain_model_label
                      ? `${r.model_label} → ${r.chain_model_label}`
                      : r.model_label || r.model_id;
                    return (
                      <div
                        key={r.path}
                        className="rounded-lg bg-white/[0.04] border border-white/[0.07] px-2.5 py-1.5 space-y-0.5 text-[10.5px]"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate font-semibold text-white/90" title={r.path}>
                            {r.name}
                          </span>
                          <span className="shrink-0 text-white/55 font-medium">
                            {kindBadge}
                          </span>
                        </div>
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className="truncate text-[var(--accent-hover)] font-semibold"
                            title={r.model_id}
                          >
                            → {modelText}
                          </span>
                          <span className="shrink-0 text-[10px] font-bold text-white/70">
                            {r.scale}x
                          </span>
                        </div>
                      </div>
                    );
                  })}
                  {routeSummary.routes.length > 6 && (
                    <button
                      type="button"
                      onClick={() => setRoutingModalOpen(true)}
                      className="w-full py-1 text-[10.5px] font-semibold text-[var(--accent-hover)] hover:underline cursor-pointer"
                    >
                      + View all {routeSummary.routes.length} files in Queue Routing Inspector →
                    </button>
                  )}
                </div>
              )}

              {missingFromReport.length > 0 && (
                <div className="rounded-lg bg-amber-500/15 border border-amber-400/30 p-2 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-amber-200 font-semibold text-[11px]">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{missingFromReport.length} routed model(s) not downloaded yet</span>
                  </div>
                  {activeMissingDownloads.map((mid) => {
                    const p = downloadProgress[mid];
                    return (
                      <div key={mid} className="space-y-0.5 text-[10px] text-white/75">
                        <div className="flex justify-between gap-2">
                          <span className="truncate">{mid}</span>
                          <span className="shrink-0 tabular-nums font-bold">{p?.percent || 0}%</span>
                        </div>
                        <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                          <div
                            style={{
                              width: `${Math.max(4, p?.percent || 0)}%`,
                              background: "linear-gradient(90deg, var(--accent), var(--accent-hover))",
                            }}
                            className="h-full rounded-full transition-all duration-150"
                          />
                        </div>
                      </div>
                    );
                  })}
                  {onInstallModel && (
                    <button
                      type="button"
                      disabled={activeMissingDownloads.length > 0}
                      onClick={() => missingFromReport.forEach((mid) => onInstallModel(mid))}
                      className="liquid-hero-btn w-full rounded-lg py-1 text-[11px] font-semibold text-white flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                    >
                      {activeMissingDownloads.length > 0 ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Download className="w-3 h-3" />
                      )}
                      <span>
                        {activeMissingDownloads.length > 0
                          ? `Downloading (${activeMissingDownloads.length} active)...`
                          : `Download Missing Models (${missingFromReport.length})`}
                      </span>
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          <SettingRow label="Post-Resize / Fit" hint="Optional LANCZOS fit">
            <select
              value={postResizeMode}
              onChange={(e) => setPostResizeMode(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
            >
              <option value="Native">Native Full Scale</option>
              <option value="50% SSAA">50% SSAA (Crisp Anti-Aliased)</option>
              <option value="2160p Height Fit">2160p Height Fit (4K Manga Reader)</option>
              <option value="3200p Height Fit">3200p Height Fit (Hi-Res Reader)</option>
              <option value="4096p Height Fit">4096p Height Fit (Archival Cap)</option>
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

        <CollapsibleGlassCard title="Vulkan NCNN, Tiling & Naming" defaultOpen={false}>
          <SettingRow label="Custom Suffix">
            <input
              type="text"
              placeholder={`Default (_janai${previewScaleLabel})`}
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

          <SettingRow label="VRAM Tile Size" hint="Prevents GPU OOM">
            <select
              value={tileSize}
              onChange={(e) => setTileSize(e.target.value)}
              className="liquid-select w-full rounded-xl px-3 py-1.5 text-[12px]"
            >
              <option value="Auto (0)">Auto (Smart Tiling)</option>
              <option value="128">128px Tiles (Low VRAM)</option>
              <option value="256">256px Tiles (Balanced)</option>
              <option value="384">384px Tiles (8GB+ VRAM)</option>
              <option value="512">512px Tiles (High VRAM)</option>
              <option value="full">No Tiling (Full Frame)</option>
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

          <GlassSwitch
            checked={useFp16}
            onChange={setUseFp16}
            label="FP16 Vulkan Compute"
            sublabel="2x faster on modern GPUs; auto-falls back to FP32"
          />
        </CollapsibleGlassCard>
      </div>

      {!runtimeReady && (
        <div className="rounded-xl bg-rose-500/15 border border-rose-400/30 px-3 py-2 text-[11.5px] text-rose-200 flex items-center gap-2">
          <Cpu className="w-4 h-4 shrink-0" />
          <span>Python `ncnn` package is not installed (`pip install ncnn numpy`).</span>
        </div>
      )}

      <button
        type="button"
        disabled={!canLaunch}
        onClick={handleLaunch}
        data-testid="janai-launch-btn"
        className="liquid-hero-btn w-full rounded-2xl py-3 text-[14px] font-bold text-white flex items-center justify-center gap-2 cursor-pointer shrink-0"
      >
        <Sparkles className="w-4 h-4" />
        <span>
          {isBusy
            ? "Processing..."
            : mode === "single" && !isSingleReady
            ? "Download Model First"
            : missingFromReport.length > 0
            ? "Download Missing Models"
            : `Run ${mode === "auto" ? "Auto Detect" : mode === "workflow" ? "Workflow" : "Upscale"} (${selectedCount || 0})`}
        </span>
      </button>

      <QueueRoutingModal
        open={routingModalOpen}
        onClose={() => setRoutingModalOpen(false)}
        modeLabel={
          mode === "workflow"
            ? `Workflow: ${(editingWf || activeWorkflow)?.name || "Custom"}`
            : `Auto Detect (${autoScale})`
        }
        analyzing={analyzing}
        routeError={routeError}
        routeSummary={routeSummary}
        missingModels={missingFromReport}
        onRefresh={runRouteAnalysis}
        onInstallModel={onInstallModel}
      />
    </div>
  );
}
