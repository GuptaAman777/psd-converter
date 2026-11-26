import os

from src.utils.helpers import _is_dir_writable, get_app_user_data_dir, get_resource_path

JANAI_GITHUB_RELEASE_BASE = os.environ.get(
    "IMAGETOOL_JANAI_BASE_URL",
    "https://github.com/GuptaAman777/mangajanai-illustrationjanai-ncnn-vulkan/releases/download/v1.0.0",
).rstrip("/")


def _janai_entry(
    model_id: str,
    label: str,
    family: str,
    category: str,
    scale: int,
    align: int,
    size_mb: float,
    description: str,
) -> dict:
    return {
        "id": model_id,
        "label": label,
        "family": family,
        "category": category,
        "scale": scale,
        "align": align,
        "size_mb": size_mb,
        "engine": "janai_ncnn",
        "rel_dir": family,
        "description": description,
        "param_url": f"{JANAI_GITHUB_RELEASE_BASE}/{model_id}.ncnn.param",
        "bin_url": f"{JANAI_GITHUB_RELEASE_BASE}/{model_id}.ncnn.bin",
    }


JANAI_MODEL_CATALOG = [
    # --- SPAN (Fast Illustration V3, 2x, align=1) ---
    _janai_entry(
        "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16",
        "IllustrationJaNai V3 Detail (SPAN-S 2x)",
        "SPAN",
        "Fast Illustration (SPAN)",
        2,
        1,
        0.8,
        "Ultra-fast 0.8 MB 2x illustration upscaler preserving crisp ink lines and micro-details.",
    ),
    _janai_entry(
        "2x_IllustrationJaNai_V3denoise_SPAN_S_30k_fp16",
        "IllustrationJaNai V3 Denoise (SPAN-S 2x)",
        "SPAN",
        "Fast Illustration (SPAN)",
        2,
        1,
        0.8,
        "Ultra-fast 0.8 MB 2x illustration cleaner removing JPEG artifacts and subtle noise.",
    ),
    # --- FDAT (Transformer Illustration V3, 4x align=8 / 2x align=16) ---
    _janai_entry(
        "4x_IllustrationJaNai_V3detail_FDAT_XL_27k_fp16",
        "IllustrationJaNai V3 Detail (FDAT-XL 4x)",
        "FDAT",
        "Illustration (FDAT)",
        4,
        8,
        45.6,
        "Flagship FDAT-XL transformer for maximum 4x illustration detail, shading, and texture recovery.",
    ),
    _janai_entry(
        "4x_IllustrationJaNai_V3denoise_FDAT_XL_32k_fp16",
        "IllustrationJaNai V3 Denoise (FDAT-XL 4x)",
        "FDAT",
        "Illustration (FDAT)",
        4,
        8,
        45.6,
        "Flagship FDAT-XL 4x transformer tuned for compressed or noisy digital artwork and CGs.",
    ),
    _janai_entry(
        "4x_IllustrationJaNai_V3detail_FDAT_M_40k_fp16",
        "IllustrationJaNai V3 Detail (FDAT-M 4x)",
        "FDAT",
        "Illustration (FDAT)",
        4,
        8,
        8.1,
        "Balanced 8.1 MB FDAT-M 4x transformer with fast Vulkan speed and sharp line fidelity.",
    ),
    _janai_entry(
        "4x_IllustrationJaNai_V3denoise_FDAT_M_47k_fp16",
        "IllustrationJaNai V3 Denoise (FDAT-M 4x)",
        "FDAT",
        "Illustration (FDAT)",
        4,
        8,
        8.1,
        "Balanced 8.1 MB FDAT-M 4x transformer removing JPEG blockiness while keeping crisp lines.",
    ),
    _janai_entry(
        "2x_IllustrationJaNai_V3detail_FDAT_M_unshuffle_40k_fp16",
        "IllustrationJaNai V3 Detail (FDAT-M 2x)",
        "FDAT",
        "Illustration (FDAT)",
        2,
        16,
        8.1,
        "High-fidelity 2x FDAT-M unshuffle transformer for clean digital paintings and line art.",
    ),
    _janai_entry(
        "2x_IllustrationJaNai_V3denoise_FDAT_M_unshuffle_30k_fp16",
        "IllustrationJaNai V3 Denoise (FDAT-M 2x)",
        "FDAT",
        "Illustration (FDAT)",
        2,
        16,
        8.1,
        "High-fidelity 2x FDAT-M unshuffle transformer that cleans artifacts during 2x enlargement.",
    ),
    # --- ESRGAN_4x (MangaJaNai V1, 4x, align=1) ---
    _janai_entry(
        "4x_MangaJaNai_1200p_V1_ESRGAN_70k_fp16",
        "MangaJaNai 1200p V1 (ESRGAN 4x)",
        "ESRGAN_4x",
        "Manga 4x (ESRGAN)",
        4,
        1,
        32.0,
        "Tuned for ~1200p digital manga scans; restores screentones and sharp ink without halos.",
    ),
    _janai_entry(
        "4x_MangaJaNai_1300p_V1_ESRGAN_75k_fp16",
        "MangaJaNai 1300p V1 (ESRGAN 4x)",
        "ESRGAN_4x",
        "Manga 4x (ESRGAN)",
        4,
        1,
        32.0,
        "Tuned for ~1300p manga releases with clean gray tones and speech-bubble text.",
    ),
    _janai_entry(
        "4x_MangaJaNai_1400p_V1_ESRGAN_105k_fp16",
        "MangaJaNai 1400p V1 (ESRGAN 4x)",
        "ESRGAN_4x",
        "Manga 4x (ESRGAN)",
        4,
        1,
        32.0,
        "Tuned for ~1400p manga scans balancing halftone preservation and crisp blacks.",
    ),
    _janai_entry(
        "4x_MangaJaNai_1500p_V1_ESRGAN_105k_fp16",
        "MangaJaNai 1500p V1 (ESRGAN 4x)",
        "ESRGAN_4x",
        "Manga 4x (ESRGAN)",
        4,
        1,
        32.0,
        "Tuned for ~1500p manga scans with faithful screentone pattern reconstruction.",
    ),
    _janai_entry(
        "4x_MangaJaNai_1600p_V1_ESRGAN_70k_fp16",
        "MangaJaNai 1600p V1 (ESRGAN 4x)",
        "ESRGAN_4x",
        "Manga 4x (ESRGAN)",
        4,
        1,
        32.0,
        "Tuned for ~1600p high-resolution manga pages and clean tankobon rips.",
    ),
    _janai_entry(
        "4x_MangaJaNai_1920p_V1_ESRGAN_105k_fp16",
        "MangaJaNai 1920p V1 (ESRGAN 4x)",
        "ESRGAN_4x",
        "Manga 4x (ESRGAN)",
        4,
        1,
        32.0,
        "Tuned for ~1920p high-res manga scans preserving subtle pen strokes and dot patterns.",
    ),
    _janai_entry(
        "4x_MangaJaNai_2048p_V1_ESRGAN_70k_fp16",
        "MangaJaNai 2048p V1 (ESRGAN 4x)",
        "ESRGAN_4x",
        "Manga 4x (ESRGAN)",
        4,
        1,
        32.0,
        "Tuned for ~2048p native-HD manga volumes with minimal smoothing.",
    ),
    # --- ESRGAN_2x (MangaJaNai V1, 2x, align=2) ---
    _janai_entry(
        "2x_MangaJaNai_1200p_V1_ESRGAN_70k_fp16",
        "MangaJaNai 1200p V1 (ESRGAN 2x)",
        "ESRGAN_2x",
        "Manga 2x (ESRGAN)",
        2,
        2,
        32.0,
        "Fast 2x manga model tuned for ~1200p scans; preserves screentones and fine lettering.",
    ),
    _janai_entry(
        "2x_MangaJaNai_1300p_V1_ESRGAN_75k_fp16",
        "MangaJaNai 1300p V1 (ESRGAN 2x)",
        "ESRGAN_2x",
        "Manga 2x (ESRGAN)",
        2,
        2,
        32.0,
        "Fast 2x manga model tuned for ~1300p scans with clean line edges.",
    ),
    _janai_entry(
        "2x_MangaJaNai_1400p_V1_ESRGAN_70k_fp16",
        "MangaJaNai 1400p V1 (ESRGAN 2x)",
        "ESRGAN_2x",
        "Manga 2x (ESRGAN)",
        2,
        2,
        32.0,
        "Fast 2x manga model tuned for ~1400p pages and compressed web manga.",
    ),
    _janai_entry(
        "2x_MangaJaNai_1500p_V1_ESRGAN_90k_fp16",
        "MangaJaNai 1500p V1 (ESRGAN 2x)",
        "ESRGAN_2x",
        "Manga 2x (ESRGAN)",
        2,
        2,
        32.0,
        "Fast 2x manga model tuned for ~1500p digital manga with accurate halftone dots.",
    ),
    _janai_entry(
        "2x_MangaJaNai_1600p_V1_ESRGAN_90k_fp16",
        "MangaJaNai 1600p V1 (ESRGAN 2x)",
        "ESRGAN_2x",
        "Manga 2x (ESRGAN)",
        2,
        2,
        32.0,
        "Fast 2x manga model tuned for ~1600p high-res manga chapters.",
    ),
    _janai_entry(
        "2x_MangaJaNai_1920p_V1_ESRGAN_70k_fp16",
        "MangaJaNai 1920p V1 (ESRGAN 2x)",
        "ESRGAN_2x",
        "Manga 2x (ESRGAN)",
        2,
        2,
        32.0,
        "Fast 2x manga model tuned for ~1920p crisp digital volumes.",
    ),
    _janai_entry(
        "2x_MangaJaNai_2048p_V1_ESRGAN_95k_fp16",
        "MangaJaNai 2048p V1 (ESRGAN 2x)",
        "ESRGAN_2x",
        "Manga 2x (ESRGAN)",
        2,
        2,
        32.0,
        "Fast 2x manga model tuned for ~2048p UHD manga spreads.",
    ),
]

JANAI_MODEL_MAP = {m["id"]: m for m in JANAI_MODEL_CATALOG}


def _valid_pair(param_path: str, bin_path: str) -> bool:
    return (
        os.path.isfile(param_path)
        and os.path.getsize(param_path) > 64
        and os.path.isfile(bin_path)
        and os.path.getsize(bin_path) > 1024
    )


def get_local_janai_root() -> str:
    """Return local/bundled `ncnn/` root directory if present on disk."""
    return get_resource_path("ncnn")


def get_downloaded_janai_root() -> str:
    """Return writable directory for user-downloaded JaNai NCNN models from GitHub."""
    local_root = get_local_janai_root()
    if os.path.isdir(local_root) and _is_dir_writable(local_root):
        return local_root
    user_janai = os.path.join(get_app_user_data_dir(), "models", "janai")
    os.makedirs(user_janai, exist_ok=True)
    return user_janai


def get_janai_download_dest(model_id: str) -> tuple[str, str]:
    """Return target (param_path, bin_path) for downloading `model_id`."""
    meta = JANAI_MODEL_MAP[model_id]
    user_janai = os.path.join(get_app_user_data_dir(), "models", "janai", meta["rel_dir"])
    os.makedirs(user_janai, exist_ok=True)
    return (
        os.path.join(user_janai, f"{model_id}.ncnn.param"),
        os.path.join(user_janai, f"{model_id}.ncnn.bin"),
    )


def resolve_janai_model_paths(model_id: str) -> dict:
    """Resolve `.ncnn.param` and `.ncnn.bin` paths from either local `ncnn/` or downloaded store."""
    meta = JANAI_MODEL_MAP.get(model_id)
    if not meta:
        return {"installed": False, "source": "unknown", "param_path": "", "bin_path": "", "removable": False}

    rel_dir = meta["rel_dir"]
    p_name = f"{model_id}.ncnn.param"
    b_name = f"{model_id}.ncnn.bin"

    # 1. Local/bundled `ncnn/` folder (used during local testing or offline packs)
    local_p = os.path.join(get_local_janai_root(), rel_dir, p_name)
    local_b = os.path.join(get_local_janai_root(), rel_dir, b_name)
    if _valid_pair(local_p, local_b):
        return {
            "installed": True,
            "source": "local",
            "param_path": local_p,
            "bin_path": local_b,
            "removable": False,
        }

    # 2. User-downloaded store under LocalAppData / AppUserData (GitHub download mode)
    dl_dir = os.path.join(get_app_user_data_dir(), "models", "janai", rel_dir)
    dl_p = os.path.join(dl_dir, p_name)
    dl_b = os.path.join(dl_dir, b_name)
    if _valid_pair(dl_p, dl_b):
        return {
            "installed": True,
            "source": "downloaded",
            "param_path": dl_p,
            "bin_path": dl_b,
            "removable": True,
        }

    return {
        "installed": False,
        "source": "none",
        "param_path": dl_p,
        "bin_path": dl_b,
        "removable": False,
    }
