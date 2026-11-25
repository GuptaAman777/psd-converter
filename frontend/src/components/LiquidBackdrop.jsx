import React from "react";

export const LIQUID_THEMES = {
  "Blue (Default)": {
    accent: "#0a84ff",
    accentHover: "#3ea0ff",
    accentSoft: "rgba(10, 132, 255, 0.22)",
    accentGlow: "rgba(10, 132, 255, 0.44)",
    bgDeep: "#060a14",
    orb1: "rgba(10, 132, 255, 0.36)",
    orb2: "rgba(94, 92, 230, 0.28)",
    orb3: "rgba(56, 189, 248, 0.18)",
  },
  "Red (Crimson)": {
    accent: "#ff375f",
    accentHover: "#ff5c7c",
    accentSoft: "rgba(255, 55, 95, 0.22)",
    accentGlow: "rgba(255, 55, 95, 0.44)",
    bgDeep: "#10060a",
    orb1: "rgba(255, 55, 95, 0.36)",
    orb2: "rgba(191, 90, 242, 0.24)",
    orb3: "rgba(255, 100, 130, 0.16)",
  },
  "Black (OLED Dark)": {
    accent: "#27272e",
    accentHover: "#d4d4d8",
    accentSoft: "rgba(255, 255, 255, 0.10)",
    accentGlow: "rgba(255, 255, 255, 0.18)",
    heroStart: "#32323c",
    heroEnd: "#16161b",
    bgDeep: "#000000",
    orb1: "rgba(255, 255, 255, 0.032)",
    orb2: "rgba(210, 210, 220, 0.02)",
    orb3: "rgba(150, 150, 165, 0.016)",
    vignetteBg:
      "radial-gradient(circle at 50% 0%, rgba(255,255,255,0.014), transparent 52%), linear-gradient(180deg, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.95) 100%)",
    dockBg: "linear-gradient(155deg, rgba(9, 9, 11, 0.90), rgba(0, 0, 0, 0.96))",
    panelBg: "linear-gradient(165deg, rgba(6, 6, 8, 0.90), rgba(0, 0, 0, 0.96))",
    cardBg: "linear-gradient(160deg, rgba(255, 255, 255, 0.022), rgba(0, 0, 0, 0.80))",
    pillBg: "rgba(255, 255, 255, 0.035)",
    inputBg: "rgba(0, 0, 0, 0.88)",
    inputFocusBg: "rgba(4, 4, 6, 0.96)",
    selectOptionBg: "#050507",
    glassBorder: "rgba(255, 255, 255, 0.10)",
    glassSpecular: "rgba(255, 255, 255, 0.14)",
  },
  "Purple (Cyberpunk)": {
    accent: "#bf5af2",
    accentHover: "#d47fff",
    accentSoft: "rgba(191, 90, 242, 0.22)",
    accentGlow: "rgba(191, 90, 242, 0.46)",
    bgDeep: "#0a0614",
    orb1: "rgba(191, 90, 242, 0.38)",
    orb2: "rgba(10, 132, 255, 0.26)",
    orb3: "rgba(255, 55, 95, 0.18)",
  },
  "Green (Emerald)": {
    accent: "#30d158",
    accentHover: "#52e378",
    accentSoft: "rgba(48, 209, 88, 0.22)",
    accentGlow: "rgba(48, 209, 88, 0.42)",
    bgDeep: "#050f0a",
    orb1: "rgba(48, 209, 88, 0.34)",
    orb2: "rgba(100, 210, 255, 0.22)",
    orb3: "rgba(48, 176, 199, 0.16)",
  },
  "Amber (Sunset)": {
    accent: "#ff9f0a",
    accentHover: "#ffb340",
    accentSoft: "rgba(255, 159, 10, 0.22)",
    accentGlow: "rgba(255, 159, 10, 0.42)",
    bgDeep: "#120b05",
    orb1: "rgba(255, 159, 10, 0.34)",
    orb2: "rgba(255, 69, 58, 0.24)",
    orb3: "rgba(255, 214, 10, 0.16)",
  },
};

const DEFAULT_SURFACES = {
  vignetteBg:
    "radial-gradient(circle at 50% 0%, rgba(255,255,255,0.03), transparent 55%), linear-gradient(180deg, rgba(6,8,16,0.18) 0%, rgba(4,6,12,0.55) 100%)",
  dockBg: "linear-gradient(155deg, rgba(34, 41, 64, 0.66), rgba(14, 18, 30, 0.56))",
  panelBg: "linear-gradient(165deg, rgba(28, 34, 54, 0.62), rgba(14, 17, 29, 0.52))",
  cardBg: "linear-gradient(160deg, rgba(255, 255, 255, 0.068), rgba(255, 255, 255, 0.024))",
  pillBg: "rgba(255, 255, 255, 0.065)",
  inputBg: "rgba(8, 11, 20, 0.52)",
  inputFocusBg: "rgba(10, 14, 26, 0.72)",
  selectOptionBg: "#121728",
  glassBorder: "rgba(255, 255, 255, 0.13)",
  glassSpecular: "rgba(255, 255, 255, 0.24)",
};

export function applyThemeCssVars(themeName) {
  const pal = LIQUID_THEMES[themeName] || LIQUID_THEMES["Blue (Default)"];
  const root = document.documentElement;
  root.style.setProperty("--accent", pal.accent);
  root.style.setProperty("--accent-hover", pal.accentHover);
  root.style.setProperty("--accent-soft", pal.accentSoft);
  root.style.setProperty("--accent-glow", pal.accentGlow);
  root.style.setProperty("--hero-start", pal.heroStart || pal.accentHover);
  root.style.setProperty("--hero-end", pal.heroEnd || pal.accent);
  root.style.setProperty("--bg-deep", pal.bgDeep);
  root.style.setProperty("--orb-1", pal.orb1);
  root.style.setProperty("--orb-2", pal.orb2);
  root.style.setProperty("--orb-3", pal.orb3);
  root.style.setProperty("--vignette-bg", pal.vignetteBg || DEFAULT_SURFACES.vignetteBg);
  root.style.setProperty("--dock-bg", pal.dockBg || DEFAULT_SURFACES.dockBg);
  root.style.setProperty("--panel-bg", pal.panelBg || DEFAULT_SURFACES.panelBg);
  root.style.setProperty("--card-bg", pal.cardBg || DEFAULT_SURFACES.cardBg);
  root.style.setProperty("--pill-bg", pal.pillBg || DEFAULT_SURFACES.pillBg);
  root.style.setProperty("--input-bg", pal.inputBg || DEFAULT_SURFACES.inputBg);
  root.style.setProperty("--input-focus-bg", pal.inputFocusBg || DEFAULT_SURFACES.inputFocusBg);
  root.style.setProperty("--select-option-bg", pal.selectOptionBg || DEFAULT_SURFACES.selectOptionBg);
  root.style.setProperty("--glass-border", pal.glassBorder || DEFAULT_SURFACES.glassBorder);
  root.style.setProperty("--glass-specular", pal.glassSpecular || DEFAULT_SURFACES.glassSpecular);
}

export default function LiquidBackdrop() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none select-none" style={{ backgroundColor: "var(--bg-deep)" }}>
      {/* GPU-accelerated mesh aurora layers */}
      <div
        className="orb-a absolute -top-[18%] -left-[12%] w-[62vw] h-[62vw] rounded-full blur-[110px]"
        style={{ background: "radial-gradient(circle, var(--orb-1) 0%, transparent 70%)" }}
      />
      <div
        className="orb-b absolute -bottom-[24%] -right-[10%] w-[58vw] h-[58vw] rounded-full blur-[120px]"
        style={{ background: "radial-gradient(circle, var(--orb-2) 0%, transparent 70%)" }}
      />
      <div
        className="orb-a absolute top-[28%] left-[44%] w-[42vw] h-[42vw] rounded-full blur-[100px]"
        style={{ background: "radial-gradient(circle, var(--orb-3) 0%, transparent 72%)" }}
      />
      {/* Subtle Apple studio dark vignette */}
      <div
        className="absolute inset-0"
        style={{
          background: "var(--vignette-bg)",
        }}
      />
    </div>
  );
}
