# PSD Converter Pro

![PSD Converter Pro](screenshots/app_screenshot.png)

A powerful and user-friendly tool for converting PSD files and other image formats with AI upscaling capabilities.

## Features

- **Multi-format Support**: Convert between PNG, JPEG, BMP, GIF, TIFF, WEBP, PDF, and PSD files
- **AI Upscaling**: Enhance image quality with built-in AI upscaling (2x, 3x, or 4x)
- **Batch Processing**: Convert multiple files or entire folders at once
- **Modern UI**: Clean, intuitive interface with dark mode
- **Progress Tracking**: Real-time conversion progress with ETA and speed indicators
- **Detailed Statistics**: View conversion statistics including file size reduction/increase

## Installation

1. Download the latest release from the [Releases](https://github.com/GuptaAman777/psd-converter/releases) page
2. Extract the ZIP file to a location of your choice
3. Run `PSDConverterPro.exe` - no installation required!

## Usage

1. **Select Files or Folder**: Click "Select Files" or "Select Folder" to choose what you want to convert
2. **Choose Output Format**: Select your desired output format from the dropdown menu
3. **Enable AI Upscaling (Optional)**: Check "Enable AI Upscaling" and select a scale factor if desired
4. **Select Output Directory**: Choose where to save the converted files
5. **Convert**: Click the "Convert" button to start the conversion process

## Supported Formats

### Input Formats
- PSD (Photoshop Document)
- PNG
- JPEG/JPG
- BMP
- GIF
- TIFF
- WEBP
- PDF

### Output Formats
- PNG
- JPEG/JPG
- BMP
- GIF
- TIFF
- WEBP
- PDF

## System Requirements

- Windows 10 or later
- 4GB RAM minimum (8GB recommended for AI upscaling)
- 500MB free disk space
- For AI upscaling: NVIDIA GPU with CUDA support recommended

## License

For personal use only. For commercial licensing, please contact: [github.com/GuptaAman777](https://github.com/GuptaAman777)

## Credits

- AI upscaling powered by [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- PSD file handling via [psd-tools](https://github.com/psd-tools/psd-tools)
- PDF processing via [PyMuPDF](https://github.com/pymupdf/PyMuPDF)

## Troubleshooting

**Q: The application crashes when processing large files**  
A: Try converting files individually rather than in batch for very large PSD files.

**Q: AI upscaling is slow**  
A: AI upscaling is computationally intensive. Performance is better on systems with dedicated GPUs.

**Q: Some PDF files don't convert properly**  
A: The application currently supports single-page PDF conversion. Multi-page PDFs will only convert the first page.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.