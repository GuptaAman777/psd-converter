import React, { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, ZoomIn, ZoomOut, RotateCcw, ChevronLeft, ChevronRight, SplitSquareHorizontal, Move } from "lucide-react";
import { previewUrl } from "../api/client";

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 8;

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

/** Shared GPU zoom-to-cursor & click-drag pan controller for image inspection viewports. */
function useZoomPan(viewportRef, activeKey, minZoom = MIN_ZOOM, maxZoom = MAX_ZOOM) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);

  const stateRef = useRef({ zoom: 1, pan: { x: 0, y: 0 } });
  stateRef.current = { zoom, pan };

  const panDragRef = useRef({ active: false, pointerId: null, startX: 0, startY: 0, origX: 0, origY: 0 });

  const clampPan = useCallback(
    (nx, ny, nextZoom) => {
      const el = viewportRef.current;
      if (!el) return { x: nx, y: ny };
      const rect = el.getBoundingClientRect();
      const maxX = Math.max(120, rect.width * Math.max(0.6, nextZoom * 0.55));
      const maxY = Math.max(120, rect.height * Math.max(0.6, nextZoom * 0.55));
      return { x: clamp(nx, -maxX, maxX), y: clamp(ny, -maxY, maxY) };
    },
    [viewportRef]
  );

  const applyZoom = useCallback(
    (computeNext, anchorClient = null) => {
      const { zoom: prevZoom, pan: prevPan } = stateRef.current;
      const nextZoom = clamp(Number(computeNext(prevZoom).toFixed(3)), minZoom, maxZoom);
      if (nextZoom === prevZoom) return;

      const ratio = nextZoom / prevZoom;
      let ox = 0;
      let oy = 0;
      if (anchorClient && viewportRef.current) {
        const rect = viewportRef.current.getBoundingClientRect();
        ox = anchorClient.x - (rect.left + rect.width / 2);
        oy = anchorClient.y - (rect.top + rect.height / 2);
      }

      const rawX = ox - (ox - prevPan.x) * ratio;
      const rawY = oy - (oy - prevPan.y) * ratio;
      const nextPan = clampPan(rawX, rawY, nextZoom);
      setZoom(nextZoom);
      setPan(nextPan);
    },
    [clampPan, maxZoom, minZoom, viewportRef]
  );

  const resetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  useEffect(() => {
    resetView();
  }, [activeKey, resetView]);

  // Attach non-passive wheel listener so wheel zoom never scrolls background or emits passive warnings
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.16 : 1 / 1.16;
      applyZoom((z) => z * factor, { x: e.clientX, y: e.clientY });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [viewportRef, applyZoom, activeKey]);

  const startPan = useCallback((e) => {
    if (e.button !== undefined && e.button !== 0) return;
    panDragRef.current = {
      active: true,
      pointerId: e.pointerId ?? null,
      startX: e.clientX,
      startY: e.clientY,
      origX: stateRef.current.pan.x,
      origY: stateRef.current.pan.y,
    };
    setIsPanning(true);
    try {
      e.currentTarget?.setPointerCapture?.(e.pointerId);
    } catch {
      // ignore synthetic events
    }
  }, []);

  const movePan = useCallback(
    (e) => {
      const d = panDragRef.current;
      if (!d.active) return;
      const dx = e.clientX - d.startX;
      const dy = e.clientY - d.startY;
      setPan(clampPan(d.origX + dx, d.origY + dy, stateRef.current.zoom));
    },
    [clampPan]
  );

  const endPan = useCallback((e) => {
    if (!panDragRef.current.active) return;
    panDragRef.current.active = false;
    setIsPanning(false);
    try {
      if (panDragRef.current.pointerId != null) {
        e.currentTarget?.releasePointerCapture?.(panDragRef.current.pointerId);
      }
    } catch {
      // ignore
    }
  }, []);

  return {
    zoom,
    pan,
    isPanning,
    zoomIn: () => applyZoom((z) => z * 1.25),
    zoomOut: () => applyZoom((z) => z / 1.25),
    resetView,
    startPan,
    movePan,
    endPan,
  };
}

export function QuickPreviewModal({ filePath, onClose }) {
  const stageRef = useRef(null);
  const { zoom, pan, isPanning, zoomIn, zoomOut, resetView, startPan, movePan, endPan } = useZoomPan(
    stageRef,
    filePath || ""
  );

  return (
    <AnimatePresence>
      {filePath && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xl flex items-center justify-center p-2 sm:p-6"
        >
          <motion.div
            initial={{ scale: 0.94, opacity: 0, y: 12 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.94, opacity: 0 }}
            transition={{ type: "spring", stiffness: 360, damping: 28 }}
            onClick={(e) => e.stopPropagation()}
            className="liquid-dock rounded-2xl sm:rounded-3xl w-full max-w-5xl h-[92vh] sm:h-[82vh] flex flex-col overflow-hidden"
          >
            <div className="px-3 sm:px-5 py-2.5 sm:py-3 border-b border-white/10 flex flex-wrap items-center justify-between gap-2 sm:gap-3">
              <div className="min-w-0">
                <div className="text-[13px] font-bold text-white truncate">
                  {filePath.split(/[/\\]/).pop()}
                </div>
                <div className="text-[11px] text-white/50 truncate">{filePath}</div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={zoomOut}
                  title="Zoom out"
                  className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="text-[12px] font-semibold w-12 text-center tabular-nums">
                  {Math.round(zoom * 100)}%
                </span>
                <button
                  type="button"
                  onClick={zoomIn}
                  title="Zoom in"
                  className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={resetView}
                  title="Reset zoom & pan"
                  className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center text-white hover:bg-rose-500/30 cursor-pointer ml-2"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div
              ref={stageRef}
              data-testid="quick-preview-stage"
              onPointerDown={startPan}
              onPointerMove={movePan}
              onPointerUp={endPan}
              onPointerCancel={endPan}
              onDoubleClick={resetView}
              className={`relative flex-1 overflow-hidden flex items-center justify-center p-4 bg-black/40 select-none touch-none ${
                isPanning ? "cursor-grabbing" : "cursor-grab"
              }`}
            >
              <div
                style={{
                  transform: `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${zoom})`,
                  transition: isPanning ? "none" : "transform 0.14s cubic-bezier(0.22,1,0.36,1)",
                }}
                className="w-full h-full flex items-center justify-center pointer-events-none"
              >
                <img
                  src={previewUrl(filePath, 1800)}
                  alt="Preview"
                  draggable={false}
                  className="max-h-full max-w-full object-contain rounded-xl shadow-2xl"
                />
              </div>

              <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 liquid-pill-btn rounded-full px-3 py-1 text-[10.5px] text-white/75 flex items-center gap-1.5 whitespace-nowrap">
                <Move className="w-3 h-3 text-[var(--accent-hover)]" />
                <span>Scroll to zoom • Drag to pan • Double-click to reset</span>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function CompareModal({ open, pairs, onClose }) {
  const [idx, setIdx] = useState(0);
  const [splitPct, setSplitPct] = useState(50);
  const [isSplitting, setIsSplitting] = useState(false);

  const stageRef = useRef(null);
  const splitDragRef = useRef(false);

  const list = pairs && pairs.length > 0 ? pairs : [];
  const safeIdx = Math.min(idx, Math.max(0, list.length - 1));
  const current = list[safeIdx];
  const activeKey = open ? `${safeIdx}:${current?.before || ""}:${current?.after || ""}` : "closed";

  const { zoom, pan, isPanning, zoomIn, zoomOut, resetView, startPan, movePan, endPan } = useZoomPan(
    stageRef,
    activeKey
  );

  if (!open) return null;

  const updateSplit = (clientX) => {
    if (!stageRef.current) return;
    const rect = stageRef.current.getBoundingClientRect();
    const pct = ((clientX - rect.left) / Math.max(1, rect.width)) * 100;
    setSplitPct(clamp(pct, 2, 98));
  };

  const handleStagePointerDown = (e) => {
    if (splitDragRef.current) return;
    startPan(e);
  };

  const handleStagePointerMove = (e) => {
    if (splitDragRef.current) {
      updateSplit(e.clientX);
      return;
    }
    movePan(e);
  };

  const handleStagePointerUp = (e) => {
    if (splitDragRef.current) {
      splitDragRef.current = false;
      setIsSplitting(false);
    }
    endPan(e);
  };

  const layerTransformStyle = {
    transform: `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${zoom})`,
    transition: isPanning ? "none" : "transform 0.12s cubic-bezier(0.22,1,0.36,1)",
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-2xl flex items-center justify-center p-2 sm:p-5"
    >
      <motion.div
        initial={{ scale: 0.94, opacity: 0, y: 12 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.94, opacity: 0 }}
        transition={{ type: "spring", stiffness: 360, damping: 28 }}
        onClick={(e) => e.stopPropagation()}
        className="liquid-dock rounded-2xl sm:rounded-3xl w-full max-w-6xl h-[92vh] sm:h-[86vh] flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="px-3 sm:px-5 py-2.5 sm:py-3.5 border-b border-white/10 flex flex-wrap items-center justify-between gap-2 sm:gap-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-[var(--accent-soft)] flex items-center justify-center border border-white/20 shrink-0">
              <SplitSquareHorizontal className="w-4 h-4 text-[var(--accent-hover)]" />
            </div>
            <div className="min-w-0">
              <div className="text-[14px] font-bold text-white">Before / After Visual Inspector</div>
              <div className="text-[11px] text-white/55 truncate">
                {current
                  ? `Comparing pair ${safeIdx + 1} of ${list.length} — ${current.before.split(/[/\\]/).pop()}`
                  : "Process a batch in Converter, Upscaler, or Denoiser to inspect live outputs here"}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 shrink-0">
            {list.length > 1 && (
              <>
                <button
                  type="button"
                  onClick={() => setIdx((i) => Math.max(0, i - 1))}
                  className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-[12px] font-semibold px-2 tabular-nums">{safeIdx + 1} / {list.length}</span>
                <button
                  type="button"
                  onClick={() => setIdx((i) => Math.min(list.length - 1, i + 1))}
                  className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </>
            )}

            <button
              type="button"
              onClick={zoomOut}
              title="Zoom out"
              className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span
              data-testid="compare-zoom-label"
              className="text-[12px] font-semibold w-12 text-center tabular-nums"
            >
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={zoomIn}
              title="Zoom in"
              className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={resetView}
              title="Reset zoom & position"
              className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center hover:bg-rose-500/30 cursor-pointer ml-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Split Stage: scroll-to-zoom, drag stage to pan images, drag handle/bar to slide split */}
        <div
          ref={stageRef}
          data-testid="compare-stage"
          onPointerDown={handleStagePointerDown}
          onPointerMove={handleStagePointerMove}
          onPointerUp={handleStagePointerUp}
          onPointerCancel={handleStagePointerUp}
          onDoubleClick={resetView}
          className={`relative flex-1 bg-black/50 overflow-hidden select-none touch-none ${
            isSplitting ? "cursor-ew-resize" : isPanning ? "cursor-grabbing" : "cursor-grab"
          }`}
        >
          {current ? (
            <>
              {/* After Base Layer */}
              <div
                data-testid="compare-after-layer"
                style={layerTransformStyle}
                className="absolute inset-0 flex items-center justify-center p-4 sm:p-6 pointer-events-none"
              >
                <img
                  src={previewUrl(current.after, 2200)}
                  alt="After"
                  draggable={false}
                  className="max-h-full max-w-full object-contain"
                />
              </div>

              {/* Before Clipped Stage Overlay (stage-level clip keeps divider pixel-exact at all zoom/pan) */}
              <div
                style={{ clipPath: `inset(0 ${100 - splitPct}% 0 0)` }}
                className="absolute inset-0 pointer-events-none"
              >
                <div
                  data-testid="compare-before-layer"
                  style={layerTransformStyle}
                  className="w-full h-full flex items-center justify-center p-4 sm:p-6"
                >
                  <img
                    src={previewUrl(current.before, 2200)}
                    alt="Before"
                    draggable={false}
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
              </div>

              {/* Interactive Liquid Split Divider Line + Handle */}
              <div
                data-testid="compare-divider"
                style={{ left: `${splitPct}%` }}
                onPointerDown={(e) => {
                  e.stopPropagation();
                  splitDragRef.current = true;
                  setIsSplitting(true);
                  updateSplit(e.clientX);
                  try {
                    stageRef.current?.setPointerCapture?.(e.pointerId);
                  } catch {
                    // ignore
                  }
                }}
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  setSplitPct(50);
                }}
                title="Drag to slide Before / After • Double-click to center divider"
                className="absolute top-0 bottom-0 -translate-x-1/2 w-7 flex items-center justify-center cursor-ew-resize z-20"
              >
                <div className="w-0.5 h-full bg-white/85 shadow-[0_0_16px_rgba(255,255,255,0.8)] pointer-events-none" />
                <div className="absolute top-1/2 -translate-y-1/2 w-9 h-9 rounded-full liquid-dock flex items-center justify-center border border-white/45 text-white text-[12px] font-bold shadow-xl pointer-events-none">
                  ⇄
                </div>
              </div>

              <div className="pointer-events-none absolute top-3 sm:top-4 left-3 sm:left-4 liquid-pill-btn rounded-full px-3 py-1 text-[10.5px] sm:text-[11px] font-bold z-10">
                BEFORE • ORIGINAL
              </div>
              <div className="pointer-events-none absolute top-3 sm:top-4 right-3 sm:right-4 liquid-hero-btn rounded-full px-3 py-1 text-[10.5px] sm:text-[11px] font-bold z-10">
                AFTER • PROCESSED
              </div>

              <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 liquid-pill-btn rounded-full px-3 py-1 text-[10.5px] text-white/75 flex items-center gap-1.5 whitespace-nowrap z-10">
                <Move className="w-3 h-3 text-[var(--accent-hover)]" />
                <span className="hidden sm:inline">Scroll to zoom • Drag image to pan • Drag ⇄ divider to split • Double-click to reset</span>
                <span className="sm:hidden">Scroll zoom • Drag pan • ⇄ split</span>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-center text-white/50 text-[14px] px-4">
              No processed image pairs recorded yet in this session.
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
