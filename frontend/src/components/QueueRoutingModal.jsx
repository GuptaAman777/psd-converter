import React, { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Eye, X, RefreshCw, Download, CheckCircle2, AlertCircle, Search, ArrowRight
} from "lucide-react";
import { previewUrl } from "../api/client";

export default function QueueRoutingModal({
  open,
  onClose,
  modeLabel = "Auto Detect",
  analyzing = false,
  routeError = "",
  routeSummary,
  missingModels = [],
  onRefresh,
  onInstallModel,
}) {
  const [filterKind, setFilterKind] = useState("all");
  const [query, setQuery] = useState("");

  const routes = routeSummary?.routes || [];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return routes.filter((r) => {
      if (filterKind === "bw" && !r.analysis?.is_grayscale) return false;
      if (filterKind === "color" && (!r.analysis || r.analysis.is_grayscale)) return false;
      if (filterKind === "missing" && r.installed !== false) return false;
      if (q) {
        const hay = `${r.name} ${r.path} ${r.model_label || ""} ${r.model_id || ""} ${r.reason || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [routes, filterKind, query]);

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
            data-testid="queue-routing-modal"
            className="liquid-dock rounded-2xl sm:rounded-3xl w-full max-w-5xl h-[88vh] sm:h-[82vh] flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="px-4 sm:px-6 py-3.5 border-b border-white/10 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-[var(--accent-soft)] border border-white/20 flex items-center justify-center shrink-0">
                  <Eye className="w-4.5 h-4.5 text-[var(--accent-hover)]" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[15px] font-bold text-white">Queue Routing Inspector</span>
                    <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent-hover)] border border-white/10">
                      {modeLabel}
                    </span>
                  </div>
                  <div className="text-[11.5px] text-white/60 truncate">
                    Per-image B&amp;W / Color detection, height tier matching, and exact NCNN model assignment
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {onRefresh && (
                  <button
                    type="button"
                    onClick={onRefresh}
                    disabled={analyzing}
                    className="liquid-pill-btn rounded-full px-3 py-1.5 text-[11.5px] font-semibold text-white/85 flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${analyzing ? "animate-spin" : ""}`} />
                    <span>{analyzing ? "Scanning..." : "Re-scan"}</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center hover:bg-rose-500/30 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Summary Strip + Filters */}
            <div className="px-4 sm:px-6 py-2.5 border-b border-white/10 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { id: "all", label: `All (${routes.length})` },
                  { id: "bw", label: `B&W Manga (${routeSummary?.grayCount || 0})` },
                  { id: "color", label: `Color (${routeSummary?.colorCount || 0})` },
                  ...(missingModels.length > 0
                    ? [{ id: "missing", label: `Missing (${missingModels.length})` }]
                    : []),
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setFilterKind(f.id)}
                    className={`rounded-full px-3 py-1 text-[11.5px] font-semibold cursor-pointer ${
                      filterKind === f.id ? "bg-[var(--accent)] text-white shadow" : "liquid-pill-btn text-white/75"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              <div className="relative w-full sm:w-56">
                <Search className="w-3.5 h-3.5 text-white/45 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Filter filename or model..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="liquid-input w-full rounded-full pl-8 pr-3 py-1 text-[12px]"
                />
              </div>
            </div>

            {/* Active Model Groups Banner */}
            {(routeSummary?.models || []).length > 0 && (
              <div className="px-4 sm:px-6 py-2 bg-black/25 border-b border-white/10 flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 mr-1">
                  Models Active:
                </span>
                {routeSummary.models.map((grp) => (
                  <span
                    key={grp.key}
                    className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-white/[0.07] border border-white/10 text-white/90"
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        grp.installed ? "bg-emerald-400" : "bg-amber-400"
                      }`}
                    />
                    <span>
                      {grp.label}
                      {grp.chainLabel ? ` → ${grp.chainLabel}` : ""}
                    </span>
                    <span className="text-[var(--accent-hover)] font-bold">×{grp.count}</span>
                  </span>
                ))}
              </div>
            )}

            {/* Detailed File-to-Model Mapping List */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-2">
              {routeError && (
                <div className="rounded-xl bg-rose-500/15 border border-rose-400/30 p-3 text-[12px] text-rose-200 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>Routing analysis error: {routeError}</span>
                </div>
              )}

              {filtered.length === 0 ? (
                <div className="h-40 flex items-center justify-center text-[12.5px] text-white/50">
                  {analyzing ? "Inspecting queued images..." : "No matching files found."}
                </div>
              ) : (
                filtered.map((r) => {
                  const isBw = Boolean(r.analysis?.is_grayscale);
                  const dims = r.analysis ? `${r.analysis.width}×${r.analysis.height}` : "—";
                  return (
                    <div
                      key={r.path}
                      className="liquid-card rounded-2xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      {/* File Info + Thumbnail */}
                      <div className="flex items-center gap-3 min-w-0">
                        <img
                          src={previewUrl(r.path, 96)}
                          alt=""
                          loading="lazy"
                          className="w-12 h-12 rounded-xl object-cover bg-black/40 border border-white/10 shrink-0"
                        />
                        <div className="min-w-0 space-y-1">
                          <div className="text-[13px] font-bold text-white truncate" title={r.path}>
                            {r.name}
                          </div>
                          <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                            <span className="px-2 py-0.5 rounded-full bg-white/10 text-white/80 font-semibold">
                              {dims} {r.analysis?.ext ? `• ${r.analysis.ext.toUpperCase()}` : ""}
                            </span>
                            {r.analysis && (
                              <span
                                className={`px-2 py-0.5 rounded-full font-bold ${
                                  isBw
                                    ? "bg-zinc-500/25 text-zinc-200 border border-zinc-400/30"
                                    : "bg-[var(--accent-soft)] text-[var(--accent-hover)] border border-[var(--accent)]/30"
                                }`}
                              >
                                {isBw
                                  ? `B&W Manga → ${r.analysis.nearest_tier}p tier`
                                  : `Color Artwork`}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Assigned Model & Chain */}
                      <div className="flex flex-col sm:items-end gap-1 shrink-0 sm:max-w-[52%]">
                        {r.error ? (
                          <span className="text-[11.5px] text-rose-300 font-semibold">{r.error}</span>
                        ) : (
                          <>
                            <div className="flex flex-wrap items-center gap-1.5 text-[12px] font-bold text-[var(--accent-hover)]">
                              <span>{r.model_label || r.model_id}</span>
                              {r.chain_model_label && (
                                <>
                                  <ArrowRight className="w-3.5 h-3.5 text-white/50" />
                                  <span className="text-emerald-300">{r.chain_model_label}</span>
                                </>
                              )}
                              <span className="px-2 py-0.5 rounded-full bg-white/12 text-white text-[10.5px] font-bold">
                                {r.scale}x Out
                              </span>
                            </div>
                            <div className="text-[10.5px] font-mono text-white/55 truncate max-w-full" title={r.model_id}>
                              {r.model_id}
                              {r.chain_model_id ? ` + ${r.chain_model_id}` : ""}
                            </div>
                            <div className="flex items-center gap-2 text-[10.5px]">
                              <span className="text-white/60">{r.reason}</span>
                              {r.installed ? (
                                <span className="text-emerald-300 font-semibold flex items-center gap-1">
                                  <CheckCircle2 className="w-3 h-3" />
                                  {r.source === "local" ? "Local" : "Ready"}
                                </span>
                              ) : (
                                onInstallModel && (
                                  <button
                                    type="button"
                                    onClick={() => onInstallModel(r.model_id)}
                                    className="liquid-hero-btn rounded-full px-2.5 py-0.5 text-[10.5px] font-semibold text-white flex items-center gap-1 cursor-pointer"
                                  >
                                    <Download className="w-3 h-3" /> Download
                                  </button>
                                )
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            {missingModels.length > 0 && onInstallModel && (
              <div className="px-4 sm:px-6 py-3 border-t border-white/10 bg-amber-500/10 flex flex-wrap items-center justify-between gap-2">
                <span className="text-[12px] font-semibold text-amber-200">
                  {missingModels.length} required model pack(s) are not installed yet.
                </span>
                <button
                  type="button"
                  onClick={() => missingModels.forEach((mid) => onInstallModel(mid))}
                  className="liquid-hero-btn rounded-full px-4 py-1.5 text-[12px] font-semibold text-white flex items-center gap-1.5 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download All Missing ({missingModels.length})</span>
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
