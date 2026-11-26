import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Cpu, CheckCircle2, XCircle, X } from "lucide-react";

import {
  apiDelete,
  apiGet,
  apiPost,
  nativeBrowseFiles,
  nativeBrowseFolder,
  openExternalUrl,
  openFolderInOS,
  subscribeEvents,
} from "./api/client";
import LiquidBackdrop, { applyThemeCssVars } from "./components/LiquidBackdrop";
import FloatingDock from "./components/FloatingDock";
import QueuePane from "./components/QueuePane";
import ConverterWorkspace from "./components/ConverterWorkspace";
import UpscalerWorkspace from "./components/UpscalerWorkspace";
import DenoiserWorkspace from "./components/DenoiserWorkspace";
import JanaiWorkspace from "./components/JanaiWorkspace";
import StitcherWorkspace from "./components/StitcherWorkspace";
import SettingsWorkspace from "./components/SettingsWorkspace";
import ProgressHud from "./components/ProgressHud";
import { CompareModal, QuickPreviewModal } from "./components/CompareModal";
import ModelManagerModal from "./components/ModelManagerModal";

function emptyWorkspaceQueue() {
  return { items: [], selectedMap: {}, outputDir: "", autoOpen: false };
}

export default function App() {
  const [bootstrap, setBootstrap] = useState(null);
  const [activeTab, setActiveTab] = useState("converter");
  const [activeTheme, setActiveTheme] = useState("Blue (Default)");
  const [logs, setLogs] = useState([]);

  // Separate queues per workspace just like desktop workflow
  const [queues, setQueues] = useState({
    converter: emptyWorkspaceQueue(),
    upscaler: emptyWorkspaceQueue(),
    denoiser: emptyWorkspaceQueue(),
    janai: emptyWorkspaceQueue(),
  });
  const [previewRules, setPreviewRules] = useState({
    converter: { suffix: "", ext: "png" },
    upscaler: { suffix: "_2x", ext: "" },
    denoiser: { suffix: "_denoised", ext: "" },
    janai: { suffix: "_janai2x", ext: "" },
  });

  // Stitcher queue state
  const [stitchGroups, setStitchGroups] = useState([]);
  const [stitchSelectedIds, setStitchSelectedIds] = useState({});
  const [stitchOutputDir, setStitchOutputDir] = useState("");
  const [stitchAutoOpen, setStitchAutoOpen] = useState(false);

  // Modals & Streaming Job State
  const [activeJob, setActiveJob] = useState(null);
  const [completion, setCompletion] = useState(null);
  const [errorAlert, setErrorAlert] = useState("");
  const [compareBatches, setCompareBatches] = useState([]);
  const [activeCompareBatchId, setActiveCompareBatchId] = useState("");
  const [compareOpen, setCompareOpen] = useState(false);
  const [quickPreviewPath, setQuickPreviewPath] = useState("");
  const [gpuModalOpen, setGpuModalOpen] = useState(false);
  const [modelModalOpen, setModelModalOpen] = useState(false);
  const [modelModalEngine, setModelModalEngine] = useState("all");
  const [modelDownloads, setModelDownloads] = useState({});
  const [externalUpscaleModel, setExternalUpscaleModel] = useState(null);
  const [externalJanaiModel, setExternalJanaiModel] = useState(null);
  const [janaiPrefs, setJanaiPrefs] = useState({
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
  const [dndResetTick, setDndResetTick] = useState(0);

  const activeTabRef = useRef(activeTab);
  activeTabRef.current = activeTab;
  const autoOpenRef = useRef({ converter: false, upscaler: false, denoiser: false, janai: false, stitcher: false });

  useEffect(() => {
    autoOpenRef.current = {
      converter: queues.converter.autoOpen,
      upscaler: queues.upscaler.autoOpen,
      denoiser: queues.denoiser.autoOpen,
      janai: queues.janai.autoOpen,
      stitcher: stitchAutoOpen,
    };
  }, [queues, stitchAutoOpen]);

  // Initial load from FastAPI backend
  useEffect(() => {
    apiGet("/api/bootstrap")
      .then((data) => {
        setBootstrap(data);
        const theme = data.current_theme || "Blue (Default)";
        setActiveTheme(theme);
        applyThemeCssVars(theme);
        setLogs(data.logs || []);
      })
      .catch((err) => setErrorAlert(`Backend connection failed: ${err.message}`));
  }, []);

  const mergeProbedFiles = useCallback((ws, probedList) => {
    if (!probedList || probedList.length === 0) return;
    setQueues((prev) => {
      const cur = prev[ws];
      const existing = new Set(cur.items.map((it) => it.path));
      const added = probedList.filter((it) => it.path && !existing.has(it.path));
      if (added.length === 0) return prev;
      const nextMap = { ...cur.selectedMap };
      for (const it of added) nextMap[it.path] = true;
      return {
        ...prev,
        [ws]: { ...cur, items: [...cur.items, ...added], selectedMap: nextMap },
      };
    });
  }, []);

  const handleDropPathsToWorkspace = useCallback(
    async (ws, paths) => {
      if (!paths || paths.length === 0) return;
      if (ws === "stitcher") {
        const resScan = await Promise.all(
          paths.map((p) => apiPost("/api/scan-folders", { folder: p, stitcher_mode: true }).catch(() => ({ groups: [] })))
        );
        const folderGroups = resScan.flatMap((r) => r.groups || []);
        const probeRes = await apiPost("/api/probe", { paths });
        const looseImgs = (probeRes.files || []).filter((f) =>
          ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif"].includes(f.ext)
        );
        setStitchGroups((prev) => {
          const existingIds = new Set(prev.map((g) => g.id));
          const next = [...prev];
          for (const g of folderGroups) {
            if (!existingIds.has(g.id)) {
              next.push(g);
              existingIds.add(g.id);
            }
          }
          if (looseImgs.length > 0) {
            const vid = `virtual:Group ${next.length + 1}`;
            next.push({
              id: vid,
              name: vid.replace("virtual:", ""),
              is_virtual: true,
              files: looseImgs.map((x) => x.path),
              count: looseImgs.length,
              size_str: "",
            });
          }
          return next;
        });
        return;
      }

      const exts = bootstrap?.formats?.[ws === "converter" ? "input" : ws === "denoiser" ? "denoise" : "upscale"];
      const res = await apiPost("/api/probe", { paths, allowed_exts: exts });
      mergeProbedFiles(ws, res.files || []);
    },
    [bootstrap, mergeProbedFiles]
  );

  // WebSocket live event subscriber
  useEffect(() => {
    return subscribeEvents((msg) => {
      if (msg.type === "log") {
        setLogs((prev) => [...prev.slice(-299), { timestamp: msg.timestamp, level: msg.level, message: msg.message }]);
      } else if (msg.type === "progress") {
        setActiveJob({
          job_id: msg.job_id,
          workspace: msg.workspace,
          percent: msg.percent,
          eta: msg.eta,
          speed: msg.speed,
        });
      } else if (msg.type === "completed") {
        setActiveJob(null);
        if (msg.pairs && msg.pairs.length > 0) {
          const bid = msg.job_id || `batch_${Date.now()}`;
          const batchEntry = {
            id: bid,
            workspace: msg.workspace || "job",
            createdAt: Date.now(),
            pairs: msg.pairs,
          };
          setCompareBatches((prev) => [batchEntry, ...prev.filter((b) => b.id !== bid)].slice(0, 20));
          setActiveCompareBatchId(bid);
        }
        if (autoOpenRef.current[msg.workspace] && msg.output_dir) {
          openFolderInOS(msg.output_dir);
        } else {
          setCompletion(msg);
        }
      } else if (msg.type === "cancelled") {
        setActiveJob(null);
      } else if (msg.type === "error") {
        setErrorAlert(msg.message || "Unknown processing error");
      } else if (msg.type === "dnd_drop" && Array.isArray(msg.paths)) {
        setDndResetTick((t) => t + 1);
        const tab = activeTabRef.current;
        const targetTab = ["converter", "upscaler", "denoiser", "janai", "stitcher"].includes(tab) ? tab : "converter";
        if (targetTab !== tab) setActiveTab(targetTab);
        handleDropPathsToWorkspace(targetTab, msg.paths);
      } else if (msg.type === "model_download" && msg.model_id) {
        setModelDownloads((prev) => ({
          ...prev,
          [msg.model_id]: {
            status: msg.status,
            percent: msg.percent ?? 0,
            detail: msg.detail || "",
          },
        }));
        if (Array.isArray(msg.catalog)) {
          setBootstrap((prev) => (prev ? { ...prev, model_catalog: msg.catalog } : prev));
        }
      }
    });
  }, [handleDropPathsToWorkspace]);

  // Prevent WebView2 / browser navigation on global dragover/drop without blocking bubbling to document
  useEffect(() => {
    const preventDragNav = (e) => {
      e.preventDefault();
      if (e.dataTransfer) {
        e.dataTransfer.dropEffect = "copy";
      }
    };
    const handleWindowDrop = (e) => {
      e.preventDefault();
      setDndResetTick((t) => t + 1);
    };
    const handleWindowDragEnd = () => setDndResetTick((t) => t + 1);

    window.addEventListener("dragenter", preventDragNav);
    window.addEventListener("dragover", preventDragNav);
    window.addEventListener("drop", handleWindowDrop);
    window.addEventListener("dragend", handleWindowDragEnd);
    window.addEventListener("blur", handleWindowDragEnd);
    return () => {
      window.removeEventListener("dragenter", preventDragNav);
      window.removeEventListener("dragover", preventDragNav);
      window.removeEventListener("drop", handleWindowDrop);
      window.removeEventListener("dragend", handleWindowDragEnd);
      window.removeEventListener("blur", handleWindowDragEnd);
    };
  }, []);

  // Global keyboard shortcuts
  useEffect(() => {
    const mapKeys = {
      1: "converter",
      2: "upscaler",
      3: "denoiser",
      4: "janai",
      5: "stitcher",
      6: "settings",
    };
    const onKey = (e) => {
      if (e.ctrlKey && mapKeys[e.key]) {
        e.preventDefault();
        setActiveTab(mapKeys[e.key]);
      } else if (e.ctrlKey && (e.key === "b" || e.key === "B")) {
        e.preventDefault();
        setCompareOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const installModelPack = useCallback(async (modelId) => {
    setModelDownloads((prev) => {
      if (prev[modelId]?.status === "downloading") return prev;
      return {
        ...prev,
        [modelId]: { status: "downloading", percent: 2, detail: "Starting..." },
      };
    });
    try {
      await apiPost("/api/models/install", { model_id: modelId });
    } catch (err) {
      setModelDownloads((prev) => ({
        ...prev,
        [modelId]: { status: "error", percent: 0, detail: err.message || "Download failed" },
      }));
      setErrorAlert(err.message);
    }
  }, []);

  const handleBrowseFiles = async (ws) => {
    const exts = bootstrap?.formats?.[ws === "converter" ? "input" : ws === "denoiser" ? "denoise" : "upscale"];
    const chosen = await nativeBrowseFiles(exts);
    if (chosen && chosen.length > 0) {
      const res = await apiPost("/api/probe", { paths: chosen, allowed_exts: exts });
      mergeProbedFiles(ws, res.files || []);
    }
  };

  const handleBrowseFolder = async (ws) => {
    const folder = await nativeBrowseFolder();
    if (folder) {
      const exts = bootstrap?.formats?.[ws === "converter" ? "input" : ws === "denoiser" ? "denoise" : "upscale"];
      const res = await apiPost("/api/scan-folders", { folder, allowed_exts: exts, stitcher_mode: false });
      mergeProbedFiles(ws, res.files || []);
    }
  };

  const handleBrowseOutput = async (ws) => {
    const folder = await nativeBrowseFolder();
    if (!folder) return;
    if (ws === "stitcher") {
      setStitchOutputDir(folder);
    } else {
      setQueues((prev) => ({
        ...prev,
        [ws]: { ...prev[ws], outputDir: folder },
      }));
    }
  };

  const startWorkspaceJob = async (ws, payload) => {
    setCompletion(null);
    setErrorAlert("");
    const q = queues[ws];
    const selectedFiles = q ? q.items.filter((it) => q.selectedMap[it.path] !== false).map((it) => it.path) : [];
    const body =
      ws === "stitcher"
        ? { ...payload, output_dir: stitchOutputDir }
        : { ...payload, files: selectedFiles, output_dir: q.outputDir };

    try {
      const res = await apiPost("/api/jobs/start", { workspace: ws, payload: body });
      setActiveJob({ job_id: res.job_id, workspace: ws, percent: 2, eta: "Starting...", speed: "" });
    } catch (err) {
      setErrorAlert(err.message);
    }
  };

  const handleCancelJob = async (jobId) => {
    try {
      await apiPost("/api/jobs/cancel", { job_id: jobId });
    } catch {
      // ignore
    }
    setActiveJob(null);
  };

  const handleChangeTheme = async (themeName) => {
    setActiveTheme(themeName);
    applyThemeCssVars(themeName);
    try {
      await apiPost("/api/settings", { settings: { theme: themeName } });
    } catch {
      // ignore
    }
  };

  const handleSaveSettings = async (patch) => {
    try {
      const res = await apiPost("/api/settings", { settings: patch });
      setBootstrap((prev) => (prev ? { ...prev, settings: res.settings } : prev));
    } catch (err) {
      setErrorAlert(err.message);
    }
  };

  const gpuShortLabel = useMemo(() => {
    const gpus = bootstrap?.gpus || [];
    if (gpus.length && bootstrap?.vulkan_support) {
      return gpus[0].replace("AMD Radeon ", "").replace("NVIDIA GeForce ", "").trim();
    }
    return bootstrap?.vulkan_support ? "Vulkan GPU Ready" : "CPU Compute";
  }, [bootstrap]);

  const currentQ = queues[activeTab];
  const currentSelectedCount = currentQ
    ? currentQ.items.filter((it) => currentQ.selectedMap[it.path] !== false).length
    : 0;

  const janaiSelectedFiles = useMemo(() => {
    const q = queues.janai;
    if (!q || !q.items) return [];
    return q.items.filter((it) => q.selectedMap[it.path] !== false).map((it) => it.path);
  }, [queues.janai]);

  const updateConverterPreviewRule = useCallback(
    (rule) => setPreviewRules((p) => ({ ...p, converter: rule })),
    []
  );
  const updateUpscalerPreviewRule = useCallback(
    (rule) => setPreviewRules((p) => ({ ...p, upscaler: rule })),
    []
  );
  const updateDenoiserPreviewRule = useCallback(
    (rule) => setPreviewRules((p) => ({ ...p, denoiser: rule })),
    []
  );
  const updateJanaiPreviewRule = useCallback(
    (rule) => setPreviewRules((p) => ({ ...p, janai: rule })),
    []
  );
  const patchJanaiPrefs = useCallback(
    (patch) => setJanaiPrefs((prev) => ({ ...prev, ...patch })),
    []
  );

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden relative">
      <LiquidBackdrop />

      <FloatingDock
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        version={bootstrap?.version || "7.5"}
        gpuLabel={gpuShortLabel}
        vulkanOk={Boolean(bootstrap?.vulkan_support)}
        hasComparePairs={compareBatches.some((b) => b.pairs.length > 0)}
        onOpenCompare={() => {
          if (compareBatches.length > 0 && !compareBatches.some((b) => b.id === activeCompareBatchId)) {
            setActiveCompareBatchId(compareBatches[0].id);
          }
          setCompareOpen(true);
        }}
        onOpenGpuInfo={() => setGpuModalOpen(true)}
        onOpenGithub={() => openExternalUrl("https://github.com/GuptaAman777/psd-converter")}
      />

      {/* Main Fluid Workspace Stage */}
      <main className="flex-1 min-h-0 p-2 sm:p-3 lg:p-3.5 pt-1.5 sm:pt-2 overflow-y-auto lg:overflow-hidden">
        <div className="max-w-[2200px] mx-auto h-auto lg:h-full">
        <AnimatePresence mode="wait">
          {["converter", "upscaler", "denoiser", "janai"].includes(activeTab) && (
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 8, scale: 0.992 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.992 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-col lg:flex-row gap-2.5 sm:gap-3.5 lg:h-full lg:min-h-0"
            >
              {activeTab === "converter" && (
                <ConverterWorkspace
                  bootstrap={bootstrap}
                  selectedCount={currentSelectedCount}
                  outputDir={currentQ.outputDir}
                  isBusy={Boolean(activeJob)}
                  onPreviewRuleChange={updateConverterPreviewRule}
                  onStart={(payload) => startWorkspaceJob("converter", payload)}
                />
              )}

              {activeTab === "upscaler" && (
                <UpscalerWorkspace
                  bootstrap={bootstrap}
                  selectedCount={currentSelectedCount}
                  outputDir={currentQ.outputDir}
                  isBusy={Boolean(activeJob)}
                  externalModelSelection={externalUpscaleModel}
                  onOpenModelManager={() => {
                    setModelModalEngine("realesr");
                    setModelModalOpen(true);
                  }}
                  onPreviewRuleChange={updateUpscalerPreviewRule}
                  onStart={(payload) => startWorkspaceJob("upscaler", payload)}
                />
              )}

              {activeTab === "denoiser" && (
                <DenoiserWorkspace
                  bootstrap={bootstrap}
                  selectedCount={currentSelectedCount}
                  outputDir={currentQ.outputDir}
                  isBusy={Boolean(activeJob)}
                  onPreviewRuleChange={updateDenoiserPreviewRule}
                  onStart={(payload) => startWorkspaceJob("denoiser", payload)}
                />
              )}

              {activeTab === "janai" && (
                <JanaiWorkspace
                  bootstrap={bootstrap}
                  prefs={janaiPrefs}
                  onChangePrefs={patchJanaiPrefs}
                  selectedFiles={janaiSelectedFiles}
                  selectedCount={currentSelectedCount}
                  outputDir={currentQ.outputDir}
                  isBusy={Boolean(activeJob)}
                  externalModelSelection={externalJanaiModel}
                  downloadProgress={modelDownloads}
                  onInstallModel={installModelPack}
                  onSaveSettings={handleSaveSettings}
                  onOpenModelManager={() => {
                    setModelModalEngine("janai_ncnn");
                    setModelModalOpen(true);
                  }}
                  onPreviewRuleChange={updateJanaiPreviewRule}
                  onStart={(payload) => startWorkspaceJob("janai", payload)}
                />
              )}

              <div className="flex-1 min-w-0 min-h-[420px] lg:min-h-0 lg:h-full">
                <QueuePane
                  items={currentQ.items}
                  selectedMap={currentQ.selectedMap}
                  outputDir={currentQ.outputDir}
                  autoOpen={currentQ.autoOpen}
                  previewRule={previewRules[activeTab]}
                  dndResetTick={dndResetTick}
                  onAddFiles={() => handleBrowseFiles(activeTab)}
                  onAddFolder={() => handleBrowseFolder(activeTab)}
                  onDropPaths={(paths) => handleDropPathsToWorkspace(activeTab, paths)}
                  onToggleItem={(path, val) =>
                    setQueues((prev) => ({
                      ...prev,
                      [activeTab]: {
                        ...prev[activeTab],
                        selectedMap: { ...prev[activeTab].selectedMap, [path]: val },
                      },
                    }))
                  }
                  onToggleAll={(val, visiblePaths) =>
                    setQueues((prev) => {
                      const nextMap = { ...prev[activeTab].selectedMap };
                      for (const vp of visiblePaths) nextMap[vp] = val;
                      return { ...prev, [activeTab]: { ...prev[activeTab], selectedMap: nextMap } };
                    })
                  }
                  onRemoveItem={(path) =>
                    setQueues((prev) => ({
                      ...prev,
                      [activeTab]: {
                        ...prev[activeTab],
                        items: prev[activeTab].items.filter((it) => it.path !== path),
                      },
                    }))
                  }
                  onRemoveUnchecked={() =>
                    setQueues((prev) => ({
                      ...prev,
                      [activeTab]: {
                        ...prev[activeTab],
                        items: prev[activeTab].items.filter(
                          (it) => prev[activeTab].selectedMap[it.path] !== false
                        ),
                      },
                    }))
                  }
                  onClear={() =>
                    setQueues((prev) => ({
                      ...prev,
                      [activeTab]: { ...prev[activeTab], items: [], selectedMap: {} },
                    }))
                  }
                  onBrowseOutputDir={() => handleBrowseOutput(activeTab)}
                  onOpenOutputDir={() => openFolderInOS(currentQ.outputDir)}
                  onSetAutoOpen={(v) =>
                    setQueues((prev) => ({
                      ...prev,
                      [activeTab]: { ...prev[activeTab], autoOpen: v },
                    }))
                  }
                  onPreviewFile={(fp) => setQuickPreviewPath(fp)}
                />
              </div>
            </motion.div>
          )}

          {activeTab === "stitcher" && (
            <motion.div
              key="stitcher"
              initial={{ opacity: 0, y: 8, scale: 0.992 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.992 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="lg:h-full lg:min-h-0"
            >
              <StitcherWorkspace
                groups={stitchGroups}
                selectedGroupIds={stitchSelectedIds}
                outputDir={stitchOutputDir}
                autoOpen={stitchAutoOpen}
                isBusy={Boolean(activeJob)}
                dndResetTick={dndResetTick}
                onToggleGroup={(id, val) =>
                  setStitchSelectedIds((p) => ({ ...p, [id]: val }))
                }
                onAddFilesGroup={async () => {
                  const chosen = await nativeBrowseFiles(bootstrap?.formats?.upscale);
                  if (chosen && chosen.length > 0) {
                    setStitchGroups((prev) => [
                      ...prev,
                      {
                        id: `virtual:Custom Set ${prev.length + 1}`,
                        name: `Custom Set ${prev.length + 1}`,
                        is_virtual: true,
                        files: chosen,
                        count: chosen.length,
                      },
                    ]);
                  }
                }}
                onAddFolderTree={async () => {
                  const folder = await nativeBrowseFolder();
                  if (folder) handleDropPathsToWorkspace("stitcher", [folder]);
                }}
                onDropPaths={(paths) => handleDropPathsToWorkspace("stitcher", paths)}
                onRemoveGroup={(id) =>
                  setStitchGroups((prev) => prev.filter((g) => g.id !== id))
                }
                onClearGroups={() => {
                  setStitchGroups([]);
                  setStitchSelectedIds({});
                }}
                onBrowseOutputDir={() => handleBrowseOutput("stitcher")}
                onOpenOutputDir={() => openFolderInOS(stitchOutputDir)}
                onSetAutoOpen={setStitchAutoOpen}
                onPreviewFile={(fp) => setQuickPreviewPath(fp)}
                onStart={(payload) => startWorkspaceJob("stitcher", payload)}
              />
            </motion.div>
          )}

          {activeTab === "settings" && (
            <motion.div
              key="settings"
              initial={{ opacity: 0, y: 8, scale: 0.992 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.992 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="lg:h-full lg:min-h-0"
            >
              <SettingsWorkspace
                bootstrap={bootstrap}
                activeTheme={activeTheme}
                onChangeTheme={handleChangeTheme}
                onSaveSettings={handleSaveSettings}
                logs={logs}
                onClearLogs={() => setLogs([])}
                onJumpToTab={(id) => setActiveTab(id)}
                onOpenGpuInfo={() => setGpuModalOpen(true)}
                onOpenModelManager={() => {
                  setModelModalEngine("all");
                  setModelModalOpen(true);
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
        </div>
      </main>

      <ProgressHud
        activeJob={activeJob}
        completion={completion}
        errorAlert={errorAlert}
        liquidGlass={bootstrap?.settings?.progress_liquid_glass !== false}
        onCancel={handleCancelJob}
        onOpenFolder={openFolderInOS}
        onCompare={(pairs, meta) => {
          const bid = meta?.job_id || `batch_${Date.now()}`;
          if (pairs && pairs.length > 0) {
            setCompareBatches((prev) => {
              if (prev.some((b) => b.id === bid)) return prev;
              return [
                {
                  id: bid,
                  workspace: meta?.workspace || "job",
                  createdAt: Date.now(),
                  pairs,
                },
                ...prev,
              ].slice(0, 20);
            });
            setActiveCompareBatchId(bid);
          }
          setCompletion(null);
          setCompareOpen(true);
        }}
        onDismissComplete={() => setCompletion(null)}
        onDismissError={() => setErrorAlert("")}
      />

      <CompareModal
        open={compareOpen}
        batches={compareBatches}
        activeBatchId={activeCompareBatchId}
        onSelectBatch={(bid) => setActiveCompareBatchId(bid)}
        onRemovePair={(bid, pairIdx) => {
          setCompareBatches((prev) => {
            const next = prev
              .map((b) =>
                b.id === bid
                  ? { ...b, pairs: b.pairs.filter((_, i) => i !== pairIdx) }
                  : b
              )
              .filter((b) => b.pairs.length > 0);
            if (!next.some((b) => b.id === activeCompareBatchId)) {
              setActiveCompareBatchId(next[0]?.id || "");
            }
            return next;
          });
        }}
        onRemoveBatch={(bid) => {
          setCompareBatches((prev) => {
            const next = prev.filter((b) => b.id !== bid);
            if (activeCompareBatchId === bid) {
              setActiveCompareBatchId(next[0]?.id || "");
            }
            return next;
          });
        }}
        onClose={() => setCompareOpen(false)}
      />

      <QuickPreviewModal
        filePath={quickPreviewPath}
        onClose={() => setQuickPreviewPath("")}
      />

      <ModelManagerModal
        open={modelModalOpen}
        onClose={() => setModelModalOpen(false)}
        catalog={bootstrap?.model_catalog || []}
        downloadProgress={modelDownloads}
        initialEngineFilter={modelModalEngine}
        confirmInstall={bootstrap?.settings?.confirm_model_install !== false}
        confirmDelete={bootstrap?.settings?.confirm_model_delete !== false}
        onSetConfirmInstall={(val) => handleSaveSettings({ confirm_model_install: val })}
        onSetConfirmDelete={(val) => handleSaveSettings({ confirm_model_delete: val })}
        onInstall={installModelPack}
        onRemove={async (modelId) => {
          try {
            const res = await apiDelete(`/api/models/${encodeURIComponent(modelId)}`);
            setBootstrap((prev) => (prev ? { ...prev, model_catalog: res.models } : prev));
            setModelDownloads((prev) => {
              const next = { ...prev };
              delete next[modelId];
              return next;
            });
          } catch (err) {
            setErrorAlert(err.message);
          }
        }}
        onUseModel={(item) => {
          setModelModalOpen(false);
          if (item.engine === "janai_ncnn") {
            setActiveTab("janai");
            setExternalJanaiModel({ model_id: item.id, tick: Date.now() });
          } else {
            setActiveTab("upscaler");
            setExternalUpscaleModel({ model: item.engine || "realesr", style_model: item.id, tick: Date.now() });
          }
        }}
      />

      {/* Hardware Diagnostics Modal */}
      <AnimatePresence>
        {gpuModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setGpuModalOpen(false)}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xl flex items-center justify-center p-6"
          >
            <motion.div
              initial={{ scale: 0.94, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.94, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="liquid-dock rounded-3xl w-full max-w-lg p-6 space-y-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Cpu className="w-5 h-5 text-[var(--accent-hover)]" />
                  <span className="text-[16px] font-bold text-white">Vulkan Compute & AI Engines</span>
                </div>
                <button
                  type="button"
                  onClick={() => setGpuModalOpen(false)}
                  className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="rounded-2xl bg-black/35 border border-white/10 p-3.5 space-y-2 text-[12.5px]">
                <div className="font-semibold text-white/85">Detected Physical GPUs:</div>
                {(bootstrap?.gpus || []).length > 0 ? (
                  bootstrap.gpus.map((g, i) => (
                    <div key={g} className="text-emerald-300 font-medium">
                      • GPU {i}: {g}
                    </div>
                  ))
                ) : (
                  <div className="text-amber-300">No discrete Vulkan GPU reported (CPU -1 fallback enabled)</div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2 text-[12px]">
                {Object.entries(bootstrap?.tools || {}).map(([name, ok]) => (
                  <div
                    key={name}
                    className="rounded-xl bg-black/30 border border-white/10 px-3 py-2 flex items-center justify-between"
                  >
                    <span className="font-bold uppercase text-white/90">{name}</span>
                    {ok ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-400" />
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
