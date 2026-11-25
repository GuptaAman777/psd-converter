import React, { useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  FilePlus2, FolderPlus, Search, LayoutList, LayoutGrid, FilterX,
  Trash2, Eye, X, FolderOpen, UploadCloud, Sparkles, ArrowUpRight, CheckSquare, Square
} from "lucide-react";
import { previewUrl } from "../api/client";
import { GlassSwitch } from "./GlassPrimitives";

function naturalCompare(a, b) {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}

function formatPredictedName(item, previewRule) {
  if (!previewRule || (!previewRule.suffix && !previewRule.ext)) return "";
  const dot = item.name.lastIndexOf(".");
  const stem = dot > 0 ? item.name.slice(0, dot) : item.name;
  const origExt = dot > 0 ? item.name.slice(dot + 1) : item.ext;
  const nextExt = previewRule.ext || origExt;
  return `${stem}${previewRule.suffix || ""}.${nextExt}`;
}

export default function QueuePane({
  items,
  selectedMap,
  onToggleItem,
  onToggleAll,
  onAddFiles,
  onAddFolder,
  onDropPaths,
  onRemoveItem,
  onRemoveUnchecked,
  onClear,
  outputDir,
  onBrowseOutputDir,
  onOpenOutputDir,
  autoOpen,
  onSetAutoOpen,
  onPreviewFile,
  previewRule,
  dndResetTick = 0,
  emptyTitle = "Drop Images, PSDs, PDFs or Folders",
  emptySub = "Supports PNG, JPEG, WEBP, BMP, TIFF, GIF, multi-page PDF & layered PSD",
}) {
  const [filterText, setFilterText] = useState("");
  const [sortMode, setSortMode] = useState("natural");
  const [viewMode, setViewMode] = useState("list");
  const [inspectedPath, setInspectedPath] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);

  React.useEffect(() => {
    dragCounter.current = 0;
    setIsDragging(false);
  }, [dndResetTick]);

  const visibleItems = useMemo(() => {
    const q = filterText.trim().toLowerCase();
    const filtered = q
      ? items.filter((it) => it.name.toLowerCase().includes(q) || it.path.toLowerCase().includes(q))
      : [...items];

    if (sortMode === "alpha") {
      filtered.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
    } else if (sortMode === "size") {
      filtered.sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0));
    } else if (sortMode === "format") {
      filtered.sort((a, b) => a.ext.localeCompare(b.ext) || naturalCompare(a.name, b.name));
    } else {
      filtered.sort((a, b) => naturalCompare(a.path, b.path));
    }
    return filtered;
  }, [items, filterText, sortMode]);

  const checkedCount = useMemo(
    () => items.filter((it) => selectedMap[it.path] !== false).length,
    [items, selectedMap]
  );

  const checkedVisibleCount = useMemo(
    () => visibleItems.filter((it) => selectedMap[it.path] !== false).length,
    [visibleItems, selectedMap]
  );

  const allVisibleChecked = visibleItems.length > 0 && checkedVisibleCount === visibleItems.length;

  const activeItem = useMemo(() => {
    return items.find((it) => it.path === inspectedPath) || visibleItems[0] || null;
  }, [items, visibleItems, inspectedPath]);

  const hasDraggedFiles = (e) => {
    const types = e.dataTransfer?.types;
    return !types || Array.from(types).includes("Files");
  };

  const handleDragEnter = (e) => {
    if (!hasDraggedFiles(e)) return;
    e.preventDefault();
    dragCounter.current += 1;
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    if (!hasDraggedFiles(e)) return;
    e.preventDefault();
    dragCounter.current = Math.max(0, dragCounter.current - 1);
    if (dragCounter.current === 0) setIsDragging(false);
  };

  const handleDragOver = (e) => {
    if (!hasDraggedFiles(e)) return;
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = "copy";
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    dragCounter.current = 0;
    setIsDragging(false);
    // Keep drop bubbling up to `document` so pywebview's DOMEventHandler resolves full OS file/folder paths.
    const fileList = Array.from(e.dataTransfer?.files || []);
    const paths = fileList
      .map((f) => f.pywebviewFullPath || f.path || "")
      .filter(Boolean);
    if (paths.length > 0) {
      onDropPaths(paths);
    }
  };

  return (
    <div
      className="liquid-panel rounded-2xl sm:rounded-3xl p-2.5 sm:p-4 flex flex-col gap-2.5 sm:gap-3 min-w-0 h-full relative overflow-hidden"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={onAddFiles}
            className="liquid-hero-btn rounded-full px-3 sm:px-3.5 py-1.5 text-[11.5px] sm:text-[12px] font-semibold text-white flex items-center gap-1.5 cursor-pointer"
          >
            <FilePlus2 className="w-3.5 h-3.5" />
            <span>Add Files</span>
          </button>

          <button
            type="button"
            onClick={onAddFolder}
            className="liquid-pill-btn rounded-full px-2.5 sm:px-3 py-1.5 text-[11.5px] sm:text-[12px] font-semibold text-white/90 flex items-center gap-1.5 cursor-pointer"
          >
            <FolderPlus className="w-3.5 h-3.5" />
            <span>Folder</span>
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 flex-1 min-w-[200px] justify-end">
          <div className="relative flex-1 min-w-[110px] max-w-[240px]">
            <Search className="w-3.5 h-3.5 text-white/45 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              placeholder="Filter filename..."
              className="liquid-input w-full rounded-full pl-8 pr-3 py-1.5 text-[12px]"
            />
          </div>

          <select
            value={sortMode}
            onChange={(e) => setSortMode(e.target.value)}
            className="liquid-select rounded-full px-2.5 sm:px-3 py-1.5 text-[11.5px] sm:text-[12px] font-medium cursor-pointer shrink-0"
          >
            <option value="natural">Natural</option>
            <option value="alpha">Name A–Z</option>
            <option value="size">File Size</option>
            <option value="format">Format</option>
          </select>

          {/* Segmented List / Grid Pill */}
          <div className="flex items-center p-0.5 rounded-full bg-black/35 border border-white/10 shrink-0">
            {[
              { id: "list", Icon: LayoutList, tip: "Detailed List" },
              { id: "grid", Icon: LayoutGrid, tip: "Thumbnail Cards" },
            ].map(({ id, Icon, tip }) => {
              const active = viewMode === id;
              return (
                <button
                  key={id}
                  type="button"
                  title={tip}
                  onClick={() => setViewMode(id)}
                  className={`relative w-7 h-7 rounded-full flex items-center justify-center cursor-pointer ${
                    active ? "text-white" : "text-white/50 hover:text-white"
                  }`}
                >
                  {active && (
                    <motion.div
                      layoutId="queueViewModePill"
                      transition={{ type: "spring", stiffness: 500, damping: 34 }}
                      className="absolute inset-0 rounded-full bg-[var(--accent)] shadow"
                    />
                  )}
                  <Icon className="w-3.5 h-3.5 relative z-10" />
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={onRemoveUnchecked}
            title="Remove unchecked items"
            className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center text-white/70 hover:text-white cursor-pointer shrink-0"
          >
            <FilterX className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={onClear}
            disabled={items.length === 0}
            className="liquid-pill-btn rounded-full px-2.5 sm:px-3 py-1.5 text-[11px] font-semibold text-rose-300 border-rose-400/25 hover:bg-rose-500/20 disabled:opacity-40 cursor-pointer flex items-center gap-1 shrink-0"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Subheader Select All Bar */}
      {items.length > 0 && (
        <div className="flex items-center justify-between gap-2 px-1.5 sm:px-2 py-0.5 text-[11px] text-white/65">
          <button
            type="button"
            onClick={() => onToggleAll(!allVisibleChecked, visibleItems.map((it) => it.path))}
            className="flex items-center gap-1.5 hover:text-white cursor-pointer font-medium"
          >
            {allVisibleChecked ? (
              <CheckSquare className="w-3.5 h-3.5 text-[var(--accent-hover)]" />
            ) : (
              <Square className="w-3.5 h-3.5 text-white/45" />
            )}
            <span>
              Select All ({checkedVisibleCount}/{visibleItems.length})
            </span>
          </button>
          <span className="truncate">{checkedCount} selected • {items.length} queued</span>
        </div>
      )}

      {/* Main Viewport */}
      <div className="relative flex-1 min-h-[210px] rounded-2xl bg-black/25 border border-white/10 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto p-2 sm:p-2.5">
          {items.length === 0 ? (
            <div className="h-full min-h-[190px] flex flex-col items-center justify-center text-center p-3 sm:p-6">
              <motion.div
                initial={{ scale: 0.94, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className="max-w-md w-full rounded-2xl sm:rounded-3xl p-5 sm:p-7 liquid-card flex flex-col items-center gap-2.5 sm:gap-3"
              >
                <div
                  className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl flex items-center justify-center border border-white/25"
                  style={{
                    background: "linear-gradient(145deg, var(--accent-soft), rgba(255,255,255,0.06))",
                    boxShadow: "0 8px 28px var(--accent-soft)",
                  }}
                >
                  <UploadCloud className="w-6 h-6 sm:w-7 sm:h-7 text-[var(--accent-hover)]" />
                </div>
                <div className="text-[14.5px] sm:text-[16px] font-bold text-white">{emptyTitle}</div>
                <div className="text-[11.5px] sm:text-[12px] text-white/60 leading-relaxed">{emptySub}</div>
                <div className="flex flex-wrap justify-center items-center gap-2 pt-1.5">
                  <button
                    type="button"
                    onClick={onAddFiles}
                    className="liquid-hero-btn rounded-full px-4 py-1.5 text-[12px] font-semibold text-white cursor-pointer"
                  >
                    + Choose Files
                  </button>
                  <button
                    type="button"
                    onClick={onAddFolder}
                    className="liquid-pill-btn rounded-full px-4 py-1.5 text-[12px] font-semibold text-white/85 cursor-pointer"
                  >
                    Browse Folder
                  </button>
                </div>
              </motion.div>
            </div>
          ) : visibleItems.length === 0 ? (
            <div className="py-12 text-center text-[13px] text-white/50">
              No queued items match &ldquo;{filterText}&rdquo;
            </div>
          ) : viewMode === "grid" ? (
            <div className="grid grid-cols-1 min-[460px]:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 min-[2000px]:grid-cols-5 gap-2 sm:gap-2.5">
              <AnimatePresence mode="popLayout">
                {visibleItems.map((item) => {
                  const isChecked = selectedMap[item.path] !== false;
                  const isSelected = activeItem?.path === item.path;
                  return (
                    <motion.div
                      layout
                      key={item.path}
                      initial={{ opacity: 0, scale: 0.94 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ duration: 0.2 }}
                      onClick={() => setInspectedPath(item.path)}
                      onDoubleClick={() => onPreviewFile(item.path)}
                      className={`liquid-card rounded-2xl p-2.5 cursor-pointer flex flex-col gap-2 ${
                        isSelected ? "ring-1 ring-[var(--accent)] bg-white/10" : ""
                      } ${!isChecked ? "opacity-55" : ""}`}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <div className="flex items-center gap-1.5">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={(e) => {
                              e.stopPropagation();
                              onToggleItem(item.path, e.target.checked);
                            }}
                            className="accent-[var(--accent)] w-3.5 h-3.5 cursor-pointer"
                          />
                          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-white/10 text-white/80">
                            {item.ext}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onRemoveItem(item.path);
                          }}
                          className="w-6 h-6 rounded-full bg-rose-500/15 hover:bg-rose-500 text-rose-300 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>

                      <div className="h-24 rounded-xl bg-black/35 overflow-hidden flex items-center justify-center border border-white/5">
                        <img
                          src={previewUrl(item.path, 220)}
                          alt={item.name}
                          loading="lazy"
                          draggable={false}
                          className="max-h-full max-w-full object-contain"
                        />
                      </div>

                      <div className="min-w-0 text-center">
                        <div className="text-[11px] font-semibold text-white truncate">{item.name}</div>
                        <div className="text-[10px] text-white/50 truncate">
                          {[item.dims, item.size_str].filter(Boolean).join(" • ")}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          ) : (
            <div className="space-y-1.5">
              <AnimatePresence mode="popLayout">
                {visibleItems.map((item) => {
                  const isChecked = selectedMap[item.path] !== false;
                  const isSelected = activeItem?.path === item.path;
                  const pred = formatPredictedName(item, previewRule);
                  return (
                    <motion.div
                      layout
                      key={item.path}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, x: -12 }}
                      transition={{ duration: 0.18 }}
                      onClick={() => setInspectedPath(item.path)}
                      onDoubleClick={() => onPreviewFile(item.path)}
                      className={`liquid-card rounded-2xl px-2.5 sm:px-3 py-2 cursor-pointer flex items-center gap-2 sm:gap-3 ${
                        isSelected ? "ring-1 ring-[var(--accent)] bg-white/10" : ""
                      } ${!isChecked ? "opacity-55" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => onToggleItem(item.path, e.target.checked)}
                        className="accent-[var(--accent)] w-4 h-4 cursor-pointer shrink-0"
                      />

                      <div className="w-9 h-9 sm:w-11 sm:h-11 rounded-xl bg-black/35 border border-white/10 overflow-hidden shrink-0 flex items-center justify-center">
                        <img
                          src={previewUrl(item.path, 120)}
                          alt={item.name}
                          loading="lazy"
                          draggable={false}
                          className="max-w-full max-h-full object-contain"
                        />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-[12px] sm:text-[12.5px] font-semibold text-white truncate">
                            {item.name}
                          </span>
                          {pred && (
                            <span className="hidden sm:inline-block text-[10px] font-medium px-2 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent-hover)] truncate max-w-[180px]">
                              → {pred}
                            </span>
                          )}
                        </div>
                        <div className="text-[10.5px] sm:text-[11px] text-white/55 truncate mt-0.5">
                          {[item.ext.toUpperCase(), item.dims, item.mode, item.size_str]
                            .filter(Boolean)
                            .join("  •  ")}
                        </div>
                      </div>

                      <button
                        type="button"
                        title="Quick Full Preview"
                        onClick={(e) => {
                          e.stopPropagation();
                          onPreviewFile(item.path);
                        }}
                        className="liquid-pill-btn rounded-full w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center text-white/75 hover:text-white cursor-pointer shrink-0"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>

                      <button
                        type="button"
                        title="Remove from queue"
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemoveItem(item.path);
                        }}
                        className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-rose-500/15 border border-rose-400/25 hover:bg-rose-500 text-rose-300 hover:text-white flex items-center justify-center transition-colors cursor-pointer shrink-0"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* GPU Liquid Glass Drag & Drop Refraction Portal */}
        <AnimatePresence>
          {isDragging && (
            <motion.div
              initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
              animate={{ opacity: 1, backdropFilter: "blur(26px)" }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.16 }}
              className="absolute inset-0 z-30 flex items-center justify-center rounded-2xl bg-[#070b16]/80 border-2 border-dashed border-[var(--accent)] pointer-events-none"
            >
              <motion.div
                initial={{ scale: 0.9, y: 8 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.94, opacity: 0, transition: { duration: 0.14 } }}
                transition={{ type: "spring", stiffness: 420, damping: 28 }}
                className="liquid-dock rounded-3xl px-6 py-5 sm:px-9 sm:py-7 flex flex-col items-center gap-2.5 text-center border border-[var(--accent)]/60 mx-3"
              >
                <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] flex items-center justify-center border border-white/25">
                  <Sparkles className="w-6 h-6 text-[var(--accent-hover)]" />
                </div>
                <div className="text-[15px] sm:text-[16px] font-bold text-white">Release to Queue Items</div>
                <div className="text-[11.5px] sm:text-[12px] text-white/65">
                  Images, layered PSDs, multi-page PDFs & folders
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Live Docked Inspector Strip */}
      <div className="liquid-card rounded-2xl px-2.5 sm:px-3 py-2 flex items-center justify-between gap-2 sm:gap-3">
        <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-black/40 border border-white/10 overflow-hidden shrink-0 flex items-center justify-center">
            {activeItem ? (
              <img
                src={previewUrl(activeItem.path, 120)}
                alt={activeItem.name}
                draggable={false}
                className="max-w-full max-h-full object-contain"
              />
            ) : (
              <Eye className="w-4 h-4 text-white/35" />
            )}
          </div>
          <div className="min-w-0">
            {activeItem ? (
              <>
                <div className="text-[12px] font-semibold text-white truncate">{activeItem.name}</div>
                <div className="text-[10.5px] sm:text-[11px] text-white/55 truncate">
                  {[activeItem.dims && `${activeItem.dims} px`, activeItem.mode, activeItem.size_str]
                    .filter(Boolean)
                    .join("  •  ")}
                </div>
              </>
            ) : (
              <div className="text-[11.5px] sm:text-[12px] text-white/50 truncate">
                Select any queued asset to inspect preview
              </div>
            )}
          </div>
        </div>

        <button
          type="button"
          disabled={!activeItem}
          onClick={() => activeItem && onPreviewFile(activeItem.path)}
          className="liquid-pill-btn rounded-full px-3 sm:px-3.5 py-1.5 text-[11.5px] font-semibold text-white/90 disabled:opacity-40 flex items-center gap-1.5 cursor-pointer shrink-0"
        >
          <Eye className="w-3.5 h-3.5" />
          <span className="hidden min-[440px]:inline">Full Preview</span>
        </button>
      </div>

      {/* Output Bar (wraps gracefully on tiny screens) */}
      <div className="liquid-card rounded-2xl px-3 sm:px-3.5 py-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex items-center gap-2 min-w-[160px] flex-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--accent-hover)] shrink-0">
            Output
          </span>
          <FolderOpen className="w-4 h-4 text-white/55 shrink-0" />
          <span
            title={outputDir || "No folder chosen"}
            className={`text-[12px] truncate ${outputDir ? "text-white font-medium" : "text-white/45"}`}
          >
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
            className="liquid-hero-btn rounded-full px-3 sm:px-3.5 py-1.5 text-[11.5px] font-semibold text-white cursor-pointer"
          >
            Browse
          </button>

          <button
            type="button"
            disabled={!outputDir}
            onClick={onOpenOutputDir}
            className="liquid-pill-btn rounded-full px-2.5 sm:px-3 py-1.5 text-[11.5px] font-semibold text-white/85 disabled:opacity-35 flex items-center gap-1 cursor-pointer"
          >
            <span>Open</span>
            <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
