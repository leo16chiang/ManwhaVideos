"""
CHAPTER_URL = "https://demonicscans.org/title/Reborn-Rich/chapter/"

async def main():
    downloader = DemonicScansDownloader(
        CHAPTER_URL,
        max_concurrent=10,
    )

    await downloader.download(1, 210)

asyncio.run(main())

"""


import asyncio
import os
import re
from urllib.parse import unquote, urljoin

import aiohttp
from bs4 import BeautifulSoup


class DemonicScansDownloader:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/144.0.0.0 Safari/537.36"
        ),
        "Referer": "https://demonicscans.org/",
    }

    PANEL_PATTERN = re.compile(r"/(\d+)\.(jpg|webp)$", re.IGNORECASE)

    def __init__(
        self,
        base_chapter_url: str,
        download_root: str = "downloads",
        max_concurrent: int = 10,
        max_empty_chapters: int = 3,
        timeout: int = 30,
        output_dir=None,
    ):
        self.base_chapter_url = base_chapter_url
        self.max_concurrent = max_concurrent
        self.max_empty_chapters = max_empty_chapters
        self.output_dir = output_dir

        if output_dir:
            self.comic_dir = output_dir
            os.makedirs(self.comic_dir, exist_ok=True)
        else:
            comic_name = unquote(unquote(base_chapter_url.split("/")[4]))
            self.comic_dir = os.path.join(download_root, comic_name)
            os.makedirs(self.comic_dir, exist_ok=True)

        self.connector = None
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def download(self, chapter_start: int, chapter_end: int):
        empty_count = 0

        async with aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
            headers=self.HEADERS,
        ) as session:

            for chapter in range(chapter_start, chapter_end + 1):
                print(f"Fetching chapter {chapter}...")

                image_urls = await self._fetch_chapter_images(session, chapter)

                if image_urls is None:
                    print("Stopping.")
                    break

                if not image_urls:
                    empty_count += 1
                    print(f"Chapter {chapter}: No images found.")

                    if empty_count >= self.max_empty_chapters:
                        print("Multiple empty chapters detected. Stopping.")
                        break

                    continue

                empty_count = 0

                chapter_dir = self.output_dir or os.path.join(
                    self.comic_dir,
                    f"chapter_{chapter}",
                )
                os.makedirs(chapter_dir, exist_ok=True)

                print(
                    f"Chapter {chapter}: Found {len(image_urls)} images."
                )

                await asyncio.gather(
                    *[
                        self._download_image(session, url, chapter_dir)
                        for url in image_urls
                    ],
                    return_exceptions=True,
                )

        print("All done.")

    async def _fetch_chapter_images(self, session, chapter):
        chapter_url = f"{self.base_chapter_url}{chapter}/1"

        try:
            async with session.get(chapter_url) as response:

                if response.status in (404, 410):
                    print(f"Chapter {chapter} not found.")
                    return None

                if response.status != 200:
                    print(
                        f"Chapter {chapter}: Unexpected status "
                        f"{response.status}"
                    )
                    return None

                html = await response.text()

        except asyncio.TimeoutError:
            print(f"Chapter {chapter}: Timeout.")
            return None

        except Exception as exc:
            print(f"Chapter {chapter}: {exc}")
            return None

        soup = BeautifulSoup(html, "html.parser")

        candidates = set()

        for img in soup.find_all("img"):
            for attr in (
                "src",
                "data-src",
                "data-lazy",
                "data-original",
            ):
                url = img.get(attr)

                if not url:
                    continue

                full_url = urljoin(chapter_url, url)

                if self.PANEL_PATTERN.search(full_url):
                    candidates.add(full_url)

        return sorted(candidates)

    async def _download_image(self, session, url, chapter_dir):
        match = self.PANEL_PATTERN.search(url)

        if not match:
            return

        page, ext = match.groups()

        out_path = os.path.join(
            chapter_dir,
            f"{int(page):03}.{ext}",
        )

        if os.path.exists(out_path):
            return

        try:
            async with session.get(url) as response:

                if response.status != 200:
                    return

                with open(out_path, "wb") as f:
                    f.write(await response.read())

        except Exception as exc:
            print(f"Failed to download {url}: {exc}")