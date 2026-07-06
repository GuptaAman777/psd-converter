# ImageTool

A powerful, all-in-one desktop application for image processing built with Python and PyQt6. This tool provides an intuitive graphical interface for converting, upscaling, denoising, and stitching images.

## ✨ Features

*   **Image Conversion**: Convert between various image formats (JPEG, PNG, WEBP) and even PDF with customizable quality and compression settings.
*   **AI Upscaling**: High-quality image upscaling using state-of-the-art models (Real-ESRGAN, Real-CUGAN, Waifu2x).
*   **Image Denoising**: Reduce noise and artifacts in images with adjustable strength levels.
*   **Image Stitching**: Seamlessly stitch multiple images together with customizable spacing.
*   **Modern UI**: A clean, responsive, and user-friendly interface built with PyQt6.
*   **Multi-threading**: Processing tasks run in the background without freezing the UI.

## 📂 Project Structure

```text
ImageTool - Copy/
│
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── fix_panel.py                # Standalone script/utility for panels
├── fix_upscale.py              # Standalone script/utility for upscaler
│
└── src/                        # Main source code directory
    ├── config.py               # Default settings and configurations
    ├── constants.py            # Global constants and app-wide values
    │
    ├── assets/                 # Static assets (images, icons, etc.)
    │   └── icons/
    │
    ├── core/                   # Background processing and core logic
    │   ├── converter_thread.py # Thread for image conversion
    │   ├── denoiser_thread.py  # Thread for image denoising
    │   ├── stitcher_thread.py  # Thread for image stitching
    │   ├── upscaler_thread.py  # Thread for image upscaling
    │   ├── esr/                # Real-ESRGAN backend
    │   ├── realcugan-ncnn-vulkan/ # Real-CUGAN backend
    │   └── waifu2x-ncnn-vulkan/   # Waifu2x backend
    │
    ├── managers/               # Managers for handling data and state
    │   └── file_list_manager.py# Manages the list of files to process
    │
    ├── ui/                     # User Interface components
    │   ├── main_window.py      # Main application window
    │   ├── styles.py           # UI styles and themes
    │   ├── panels/             # Different feature panels
    │   │   ├── converter_panel.py
    │   │   ├── denoiser_panel.py
    │   │   ├── footer.py
    │   │   ├── settings_panel.py
    │   │   ├── stitcher_panel.py
    │   │   └── upscaler_panel.py
    │   └── widgets/            # Reusable UI widgets
    │       ├── animated_combobox.py
    │       ├── progress_dialog.py
    │       ├── update_notification.py
    │       └── upscale_settings.py
    │
    └── utils/                  # Helper utilities and functions
        ├── helpers.py          # General helper functions
        ├── logger.py           # Logging utility
        └── updater.py          # Application updater
```

## 🚀 Getting Started

### Prerequisites

Ensure you have Python installed on your system. 

### Installation

1.  Clone the repository or download the source code.
2.  Install the required dependencies using `pip`:

```bash
pip install -r requirements.txt
```

### Running the Application

Execute `main.py` to start the application:

```bash
python main.py
```

## 📦 Dependencies

The project relies on the following main Python libraries:

*   `PyQt6` - For the Graphical User Interface.
*   `Pillow` - For image processing and manipulation.
*   `psd-tools` - For handling Photoshop (PSD) files.
*   `PyMuPDF` - For PDF handling.
*   `requests` - For checking updates and internet requests.
*   `psutil` - For process and system monitoring.
