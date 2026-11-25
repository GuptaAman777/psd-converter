import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Layers, FolderPlus, FilePlus2, Trash2, X, FolderOpen, ArrowUpRight, UploadCloud } from "lucide-react";
import { apiPost, previewUrl } from "../api/client";
import { GlassCard, SettingRow, GlassSwitch } from "./GlassPrimitives";

export default function StitcherWorkspace({
  groups,
  selectedGroupIds,
  onToggleGroup,
  onAddFilesGroup,
  onAddFolderTree,
  onRemoveGroup,
  onClearGroups,
  onDropPaths,
  outputDir,
  onBrowseOutputDir,
  onOpenOutputDir,
  autoOpen,
  onSetAutoOpen,
  onPreviewFile,
  isBusy,
  onStart,
  dndResetTick = 0,
}) {
  const [layoutMode, setLayoutMode] = useState("Vertical (Top to Bottom)");
  const [gridColumns, setGridColumns] = useState(2);
  const [alignment, setAlignment] = useState("Center");
  const [resizeOption, setResizeOption] = useState("Don't Resize");
  const [sortMode, setSortMode] = useState("natural");
  const [reverseOrder, setReverseOrder] = useState(false);

  const [spacing, setSpacing] = useState(0);
  const [outerPadding, setOuterPadding] = useState(0);
  const [bgChoice, setBgChoice] = useState("Transparent");
  const [customHex, setCustomHex] = useState("#1E1E2E");

  const [outputFormat, setOutputFormat] = useState("PNG");
  const [quality, setQuality] = useState(95);

  const [estimates, setEstimates] = useState({});
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    setIsDragging(false);
  }, [dndResetTick]);

  useEffect(() => {
    if (!groups.length) {
      setEstimates({});
      return;
    }
    let cancelled = false;
    apiPost("/api/stitch-estimate", {
      groups: groups.map((g) => ({ id: g.id, files: g.files || [] })),
      layout_mode: layoutMode,
      grid_columns: gridColumns,
      spacing,
      outer_padding: outerPadding,
      output_format: outputFormat,
      sort_mode: sortMode,
      reverse_order: reverseOrder,
    })
      .then((res) => {
        if (cancelled) return;
        const map = {};
        for (const item of res.estimates || []) {
          map[item.id] = item;
        }
        setEstimates(map);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [groups, layoutMode, gridColumns, spacing, outerPadding, outputFormat, sortMode, reverseOrder]);

  const activeGroups = groups.filter((g) => selectedGroupIds[g.id] !== false);

  const handleLaunch = () => {
    onStart({
      groups: activeGroups,
      layout_mode: layoutMode,
      grid_columns: gridColumns,
      alignment,
      resize_option: resizeOption,
      sort_mode: sortMode,
      reverse_order: reverseOrder,
      spacing,
      outer_padding: outerPadding,
      bg_color: bgChoice === "Custom" ? customHex : bgChoice,
      output_format: outputFormat,
      quality,
    });
  };

  return (
    <div className="flex flex-col lg:flex-row gap-2.5 sm:gap-3.5 lg:h-full lg:min-h-0">
      {/* Left Configuration Column */}
      <div className="liquid-panel rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col gap-3 w-full lg:w-[356px] xl:w-[404px] 2xl:w-[440px] shrink-0 lg:h-full overflow-hidden">
        <div className="lg:flex-1 lg:overflow-y-auto lg:pr-1 space-y-2.5 sm:space-y-3">
          <GlassCard title="Canvas Layout & Ordering">
            <SettingRow label="Stitch Direction">
              <select
                value={layoutMode}
                onChange={(e) => setLayoutMode(e.target.value)}
                className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
              >
                <option>Vertical (Top to Bottom)</option>
                <option>Vertical (Bottom to Top)</option>
                <option>Horizontal (Left to Right)</option>
                <option>Horizontal (Right to Left)</option>
                <option>Grid (Matrix Layout)</option>
              </select>
            </SettingRow>

            <AnimatePresence initial={false}>
              {layoutMode.includes("Grid") && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <SettingRow label="Grid Columns">
                    <input
                      type="number"
                      min={2}
                      max={20}
                      value={gridColumns}
                      onChange={(e) => setGridColumns(Math.max(2, Math.min(20, Number(e.target.value) || 2)))}
                      className="liquid-input w-full rounded-xl px-3 py-1.5 text-[12.5px]"
                    />
                  </SettingRow>
                </motion.div>
              )}
            </AnimatePresence>

            <SettingRow label="Alignment">
              <select
                value={alignment}
                onChange={(e) => setAlignment(e.target.value)}
                className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
              >
                <option>Center</option>
                <option>Start (Left/Top)</option>
                <option>End (Right/Bottom)</option>
              </select>
            </SettingRow>

            <SettingRow label="Resize Images">
              <select
                value={resizeOption}
                onChange={(e) => setResizeOption(e.target.value)}
                className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
              >
                <option>Don't Resize</option>
                <option>Match Smallest</option>
                <option>Match Largest</option>
                <option>Match First</option>
              </select>
            </SettingRow>

            <SettingRow label="Stacking Order">
              <select
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value)}
                className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
              >
                <option value="natural">Natural Order (1, 2, 10)</option>
                <option value="alpha">Alphabetical (A–Z)</option>
                <option value="mtime">Modified Time</option>
              </select>
            </SettingRow>

            <GlassSwitch
              checked={reverseOrder}
              onChange={setReverseOrder}
              label="Reverse Sequence"
            />
          </GlassCard>

          <GlassCard title="Spacing, Margins & Matte">
            <SettingRow label="Panel Gap (px)" hint="Negative overlaps">
              <input
                type="number"
                min={-200}
                max={500}
                value={spacing}
                onChange={(e) => setSpacing(Number(e.target.value) || 0)}
                className="liquid-input w-full rounded-xl px-3 py-1.5 text-[12.5px]"
              />
            </SettingRow>

            <SettingRow label="Outer Margin (px)">
              <input
                type="number"
                min={0}
                max={200}
                value={outerPadding}
                onChange={(e) => setOuterPadding(Math.max(0, Number(e.target.value) || 0))}
                className="liquid-input w-full rounded-xl px-3 py-1.5 text-[12.5px]"
              />
            </SettingRow>

            <SettingRow label="Canvas Matte">
              <div className="flex items-center gap-2">
                <select
                  value={bgChoice}
                  onChange={(e) => setBgChoice(e.target.value)}
                  className="liquid-select flex-1 rounded-xl px-3 py-2 text-[12.5px]"
                >
                  <option value="Transparent">Transparent</option>
                  <option value="White">White</option>
                  <option value="Black">Black</option>
                  <option value="Custom">Custom Color</option>
                </select>
                {bgChoice === "Custom" && (
                  <input
                    type="color"
                    value={customHex}
                    onChange={(e) => setCustomHex(e.target.value)}
                    className="w-9 h-9 rounded-lg bg-transparent border border-white/20 cursor-pointer"
                  />
                )}
              </div>
            </SettingRow>
          </GlassCard>

          <GlassCard title="Output Encoding">
            <SettingRow label="Format">
              <select
                value={outputFormat}
                onChange={(e) => setOutputFormat(e.target.value)}
                className="liquid-select w-full rounded-xl px-3 py-2 text-[12.5px]"
              >
                <option value="PNG">PNG</option>
                <option value="JPEG">JPEG</option>
                <option value="WEBP">WEBP</option>
              </select>
            </SettingRow>

            {outputFormat !== "PNG" && (
              <SettingRow label="Encode Quality">
                <div className="flex items-center gap-2.5">
                  <input
                    type="range"
                    min={50}
                    max={100}
                    value={quality}
                    onChange={(e) => setQuality(Number(e.target.value))}
                    className="liquid-slider flex-1"
                  />
                  <span className="text-[12px] font-bold w-10 text-right">{quality}%</span>
                </div>
              </SettingRow>
            )}
          </GlassCard>
        </div>

        <button
          type="button"
          disabled={isBusy || activeGroups.length === 0 || !outputDir}
          onClick={handleLaunch}
          className="liquid-hero-btn w-full rounded-2xl py-3 text-[14px] font-bold text-white flex items-center justify-center gap-2 cursor-pointer shrink-0"
        >
          <Layers className="w-4 h-4" />
          <span>{isBusy ? "Stitching Canvases..." : `Stitch ${activeGroups.length || ""} Group${activeGroups.length === 1 ? "" : "s"}`}</span>
        </button>
      </div>

      {/* Right Stitch Queue + Filmstrip Cards */}
      <div
        className="liquid-panel rounded-2xl sm:rounded-3xl p-2.5 sm:p-4 flex-1 flex flex-col gap-2.5 sm:gap-3 min-w-0 min-h-[380px] lg:min-h-0 lg:h-full relative overflow-hidden"
        onDragEnter={(e) => {
          const types = e.dataTransfer?.types;
          if (types && !Array.from(types).includes("Files")) return;
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          if (!e.currentTarget.contains(e.relatedTarget)) setIsDragging(false);
        }}
        onDragOver={(e) => {
          const types = e.dataTransfer?.types;
          if (types && !Array.from(types).includes("Files")) return;
          e.preventDefault();
          if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
        }}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          // Let drop bubble up to `document` so pywebview's DOMEventHandler resolves full OS file/folder paths.
          const paths = Array.from(e.dataTransfer?.files || [])
            .map((f) => f.pywebviewFullPath || f.path || "")
            .filter(Boolean);
          if (paths.length) onDropPaths(paths);
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
            <button
              type="button"
              onClick={onAddFilesGroup}
              className="liquid-hero-btn rounded-full px-3 sm:px-3.5 py-1.5 text-[11.5px] sm:text-[12px] font-semibold text-white flex items-center gap-1.5 cursor-pointer"
            >
              <FilePlus2 className="w-3.5 h-3.5" />
              <span>Add Files Group</span>
            </button>
            <button
              type="button"
              onClick={onAddFolderTree}
              className="liquid-pill-btn rounded-full px-2.5 sm:px-3 py-1.5 text-[11.5px] sm:text-[12px] font-semibold text-white/90 flex items-center gap-1.5 cursor-pointer"
            >
              <FolderPlus className="w-3.5 h-3.5" />
              <span>Folder Tree</span>
            </button>
          </div>

          <div className="flex items-center gap-2.5 sm:gap-3 ml-auto">
            <span className="text-[11.5px] sm:text-[12px] text-white/60 font-medium">{groups.length} group(s)</span>
            <button
              type="button"
              disabled={groups.length === 0}
              onClick={onClearGroups}
              className="liquid-pill-btn rounded-full px-2.5 sm:px-3 py-1.5 text-[11px] font-semibold text-rose-300 border-rose-400/25 disabled:opacity-40 cursor-pointer flex items-center gap-1"
            >
              <Trash2 className="w-3 h-3" />
              <span>Clear</span>
            </button>
          </div>
        </div>

        <div className="relative flex-1 min-h-[210px] rounded-2xl bg-black/25 border border-white/10 overflow-y-auto p-2.5 sm:p-3 space-y-2.5">
          {groups.length === 0 ? (
            <div className="h-full min-h-[200px] flex flex-col items-center justify-center text-center p-3 sm:px-6">
              <div className="max-w-md w-full rounded-2xl sm:rounded-3xl p-5 sm:p-7 liquid-card flex flex-col items-center gap-2.5 sm:gap-3">
                <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-[var(--accent-soft)] border border-white/25 flex items-center justify-center">
                  <UploadCloud className="w-6 h-6 sm:w-7 sm:h-7 text-[var(--accent-hover)]" />
                </div>
                <div className="text-[14.5px] sm:text-[16px] font-bold text-white">Drop Chapter Folders or Image Sets</div>
                <div className="text-[11.5px] sm:text-[12px] text-white/60">
                  Builds continuous strips or grids with safe WebP/JPEG pixel limit chunking
                </div>
                <div className="flex flex-wrap justify-center items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={onAddFilesGroup}
                    className="liquid-hero-btn rounded-full px-4 py-1.5 text-[12px] font-semibold cursor-pointer"
                  >
                    + Files Group
                  </button>
                  <button
                    type="button"
                    onClick={onAddFolderTree}
                    className="liquid-pill-btn rounded-full px-4 py-1.5 text-[12px] font-semibold cursor-pointer"
                  >
                    Folder Tree
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <AnimatePresence mode="popLayout">
              {groups.map((grp) => {
                const est = estimates[grp.id];
                const files = est?.sorted_files || grp.files || [];
                const checked = selectedGroupIds[grp.id] !== false;
                return (
                  <motion.div
                    layout
                    key={grp.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="liquid-card rounded-2xl p-3.5 space-y-2.5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => onToggleGroup(grp.id, e.target.checked)}
                          className="accent-[var(--accent)] w-4 h-4 cursor-pointer"
                        />
                        <div className="min-w-0">
                          <div className="text-[13px] font-bold text-white truncate">
                            {grp.name} → {grp.name}_stitched.{outputFormat.toLowerCase()}
                          </div>
                          <div className="text-[11px] text-white/60 mt-0.5">
                            {est?.count ?? files.length} images • {est?.size_str || grp.size_str || "0 B"}
                            {est?.estimate ? ` • ${est.estimate}` : ""}
                          </div>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => onRemoveGroup(grp.id)}
                        className="w-7 h-7 rounded-full bg-rose-500/15 border border-rose-400/25 hover:bg-rose-500 text-rose-300 hover:text-white flex items-center justify-center cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* Horizontal Filmstrip Previews */}
                    {files.length > 0 && (
                      <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
                        {files.slice(0, 6).map((fp) => (
                          <button
                            key={fp}
                            type="button"
                            onClick={() => onPreviewFile(fp)}
                            title={`${fp.split(/[/\\]/).pop()} (click to preview)`}
                            className="w-12 h-12 rounded-xl bg-black/40 border border-white/10 hover:border-[var(--accent)] overflow-hidden shrink-0 flex items-center justify-center cursor-pointer transition-colors"
                          >
                            <img
                              src={previewUrl(fp, 120)}
                              alt=""
                              loading="lazy"
                              draggable={false}
                              className="max-w-full max-h-full object-contain"
                            />
                          </button>
                        ))}
                        {files.length > 6 && (
                          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-white/10 text-white/75 shrink-0">
                            +{files.length - 6} more
                          </span>
                        )}
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          )}

          {isDragging && (
            <div className="absolute inset-0 z-30 flex items-center justify-center rounded-2xl bg-[#070b16]/85 backdrop-blur-xl border-2 border-dashed border-[var(--accent)] pointer-events-none">
              <div className="liquid-dock rounded-3xl px-8 py-6 text-center">
                <div className="text-[16px] font-bold text-white">Drop Folders or Image Group</div>
              </div>
            </div>
          )}
        </div>

        {/* Output Bar */}
        <div className="liquid-card rounded-2xl px-3 sm:px-3.5 py-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <div className="flex items-center gap-2 min-w-[160px] flex-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--accent-hover)] shrink-0">Output</span>
            <FolderOpen className="w-4 h-4 text-white/55 shrink-0" />
            <span className={`text-[12px] truncate ${outputDir ? "text-white font-medium" : "text-white/45"}`}>
              {outputDir || "Choose destination folder..."}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 ml-auto shrink-0">
            <div className="shrink-0 whitespace-nowrap">
              <GlassSwitch checked={autoOpen} onChange={onSetAutoOpen} label="Auto-open" />
            </div>
            <button
              type="button"
              onClick={onBrowseOutputDir}
              className="liquid-hero-btn rounded-full px-3 sm:px-3.5 py-1.5 text-[11.5px] font-semibold cursor-pointer"
            >
              Browse
            </button>
            <button
              type="button"
              disabled={!outputDir}
              onClick={onOpenOutputDir}
              className="liquid-pill-btn rounded-full px-2.5 sm:px-3 py-1.5 text-[11.5px] font-semibold disabled:opacity-35 flex items-center gap-1 cursor-pointer"
            >
              <span>Open</span>
              <ArrowUpRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
