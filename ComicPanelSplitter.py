"""
Split a borderless (webtoon-style) comic strip into individual panels by
detecting fully-white horizontal gutter bands between panels.

Usage:
    from comic_panel_splitter import ComicPanelSplitter

    splitter = ComicPanelSplitter(min_gutter_height=40)
    paths = splitter.save_panels("chapters/7.jpg", output_dir="panels")
"""

import os
from PIL import Image
import numpy as np


class ComicPanelSplitter:
    """
    Detects fully-white horizontal gutters in a comic strip image and
    splits the strip into individual panel crops.

    Config (set once, reused across images):
        white_threshold: pixel value (0-255) above which a pixel counts as "white".
        row_white_ratio: fraction of pixels in a row that must be white for
                         the row to count as part of a gutter. Default 1.0
                         means the ENTIRE row must be white — strict, so
                         speech bubbles/art touching a row disqualifies it.
        min_gutter_height: minimum consecutive white rows to count as a real
                            gutter (filters out thin white-line noise).
        min_panel_height: minimum height (px) for a cropped region to be
                           kept as a panel (filters out tiny slivers).
    """

    def __init__(
        self,
        white_threshold=250,
        row_white_ratio=1.0,
        min_gutter_height=40,
        min_panel_height=30,
    ):
        self.white_threshold = white_threshold
        self.row_white_ratio = row_white_ratio
        self.min_gutter_height = min_gutter_height
        self.min_panel_height = min_panel_height

    def find_horizontal_gutters(self, image_path):
        """
        Detect horizontal white gutter bands in an image.

        Returns:
            img: the loaded PIL Image (RGB)
            gutters: list of (start_row, end_row) tuples for each gutter band
        """
        img = Image.open(image_path).convert("RGB")
        gray = np.array(img.convert("L"))  # shape (H, W)
        height, width = gray.shape

        # For each row, what fraction of pixels are "white"?
        is_white_pixel = gray >= self.white_threshold
        white_fraction_per_row = is_white_pixel.mean(axis=1)

        # Rows that are (almost) entirely white
        is_white_row = white_fraction_per_row >= self.row_white_ratio

        # Group consecutive white rows into bands
        gutters = []
        start = None
        for y, white in enumerate(is_white_row):
            if white and start is None:
                start = y
            elif not white and start is not None:
                end = y - 1
                if (end - start + 1) >= self.min_gutter_height:
                    gutters.append((start, end))
                start = None
        # handle a gutter that runs to the bottom edge
        if start is not None:
            end = height - 1
            if (end - start + 1) >= self.min_gutter_height:
                gutters.append((start, end))

        return img, gutters

    def split_panels(self, image_path):
        """
        Split a comic strip into panel images using detected horizontal gutters.

        Returns:
            list of PIL Image crops, one per panel (top to bottom).
        """
        img, gutters = self.find_horizontal_gutters(image_path)
        height, width = img.size[1], img.size[0]

        # Build panel boundaries from the gaps between gutters
        boundaries = [0]
        for start, end in gutters:
            mid = (start + end) // 2
            boundaries.append(mid)
        boundaries.append(height)

        panels = []
        for i in range(len(boundaries) - 1):
            top, bottom = boundaries[i], boundaries[i + 1]
            if (bottom - top) >= self.min_panel_height:
                panels.append(img.crop((0, top, width, bottom)))

        return panels

    def save_panels(self, image_path, output_dir="panels", prefix="panel"):
        """
        Detect panels in a comic strip and save each one as a separate image file.

        Returns:
            list of file paths written, in top-to-bottom order.
        """
        os.makedirs(output_dir, exist_ok=True)

        panels = self.split_panels(image_path)

        saved_paths = []
        for idx, panel in enumerate(panels, start=1):
            out_path = os.path.join(output_dir, f"{prefix}_{idx:02d}.png")
            panel.save(out_path)
            saved_paths.append(out_path)
            print(f"Saved {out_path} ({panel.size[0]}x{panel.size[1]})")

        return saved_paths


if __name__ == "__main__":
    # Example usage
    splitter = ComicPanelSplitter()
    splitter.save_panels("chapters/7.jpg", output_dir="panels")