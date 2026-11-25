import React from "react";
import { motion } from "framer-motion";
import {
  Sparkles, Wand2, Eraser, Layers, Settings, SplitSquareHorizontal,
  Cpu, Github
} from "lucide-react";

const TABS = [
  { id: "converter", label: "Converter", icon: Sparkles },
  { id: "upscaler", label: "Upscaler", icon: Wand2 },
  { id: "denoiser", label: "Denoiser", icon: Eraser },
  { id: "stitcher", label: "Stitcher", icon: Layers },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function FloatingDock({
  activeTab,
  onSelectTab,
  version,
  gpuLabel,
  vulkanOk,
  onOpenCompare,
  hasComparePairs,
  onOpenGpuInfo,
  onOpenGithub,
}) {
  return (
    <header className="px-2 sm:px-3.5 pt-2 sm:pt-3 pb-1 shrink-0 z-20">
      <div className="liquid-dock rounded-2xl px-2.5 sm:px-4 py-2 flex flex-wrap lg:flex-nowrap items-center justify-between gap-2 sm:gap-3">
        {/* Brand Cluster */}
        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 order-1">
          <div
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center shrink-0 border border-white/25 shadow-lg"
            style={{
              background: "linear-gradient(135deg, var(--hero-start, var(--accent-hover)), var(--hero-end, var(--accent)))",
              boxShadow: "0 4px 18px var(--accent-glow), inset 0 1px 0 rgba(255,255,255,0.45)",
            }}
          >
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div className="leading-tight min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[13.5px] sm:text-[14px] font-bold tracking-tight text-white">
                ImageTool
              </span>
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-white/12 text-white/85 border border-white/15">
                v{version}
              </span>
            </div>
            <div className="hidden sm:block text-[10px] text-white/50 font-medium tracking-wide">
              Liquid Glass Studio
            </div>
          </div>
        </div>

        {/* Telemetry & Global Quick Actions */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 order-2 lg:order-3">
          <button
            type="button"
            onClick={onOpenCompare}
            title="Before / After Split Inspector (Ctrl+B)"
            className={`liquid-pill-btn rounded-full px-2.5 sm:px-3 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer ${
              hasComparePairs ? "text-[var(--accent-hover)] border-[var(--accent)]/40" : "text-white/80"
            }`}
          >
            <SplitSquareHorizontal className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Compare</span>
          </button>

          <button
            type="button"
            onClick={onOpenGpuInfo}
            title={`Hardware: ${gpuLabel}`}
            className="liquid-pill-btn rounded-full px-2.5 sm:px-3 py-1.5 text-[11px] font-semibold flex items-center gap-1.5 text-white/85 cursor-pointer"
          >
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                vulkanOk ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : "bg-amber-400"
              }`}
            />
            <Cpu className="w-3.5 h-3.5 text-white/70 shrink-0" />
            <span className="hidden md:inline max-w-[130px] truncate">{gpuLabel}</span>
          </button>

          <button
            type="button"
            onClick={onOpenGithub}
            title="Open GuptaAman777/psd-converter on GitHub"
            className="liquid-pill-btn rounded-full w-8 h-8 flex items-center justify-center text-white/75 hover:text-white cursor-pointer"
          >
            <Github className="w-4 h-4" />
          </button>
        </div>

        {/* Center Spring Morphing Navigation Capsule (wraps cleanly on < 1024px) */}
        <nav className="order-3 lg:order-2 w-full lg:w-auto flex items-center justify-center">
          <div className="no-scrollbar flex items-center gap-0.5 sm:gap-1 p-1 rounded-full bg-black/28 border border-white/10 shadow-inner max-w-full overflow-x-auto">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => onSelectTab(tab.id)}
                  title={tab.label}
                  className={`relative px-2 min-[420px]:px-2.5 sm:px-3.5 py-1.5 rounded-full text-[11px] sm:text-[12px] font-semibold flex items-center gap-1 sm:gap-1.5 cursor-pointer shrink-0 transition-colors duration-200 ${
                    active ? "text-white" : "text-white/60 hover:text-white/90"
                  }`}
                >
                  {active && (
                    <motion.div
                      layoutId="studioDockActivePill"
                      transition={{ type: "spring", stiffness: 460, damping: 34 }}
                      className="absolute inset-0 rounded-full border border-white/28 shadow-md"
                      style={{
                        background: "linear-gradient(135deg, rgba(255,255,255,0.18), var(--accent-soft))",
                        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.35), 0 4px 16px var(--accent-soft)",
                      }}
                    />
                  )}
                  <Icon className="w-3.5 h-3.5 relative z-10" />
                  <span className="hidden min-[440px]:inline relative z-10">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </nav>
      </div>
    </header>
  );
}
