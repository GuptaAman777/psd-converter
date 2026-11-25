import React, { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, Trash2, CheckCircle2, Sparkles, X, Loader2, ArrowUpRight, AlertTriangle } from "lucide-react";

const CATEGORIES = ["All", "Fast Compact", "Anime & Art", "Photo & Realism", "Restoration"];

const SORT_OPTIONS = [
  { value: "recommended", label: "Sort: Recommended" },
  { value: "installed", label: "Sort: Installed First" },
  { value: "alpha", label: "Sort: Name (A–Z)" },
  { value: "size_asc", label: "Sort: Smallest First" },
  { value: "size_desc", label: "Sort: Largest First" },
];

export default function ModelManagerModal({
  open,
  onClose,
  catalog = [],
  downloadProgress = {},
  confirmInstall = true,
  confirmDelete = true,
  onSetConfirmInstall,
  onSetConfirmDelete,
  onInstall,
  onRemove,
  onUseModel,
}) {
  const [cat, setCat] = useState("All");
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState("recommended");
  const [pendingAction, setPendingAction] = useState(null); // { type: "install"|"delete", model }
  const [dontAskAgain, setDontAskAgain] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = catalog.filter((m) => {
      if (cat !== "All" && m.category !== cat) return false;
      if (q) {
        const hay = `${m.label} ${m.id} ${m.category} ${m.description}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    if (sortBy === "alpha") {
      return [...list].sort((a, b) => a.label.localeCompare(b.label));
    }
    if (sortBy === "size_asc") {
      return [...list].sort((a, b) => (a.size_mb || 0) - (b.size_mb || 0) || a.label.localeCompare(b.label));
    }
    if (sortBy === "size_desc") {
      return [...list].sort((a, b) => (b.size_mb || 0) - (a.size_mb || 0) || a.label.localeCompare(b.label));
    }
    if (sortBy === "installed") {
      return [...list].sort((a, b) => Number(Boolean(b.installed)) - Number(Boolean(a.installed)) || a.label.localeCompare(b.label));
    }
    return list;
  }, [catalog, cat, query, sortBy]);

  const installedCount = catalog.filter((m) => m.installed).length;

  const requestInstall = (model) => {
    if (!confirmInstall) {
      onInstall(model.id);
      return;
    }
    setDontAskAgain(false);
    setPendingAction({ type: "install", model });
  };

  const requestDelete = (model) => {
    if (!confirmDelete) {
      onRemove(model.id);
      return;
    }
    setDontAskAgain(false);
    setPendingAction({ type: "delete", model });
  };

  const confirmPendingAction = () => {
    if (!pendingAction) return;
    const { type, model } = pendingAction;
    if (dontAskAgain) {
      if (type === "install") onSetConfirmInstall?.(false);
      else onSetConfirmDelete?.(false);
    }
    setPendingAction(null);
    if (type === "install") onInstall(model.id);
    else onRemove(model.id);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-2xl flex items-center justify-center p-2 sm:p-5"
        >
          <motion.div
            initial={{ scale: 0.94, opacity: 0, y: 12 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.94, opacity: 0 }}
            transition={{ type: "spring", stiffness: 360, damping: 28 }}
            onClick={(e) => e.stopPropagation()}
            data-testid="model-manager-modal"
            className="relative liquid-dock rounded-2xl sm:rounded-3xl w-full max-w-4xl h-[90vh] sm:h-[82vh] flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="px-4 sm:px-6 py-3.5 border-b border-white/10 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-[var(--accent-soft)] border border-white/20 flex items-center justify-center shrink-0">
                  <Sparkles className="w-4.5 h-4.5 text-[var(--accent-hover)]" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[15px] font-bold text-white">Additional AI Model Packs</span>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-white/10 text-white/80">
                      {installedCount} / {catalog.length} Installed
                    </span>
                  </div>
                  <div className="text-[11.5px] text-white/55 truncate">
                    On-demand NCNN Vulkan models powered by Upscayl Engine (2025-12-07)
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center hover:bg-rose-500/30 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Filters & Sorting */}
            <div className="px-4 sm:px-6 py-2.5 border-b border-white/10 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-1.5">
                {CATEGORIES.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setCat(c)}
                    className={`rounded-full px-3 py-1 text-[11.5px] font-semibold cursor-pointer ${
                      cat === c ? "bg-[var(--accent)] text-white shadow" : "liquid-pill-btn text-white/75"
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  data-testid="model-sort-select"
                  className="liquid-select rounded-full px-3 py-1 text-[11.5px] font-medium cursor-pointer"
                >
                  {SORT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="Filter models..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="liquid-input rounded-full px-3.5 py-1 text-[12px] flex-1 sm:w-44"
                />
              </div>
            </div>

            {/* Grid */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5 grid grid-cols-1 md:grid-cols-2 gap-3 content-start">
              {filtered.map((m) => {
                const prog = downloadProgress[m.id];
                const isBusy = m.downloading || prog?.status === "downloading";
                const pct = prog?.percent || 0;
                const hasError = prog?.status === "error";

                return (
                  <div
                    key={m.id}
                    data-testid={`model-card-${m.id}`}
                    className="liquid-card rounded-2xl p-3.5 flex flex-col justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="text-[13.5px] font-bold text-white truncate">{m.label}</div>
                          <div className="flex flex-wrap items-center gap-1.5 mt-1">
                            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent-hover)]">
                              {m.category}
                            </span>
                            <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-white/10 text-white/75">
                              {m.scale}x • {m.size_mb} MB
                            </span>
                          </div>
                        </div>

                        {m.installed && !isBusy && (
                          <span className="text-[10.5px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 flex items-center gap-1 shrink-0">
                            <CheckCircle2 className="w-3 h-3" /> Ready
                          </span>
                        )}
                      </div>

                      <p className="text-[11.5px] text-white/70 mt-2 leading-relaxed">{m.description}</p>
                    </div>

                    <div className="space-y-2">
                      {isBusy && (
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10.5px] text-white/70">
                            <span>{prog?.detail || "Downloading..."}</span>
                            <span className="tabular-nums font-bold">{pct}%</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                            <div
                              style={{
                                width: `${Math.max(4, pct)}%`,
                                background: "linear-gradient(90deg, var(--accent), var(--accent-hover))",
                              }}
                              className="h-full rounded-full transition-all duration-150"
                            />
                          </div>
                        </div>
                      )}

                      {hasError && (
                        <div className="text-[11px] text-rose-300 truncate" title={prog.detail}>
                          Failed: {prog.detail}
                        </div>
                      )}

                      <div className="flex items-center justify-end gap-2">
                        {m.installed ? (
                          <>
                            <button
                              type="button"
                              onClick={() => requestDelete(m)}
                              className="liquid-pill-btn rounded-full px-3 py-1.5 text-[11.5px] font-semibold text-rose-300 hover:bg-rose-500/25 flex items-center gap-1 cursor-pointer"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span>Remove</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => onUseModel(m)}
                              className="liquid-hero-btn rounded-full px-3.5 py-1.5 text-[11.5px] font-semibold text-white flex items-center gap-1 cursor-pointer"
                            >
                              <span>Use in Upscaler</span>
                              <ArrowUpRight className="w-3.5 h-3.5" />
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => requestInstall(m)}
                            className="liquid-hero-btn rounded-full px-4 py-1.5 text-[11.5px] font-semibold text-white flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                          >
                            {isBusy ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Download className="w-3.5 h-3.5" />
                            )}
                            <span>{isBusy ? "Downloading..." : `Download (${m.size_mb} MB)`}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Install / Delete Confirmation Overlay */}
            <AnimatePresence>
              {pendingAction && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setPendingAction(null)}
                  className="absolute inset-0 z-30 bg-black/70 backdrop-blur-md flex items-center justify-center p-4"
                >
                  <motion.div
                    initial={{ scale: 0.94, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.94, opacity: 0 }}
                    onClick={(e) => e.stopPropagation()}
                    data-testid="model-confirm-dialog"
                    className="liquid-dock rounded-2xl w-full max-w-md p-5 space-y-4 border border-white/25"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border ${
                          pendingAction.type === "delete"
                            ? "bg-rose-500/20 border-rose-400/35 text-rose-300"
                            : "bg-[var(--accent-soft)] border-white/20 text-[var(--accent-hover)]"
                        }`}
                      >
                        {pendingAction.type === "delete" ? (
                          <AlertTriangle className="w-5 h-5" />
                        ) : (
                          <Download className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <div className="text-[14.5px] font-bold text-white">
                          {pendingAction.type === "delete" ? "Are you sure you want to delete this model?" : "Are you sure you want to install this model?"}
                        </div>
                        <p className="text-[12px] text-white/75 mt-1 leading-relaxed">
                          {pendingAction.type === "delete"
                            ? `Removing "${pendingAction.model.label}" (${pendingAction.model.size_mb} MB) deletes it from local storage. You can re-download it anytime.`
                            : `Download and install "${pendingAction.model.label}" (${pendingAction.model.size_mb} MB) to your local NCNN models folder?`}
                        </p>
                      </div>
                    </div>

                    <label className="flex items-start gap-2.5 text-[11.5px] text-white/80 cursor-pointer select-none rounded-xl bg-white/[0.04] border border-white/10 p-2.5">
                      <input
                        type="checkbox"
                        checked={dontAskAgain}
                        onChange={(e) => setDontAskAgain(e.target.checked)}
                        data-testid="model-confirm-dont-ask"
                        className="accent-[var(--accent)] mt-0.5 cursor-pointer"
                      />
                      <span>
                        Never show again for{" "}
                        {pendingAction.type === "delete" ? "deleting" : "installing"} models{" "}
                        <span className="text-white/50">(re-enable anytime in Settings)</span>
                      </span>
                    </label>

                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setPendingAction(null)}
                        className="liquid-pill-btn rounded-full px-4 py-1.5 text-[12px] font-semibold cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={confirmPendingAction}
                        data-testid="model-confirm-proceed"
                        className={`rounded-full px-4 py-1.5 text-[12px] font-semibold text-white cursor-pointer ${
                          pendingAction.type === "delete"
                            ? "bg-rose-500/85 hover:bg-rose-500 border border-rose-300/35"
                            : "liquid-hero-btn"
                        }`}
                      >
                        {pendingAction.type === "delete" ? "Yes, Delete Model" : "Yes, Install Model"}
                      </button>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
