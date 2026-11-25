import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";

export function GlassCard({ title, badge, children, className = "", rightHeader = null }) {
  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - rect.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - rect.top}px`);
  };

  return (
    <div
      onMouseMove={handleMouseMove}
      className={`liquid-card rounded-2xl p-3 sm:p-4 ${className}`}
    >
      {(title || rightHeader) && (
        <div className="flex items-center justify-between gap-2 mb-2.5 sm:mb-3">
          <div className="flex items-center gap-2 min-w-0">
            {title && (
              <span className="text-[10.5px] sm:text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--accent-hover)] truncate">
                {title}
              </span>
            )}
            {badge && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white/10 text-white/75 border border-white/10 shrink-0">
                {badge}
              </span>
            )}
          </div>
          {rightHeader}
        </div>
      )}
      <div className="space-y-2.5">{children}</div>
    </div>
  );
}

export function CollapsibleGlassCard({ title, badge, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="liquid-card rounded-2xl px-3 py-2.5 sm:px-4 sm:py-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 text-left cursor-pointer py-0.5"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10.5px] sm:text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--accent-hover)] truncate">
            {title}
          </span>
          {badge && (
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white/10 text-white/70 shrink-0">
              {badge}
            </span>
          )}
        </div>
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ type: "spring", stiffness: 360, damping: 28 }}
          className="text-white/60 shrink-0"
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="pt-2.5 sm:pt-3 space-y-2.5 border-t border-white/10 mt-2.5">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function SettingRow({ label, hint, children }) {
  return (
    <div className="flex flex-col min-[390px]:flex-row min-[390px]:items-center justify-between gap-1.5 min-[390px]:gap-3">
      <div className="min-[390px]:w-[106px] sm:w-[118px] shrink-0">
        <div className="text-[12px] font-medium text-white/88 leading-tight">{label}</div>
        {hint && <div className="text-[10px] text-white/45 leading-tight mt-0.5">{hint}</div>}
      </div>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}

export function GlassSwitch({ checked, onChange, label, sublabel, disabled = false }) {
  return (
    <label
      className={`flex items-center justify-between gap-2.5 sm:gap-3 cursor-pointer py-0.5 ${
        disabled ? "opacity-45 cursor-not-allowed" : ""
      }`}
    >
      <div className="min-w-0">
        <div className="text-[12px] font-medium text-white/90 leading-snug">{label}</div>
        {sublabel && <div className="text-[10.5px] text-white/50 leading-tight mt-0.5">{sublabel}</div>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative w-10 h-[22px] rounded-full shrink-0 transition-colors duration-200 border ${
          checked
            ? "bg-[var(--accent)] border-white/25 shadow-[0_0_12px_var(--accent-soft)]"
            : "bg-white/12 border-white/15"
        }`}
      >
        <motion.span
          layout
          transition={{ type: "spring", stiffness: 520, damping: 32 }}
          className={`block w-4 h-4 rounded-full bg-white shadow-md ${
            checked ? "ml-[21px]" : "ml-[2px]"
          }`}
        />
      </button>
    </label>
  );
}
