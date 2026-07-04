import importlib.util
import pathlib
import unittest
from importlib.machinery import SourceFileLoader

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "main,py"
LOADER = SourceFileLoader("main_orchestrator", str(MODULE_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
module = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(module)


class PipelineTests(unittest.TestCase):
    def test_build_chapter_url_slugifies_series_name(self):
        self.assertEqual(
            module.build_chapter_url("Reborn Rich"),
            "https://demonicscans.org/title/reborn-rich/chapter/",
        )

    def test_resolve_chapter_dir_uses_series_and_chapter(self):
        self.assertEqual(
            module.resolve_chapter_dir("downloads", "Reborn Rich", "1"),
            pathlib.Path("downloads/Reborn Rich/chapter_1"),
        )

    def test_build_chapter_layout_creates_expected_subfolders(self):
        layout = module.build_chapter_layout("downloads", "Reborn Rich", "1")
        self.assertEqual(
            layout["raw_images_dir"],
            pathlib.Path("downloads/Reborn Rich/chapter_1/raw_images"),
        )
        self.assertEqual(
            layout["split_panels_dir"],
            pathlib.Path("downloads/Reborn Rich/chapter_1/split_panels"),
        )
        self.assertEqual(
            layout["text_dir"],
            pathlib.Path("downloads/Reborn Rich/chapter_1/text"),
        )
        self.assertEqual(
            layout["mp4_dir"],
            pathlib.Path("downloads/Reborn Rich/chapter_1/mp4"),
        )


if __name__ == "__main__":
    unittest.main()
