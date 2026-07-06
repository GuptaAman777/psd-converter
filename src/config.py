QUALITY_MAP = {
    "Maximum": 95,
    "High": 85,
    "Medium": 70,
    "Low": 50
}

COMPRESSION_MAP = {
    "None": 0,
    "Fast": 1,
    "Normal": 6,
    "Maximum": 9
}

DEFAULT_CONVERTER_SETTINGS = {
    'jpeg_quality': 'High',
    'webp_quality': 'High',
    'png_compression': 'Normal',
    'pdf_dpi': '150 DPI',
    'pdf_quality': 'High'
}

DEFAULT_UPSCALER_SETTINGS = {
    'scale': '2x',
    'model': 'realesr',
    'style_model': 'realesr-animevideov3',
    'noise_level': -1,
    'output_format': 'PNG',
    'keep_format': True
}

DEFAULT_DENOISER_SETTINGS = {
    'strength': 'Medium',
    'output_format': 'PNG',
    'keep_format': True
}

DEFAULT_STITCHER_SETTINGS = {
    'output_format': 'PNG',
    'spacing': 0
}
