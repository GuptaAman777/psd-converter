import os
import sys
import tempfile
import unittest
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from src.core.converter_thread import ConverterThread
from src.core.upscaler_thread import UpscalerThread
from src.core.denoiser_thread import DenoiserThread
from src.core.stitcher_thread import StitcherThread
from src.utils.helpers import get_tool_info

class TestImageToolSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="imagetool_test_")
        cls.test_img1 = os.path.join(cls.temp_dir, "test_sample1.png")
        cls.test_img2 = os.path.join(cls.temp_dir, "test_sample2.png")
        cls.test_pdf = os.path.join(cls.temp_dir, "test_doc.pdf")
        
        # Create sample test images
        img1 = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
        img1.save(cls.test_img1, "PNG")
        
        img2 = Image.new("RGB", (64, 48), (0, 255, 0))
        img2.save(cls.test_img2, "PNG")

        # Create sample 2-page PDF
        doc = fitz.open()
        p1 = doc.new_page(width=200, height=200)
        p1.draw_rect(fitz.Rect(10, 10, 190, 190), color=(1, 0, 0), fill=(1, 0, 0))
        p2 = doc.new_page(width=200, height=200)
        p2.draw_rect(fitz.Rect(10, 10, 190, 190), color=(0, 0, 1), fill=(0, 0, 1))
        doc.save(cls.test_pdf)
        doc.close()

    def test_01_tool_paths(self):
        """Verify all 4 AI engines exist and are located."""
        for tool in ["esr", "waifu2x", "realcugan", "srmd"]:
            exe_path, exe_dir = get_tool_info(tool)
            self.assertTrue(os.path.exists(exe_path), f"Binary for {tool} missing at {exe_path}")
            self.assertTrue(os.path.isdir(exe_dir), f"Directory for {tool} missing at {exe_dir}")

    def test_02_converter_resizing(self):
        """Test conversion and percentage batch resizing."""
        out_dir = os.path.join(self.temp_dir, "converter_out")
        os.makedirs(out_dir, exist_ok=True)
        
        settings = {
            'jpeg_quality': 'High',
            'resize_preset': '50%'
        }
        
        thread = ConverterThread(
            [self.test_img1],
            out_dir,
            "jpeg",
            settings
        )
        thread.run()
        
        expected_output = os.path.join(out_dir, "test_sample1.jpeg")
        self.assertTrue(os.path.exists(expected_output), "Converted file does not exist")
        
        with Image.open(expected_output) as result:
            self.assertEqual(result.size, (32, 32), f"Expected 32x32 from 50% resize, got {result.size}")

    def test_03_converter_pdf_all_pages(self):
        """Test multi-page PDF extraction into dedicated document folder."""
        out_dir = os.path.join(self.temp_dir, "pdf_out")
        os.makedirs(out_dir, exist_ok=True)
        
        settings = {
            'pdf_dpi': '72 DPI',
            'pdf_quality': 'Low',
            'pdf_extract_all': True
        }
        thread = ConverterThread([self.test_pdf], out_dir, "png", settings)
        thread.run()
        
        p1 = os.path.join(out_dir, "test_doc", "page_001.png")
        p2 = os.path.join(out_dir, "test_doc", "page_002.png")
        self.assertTrue(os.path.exists(p1), "Page 1 was not extracted")
        self.assertTrue(os.path.exists(p2), "Page 2 was not extracted")

    def test_04_stitcher_grid(self):
        """Test Grid/Matrix stitching."""
        out_dir = os.path.join(self.temp_dir, "stitcher_out")
        os.makedirs(out_dir, exist_ok=True)
        
        thread = StitcherThread(
            [f"virtual:grid_test"],
            out_dir,
            is_vertical=True,
            spacing=4,
            output_format="png",
            virtual_files={f"virtual:grid_test": [self.test_img1, self.test_img2, self.test_img1, self.test_img2]},
            layout_mode="Grid (Matrix Layout)",
            grid_columns=2
        )
        thread.run()
        
        stitched_file = os.path.join(out_dir, "grid_test_stitched.png")
        self.assertTrue(os.path.exists(stitched_file), "Stitched grid file does not exist")
        with Image.open(stitched_file) as img:
            self.assertGreater(img.width, 64)
            self.assertGreater(img.height, 48)

    def test_05_denoiser_thread(self):
        """Test Waifu2x denoising."""
        out_dir = os.path.join(self.temp_dir, "denoiser_out")
        os.makedirs(out_dir, exist_ok=True)
        
        thread = DenoiserThread(
            [self.test_img1],
            out_dir,
            noise_level=1,
            model="anime",
            engine="waifu2x"
        )
        thread.run()
        
        denoised_file = os.path.join(out_dir, "test_sample1_denoised.png")
        self.assertTrue(os.path.exists(denoised_file), "Denoised file was not produced")

    def test_06_upscaler_srmd(self):
        """Test SRMD upscaling on small image."""
        out_dir = os.path.join(self.temp_dir, "srmd_out")
        os.makedirs(out_dir, exist_ok=True)
        
        thread = UpscalerThread(
            [self.test_img1],
            out_dir,
            upscale_factor="2x",
            model="srmd",
            style_model="models-srmd",
            noise_level=3
        )
        thread.run()
        
        upscaled_file = os.path.join(out_dir, "test_sample1_upscaled2x.png")
        self.assertTrue(os.path.exists(upscaled_file), "SRMD upscaled file was not produced")
        with Image.open(upscaled_file) as img:
            self.assertEqual(img.size, (128, 128), f"Expected 128x128 from 2x upscaler, got {img.size}")

    def test_07_upscaler_realesrgan(self):
        """Test Real-ESRGAN upscaling."""
        out_dir = os.path.join(self.temp_dir, "esr_out")
        os.makedirs(out_dir, exist_ok=True)
        
        thread = UpscalerThread(
            [self.test_img1],
            out_dir,
            upscale_factor="2x",
            model="realesr",
            style_model="realesr-animevideov3",
            noise_level=-1
        )
        thread.run()
        
        upscaled_file = os.path.join(out_dir, "test_sample1_upscaled2x.png")
        self.assertTrue(os.path.exists(upscaled_file), "Real-ESRGAN upscaled file was not produced")
        with Image.open(upscaled_file) as img:
            self.assertEqual(img.size, (128, 128), f"Expected 128x128 from 2x upscaler, got {img.size}")

    def test_08_upscaler_realcugan(self):
        """Test Real-CUGAN upscaling."""
        out_dir = os.path.join(self.temp_dir, "cugan_out")
        os.makedirs(out_dir, exist_ok=True)
        
        thread = UpscalerThread(
            [self.test_img1],
            out_dir,
            upscale_factor="2x",
            model="realcugan",
            style_model="models-se",
            noise_level=1
        )
        thread.run()
        
        upscaled_file = os.path.join(out_dir, "test_sample1_upscaled2x.png")
        self.assertTrue(os.path.exists(upscaled_file), "Real-CUGAN upscaled file was not produced")
        with Image.open(upscaled_file) as img:
            self.assertEqual(img.size, (128, 128), f"Expected 128x128 from 2x upscaler, got {img.size}")

    def test_09_converter_psd_layers_folder(self):
        """Test PSD conversion with extract_layers creates a dedicated folder for each image's layers and composite."""
        import psd_tools
        psd_path = os.path.join(self.temp_dir, "sample_ch19_06.psd")
        psd = psd_tools.PSDImage.new(mode='RGB', size=(64, 64))
        psd.create_pixel_layer(Image.new('RGBA', (64, 64), (255, 0, 0, 255)), name='Background')
        psd.create_pixel_layer(Image.new('RGBA', (32, 32), (0, 255, 0, 255)), name='SpeechBubble')
        psd.save(psd_path)

        out_dir = os.path.join(self.temp_dir, "psd_layers_out")
        os.makedirs(out_dir, exist_ok=True)

        settings = {'extract_layers': True}
        thread = ConverterThread([psd_path], out_dir, "png", settings)
        thread.run()

        # Check dedicated folder for this image exists
        image_subfolder = os.path.join(out_dir, "sample_ch19_06")
        self.assertTrue(os.path.isdir(image_subfolder), f"Subfolder {image_subfolder} was not created")

        # Check composite image and all layers exist inside this image's folder
        composite_file = os.path.join(image_subfolder, "sample_ch19_06.png")
        layer1_file = os.path.join(image_subfolder, "layer_01_Background.png")
        layer2_file = os.path.join(image_subfolder, "layer_02_SpeechBubble.png")

        self.assertTrue(os.path.exists(composite_file), f"Composite file {composite_file} missing")
        self.assertTrue(os.path.exists(layer1_file), f"Layer 1 file {layer1_file} missing")
        self.assertTrue(os.path.exists(layer2_file), f"Layer 2 file {layer2_file} missing")

    def test_10_cancellation_suppresses_errors(self):
        """Test that cancelling ConverterThread, UpscalerThread, DenoiserThread, and StitcherThread does not emit error_signal."""
        out_dir = os.path.join(self.temp_dir, "cancel_test_out")
        os.makedirs(out_dir, exist_ok=True)

        converter_errors = []
        c_thread = ConverterThread(["non_existent_file.png"], out_dir, "png", {})
        c_thread.error_signal.connect(lambda msg, typ: converter_errors.append(msg))
        c_thread.stop()
        c_thread.run()
        self.assertEqual(converter_errors, [], "ConverterThread emitted error signal after cancellation")

        upscaler_errors = []
        u_thread = UpscalerThread(["non_existent_file.png"], out_dir)
        u_thread.error_signal.connect(lambda msg, typ: upscaler_errors.append(msg))
        u_thread.stop()
        u_thread.run()
        self.assertEqual(upscaler_errors, [], "UpscalerThread emitted error signal after cancellation")

        denoiser_errors = []
        d_thread = DenoiserThread(["non_existent_file.png"], out_dir)
        d_thread.error_signal.connect(lambda msg, typ: denoiser_errors.append(msg))
        d_thread.stop()
        d_thread.run()
        self.assertEqual(denoiser_errors, [], "DenoiserThread emitted error signal after cancellation")

        stitcher_errors = []
        s_thread = StitcherThread(["non_existent_folder"], out_dir, is_vertical=True, spacing=0, output_format="png")
        s_thread.error_signal.connect(lambda msg: stitcher_errors.append(msg))
        s_thread.stop()
        s_thread.run()
        self.assertEqual(stitcher_errors, [], "StitcherThread emitted error signal after cancellation")

    def test_11_theme_palette_switching(self):
        """Test switching themes updates COLORS dictionary and saves to settings."""
        from src.constants import THEMES, COLORS, set_theme, get_current_theme_name
        from src.utils.helpers import load_user_settings

        initial_theme = get_current_theme_name()
        
        # Switch to Red (Crimson)
        set_theme("Red (Crimson)")
        self.assertEqual(get_current_theme_name(), "Red (Crimson)")
        self.assertEqual(COLORS['primary'], THEMES["Red (Crimson)"]['primary'])
        self.assertEqual(COLORS['hover'], THEMES["Red (Crimson)"]['hover'])

        # Switch to Black (OLED Dark)
        set_theme("Black (OLED Dark)")
        self.assertEqual(get_current_theme_name(), "Black (OLED Dark)")
        self.assertEqual(COLORS['background'], THEMES["Black (OLED Dark)"]['background'])

        # Restore initial theme
        set_theme(initial_theme)
        self.assertEqual(get_current_theme_name(), initial_theme)

    def test_12_zero_pyqt6_imports_in_src(self):
        """Verify PyQt6 has been completely removed from main.py and all files under src/."""
        offenders = []
        for root_target in [os.path.join(PROJECT_ROOT, "main.py"), os.path.join(PROJECT_ROOT, "src")]:
            if os.path.isfile(root_target):
                files_to_check = [root_target]
            else:
                files_to_check = [
                    os.path.join(r, fn)
                    for r, _, fs in os.walk(root_target)
                    for fn in fs if fn.endswith(".py")
                ]
            for fp in files_to_check:
                with open(fp, encoding="utf-8", errors="ignore") as f:
                    for idx, line in enumerate(f, 1):
                        if "PyQt6" in line and not line.strip().startswith(('"', "'", "#")):
                            offenders.append(f"{fp}:{idx}")
        self.assertEqual(offenders, [], f"PyQt6 references remain: {offenders}")

    def test_13_frontend_liquid_glass_bundle_built(self):
        """Verify compiled React/Tailwind/Framer-Motion Liquid Glass UI bundle & shaders exist."""
        dist_dir = os.path.join(PROJECT_ROOT, "frontend", "dist")
        index_html = os.path.join(dist_dir, "index.html")
        self.assertTrue(os.path.exists(index_html), "frontend/dist/index.html missing — run npm run build")
        assets = os.path.join(dist_dir, "assets")
        css_files = [f for f in os.listdir(assets) if f.endswith(".css")]
        js_files = [f for f in os.listdir(assets) if f.endswith(".js")]
        self.assertGreaterEqual(len(css_files), 1)
        self.assertGreaterEqual(len(js_files), 1)
        with open(os.path.join(assets, css_files[0]), encoding="utf-8") as cf:
            css_text = cf.read()
        self.assertIn("backdrop-filter", css_text)

    def test_14_fastapi_bootstrap_and_theme_api(self):
        """Verify FastAPI /api/bootstrap and live /api/settings theme persistence without PyQt6."""
        from fastapi.testclient import TestClient
        from src.server.app import create_app
        from src.constants import THEMES, get_current_theme_name, set_theme
        from src.utils.helpers import save_user_settings

        orig_theme = get_current_theme_name()
        client = TestClient(create_app())
        try:
            resp = client.get("/api/bootstrap")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("themes", data)
            self.assertEqual(set(data["themes"].keys()), set(THEMES.keys()))
            self.assertIn("gpus", data)
            self.assertIn("tools", data)

            up = client.post("/api/settings", json={"settings": {"theme": "Purple (Cyberpunk)"}})
            self.assertEqual(up.status_code, 200)
            self.assertEqual(up.json()["current_theme"], "Purple (Cyberpunk)")
        finally:
            set_theme(orig_theme)
            save_user_settings({"theme": orig_theme})

    def test_15_fastapi_probe_preview_and_stitch_estimate(self):
        """Verify /api/probe metadata extraction, /api/preview WebP rendering, and /api/stitch-estimate."""
        import io
        from fastapi.testclient import TestClient
        from src.server.app import create_app

        client = TestClient(create_app())
        probe = client.post("/api/probe", json={"paths": [self.test_img1, self.test_pdf]}).json()
        self.assertEqual(len(probe["files"]), 2)
        self.assertEqual(probe["files"][0]["dims"], "64×64")

        prev = client.get("/api/preview", params={"path": self.test_img1, "max_size": 128})
        self.assertEqual(prev.status_code, 200)
        self.assertEqual(prev.headers["content-type"], "image/webp")
        with Image.open(io.BytesIO(prev.content)) as im:
            self.assertEqual(im.size, (64, 64))

        est = client.post("/api/stitch-estimate", json={
            "groups": [{"id": "virtual:g1", "files": [self.test_img1, self.test_img2]}],
            "layout_mode": "Vertical (Top to Bottom)",
            "outer_padding": 10,
            "spacing": 0,
            "output_format": "PNG",
        }).json()
        self.assertIn("84×132", est["estimates"][0]["estimate"])

    def test_16_exif_orient_and_transparent_jpg(self):
        """Verify transparent RGBA -> JPEG composites on white (not black) and EXIF orientation is transposed."""
        trans_png = os.path.join(self.temp_dir, "trans_alpha.png")
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        img.save(trans_png, "PNG")

        out_dir = os.path.join(self.temp_dir, "conv_white_bg")
        t = ConverterThread([trans_png], out_dir, "jpg", {"preserve_exif": True})
        t.run()
        out_jpg = os.path.join(out_dir, "trans_alpha.jpg")
        self.assertTrue(os.path.exists(out_jpg))
        with Image.open(out_jpg) as res:
            r, g, b = res.getpixel((16, 16))
            self.assertGreater(r, 240)
            self.assertGreater(g, 240)
            self.assertGreater(b, 240)

        # EXIF orientation tag 6 (Rotate 90 CW) on 40x20 -> becomes 20x40 after transpose
        exif_src = os.path.join(self.temp_dir, "exif_rot.jpg")
        rot_img = Image.new("RGB", (40, 20), (10, 20, 30))
        exif = rot_img.getexif()
        exif[0x0112] = 6
        rot_img.save(exif_src, "JPEG", exif=exif)
        t2 = ConverterThread([exif_src], out_dir, "png", {"preserve_exif": True})
        t2.run()
        out_rot = os.path.join(out_dir, "exif_rot.png")
        with Image.open(out_rot) as res:
            self.assertEqual(res.size, (20, 40))

    def test_17_psd_hidden_group_layers(self):
        """Verify _iter_visible_psd_layers skips visible children inside hidden parent groups."""
        from src.core.converter_thread import _iter_visible_psd_layers

        class FakeLayer:
            def __init__(self, name, visible, is_grp=False, children=None):
                self.name = name
                self._visible = visible
                self._is_grp = is_grp
                self._children = children or []
                self.width = 10
                self.height = 10
            def is_visible(self): return self._visible
            def is_group(self): return self._is_grp
            def __iter__(self): return iter(self._children)

        tree = [
            FakeLayer("VisibleLayer", True),
            FakeLayer("HiddenGroup", False, is_grp=True, children=[FakeLayer("ChildOfHidden", True)]),
            FakeLayer("VisibleGroup", True, is_grp=True, children=[FakeLayer("ChildOfVisible", True)]),
        ]
        names = [l.name for l in _iter_visible_psd_layers(tree)]
        self.assertEqual(names, ["VisibleLayer", "ChildOfVisible"])

    def test_18_stitcher_alpha_and_negative_spacing(self):
        """Verify Stitcher preserves white background behind transparent PNGs and clamps negative spacing."""
        trans1 = os.path.join(self.temp_dir, "st_t1.png")
        Image.new("RGBA", (30, 30), (0, 0, 0, 0)).save(trans1, "PNG")
        out_dir = os.path.join(self.temp_dir, "stitch_alpha")
        t = StitcherThread(
            ["virtual:AlphaTest"], out_dir, True, -50, "png",
            virtual_files={"virtual:AlphaTest": [trans1, self.test_img1]},
            bg_color="White"
        )
        t.run()
        out_file = os.path.join(out_dir, "AlphaTest_stitched.png")
        self.assertTrue(os.path.exists(out_file))
        with Image.open(out_file) as im:
            self.assertGreaterEqual(im.width, 1)
            self.assertGreaterEqual(im.height, 1)

    def test_19_signals_and_worker_thread_isolation(self):
        """Verify pure-Python Signal descriptors keep slot lists isolated per WorkerThread instance."""
        from src.core.signals import Signal, WorkerThread

        class DummyWorker(WorkerThread):
            ping = Signal(str)

        a = DummyWorker()
        b = DummyWorker()
        res_a, res_b = [], []
        a.ping.connect(res_a.append)
        b.ping.connect(res_b.append)
        a.ping.emit("alpha")
        self.assertEqual(res_a, ["alpha"])
        self.assertEqual(res_b, [])

    def test_20_dynamic_gpus_and_converter_api_job(self):
        """Verify dynamic GPU discovery, FastAPI /api/jobs/start, and output verification."""
        from fastapi.testclient import TestClient
        from src.server.app import create_app
        from src.utils.helpers import get_gpu_combo_items, parse_gpu_id, normalize_ncnn_format

        self.assertEqual(parse_gpu_id("GPU 0: AMD Radeon RX 6600"), "0")
        self.assertEqual(parse_gpu_id("CPU (-1)"), "-1")
        self.assertEqual(parse_gpu_id("Auto (GPU)"), "auto")
        self.assertEqual(normalize_ncnn_format("jpeg"), "jpg")
        items = get_gpu_combo_items()
        self.assertIn("Auto (GPU)", items)
        self.assertIn("CPU (-1)", items)

        out_dir = os.path.join(self.temp_dir, "api_job_out")
        os.makedirs(out_dir, exist_ok=True)
        client = TestClient(create_app())
        start_resp = client.post("/api/jobs/start", json={
            "workspace": "converter",
            "payload": {
                "files": [self.test_img1],
                "output_dir": out_dir,
                "output_format": "webp",
                "settings": {"webp_quality_num": 85},
                "enable_upscale": False,
            },
        })
        self.assertEqual(start_resp.status_code, 200)
        import time
        expected = os.path.join(out_dir, "test_sample1.webp")
        for _ in range(30):
            if os.path.exists(expected):
                break
            time.sleep(0.1)
        self.assertTrue(os.path.exists(expected), "FastAPI /api/jobs/start did not output WEBP file")

    def test_21_desktop_bridge_and_about_repo_credits(self):
        """Verify DesktopBridge instantiation and About credits for GuptaAman777 without PyQt6."""
        from src.desktop.bridge import DesktopBridge

        bridge = DesktopBridge()
        self.assertIsNone(bridge._window)

        with open(
            os.path.join(PROJECT_ROOT, "frontend", "src", "components", "SettingsWorkspace.jsx"),
            encoding="utf-8",
        ) as af:
            about_src = af.read()
        self.assertIn("Made by GuptaAman777", about_src)
        self.assertIn("GuptaAman777/psd-converter", about_src)
        self.assertIn("Real-ESRGAN", about_src)
        self.assertNotIn("alvanheim", about_src.lower())

    def test_22_converter_advanced_options(self):
        """Verify PDF page range, hex alpha matte, naming affixes, conflict policies, mirror folders, and Match Width."""
        from src.utils.helpers import parse_page_range, parse_color_spec

        self.assertEqual(parse_page_range("2", 5), [1])
        self.assertEqual(parse_page_range("1-2, 4", 5), [0, 1, 3])
        self.assertEqual(parse_color_spec("#112233"), (17, 34, 51))

        # PDF single range extraction ("2") -> only page_002
        pdf_out = os.path.join(self.temp_dir, "adv_pdf_range")
        t_pdf = ConverterThread([self.test_pdf], pdf_out, "png", {
            'pdf_extract_all': True, 'pdf_page_range': '2', 'pdf_dpi': '72 DPI', 'pdf_quality': 'Low'
        })
        t_pdf.run()
        self.assertFalse(os.path.exists(os.path.join(pdf_out, "test_doc", "page_001.png")))
        self.assertTrue(os.path.exists(os.path.join(pdf_out, "test_doc", "page_002.png")))

        # Transparent PNG -> JPEG with custom hex matte (#112233), prefix/suffix, and Match Width
        trans = os.path.join(self.temp_dir, "matte_src.png")
        Image.new("RGBA", (40, 20), (0, 0, 0, 0)).save(trans, "PNG")
        sub_in = os.path.join(self.temp_dir, "nested_src", "chapterA")
        os.makedirs(sub_in, exist_ok=True)
        nested_file = os.path.join(sub_in, "page.png")
        Image.new("RGBA", (40, 20), (0, 0, 0, 0)).save(nested_file, "PNG")

        out_dir = os.path.join(self.temp_dir, "adv_conv_out")
        t = ConverterThread([trans, nested_file], out_dir, "jpg", {
            'alpha_bg_color': '#112233',
            'filename_prefix': 'pre_',
            'filename_suffix': '_suf',
            'resize_preset': 'Match Width (Auto H)',
            'custom_max_width': 20,
            'resample_filter': 'nearest',
            'mirror_folders': True,
        })
        t.run()
        out_nested = os.path.join(out_dir, "chapterA", "pre_page_suf.jpg")
        # Common root is self.temp_dir vs nested_src/chapterA -> verify mirrored tail exists
        found = []
        for r, _, fs in os.walk(out_dir):
            for fn in fs:
                if fn.startswith("pre_matte_src_suf"):
                    found.append(os.path.join(r, fn))
        self.assertEqual(len(found), 1)
        with Image.open(found[0]) as res:
            self.assertEqual(res.size, (20, 10))
            r, g, b = res.getpixel((5, 5))
            self.assertLess(abs(r - 17), 5)
            self.assertLess(abs(g - 34), 5)
            self.assertLess(abs(b - 51), 5)

        # Conflict policy: skip vs rename
        flat_out = os.path.join(self.temp_dir, "conflict_out")
        t_first = ConverterThread([trans], flat_out, "png", {})
        t_first.run()
        t_skip = ConverterThread([trans], flat_out, "png", {'conflict_policy': 'skip'})
        t_skip.run()
        self.assertEqual(t_skip.skipped_count, 1)

        t_ren = ConverterThread([trans], flat_out, "png", {'conflict_policy': 'rename'})
        t_ren.run()
        self.assertTrue(os.path.exists(os.path.join(flat_out, "matte_src_1.png")))

    def test_23_upscaler_ssaa_syncgap_and_denoiser_blend(self):
        """Verify Upscaler SSAA post-resize, SyncGap (-c), custom suffix/rename, and Denoiser grain blend."""
        out_up = os.path.join(self.temp_dir, "ssaa_up_out")
        t_up = UpscalerThread(
            [self.test_img1], out_up, upscale_factor="2x", model="realcugan",
            style_model="models-se", noise_level=0, custom_suffix="_ssaa",
            syncgap_mode=2, thread_spec="1:2:2", post_resize_mode="50% SSAA", conflict_policy="rename"
        )
        t_up.run()
        first_up = os.path.join(out_up, "test_sample1_ssaa.png")
        self.assertTrue(os.path.exists(first_up))
        with Image.open(first_up) as im:
            # 64x64 * 2x * 50% SSAA = 64x64 crisp downsampled result
            self.assertEqual(im.size, (64, 64))

        t_up2 = UpscalerThread(
            [self.test_img1], out_up, upscale_factor="2x", model="realcugan",
            style_model="models-se", noise_level=0, custom_suffix="_ssaa",
            post_resize_mode="50% SSAA", conflict_policy="rename"
        )
        t_up2.run()
        self.assertTrue(os.path.exists(os.path.join(out_up, "test_sample1_ssaa_1.png")))

        out_dn = os.path.join(self.temp_dir, "blend_dn_out")
        t_dn = DenoiserThread(
            [self.test_img1], out_dn, noise_level=1, model="anime", engine="waifu2x",
            custom_suffix="_blend50", blend_pct=50, thread_spec="1:2:2", conflict_policy="skip"
        )
        t_dn.run()
        dn_path = os.path.join(out_dn, "test_sample1_blend50.png")
        self.assertTrue(os.path.exists(dn_path))
        with Image.open(dn_path) as im:
            self.assertEqual(im.size, (64, 64))

    def test_24_stitcher_padding_matte_and_sort(self):
        """Verify Stitcher outer_padding, custom hex matte, and sort_mode."""
        out_dir = os.path.join(self.temp_dir, "stitch_pad_out")
        t = StitcherThread(
            ["virtual:pad_test"], out_dir, is_vertical=True, spacing=0, output_format="png",
            virtual_files={"virtual:pad_test": [self.test_img1, self.test_img2]},
            bg_color="#FF0080", outer_padding=10, sort_mode="alpha"
        )
        t.run()
        out_file = os.path.join(out_dir, "pad_test_stitched.png")
        self.assertTrue(os.path.exists(out_file))
        with Image.open(out_file) as im:
            # 64px wide + 20px outer padding = 84px; 64+48 height + 20px outer padding = 132px
            self.assertEqual(im.size, (84, 132))
            px = im.getpixel((2, 2))
            self.assertEqual(px[:3], (255, 0, 128))

    def test_25_scan_folders_and_stitch_groups_api(self):
        """Verify /api/scan-folders returns flat files and Stitcher grouped subfolders cleanly."""
        from fastapi.testclient import TestClient
        from src.server.app import create_app

        scan_root = os.path.join(self.temp_dir, "scan_tree")
        ch1 = os.path.join(scan_root, "ch01")
        ch2 = os.path.join(scan_root, "ch02")
        os.makedirs(ch1, exist_ok=True)
        os.makedirs(ch2, exist_ok=True)
        Image.new("RGB", (30, 40), (1, 2, 3)).save(os.path.join(ch1, "p1.png"))
        Image.new("RGB", (30, 40), (4, 5, 6)).save(os.path.join(ch2, "p1.png"))

        client = TestClient(create_app())
        flat = client.post("/api/scan-folders", json={"folder": scan_root, "stitcher_mode": False}).json()
        self.assertEqual(len(flat["files"]), 2)

        grp_res = client.post("/api/scan-folders", json={"folder": scan_root, "stitcher_mode": True}).json()
        self.assertEqual(len(grp_res["groups"]), 2)

    def test_26_spa_serving_logs_and_version_compare(self):
        """Verify SPA HTML index serving, activity log API, and semantic update version compare."""
        from fastapi.testclient import TestClient
        from src.server.app import create_app
        from src.utils.updater import compare_versions

        self.assertEqual(compare_versions("7.5", "7.0"), 1)
        self.assertEqual(compare_versions("7.0", "6.0"), 1)
        self.assertEqual(compare_versions("6.5", "7.0"), -1)

        client = TestClient(create_app())
        home = client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("ImageTool — PSD & AI Image Suite", home.text)

        logs_resp = client.get("/api/logs")
        self.assertEqual(logs_resp.status_code, 200)
        self.assertIn("logs", logs_resp.json())

    def test_27_exif_bmp_and_cpu_fallback_hardening(self):
        """Verify Upscaler/Denoiser stage EXIF-rotated JPEGs, BMPs, and safe CPU fallback."""
        out_dir = os.path.join(self.temp_dir, "hardened_out")
        os.makedirs(out_dir, exist_ok=True)

        rot_jpg = os.path.join(self.temp_dir, "rotated.jpg")
        raw = Image.new("RGB", (60, 30), (15, 110, 215))
        ex = raw.getexif()
        ex[0x0112] = 6  # Rotate 90 CW -> visual dims 30x60
        raw.save(rot_jpg, "JPEG", exif=ex)

        bmp_in = os.path.join(self.temp_dir, "bitmap.bmp")
        Image.new("RGB", (32, 24), (20, 180, 90)).save(bmp_in, "BMP")

        # Upscale rotated JPG + BMP with gpu_id='-1' (tests graceful GPU fallback on esr/upscayl-bin)
        ut = UpscalerThread(
            [rot_jpg, bmp_in], out_dir,
            upscale_factor="2x", model="realesr", style_model="realesr-animevideov3",
            keep_format=True, gpu_id="-1"
        )
        ut.run()

        out_jpg = os.path.join(out_dir, "rotated_upscaled2x.jpg")
        out_bmp = os.path.join(out_dir, "bitmap_upscaled2x.bmp")
        self.assertTrue(os.path.exists(out_jpg))
        self.assertTrue(os.path.exists(out_bmp))
        with Image.open(out_jpg) as im:
            self.assertEqual(im.size, (60, 120))  # 30x60 oriented * 2x
            self.assertEqual(im.getexif().get(0x0112, 1), 1)
        with Image.open(out_bmp) as bm:
            self.assertEqual(bm.format, "BMP")
            self.assertEqual(bm.size, (64, 48))

    def test_28_waifu2x_2025_8x_and_upscayl_8x(self):
        """Verify Waifu2x 20250915 native 8x and Upscayl/ESR 8x two-pass scaling."""
        out_dir = os.path.join(self.temp_dir, "scale8x_out")
        os.makedirs(out_dir, exist_ok=True)
        tiny = os.path.join(self.temp_dir, "tiny32.png")
        Image.new("RGB", (32, 32), (100, 120, 220)).save(tiny)

        u_waifu = UpscalerThread(
            [tiny], out_dir, upscale_factor="8x", model="waifu2x",
            style_model="models-cunet", noise_level=0, custom_suffix="_w8x"
        )
        u_waifu.run()
        with Image.open(os.path.join(out_dir, "tiny32_w8x.png")) as im:
            self.assertEqual(im.size, (256, 256))

        u_esr = UpscalerThread(
            [tiny], out_dir, upscale_factor="8x", model="realesr",
            style_model="realesr-animevideov3", custom_suffix="_e8x"
        )
        u_esr.run()
        with Image.open(os.path.join(out_dir, "tiny32_e8x.png")) as im:
            self.assertEqual(im.size, (256, 256))

    def test_29_model_catalog_download_upscale_and_remove(self):
        """Verify downloadable model catalog API, live download, real upscale, and cleanup."""
        from fastapi.testclient import TestClient
        from src.server.app import create_app
        from src.core.model_catalog import download_model_pack, is_model_installed

        client = TestClient(create_app())
        cat_resp = client.get("/api/models/catalog")
        self.assertEqual(cat_resp.status_code, 200)
        models = cat_resp.json()["models"]
        self.assertGreaterEqual(len(models), 10)
        self.assertTrue(any(m["id"] == "ultrasharp-4x" for m in models))

        was_installed = is_model_installed("4xLSDIRCompactC3")
        info = download_model_pack("4xLSDIRCompactC3")
        self.assertTrue(info["installed"])

        out_dir = os.path.join(self.temp_dir, "dl_model_out")
        os.makedirs(out_dir, exist_ok=True)
        tiny = os.path.join(self.temp_dir, "dl_src.png")
        Image.new("RGB", (32, 32), (50, 200, 140)).save(tiny)
        ut = UpscalerThread(
            [tiny], out_dir, upscale_factor="4x", model="realesr", style_model="4xLSDIRCompactC3"
        )
        ut.run()
        with Image.open(os.path.join(out_dir, "dl_src_upscaled4x.png")) as im:
            self.assertEqual(im.size, (128, 128))

        if not was_installed:
            del_resp = client.delete("/api/models/4xLSDIRCompactC3")
            self.assertEqual(del_resp.status_code, 200)
            self.assertFalse(is_model_installed("4xLSDIRCompactC3"))

    def test_30_janai_ncnn_catalog_and_inference(self):
        """Verify all 22 JaNai NCNN models, GitHub v1.0.0 release download, Vulkan inference, and cleanup."""
        from fastapi.testclient import TestClient
        from src.core.janai_catalog import JANAI_MODEL_CATALOG, resolve_janai_model_paths
        from src.core.janai_thread import JanaiUpscalerThread
        from src.core.model_catalog import download_model_pack, is_model_installed
        from src.server.app import create_app

        self.assertEqual(len(JANAI_MODEL_CATALOG), 22)
        self.assertFalse(os.path.exists("ncnn"))

        client = TestClient(create_app())
        boot = client.get("/api/bootstrap").json()
        self.assertTrue(boot["tools"].get("janai_ncnn"))

        janai_items = [m for m in boot["model_catalog"] if m.get("engine") == "janai_ncnn"]
        self.assertEqual(len(janai_items), 22)
        for item in janai_items:
            self.assertEqual(
                item["param_url"],
                f"https://github.com/GuptaAman777/mangajanai-illustrationjanai-ncnn-vulkan/releases/download/v1.0.0/{item['id']}.ncnn.param",
            )
            self.assertEqual(
                item["bin_url"],
                f"https://github.com/GuptaAman777/mangajanai-illustrationjanai-ncnn-vulkan/releases/download/v1.0.0/{item['id']}.ncnn.bin",
            )

        target_id = "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16"
        was_installed = is_model_installed(target_id)
        try:
            info = download_model_pack(target_id)
            self.assertTrue(info["installed"])
            resolved = resolve_janai_model_paths(target_id)
            self.assertTrue(resolved["installed"])
            self.assertEqual(resolved["source"], "downloaded")

            out_dir = os.path.join(self.temp_dir, "janai_out")
            os.makedirs(out_dir, exist_ok=True)

            # Odd-sized transparent PNG -> tests alpha preservation + tiled overlap path
            src_rgba = os.path.join(self.temp_dir, "sprite_odd.png")
            Image.new("RGBA", (75, 73), (40, 140, 220, 180)).save(src_rgba)

            jt_span = JanaiUpscalerThread(
                [src_rgba],
                out_dir,
                model_id=target_id,
                tile_size=64,
                use_fp16=True,
            )
            jt_span.run()
            self.assertEqual(jt_span.success_count, 1)
            out_span = os.path.join(out_dir, "sprite_odd_janai2x.png")
            self.assertTrue(os.path.exists(out_span))
            with Image.open(out_span) as res:
                self.assertEqual(res.size, (75 * 2, 73 * 2))
                self.assertEqual(res.mode, "RGBA")
        finally:
            if not was_installed and is_model_installed(target_id):
                del_resp = client.delete(f"/api/models/{target_id}")
                self.assertEqual(del_resp.status_code, 200)
                self.assertFalse(is_model_installed(target_id))

    def test_31_janai_autodetect_and_custom_workflows(self):
        """Verify MangaJaNai Auto Detect (B&W height tiers vs Color), /api/janai/analyze, and chained custom workflows."""
        from fastapi.testclient import TestClient
        from src.core.janai_router import nearest_manga_tier, select_janai_route
        from src.core.janai_thread import JanaiUpscalerThread
        from src.core.model_catalog import download_model_pack, is_model_installed, remove_model_pack
        from src.server.app import create_app

        self.assertEqual(nearest_manga_tier(1180), 1200)
        self.assertEqual(nearest_manga_tier(1420), 1400)
        self.assertEqual(nearest_manga_tier(1890), 1920)
        self.assertEqual(nearest_manga_tier(2100), 2048)

        bw_scan = os.path.join(self.temp_dir, "bw_manga_page.jpg")
        Image.new("RGB", (48, 64), (180, 180, 180)).save(bw_scan, "JPEG")

        color_art = os.path.join(self.temp_dir, "color_cover.png")
        Image.new("RGB", (40, 40), (220, 40, 110)).save(color_art, "PNG")

        color_jpg = os.path.join(self.temp_dir, "color_scan.jpg")
        Image.new("RGB", (40, 40), (40, 200, 130)).save(color_jpg, "JPEG")

        r_bw = select_janai_route(bw_scan, mode="auto", auto_config={"scale": "2x"})
        self.assertTrue(r_bw["analysis"]["is_grayscale"])
        self.assertEqual(r_bw["model_id"], "2x_MangaJaNai_1200p_V1_ESRGAN_70k_fp16")

        r_bw_4x = select_janai_route(bw_scan, mode="auto", auto_config={"scale": "4x"})
        self.assertEqual(r_bw_4x["model_id"], "4x_MangaJaNai_1200p_V1_ESRGAN_70k_fp16")

        r_color_png = select_janai_route(color_art, mode="auto", auto_config={"scale": "2x", "color_tier": "span"})
        self.assertFalse(r_color_png["analysis"]["is_grayscale"])
        self.assertEqual(r_color_png["model_id"], "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16")

        r_color_jpg = select_janai_route(color_jpg, mode="auto", auto_config={"scale": "2x", "color_tier": "span"})
        self.assertEqual(r_color_jpg["model_id"], "2x_IllustrationJaNai_V3denoise_SPAN_S_30k_fp16")

        r_color_xl = select_janai_route(color_art, mode="auto", auto_config={"scale": "2x", "color_tier": "fdat_xl"})
        self.assertEqual(r_color_xl["model_id"], "4x_IllustrationJaNai_V3detail_FDAT_XL_27k_fp16")
        self.assertEqual(r_color_xl["scale"], 4)

        client = TestClient(create_app())
        boot = client.get("/api/bootstrap").json()
        self.assertGreaterEqual(len(boot.get("builtin_janai_workflows", [])), 5)

        resp = client.post("/api/janai/analyze", json={
            "paths": [bw_scan, color_art],
            "mode": "auto",
            "auto_config": {"scale": "4x", "color_tier": "fdat_m"},
        })
        self.assertEqual(resp.status_code, 200)
        routes = resp.json()["routes"]
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0]["model_id"], "4x_MangaJaNai_1200p_V1_ESRGAN_70k_fp16")
        self.assertEqual(routes[1]["model_id"], "4x_IllustrationJaNai_V3detail_FDAT_M_40k_fp16")

        # Download the two compact SPAN models live and run a chained 2x -> 2x = 4x workflow
        span_denoise = "2x_IllustrationJaNai_V3denoise_SPAN_S_30k_fp16"
        span_detail = "2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16"
        pre_installed = {m: is_model_installed(m) for m in (span_denoise, span_detail)}
        try:
            for mid in (span_denoise, span_detail):
                if not pre_installed[mid]:
                    download_model_pack(mid)

            chain_out = os.path.join(self.temp_dir, "janai_chain_out")
            os.makedirs(chain_out, exist_ok=True)
            jt_chain = JanaiUpscalerThread(
                [color_art],
                chain_out,
                mode="workflow",
                workflow={
                    "grayscale_strategy": "auto_tier",
                    "grayscale_scale": "2x",
                    "color_model_id": span_denoise,
                    "color_auto_denoise": False,
                    "color_chain_id": span_detail,
                },
            )
            jt_chain.run()
            self.assertEqual(jt_chain.success_count, 1)
            out_chained = os.path.join(chain_out, "color_cover_janai4x.png")
            self.assertTrue(os.path.exists(out_chained))
            with Image.open(out_chained) as ch_im:
                self.assertEqual(ch_im.size, (160, 160))
        finally:
            for mid, was in pre_installed.items():
                if not was and is_model_installed(mid):
                    remove_model_pack(mid)

    def test_32_eta_tracker_fractional_smoothing(self):
        """Verify EtaTracker computes damped fractional ETA without oscillating between tiles."""
        import time
        from src.utils.helpers import EtaTracker

        tracker = EtaTracker(total_items=10, start_time=0.0)
        tracker.start_time = time.monotonic() - 2.0
        tracker.last_sample_time = tracker.start_time
        eta1, spd1 = tracker.update(1.5)
        self.assertTrue(eta1.startswith("ETA:"))
        self.assertNotIn("Calculating", eta1)
        self.assertIn("Speed:", spd1)
        v1 = tracker.last_eta_value

        # Simulate sub-tile advancement inside the same file — ETA should decrease smoothly, not double upward
        tracker.last_ui_time = time.monotonic() - 0.5
        eta2, _ = tracker.update(2.0)
        self.assertTrue(eta2.startswith("ETA:"))
        self.assertLess(tracker.last_eta_value, v1)

        eta_done, _ = tracker.update(10.0)
        self.assertEqual(eta_done, "ETA: Finishing...")

    def test_33_check_paths_and_preview_nostore(self):
        """Verify /api/check-paths detects deleted compare files and /api/preview sets Cache-Control: no-store."""
        from fastapi.testclient import TestClient
        from src.server.app import create_app

        existing_img = os.path.join(self.temp_dir, "keep_me.png")
        deleted_img = os.path.join(self.temp_dir, "deleted_me.png")
        Image.new("RGB", (24, 24), (30, 120, 220)).save(existing_img)

        client = TestClient(create_app())
        chk = client.post("/api/check-paths", json={"paths": [existing_img, deleted_img]})
        self.assertEqual(chk.status_code, 200)
        exists_map = chk.json()["exists"]
        self.assertTrue(exists_map[existing_img])
        self.assertFalse(exists_map[deleted_img])

        prev = client.get("/api/preview", params={"path": existing_img, "max_size": 120, "v": "123"})
        self.assertEqual(prev.status_code, 200)
        self.assertIn("no-store", prev.headers.get("cache-control", "").lower())

if __name__ == "__main__":
    unittest.main()
