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
    'pdf_quality': 'High',
    'pdf_extract_all': False,
    'resize_preset': 'Original (100%)',
    'custom_max_width': 0,
    'custom_max_height': 0,
    'preserve_exif': True
}

DEFAULT_UPSCALER_SETTINGS = {
    'scale': '2x',
    'model': 'realesr',
    'style_model': 'realesr-animevideov3',
    'noise_level': -1,
    'output_format': 'PNG',
    'keep_format': True,
    'tile_size': 0,
    'tta_mode': False,
    'gpu_id': 'auto'
}

DEFAULT_DENOISER_SETTINGS = {
    'engine': 'waifu2x',
    'strength': 'Medium',
    'noise_level': 1,
    'output_format': 'PNG',
    'keep_format': True,
    'tile_size': 0,
    'tta_mode': False,
    'gpu_id': 'auto'
}

DEFAULT_STITCHER_SETTINGS = {
    'output_format': 'PNG',
    'spacing': 0,
    'layout': 'Vertical (Top to Bottom)',
    'grid_columns': 2,
    'alignment': 'Center',
    'bg_color': 'Transparent',
    'resize_option': "Don't Resize"
}
