import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, animate, motion, useMotionValue } from "framer-motion";
import {
  Loader2,
  CheckCircle2,
  AlertTriangle,
  X,
  FolderOpen,
  SplitSquareHorizontal,
  GripHorizontal,
  LocateFixed,
} from "lucide-react";

function formatBytesMB(bytes) {
  if (!bytes) return "0.00 MB";
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function ProgressHud({
  activeJob,
  completion,
  errorAlert,
  onCancel,
  onOpenFolder,
  onCompare,
  onDismissComplete,
  onDismissError,
}) {
  const constraintsRef = useRef(null);
  const dragX = useMotionValue(0);
  const dragY = useMotionValue(0);
  const [isMoved, setIsMoved] = useState(false);

  // Reset offset to dead-center once no HUD card is visible
  useEffect(() => {
    if (!activeJob && !completion) {
      dragX.set(0);
      dragY.set(0);
      setIsMoved(false);
    }
  }, [activeJob, completion, dragX, dragY]);

  const recenterHud = () => {
    animate(dragX, 0, { type: "spring", stiffness: 420, damping: 32 });
    animate(dragY, 0, { type: "spring", stiffness: 420, damping: 32 });
    setIsMoved(false);
  };

  const handleDragEnd = () => {
    const moved = Math.abs(dragX.get()) > 6 || Math.abs(dragY.get()) > 6;
    setIsMoved(moved);
  };

  return (
    <>
      {/* Viewport-centered bounds container for moveable floating HUD */}
      <div
        ref={constraintsRef}
        className="fixed inset-2 sm:inset-4 z-40 pointer-events-none flex items-center justify-center"
      >
        <AnimatePresence mode="wait">
          {/* Active Running Progress Floating HUD */}
          {activeJob && (
            <motion.div
              key="active-job-hud"
              data-testid="progress-hud"
              drag
              dragConstraints={constraintsRef}
              dragElastic={0.08}
              dragMomentum={false}
              style={{ x: dragX, y: dragY }}
              onDragEnd={handleDragEnd}
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.94 }}
              transition={{ type: "spring", stiffness: 380, damping: 28 }}
              className="pointer-events-auto w-full max-w-[min(92vw,32rem)] cursor-grab active:cursor-grabbing touch-none select-none"
            >
              <div className="liquid-dock rounded-3xl p-4 sm:p-4.5 border border-white/25 shadow-2xl">
                {/* Subtle drag indicator & optional recenter button */}
                <div
                  onDoubleClick={recenterHud}
                  title="Drag to move • Double-click to recenter"
                  className="flex items-center justify-center relative -mt-1 mb-2.5"
                >
                  <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.06] border border-white/10 text-white/45">
                    <GripHorizontal className="w-3.5 h-3.5" />
                    <span className="text-[10px] font-medium tracking-wide uppercase">Move</span>
                  </div>
                  {isMoved && (
                    <button
                      type="button"
                      onPointerDown={(e) => e.stopPropagation()}
                      onClick={recenterHud}
                      title="Recenter HUD"
                      className="absolute right-0 w-6 h-6 rounded-full hover:bg-white/12 flex items-center justify-center text-white/55 hover:text-white cursor-pointer transition-colors"
                    >
                      <LocateFixed className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <div className="flex items-center justify-between gap-3 mb-2.5">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Loader2 className="w-4 h-4 text-[var(--accent-hover)] animate-spin shrink-0" />
                    <span className="text-[13px] font-bold text-white capitalize truncate">
                      Processing {activeJob.workspace}...
                    </span>
                  </div>
                  <span className="text-[13px] font-bold text-[var(--accent-hover)] tabular-nums shrink-0">
                    {activeJob.percent || 0}%
                  </span>
                </div>

                <div className="relative h-2.5 rounded-full bg-white/10 overflow-hidden mb-2.5">
                  <motion.div
                    className="h-full rounded-full relative overflow-hidden"
                    animate={{ width: `${Math.max(4, activeJob.percent || 0)}%` }}
                    transition={{ ease: "easeOut", duration: 0.25 }}
                    style={{
                      background: "linear-gradient(90deg, var(--accent), var(--accent-hover))",
                      boxShadow: "0 0 16px var(--accent-glow)",
                    }}
                  >
                    <div className="shimmer-bar absolute inset-0 w-1/2 bg-gradient-to-r from-transparent via-white/40 to-transparent" />
                  </motion.div>
                </div>

                <div className="flex items-center justify-between gap-2 text-[11px] text-white/65">
                  <div className="truncate">
                    {activeJob.eta || "Running..."} {activeJob.speed ? `• ${activeJob.speed}` : ""}
                  </div>
                  <button
                    type="button"
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={() => onCancel(activeJob.job_id)}
                    className="liquid-pill-btn rounded-full px-3 py-1 text-[11px] font-semibold text-rose-300 border-rose-400/30 hover:bg-rose-500/25 cursor-pointer shrink-0"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* Completion Glass Capsule */}
          {!activeJob && completion && (
            <motion.div
              key="completion-hud"
              data-testid="completion-hud"
              drag
              dragConstraints={constraintsRef}
              dragElastic={0.08}
              dragMomentum={false}
              style={{ x: dragX, y: dragY }}
              onDragEnd={handleDragEnd}
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.94 }}
              transition={{ type: "spring", stiffness: 380, damping: 28 }}
              className="pointer-events-auto w-full max-w-[min(92vw,36rem)] cursor-grab active:cursor-grabbing touch-none select-none"
            >
              <div className="liquid-dock rounded-3xl p-4 sm:p-4.5 border border-emerald-400/35 shadow-2xl">
                <div
                  onDoubleClick={recenterHud}
                  title="Drag to move • Double-click to recenter"
                  className="flex items-center justify-center relative -mt-1 mb-2.5"
                >
                  <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.06] border border-white/10 text-white/45">
                    <GripHorizontal className="w-3.5 h-3.5" />
                    <span className="text-[10px] font-medium tracking-wide uppercase">Move</span>
                  </div>
                </div>

                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-2xl bg-emerald-500/20 border border-emerald-400/30 flex items-center justify-center shrink-0 mt-0.5">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[14px] font-bold text-white capitalize">
                        {completion.workspace} Completed
                      </div>
                      <div className="text-[12px] text-white/70 mt-0.5 break-words">
                        {completion.success_count} succeeded
                        {completion.failure_count > 0 ? `, ${completion.failure_count} failed` : ""}
                        {completion.skipped_count > 0 ? `, ${completion.skipped_count} skipped` : ""}
                        {completion.input_size > 0
                          ? `  •  ${formatBytesMB(completion.input_size)} → ${formatBytesMB(completion.output_size)}`
                          : ""}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {isMoved && (
                      <button
                        type="button"
                        onPointerDown={(e) => e.stopPropagation()}
                        onClick={recenterHud}
                        title="Recenter HUD"
                        className="w-7 h-7 rounded-full hover:bg-white/10 flex items-center justify-center text-white/55 hover:text-white cursor-pointer"
                      >
                        <LocateFixed className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      type="button"
                      onPointerDown={(e) => e.stopPropagation()}
                      onClick={onDismissComplete}
                      className="w-7 h-7 rounded-full hover:bg-white/10 flex items-center justify-center text-white/55 hover:text-white cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-end gap-2 mt-3.5">
                  {completion.pairs && completion.pairs.length > 0 && (
                    <button
                      type="button"
                      onPointerDown={(e) => e.stopPropagation()}
                      onClick={() => onCompare(completion.pairs)}
                      className="liquid-pill-btn rounded-full px-3.5 py-1.5 text-[12px] font-semibold text-white flex items-center gap-1.5 cursor-pointer"
                    >
                      <SplitSquareHorizontal className="w-3.5 h-3.5 text-[var(--accent-hover)]" />
                      <span>Compare Before / After</span>
                    </button>
                  )}
                  {completion.output_dir && (
                    <button
                      type="button"
                      onPointerDown={(e) => e.stopPropagation()}
                      onClick={() => onOpenFolder(completion.output_dir)}
                      className="liquid-hero-btn rounded-full px-4 py-1.5 text-[12px] font-semibold text-white flex items-center gap-1.5 cursor-pointer"
                    >
                      <FolderOpen className="w-3.5 h-3.5" />
                      <span>Open Output Folder</span>
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Error Toast */}
      <AnimatePresence>
        {errorAlert && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50 w-[min(92vw,28rem)] liquid-dock rounded-2xl p-4 border border-rose-400/40"
          >
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-bold text-white">Processing Warning</div>
                <div className="text-[11.5px] text-white/75 mt-1 break-words">{errorAlert}</div>
              </div>
              <button
                type="button"
                onClick={onDismissError}
                className="text-white/50 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
