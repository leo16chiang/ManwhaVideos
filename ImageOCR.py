import easyocr

class ImageOCR:
    def __init__(self, languages=None):
        self.reader = easyocr.Reader(languages or ["en"])

    def extract_text(self, image_path: str) -> str:
        results = self.reader.readtext(image_path, detail=0)
        return "\n".join(results)