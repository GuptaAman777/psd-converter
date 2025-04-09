# Image & PSD Converter

A powerful desktop application for converting, upscaling, and enhancing image files including PSD files.

## Features

### File Conversion
- Convert between multiple image formats (PNG, JPG, WEBP, TIFF, BMP, GIF)
- Convert PSD files to standard image formats
- Convert PDF files to images
- Batch processing for multiple files
- Preserve transparency when supported by the output format

### AI Enhancement
- AI-powered upscaling using RealESRGAN technology
- Increase image resolution by 2x, 3x, or 4x
- Multiple AI models for different image types
- Noise reduction and image enhancement

### Advanced Settings
- Adjustable quality settings for JPG, WEBP, and PNG
- PDF resolution control (72 DPI to 600 DPI)
- Compression level options for optimizing file size
- Batch processing with progress tracking

## System Requirements

- Windows 10 or later (64-bit)
- 4GB RAM minimum (8GB+ recommended for AI upscaling)
- GPU with DirectX 12 support recommended for AI features
- 500MB free disk space for application
- Additional space for processed files

## Installation

1. Download the latest release from the [Releases](https://github.com/GuptaAman777/image-psd-converter/releases) page
2. Run the installer and follow the on-screen instructions
3. No additional software installation required - all dependencies are included

## Usage Guide

### Basic Conversion

1. **Select Files**: Click "Add Files" or drag and drop files into the application
2. **Choose Output Format**: Select your desired output format from the dropdown menu
3. **Set Output Location**: Choose where to save the converted files
4. **Convert**: Click the "Convert" button to begin processing

### AI Upscaling

1. **Enable Upscaling**: Check the "Enable AI Upscaling" option
2. **Select Scale Factor**: Choose 2x, 3x, or 4x upscaling
3. **Select Model**: Choose the appropriate AI model for your image type
4. **Process**: Click "Upscale" to enhance your images

### Batch Processing

1. **Add Multiple Files**: Select multiple files or entire folders
2. **Configure Settings**: Set your desired output format and quality
3. **Start Batch**: Click "Convert" to process all files
4. **Monitor Progress**: View real-time progress with estimated completion time

## Quality Settings

### JPEG Quality
- **Maximum**: Highest quality, larger file size
- **High**: Very good quality with reasonable file size
- **Medium**: Good quality with smaller file size
- **Low**: Reduced quality with minimal file size

### PNG Compression
- **Maximum**: Highest compression, smaller files (slower)
- **Normal**: Balanced compression and speed
- **Fast**: Quick compression with larger files
- **None**: No compression, largest file size but fastest

### PDF Resolution
- **72 DPI**: Web quality
- **150 DPI**: Good for general use
- **300 DPI**: Print quality
- **600 DPI**: High-detail print quality

## AI Models

- **anime**: Optimized for anime and cartoon images
- **photo**: Best for photographs and realistic images
- **general**: Good all-purpose model for mixed content

## Troubleshooting

### Common Issues

- **Slow Processing**: AI upscaling is GPU-intensive. Try using a smaller scale factor or processing fewer files at once.
- **Out of Memory**: Close other applications or reduce the number of files being processed simultaneously.
- **Unsupported File**: Ensure your files are not corrupted and are in a supported format.

### GPU Compatibility

The application will automatically detect your GPU capabilities. For optimal AI upscaling performance:
- Use a dedicated GPU rather than integrated graphics
- Ensure your graphics drivers are up to date
- Close other GPU-intensive applications while processing

## Privacy

This application processes all files locally on your computer. No files or data are uploaded to external servers.

## License

This software is released under the MIT License. See the LICENSE file for details.

## Acknowledgments

- RealESRGAN for AI upscaling technology
- PyQt for the user interface framework
- Pillow for image processing capabilities

## Support

For issues, feature requests, or questions, please open an issue on the [GitHub repository](https://github.com/GuptaAman777/image-psd-converter/issues).
