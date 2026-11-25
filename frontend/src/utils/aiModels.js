export const AI_ENGINES = [
  { value: "realesr", label: "Upscayl / Real-ESRGAN — Best All-Rounder & Extra Packs" },
  { value: "realcugan", label: "Real-CUGAN — Crisp Anime, Manga & Line Art" },
  { value: "waifu2x", label: "Waifu2x 2025 — Classic 1x–8x Anime & Photo" },
  { value: "srmd", label: "SRMD — Noisy Scans & Compressed Photos" },
];

const BUILTIN_GROUPS = {
  realesr: [
    {
      group: "Built-in — Anime & Video",
      items: [
        { label: "AnimeVideo V3 (2x / 3x / 4x • Fast)", value: "realesr-animevideov3" },
        { label: "RealESRGAN+ Anime (4x Crisp Lines)", value: "realesrgan-x4plus-anime" },
      ],
    },
    {
      group: "Built-in — Photo & Realism",
      items: [
        { label: "Classic ESRGAN (4x Archive)", value: "esrgan-x4" },
        { label: "RealESRGAN+ (4x Photo Realism)", value: "realesrgan-x4plus" },
        { label: "RealESRNet+ (4x Natural Balance)", value: "realesrnet-x4plus" },
      ],
    },
  ],
  realcugan: [
    {
      group: "Real-CUGAN Models",
      items: [
        { label: "SE — Standard Versatile (2x / 3x / 4x)", value: "models-se" },
        { label: "Pro — Advanced High Fidelity (2x / 3x)", value: "models-pro" },
        { label: "Nose — Retain Fine Line Details (2x)", value: "models-nose" },
      ],
    },
  ],
  waifu2x: [
    {
      group: "Waifu2x 2025 Models",
      items: [
        { label: "CUnet — Best Overall (1x–8x)", value: "models-cunet" },
        { label: "Upconv — Anime / Illustration (2x / 4x)", value: "models-upconv_7_anime_style_art_rgb" },
        { label: "Upconv — Photography (2x / 4x)", value: "models-upconv_7_photo" },
      ],
    },
  ],
  srmd: [
    {
      group: "SRMD Super-Resolution",
      items: [{ label: "SRMD — General Photo & Scan Restoration", value: "models-srmd" }],
    },
  ],
};

const CUSTOM_CAT_ORDER = ["Photo & Realism", "Anime & Art", "Fast Compact", "Restoration"];

/** Build clean categorized & alphabetically sorted <optgroup> entries for Engine Model Variants. */
export function getGroupedModelOptions(engine, modelCatalog = []) {
  const base = BUILTIN_GROUPS[engine] || BUILTIN_GROUPS.realesr;
  if (engine !== "realesr") return base;

  const installed = (modelCatalog || []).filter((m) => m.installed && (m.engine || "realesr") === "realesr");
  if (installed.length === 0) return base;

  const byCat = {};
  for (const m of installed) {
    const cat = m.category || "Custom Packs";
    if (!byCat[cat]) byCat[cat] = [];
    byCat[cat].push({
      label: `${m.label} (${m.scale}x • Custom)`,
      value: m.id,
    });
  }

  const customGroups = Object.keys(byCat)
    .sort((a, b) => {
      const ia = CUSTOM_CAT_ORDER.indexOf(a);
      const ib = CUSTOM_CAT_ORDER.indexOf(b);
      if (ia !== -1 && ib !== -1) return ia - ib;
      if (ia !== -1) return -1;
      if (ib !== -1) return 1;
      return a.localeCompare(b);
    })
    .map((cat) => ({
      group: `Downloaded — ${cat}`,
      items: byCat[cat].sort((a, b) => a.label.localeCompare(b.label)),
    }));

  return [...base, ...customGroups];
}
