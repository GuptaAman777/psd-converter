# Application Constants
APP_VERSION = "7.0"
GITHUB_REPO_URL = "https://github.com/GuptaAman777/psd-converter"
GITHUB_RELEASES_URL = "https://api.github.com/repos/GuptaAman777/psd-converter/releases/latest"
GITHUB_PROFILE_URL = "https://github.com/GuptaAman777"

# Formats
INPUT_FORMATS = ["PNG", "JPEG", "JPG", "BMP", "GIF", "TIFF", "WEBP", "PDF", "PSD"]
OUTPUT_FORMATS = ["PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP", "PDF"]
UPSCALE_FORMATS = ["PNG", "JPEG", "JPG", "WEBP"]
DENOISE_FORMATS = ["PNG", "JPEG", "JPG", "WEBP"]

# Upscaler Settings
UPSCALE_FACTORS = ["1x", "2x", "3x", "4x", "8x"]
UPSCALE_MODELS = ["realesr", "waifu2x", "realcugan", "srmd"]
DENOISE_MODELS = ["waifu2x", "realcugan", "srmd"]

# Tile sizes for VRAM protection
TILE_SIZES = ["Auto (0)", "64", "100", "200", "400"]

# Resizing Presets
RESIZE_PRESETS = ["Original (100%)", "25%", "50%", "75%", "150%", "200%", "Custom Bounds"]

# Color Schemes & Themes
THEMES = {
    "Blue (Default)": {
        'primary': "#007AFF", 
        'secondary': "#007AFF", 
        'background': "#1e1e2e",
        'panel': "#2d2d3f", 
        'surface': "#1e1e2e", 
        'text': "#ffffff",
        'text_secondary': "#aaaaaa", 
        'border': "#3d3d4f",
        'success': "#34c759", 
        'error': "#FF3B30", 
        'disabled': "#003063", 
        'hover': "#0064d1", 
        '!tab': "#262636", 
        'error_hover': "#c2281f"
    },
    "Red (Crimson)": {
        'primary': "#E53935", 
        'secondary': "#E53935", 
        'background': "#1c1417",
        'panel': "#2c1c22", 
        'surface': "#1c1417", 
        'text': "#ffffff",
        'text_secondary': "#c4aeb4", 
        'border': "#4d2c37",
        'success': "#34c759", 
        'error': "#FF3B30", 
        'disabled': "#4a1b1e", 
        'hover': "#c62828", 
        '!tab': "#24181d", 
        'error_hover': "#b71c1c"
    },
    "Black (OLED Dark)": {
        'primary': "#27272e", 
        'secondary': "#141418", 
        'background': "#000000",
        'panel': "#050507", 
        'surface': "#000000", 
        'text': "#f5f5f7",
        'text_secondary': "#a1a1aa", 
        'border': "#27272a",
        'success': "#30d158", 
        'error': "#ff453a", 
        'disabled': "#18181b", 
        'hover': "#3f3f46", 
        '!tab': "#0a0a0c", 
        'error_hover': "#c2281f"
    },
    "Purple (Cyberpunk)": {
        'primary': "#9D4EDD", 
        'secondary': "#9D4EDD", 
        'background': "#151022",
        'panel': "#241938", 
        'surface': "#151022", 
        'text': "#ffffff",
        'text_secondary': "#b0a3c7", 
        'border': "#3d2a5c",
        'success': "#34c759", 
        'error': "#FF3B30", 
        'disabled': "#3c175b", 
        'hover': "#7b2cbf", 
        '!tab': "#1d152e", 
        'error_hover': "#c2281f"
    },
    "Green (Emerald)": {
        'primary': "#10B981", 
        'secondary': "#10B981", 
        'background': "#0e1a14",
        'panel': "#182b20", 
        'surface': "#0e1a14", 
        'text': "#ffffff",
        'text_secondary': "#a1b8ab", 
        'border': "#264734",
        'success': "#10b981", 
        'error': "#FF3B30", 
        'disabled': "#0e3b2a", 
        'hover': "#059669", 
        '!tab': "#13231a", 
        'error_hover': "#c2281f"
    },
    "Amber (Sunset)": {
        'primary': "#F59E0B", 
        'secondary': "#F59E0B", 
        'background': "#1a130e",
        'panel': "#2c1e14", 
        'surface': "#1a130e", 
        'text': "#ffffff",
        'text_secondary': "#baa799", 
        'border': "#473020",
        'success': "#34c759", 
        'error': "#FF3B30", 
        'disabled': "#52330a", 
        'hover': "#D97706", 
        '!tab': "#221811", 
        'error_hover': "#c2281f"
    }
}
DEFAULT_THEME = "Blue (Default)"

# Active Color Scheme (initialized with default theme)
COLORS = dict(THEMES[DEFAULT_THEME])

def set_theme(theme_name):
    """Update global COLORS dictionary in-place with chosen theme."""
    if theme_name in THEMES:
        COLORS.update(THEMES[theme_name])
        return True
    return False

def get_current_theme_name():
    """Detect theme matching current COLORS dictionary."""
    for name, theme_colors in THEMES.items():
        if theme_colors.get('primary') == COLORS.get('primary') and theme_colors.get('background') == COLORS.get('background'):
            return name
    return DEFAULT_THEME
